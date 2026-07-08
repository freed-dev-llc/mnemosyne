"""Retrieval hit-rate scorer (fully offline — no Ollama, no network).

The scorer takes an injected ``retrieve`` callable, so every test here feeds canned
``Document``s instead of touching a live model or a built index.
"""

from __future__ import annotations

import dataclasses
import json
import re
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from langchain_core.documents import Document
from typer.testing import CliRunner

from mnemosyne.cli import app
from mnemosyne.config import Settings, get_settings
from mnemosyne.eval import (
    GATE_BELOW_FLOOR,
    GATE_OK,
    EvalQuestion,
    EvalReport,
    EvalResult,
    FaithfulnessReport,
    SweepConfig,
    SweepReport,
    SweepRow,
    _best_config,
    _index_key,
    expand_grid,
    faithfulness_score,
    format_sweep_table,
    gate_exit_code,
    load_questions,
    run_faithfulness_eval,
    run_retrieval_eval,
    run_sweep,
    score,
    score_faithfulness,
    score_sweep,
    serialize_retrieval_report,
)
from mnemosyne.packs.registry import get_pack


def _retrieve_from(*texts: str):
    """A fake ``retrieve`` that always returns the given chunks, ignoring the query."""

    def retrieve(question: str, k: int) -> list[Document]:
        return [Document(page_content=t) for t in texts]

    return retrieve


def test_score_counts_a_hit_when_all_expected_present() -> None:
    questions = [EvalQuestion(id="q", question="?", expected=["alpha", "beta"])]
    report = score(questions, _retrieve_from("alpha and beta together"), k=3)
    assert report.results[0].hit is True
    assert report.results[0].missing == []
    assert report.hits == 1


def test_score_reports_the_missing_strings_on_a_miss() -> None:
    questions = [EvalQuestion(id="q", question="?", expected=["alpha", "gamma"])]
    report = score(questions, _retrieve_from("only alpha here"), k=3)
    assert report.results[0].hit is False
    assert report.results[0].missing == ["gamma"]


def test_match_is_case_insensitive() -> None:
    questions = [EvalQuestion(id="q", question="?", expected=["VLAN"])]
    report = score(questions, _retrieve_from("the vlan is tagged"), k=3)
    assert report.results[0].hit is True


def test_match_spans_concatenated_top_k_chunks() -> None:
    # "alpha" is in chunk 1, "beta" in chunk 2 — the join makes it a hit.
    questions = [EvalQuestion(id="q", question="?", expected=["alpha", "beta"])]
    report = score(questions, _retrieve_from("alpha only", "beta only"), k=3)
    assert report.results[0].hit is True


def test_hit_rate_arithmetic() -> None:
    questions = [
        EvalQuestion(id="a", question="?", expected=["alpha"]),
        EvalQuestion(id="b", question="?", expected=["beta"]),
        EvalQuestion(id="c", question="?", expected=["missing"]),
    ]
    report = score(questions, _retrieve_from("alpha beta present"), k=3, pack="demo")
    assert report.total == 3
    assert report.hits == 2
    assert report.hit_rate == pytest.approx(2 / 3)
    assert report.pack == "demo"


def test_score_of_empty_question_set_is_zero_not_a_crash() -> None:
    report = score([], _retrieve_from("anything"), k=3)
    assert report.total == 0
    assert report.hit_rate == 0.0


def test_score_or_group_hits_on_any_alternative() -> None:
    # The item is a list of alternatives; retrieving *either* wording is a hit.
    questions = [
        EvalQuestion(id="q", question="?", expected=[["untagged network", "native (untagged)"]])
    ]
    a = score(questions, _retrieve_from("configured as the native (untagged) VLAN"), k=3)
    b = score(questions, _retrieve_from("this is the untagged network here"), k=3)
    assert a.results[0].hit is True
    assert b.results[0].hit is True


def test_score_or_group_misses_only_when_no_alternative_present() -> None:
    questions = [
        EvalQuestion(id="q", question="?", expected=[["untagged network", "native (untagged)"]])
    ]
    report = score(questions, _retrieve_from("only tagged VLANs discussed"), k=3)
    assert report.results[0].hit is False
    # the whole OR-group is reported as one missing item, alternatives joined
    assert report.results[0].missing == ["untagged network | native (untagged)"]


def test_score_mixes_plain_strings_and_or_groups() -> None:
    # A plain required substring AND an OR-group must both be satisfied.
    questions = [
        EvalQuestion(
            id="q", question="?", expected=["trunk", ["untagged network", "native (untagged)"]]
        )
    ]
    hit = score(questions, _retrieve_from("a trunk carries the native (untagged) VLAN"), k=3)
    miss = score(questions, _retrieve_from("a trunk carries tagged VLANs"), k=3)
    assert hit.results[0].hit is True
    assert miss.results[0].hit is False
    assert miss.results[0].missing == ["untagged network | native (untagged)"]


def _flatten_expected(question: EvalQuestion) -> list[str]:
    """Every alternative across a question's expected items (OR-groups flattened)."""
    out: list[str] = []
    for item in question.expected:
        out.extend([item] if isinstance(item, str) else item)
    return out


def test_run_retrieval_eval_uses_injected_retrieve_offline() -> None:
    # A retrieve that surfaces every expected string -> a perfect score, no Ollama needed.
    questions = load_questions("ubiquiti")
    every_expected = " ".join(s for q in questions for s in _flatten_expected(q))
    report = run_retrieval_eval("ubiquiti", k=5, retrieve=_retrieve_from(every_expected))
    assert report.pack == "ubiquiti"
    assert report.k == 5
    assert report.hit_rate == 1.0

    empty = run_retrieval_eval("ubiquiti", k=5, retrieve=lambda q, k: [])
    assert empty.hits == 0
    assert empty.hit_rate == 0.0


def test_load_questions_reads_the_shipped_ubiquiti_set() -> None:
    questions = load_questions("ubiquiti")
    # 10 seed questions + 9 primer questions (ADR-0014) + 9 VPN/DNS/QoS re-grow questions
    # (ADR-0020/ADR-0026); a range guards against a truncated load or accidental duplication
    # without going stale on every new question.
    assert 19 <= len(questions) <= 40
    assert all(isinstance(q, EvalQuestion) for q in questions)


def test_every_shipped_ubiquiti_question_has_expected_strings() -> None:
    # include_fetched=True lints the full shipped set, fetched-coverage block included.
    for q in load_questions("ubiquiti", include_fetched=True):
        assert q.expected, f"question '{q.id}' has an empty expected list"
        for item in q.expected:
            alts = [item] if isinstance(item, str) else item
            assert alts, f"question '{q.id}' has an empty OR-group"
            assert all(a.strip() for a in alts), f"question '{q.id}' has a blank expected"


def test_load_questions_raises_when_the_set_is_absent() -> None:
    # The `general` pack ships no eval/questions.yaml.
    with pytest.raises(FileNotFoundError):
        load_questions("general")


def test_load_questions_reads_the_shipped_pfsense_set() -> None:
    # The curated pfSense set ships exactly 25 questions, all curated (ADR-0025); the R2
    # expansion added aliases/advanced-rules, multi-WAN/traffic shaping, and diagnostics/backup
    # primers (17 -> 25), recovering the Step-12/13 deferred `aliases`/`floating-rules` pair. A
    # fetched Netgate harvest was declined on licensing grounds (ADR-0025), so the pack stays
    # curated-only and nothing here is tagged `corpus: fetched`.
    questions = load_questions("pfsense")
    assert len(questions) == 25
    assert all(q.corpus == "curated" for q in questions)


def test_every_shipped_pfsense_expected_string_is_grounded_in_the_primers() -> None:
    # Data contract (ADR-0006): every curated `expected` substring is verbatim in the pack's
    # own primer corpus. This is the offline proof the ground truth is real — it reads the
    # source .md files directly, with no Ollama, no index, and no network.
    primer_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((get_pack("pfsense").directory / "sources").glob("*.md"))
    ).lower()
    for q in load_questions("pfsense"):
        for item in q.expected:
            alternatives = [item] if isinstance(item, str) else item
            assert any(alt.lower() in primer_text for alt in alternatives), (
                f"question '{q.id}': none of {alternatives} found in the pfSense primers"
            )


# --- Answer faithfulness (generation-side metric; ADR-0007) --------------------------------


def _generate_from(mapping: dict[str, tuple[str, str]]):
    """A fake ``generate`` that maps each question to a canned (answer, context) pair."""

    def generate(question: str) -> tuple[str, str]:
        return mapping[question]

    return generate


def test_faithfulness_full_overlap_is_one() -> None:
    assert faithfulness_score("alpha beta gamma", "alpha beta gamma") == 1.0


def test_faithfulness_partial_overlap_is_the_exact_fraction() -> None:
    # answer bigrams: "alpha beta", "beta gamma", "gamma delta"; only the first is in context.
    assert faithfulness_score("alpha beta gamma delta", "alpha beta zzz") == pytest.approx(1 / 3)


def test_faithfulness_zero_overlap_is_zero() -> None:
    assert faithfulness_score("alpha beta", "gamma delta") == 0.0


def test_faithfulness_is_case_insensitive() -> None:
    assert faithfulness_score("ALPHA Beta", "the alpha beta link") == 1.0


def test_faithfulness_is_bigrams_not_bag_of_words() -> None:
    # Same tokens, reordered: a bag-of-words metric would score 1.0; bigrams must drop to 0.0.
    assert faithfulness_score("alpha beta", "beta alpha") == 0.0


def test_faithfulness_empty_answer_is_vacuously_one() -> None:
    # No tokens -> no bigram-level claim to contradict -> 1.0 (vacuously faithful), not 0.0.
    assert faithfulness_score("", "alpha beta gamma") == 1.0


def test_faithfulness_one_token_answer_is_vacuously_one() -> None:
    # Sub-n (one token, n=2): no bigram to ground -> 1.0, not 0.0.
    assert faithfulness_score("alpha", "alpha beta") == 1.0


def test_faithfulness_empty_context_with_real_answer_is_zero() -> None:
    # A real (>= n-token) answer with an empty context is genuinely ungrounded -> 0.0.
    assert faithfulness_score("alpha beta", "") == 0.0


def test_faithfulness_keeps_identifiers_whole() -> None:
    # The IP must match as one token, not as shredded \w+ fragments.
    assert faithfulness_score("gateway 192.168.1.1", "the gateway 192.168.1.1 address") == 1.0
    # A near-miss IP must NOT match — proves "gateway 192" isn't a colliding partial bigram.
    assert faithfulness_score("gateway 192.168.1.1", "the gateway 192.168.1.2 address") == 0.0


def test_faithfulness_reports_a_fabricated_identifier_as_ungrounded() -> None:
    # A fabricated IP (192.168.1.99) against a context that only contains 192.168.1.1: the
    # identifier-preserving tokenizer keeps each IP whole, so the bigram breaks and the
    # fabricated form surfaces in `ungrounded`. Bare \w+ would falsely overlap on "gateway 192".
    q = [EvalQuestion(id="ip", question="ip", expected=[])]
    generate = _generate_from({"ip": ("gateway 192.168.1.99", "the gateway 192.168.1.1 here")})
    result = score_faithfulness(q, generate, k=5).results[0]
    assert result.score == 0.0
    assert result.ungrounded == ["gateway 192.168.1.99"]


def test_faithfulness_n_is_parametrizable() -> None:
    # n=1 (unigrams) is bag-of-words, so the reordered pair now scores 1.0 ...
    assert faithfulness_score("alpha beta", "beta alpha", n=1) == 1.0
    # ... and n=3 (trigrams) over-punishes a single substituted token.
    assert faithfulness_score("alpha beta gamma", "alpha beta gamma", n=3) == 1.0
    assert faithfulness_score("alpha beta gamma", "alpha beta delta", n=3) == 0.0


def test_score_faithfulness_reports_labels_scores_and_mean() -> None:
    questions = [
        EvalQuestion(id="hi", question="hi", expected=[]),  # 1.0
        EvalQuestion(id="lo", question="lo", expected=[]),  # 1/3
        EvalQuestion(id="empty", question="empty", expected=[]),  # "" -> 1.0 (vacuous, included)
    ]
    generate = _generate_from(
        {
            "hi": ("alpha beta", "alpha beta"),
            "lo": ("alpha beta gamma delta", "alpha beta zzz"),
            "empty": ("", "alpha beta"),
        }
    )
    report = score_faithfulness(questions, generate, k=5, n=2, pack="demo")
    assert report.pack == "demo"
    assert report.k == 5
    assert report.n == 2
    assert report.total == 3
    # Mean over ALL three results — the empty answer scores 1.0 and is included (no exclusion).
    assert report.mean_faithfulness == pytest.approx((1.0 + 1 / 3 + 1.0) / 3)
    by_id = {r.id: r for r in report.results}
    assert by_id["empty"].score == 1.0
    assert by_id["empty"].ungrounded == []


def test_ungrounded_lists_the_answer_bigrams_absent_from_context() -> None:
    q = [EvalQuestion(id="b", question="b", expected=[])]
    generate = _generate_from({"b": ("alpha beta gamma delta", "alpha beta zzz")})
    result = score_faithfulness(q, generate, k=5).results[0]
    # "alpha beta" is grounded; the other two bigrams are not — unique, order-preserving.
    assert result.ungrounded == ["beta gamma", "gamma delta"]


def test_score_faithfulness_of_empty_question_set_is_zero_not_a_crash() -> None:
    report = score_faithfulness([], _generate_from({}), k=5)
    assert report.total == 0
    assert report.mean_faithfulness == 0.0


def test_run_faithfulness_eval_uses_injected_generate_offline() -> None:
    # A generate that echoes its answer as its own context -> every answer is fully grounded.
    grounded = lambda question: ("alpha beta gamma", "alpha beta gamma")  # noqa: E731
    report = run_faithfulness_eval("ubiquiti", k=5, n=2, generate=grounded)
    assert report.pack == "ubiquiti"
    assert report.k == 5
    assert report.n == 2
    assert report.total > 0
    assert report.mean_faithfulness == 1.0


def test_run_faithfulness_eval_defaults_k_from_settings_when_generate_injected() -> None:
    # Mirror Step 1: with an injected generate and k=None, k falls back to settings.top_k.
    grounded = lambda question: ("alpha beta", "alpha beta")  # noqa: E731
    report = run_faithfulness_eval("ubiquiti", settings=Settings(top_k=7), generate=grounded)
    assert report.k == 7


# --- Retrieval hit-rate CI gate (run-level regression floor; ADR-0008) ----------------------

runner = CliRunner()


def _report(hit_rate: float, *, total: int = 10) -> EvalReport:
    """A canned retrieval report with a given hit-rate (results are irrelevant to the gate)."""
    return EvalReport(
        pack="demo",
        k=5,
        total=total,
        hits=round(hit_rate * total),
        hit_rate=hit_rate,
        results=[],
    )


def test_gate_exit_code_passes_at_or_above_floor() -> None:
    assert gate_exit_code(0.8, 0.7) == GATE_OK
    # Exactly at the floor passes.
    assert gate_exit_code(0.7, 0.7) == GATE_OK


def test_gate_exit_code_fails_below_floor() -> None:
    assert gate_exit_code(0.5, 0.7) == GATE_BELOW_FLOOR
    # The failure code is a distinct, non-zero value (and not the operational-error code 1).
    assert GATE_BELOW_FLOOR not in (GATE_OK, 1)


def test_gate_exit_code_boundary_is_epsilon_tolerant() -> None:
    # A decimal floor (0.9) vs a rational hit-rate (9/10): IEEE-754 can land 9/10 a representable
    # hair below 0.9, which without the epsilon slack would spuriously fail. "Meets the floor"
    # must stay a pass.
    assert gate_exit_code(9 / 10, 0.9) == GATE_OK


def test_eval_command_without_gate_always_exits_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    # Default path is report-only: even a dismal hit-rate exits 0 (no regression to Step 1).
    monkeypatch.setattr(
        "mnemosyne.cli.run_retrieval_eval",
        lambda pack, k=None, include_fetched=False: _report(0.1),
    )
    result = runner.invoke(app, ["eval", "demo"])
    assert result.exit_code == 0


def test_eval_command_gate_passes_at_or_above_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "mnemosyne.cli.run_retrieval_eval",
        lambda pack, k=None, include_fetched=False: _report(0.8),
    )
    result = runner.invoke(app, ["eval", "demo", "--gate", "--min-hit-rate", "0.7"])
    assert result.exit_code == GATE_OK


def test_eval_command_gate_fails_below_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "mnemosyne.cli.run_retrieval_eval",
        lambda pack, k=None, include_fetched=False: _report(0.5),
    )
    result = runner.invoke(app, ["eval", "demo", "--gate", "--min-hit-rate", "0.7"])
    assert result.exit_code == GATE_BELOW_FLOOR


def test_eval_command_min_hit_rate_alone_implies_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    # A bare --min-hit-rate (no --gate) still gates: below the floor exits 2.
    monkeypatch.setattr(
        "mnemosyne.cli.run_retrieval_eval",
        lambda pack, k=None, include_fetched=False: _report(0.5),
    )
    result = runner.invoke(app, ["eval", "demo", "--min-hit-rate", "0.7"])
    assert result.exit_code == GATE_BELOW_FLOOR


def test_eval_command_rejects_out_of_range_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    # An out-of-[0,1] floor is an operational error (exit 1, via _die), not a gate verdict.
    monkeypatch.setattr(
        "mnemosyne.cli.run_retrieval_eval",
        lambda pack, k=None, include_fetched=False: _report(0.9),
    )
    result = runner.invoke(app, ["eval", "demo", "--min-hit-rate", "1.5"])
    assert result.exit_code == 1


# --- Config sweeps (grid + scoring + table; issue #24) -------------------------------------


def _retrieve_for(by_config: dict[SweepConfig, tuple[str, ...]]):
    """A factory: maps each config to a ``retrieve`` that returns that config's canned chunks."""

    def retrieve_for(config: SweepConfig):
        return _retrieve_from(*by_config[config])

    return retrieve_for


def _generate_for(by_config: dict[SweepConfig, dict[str, tuple[str, str]]]):
    """A factory: maps each config to a ``generate`` over its per-question (answer, context)."""

    def generate_for(config: SweepConfig):
        return _generate_from(by_config[config])

    return generate_for


def _row(
    hit_rate: float,
    mean_faithfulness: float | None = None,
    *,
    k: int = 5,
    chunk_size: int = 500,
    chunk_overlap: int = 150,
) -> SweepRow:
    """A canned :class:`SweepRow` for the ranking/table tests (models are fixed)."""
    config = SweepConfig(chunk_size, chunk_overlap, k, "bge-m3", "qwen")
    return SweepRow(config=config, hit_rate=hit_rate, mean_faithfulness=mean_faithfulness)


def test_expand_grid_is_the_cartesian_product_in_arg_order() -> None:
    configs = expand_grid(
        chunk_sizes=[500, 300],
        chunk_overlaps=[100],
        ks=[3, 5],
        embedding_models=["bge-m3"],
        chat_models=["a", "b"],
    )
    # 2 * 1 * 2 * 1 * 2 = 8 configs; overlap 100 < both sizes, so none are dropped.
    assert len(configs) == 8
    # The last axis (chat_models) varies fastest ...
    assert [c.chat_model for c in configs[:2]] == ["a", "b"]
    # ... k advances only after chat_models is exhausted ...
    assert configs[0].k == 3
    assert configs[2].k == 5
    # ... and the first axis (chunk_sizes) varies slowest.
    assert all(c.chunk_size == 500 for c in configs[:4])
    assert configs[4].chunk_size == 300


def test_expand_grid_drops_configs_where_overlap_not_smaller_than_size() -> None:
    configs = expand_grid(
        chunk_sizes=[200, 400],
        chunk_overlaps=[200, 100],
        ks=[5],
        embedding_models=["bge-m3"],
        chat_models=["c"],
    )
    # Pre-filter product is 4; only (size=200, overlap=200) is degenerate and dropped.
    assert len(configs) == 3
    assert all(c.chunk_overlap < c.chunk_size for c in configs)
    assert SweepConfig(200, 200, 5, "bge-m3", "c") not in configs


def test_expand_grid_raises_on_an_empty_axis() -> None:
    with pytest.raises(ValueError, match="empty"):
        expand_grid(
            chunk_sizes=[],
            chunk_overlaps=[100],
            ks=[5],
            embedding_models=["bge-m3"],
            chat_models=["c"],
        )


def test_sweep_config_is_frozen_and_hashable() -> None:
    a = SweepConfig(500, 150, 5, "bge-m3", "qwen")
    b = SweepConfig(500, 150, 5, "bge-m3", "qwen")
    # Usable as a dict/set key: the Step 4b re-ingest cache keys on the config.
    assert {a: 1}[b] == 1
    assert len({a, b}) == 1
    # Frozen: assignment is rejected.
    with pytest.raises(dataclasses.FrozenInstanceError):
        a.chunk_size = 999


def test_score_sweep_retrieval_only_leaves_faithfulness_none() -> None:
    questions = [
        EvalQuestion(id="q1", question="q1", expected=["alpha"]),
        EvalQuestion(id="q2", question="q2", expected=["beta"]),
    ]
    good = SweepConfig(500, 100, 5, "bge-m3", "qwen")  # retrieves both -> 1.0
    poor = SweepConfig(300, 100, 3, "bge-m3", "qwen")  # retrieves only alpha -> 0.5
    retrieve_for = _retrieve_for({good: ("alpha beta",), poor: ("alpha only",)})
    report = score_sweep(questions, [good, poor], retrieve_for, pack="demo")
    assert report.pack == "demo"
    by_config = {r.config: r for r in report.rows}
    assert by_config[good].hit_rate == 1.0
    assert by_config[poor].hit_rate == pytest.approx(0.5)
    assert all(r.mean_faithfulness is None for r in report.rows)
    assert report.best == good


def test_score_sweep_with_generate_for_populates_faithfulness() -> None:
    questions = [EvalQuestion(id="q1", question="q1", expected=["alpha"])]
    cfg = SweepConfig(500, 100, 5, "bge-m3", "qwen")
    retrieve_for = _retrieve_for({cfg: ("alpha",)})
    generate_for = _generate_for({cfg: {"q1": ("alpha beta", "alpha beta")}})
    report = score_sweep(questions, [cfg], retrieve_for, generate_for=generate_for)
    assert report.rows[0].hit_rate == 1.0
    assert report.rows[0].mean_faithfulness == 1.0


def test_score_sweep_of_no_configs_is_empty_with_no_best() -> None:
    report = score_sweep([], [], _retrieve_for({}))
    assert report.rows == []
    assert report.best is None


def test_best_config_is_none_for_empty_rows() -> None:
    assert _best_config([]) is None


def test_best_config_picks_highest_hit_rate() -> None:
    low = _row(0.5, chunk_size=300)
    high = _row(0.9, chunk_size=700)
    assert _best_config([low, high]) == high.config


def test_best_config_breaks_hit_rate_tie_by_faithfulness() -> None:
    less = _row(0.8, 0.4, chunk_size=300)
    more = _row(0.8, 0.7, chunk_size=400)
    assert _best_config([less, more]) == more.config


def test_best_config_treats_unscored_faithfulness_as_worst() -> None:
    scored = _row(0.8, 0.1, chunk_size=300)
    unscored = _row(0.8, None, chunk_size=400)
    assert _best_config([unscored, scored]) == scored.config


def test_best_config_tie_break_prefers_smaller_k_over_smaller_chunk() -> None:
    # k is ranked before chunk_size: a smaller k wins even with a larger chunk_size.
    small_k = _row(0.8, 0.5, k=3, chunk_size=900, chunk_overlap=50)
    small_chunk = _row(0.8, 0.5, k=9, chunk_size=200, chunk_overlap=50)
    assert _best_config([small_chunk, small_k]) == small_k.config


def test_format_sweep_table_marks_best_and_renders_dash_for_unscored() -> None:
    best = SweepConfig(500, 150, 5, "bge-m3", "qwen")
    other = SweepConfig(300, 100, 3, "bge-m3", "qwen")
    report = SweepReport(
        pack="demo",
        rows=[
            SweepRow(config=best, hit_rate=0.9, mean_faithfulness=0.75),
            SweepRow(config=other, hit_rate=0.5, mean_faithfulness=None),
        ],
        best=best,
    )
    lines = format_sweep_table(report).splitlines()
    # Header + one line per config.
    assert len(lines) == 3
    assert "hit_rate" in lines[0]
    assert "faithfulness" in lines[0]
    best_line = next(line for line in lines[1:] if "0.90" in line)
    other_line = next(line for line in lines[1:] if "0.50" in line)
    # The best row is marked with a leading '*'; the other is not.
    assert best_line.startswith("*")
    assert not other_line.startswith("*")
    assert "0.75" in best_line
    # Unscored faithfulness renders as '-' (the last column).
    assert other_line.rstrip().endswith("-")


def test_format_sweep_table_empty_report_is_header_only() -> None:
    table = format_sweep_table(SweepReport(pack="demo", rows=[], best=None))
    assert len(table.splitlines()) == 1
    assert "chunk_size" in table


# --- Sweep runner: index cache + live re-ingest (issue #24, ADR-0010) ----------------------


def test_index_key_ignores_k_and_chat_model() -> None:
    base = SweepConfig(500, 150, 5, "bge-m3", "qwen")
    # k and chat_model are not part of the built index, so they share a key ...
    assert _index_key(base) == _index_key(SweepConfig(500, 150, 9, "bge-m3", "other-chat"))
    # ... but chunk_size, chunk_overlap, and embedding_model each change it.
    assert _index_key(base) != _index_key(SweepConfig(800, 150, 5, "bge-m3", "qwen"))
    assert _index_key(base) != _index_key(SweepConfig(500, 100, 5, "bge-m3", "qwen"))
    assert _index_key(base) != _index_key(SweepConfig(500, 150, 5, "nomic-embed", "qwen"))


def test_run_sweep_injected_path_delegates_to_score_sweep() -> None:
    # Injected factories keep the run offline: no temp workspace, no ingest, no Ollama.
    questions = load_questions("ubiquiti")
    every_expected = " ".join(s for q in questions for s in _flatten_expected(q))
    cfg = SweepConfig(500, 150, 5, "bge-m3", "qwen")
    retrieve_for = _retrieve_for({cfg: (every_expected,)})

    # Without generate_for, faithfulness stays None ...
    report = run_sweep("ubiquiti", [cfg], retrieve_for=retrieve_for)
    assert report.pack == "ubiquiti"
    assert report.rows[0].hit_rate == 1.0
    assert report.rows[0].mean_faithfulness is None

    # ... and supplying generate_for populates it (the `faithfulness` flag is for the live path).
    generate_for = _generate_for(
        {cfg: {q.question: ("alpha beta", "alpha beta") for q in questions}}
    )
    scored = run_sweep("ubiquiti", [cfg], retrieve_for=retrieve_for, generate_for=generate_for)
    assert scored.rows[0].mean_faithfulness == 1.0


class _RecordingIngest:
    """A fake ``ingest`` that records each call instead of building a real index."""

    def __init__(self) -> None:
        self.calls: list[SimpleNamespace] = []

    def __call__(
        self,
        pack,
        settings,
        *,
        chunk_size,
        chunk_overlap,
        embedding_model,
        local_only,
    ):
        self.calls.append(
            SimpleNamespace(
                pack=pack,
                settings=settings,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                embedding_model=embedding_model,
                local_only=local_only,
            )
        )
        return None


class _FakePipeline:
    """A fake ``RagPipeline`` returning canned chunks/answers (no Ollama, no index read)."""

    def __init__(self, pack, settings, *, top_k, chat_model) -> None:
        self.pack = pack
        self.settings = settings
        self.top_k = top_k
        self.chat_model = chat_model

    def retrieve(self, question, k=None):
        return [Document(page_content="alpha beta")]

    def ask(self, question, k=None):
        return SimpleNamespace(text="alpha beta")


def test_run_sweep_live_dedups_index_builds_by_index_key(monkeypatch: pytest.MonkeyPatch) -> None:
    ingest = _RecordingIngest()
    monkeypatch.setattr("mnemosyne.eval.ingest", ingest)
    monkeypatch.setattr("mnemosyne.eval.RagPipeline", _FakePipeline)
    # Two configs with the same index key (they differ only in k) -> one ingest.
    same_key = [
        SweepConfig(500, 150, 5, "bge-m3", "qwen"),
        SweepConfig(500, 150, 10, "bge-m3", "qwen"),
    ]
    report = run_sweep("ubiquiti", same_key)
    assert len(ingest.calls) == 1
    # ... but it still produces a real two-row report from the cached build.
    assert isinstance(report, SweepReport)
    assert len(report.rows) == 2


def test_run_sweep_live_builds_one_index_per_distinct_key(monkeypatch: pytest.MonkeyPatch) -> None:
    ingest = _RecordingIngest()
    monkeypatch.setattr("mnemosyne.eval.ingest", ingest)
    monkeypatch.setattr("mnemosyne.eval.RagPipeline", _FakePipeline)
    # Distinct chunk_size -> distinct index keys -> two ingests.
    distinct = [
        SweepConfig(500, 150, 5, "bge-m3", "qwen"),
        SweepConfig(800, 150, 5, "bge-m3", "qwen"),
    ]
    run_sweep("ubiquiti", distinct)
    assert len(ingest.calls) == 2


def test_run_sweep_live_ingests_into_temp_workspace_never_canonical(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ingest = _RecordingIngest()
    monkeypatch.setattr("mnemosyne.eval.ingest", ingest)
    monkeypatch.setattr("mnemosyne.eval.RagPipeline", _FakePipeline)
    cfg = SweepConfig(500, 150, 5, "bge-m3", "qwen")
    run_sweep("ubiquiti", [cfg], local_only=True)

    call = ingest.calls[0]
    assert call.chunk_size == 500
    assert call.chunk_overlap == 150
    assert call.embedding_model == "bge-m3"
    assert call.local_only is True
    # The scratch index lives under a temp workspace, never the canonical knowledge_dir.
    scratch_dir = call.settings.knowledge_dir
    assert scratch_dir != get_settings().knowledge_dir
    assert str(scratch_dir).startswith(tempfile.gettempdir())
    assert scratch_dir.name == "idx0"


def test_sweep_command_builds_grid_from_repeated_options(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_run_sweep(pack, configs, *, faithfulness=False):
        captured["pack"] = pack
        captured["configs"] = configs
        captured["faithfulness"] = faithfulness
        return SweepReport(pack=pack, rows=[], best=None)

    monkeypatch.setattr("mnemosyne.cli.run_sweep", fake_run_sweep)
    result = runner.invoke(
        app,
        [
            "sweep",
            "demo",
            "--chunk-size",
            "500",
            "--chunk-size",
            "800",
            "--k",
            "3",
            "--k",
            "5",
            "--faithfulness",
        ],
    )
    assert result.exit_code == 0
    assert captured["pack"] == "demo"
    assert captured["faithfulness"] is True
    # The repeated axes build exactly the expand_grid product; unset axes fall back to settings.
    settings = get_settings()
    expected = expand_grid(
        chunk_sizes=[500, 800],
        chunk_overlaps=[settings.chunk_overlap],
        ks=[3, 5],
        embedding_models=[settings.embedding_model],
        chat_models=[settings.chat_model],
    )
    assert captured["configs"] == expected


def test_sweep_command_bare_runs_one_config_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_run_sweep(pack, configs, *, faithfulness=False):
        captured["configs"] = configs
        return SweepReport(pack=pack, rows=[], best=None)

    monkeypatch.setattr("mnemosyne.cli.run_sweep", fake_run_sweep)
    result = runner.invoke(app, ["sweep", "demo"])
    assert result.exit_code == 0
    settings = get_settings()
    assert captured["configs"] == [
        SweepConfig(
            settings.chunk_size,
            settings.chunk_overlap,
            settings.top_k,
            settings.embedding_model,
            settings.chat_model,
        )
    ]
    # An empty report (best is None) prints the no-op line, not a best-config suggestion.
    assert "no configs evaluated" in result.output


def test_sweep_command_unknown_pack_exits_via_die() -> None:
    # No monkeypatch: run_sweep -> load_questions -> get_pack raises KeyError before any Ollama.
    result = runner.invoke(app, ["sweep", "nonexistent-pack"])
    assert result.exit_code == 1
    assert "error:" in result.output


# --- Served-corpus eval JSON line (--json; ADR-0019) -----------------------------------------

# A meta.json as ingest writes it (pipeline.write_meta), with the fetched-inclusive chunk
# count from ADR-0017 so the served-vs-local discriminator is what the tests pin.
_META = {
    "pack": "demo",
    "documents": 18,
    "chunks": 294,
    "embedding_model": "bge-m3",
    "chunk_size": 500,
    "chunk_overlap": 150,
    "normalize": False,
}


def _json_report() -> EvalReport:
    # One question per corpus class, so the serialized `corpus` tags are pinned (ADR-0020).
    results = [
        EvalResult(id="q1", question="what is a vlan?", hit=True, missing=[]),
        EvalResult(
            id="q2",
            question="what is poe?",
            hit=False,
            missing=["802.3af | 802.3at"],
            corpus="fetched",
        ),
    ]
    return EvalReport(pack="demo", k=5, total=2, hits=1, hit_rate=0.5, results=results)


def _serialize(**overrides) -> str:
    kwargs = {
        "meta": _META,
        "score_floor": 1.0,
        "faiss_normalize": False,
        "timestamp": "2026-07-06T00:00:00Z",
    }
    kwargs.update(overrides)
    return serialize_retrieval_report(_json_report(), **kwargs)


def test_serialize_retrieval_report_is_one_valid_json_line() -> None:
    line = _serialize()
    assert "\n" not in line
    assert json.loads(line)["pack"] == "demo"


def test_serialize_retrieval_report_shape_and_injected_timestamp() -> None:
    payload = json.loads(_serialize())
    # The timestamp is the injected string, verbatim: the serializer owns no clock.
    assert payload["timestamp"] == "2026-07-06T00:00:00Z"
    assert (payload["k"], payload["total"], payload["hits"]) == (5, 2, 1)
    assert payload["hit_rate"] == 0.5
    # The index block is exactly the five meta.json discriminator fields; `normalize` is not
    # echoed here (the effective setting is the top-level `faiss_normalize`).
    assert payload["index"] == {
        "documents": 18,
        "chunks": 294,
        "embedding_model": "bge-m3",
        "chunk_size": 500,
        "chunk_overlap": 150,
    }
    assert payload["results"] == [
        {
            "id": "q1",
            "question": "what is a vlan?",
            "hit": True,
            "missing": [],
            "corpus": "curated",
        },
        {
            "id": "q2",
            "question": "what is poe?",
            "hit": False,
            "missing": ["802.3af | 802.3at"],
            "corpus": "fetched",
        },
    ]
    # Installed distribution version (or the __version__ fallback): a non-empty string.
    assert isinstance(payload["mnemosyne_version"], str)
    assert payload["mnemosyne_version"]


def test_serialize_retrieval_report_score_floor_none_vs_float() -> None:
    assert json.loads(_serialize(score_floor=None))["score_floor"] is None
    assert json.loads(_serialize(score_floor=0.75))["score_floor"] == 0.75


def test_serialize_retrieval_report_missing_meta_is_explicit_null_index() -> None:
    payload = json.loads(_serialize(meta=None))
    assert payload["index"] is None
    # The effective settings still land: they come from Settings, not from meta.json.
    assert payload["score_floor"] == 1.0
    assert payload["faiss_normalize"] is False


def test_serialize_retrieval_report_partial_meta_keeps_every_index_key() -> None:
    payload = json.loads(_serialize(meta={"chunks": 42}))
    assert payload["index"] == {
        "documents": None,
        "chunks": 42,
        "embedding_model": None,
        "chunk_size": None,
        "chunk_overlap": None,
    }


def test_serialize_retrieval_report_carries_no_host_coordinates() -> None:
    # Locked JSON surface (ADR-0019): nothing host-shaped in a line that gets pasted into
    # issues. The ollama host is deliberately not among the serialized settings.
    line = _serialize().lower()
    assert "ollama_host" not in line
    assert "localhost" not in line
    assert "11434" not in line


def _patch_json_eval(monkeypatch: pytest.MonkeyPatch, *, meta: dict | None) -> None:
    """Wire eval_cmd's --json collaborators to canned offline values (no Ollama, no index)."""
    monkeypatch.setattr(
        "mnemosyne.cli.run_retrieval_eval",
        lambda pack, k=None, include_fetched=False: _json_report(),
    )
    monkeypatch.setattr("mnemosyne.index.read_meta", lambda path: meta)
    monkeypatch.setattr(
        "mnemosyne.cli.get_settings",
        lambda: Settings(_env_file=None, score_floor=0.75, faiss_normalize=True),
    )


def test_eval_json_prints_exactly_one_parseable_line(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_json_eval(monkeypatch, meta=_META)
    result = runner.invoke(app, ["eval", "demo", "--json"])
    assert result.exit_code == 0
    out = result.output.strip()
    assert "\n" not in out  # no table, no summary line: stdout is exactly the JSON record
    payload = json.loads(out)
    assert payload["hit_rate"] == 0.5
    assert payload["index"]["chunks"] == 294
    # The effective settings come from the CLI boundary's get_settings().
    assert payload["score_floor"] == 0.75
    assert payload["faiss_normalize"] is True
    # The CLI stamps a real UTC timestamp in the Z-suffixed second-resolution format.
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", payload["timestamp"])


def test_eval_json_show_misses_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_json_eval(monkeypatch, meta=_META)
    result = runner.invoke(app, ["eval", "demo", "--json", "--show-misses"])
    assert result.exit_code == 0
    # Misses are always serialized, so the flag adds nothing and breaks nothing.
    payload = json.loads(result.output.strip())
    assert payload["results"][1]["missing"] == ["802.3af | 802.3at"]


def test_eval_json_missing_meta_serializes_null_index(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_json_eval(monkeypatch, meta=None)
    result = runner.invoke(app, ["eval", "demo", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output.strip())["index"] is None


def test_eval_json_refuses_faithfulness() -> None:
    # No monkeypatch: the posture check dies before any eval work happens.
    result = runner.invoke(app, ["eval", "demo", "--json", "--faithfulness"])
    assert result.exit_code == 1
    assert "retrieval-only" in result.output


def test_eval_json_refuses_gate() -> None:
    result = runner.invoke(app, ["eval", "demo", "--json", "--gate"])
    assert result.exit_code == 1
    assert "report-only" in result.output


def test_eval_json_refuses_min_hit_rate_because_it_implies_gate() -> None:
    result = runner.invoke(app, ["eval", "demo", "--json", "--min-hit-rate", "0.5"])
    assert result.exit_code == 1
    assert "report-only" in result.output


# --- Fetched-coverage questions (corpus tag + --include-fetched; ADR-0020) -------------------


_CORPUS_FIXTURE = """\
questions:
  - id: cur-1
    question: curated fact?
    expected:
      - alpha
  - id: fet-1
    question: fetched fact?
    expected:
      - beta
    corpus: fetched
"""


def _pack_with_questions(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, text: str) -> None:
    """Point mnemosyne.eval's ``get_pack`` at a scratch pack directory shipping ``text``."""
    (tmp_path / "eval").mkdir()
    (tmp_path / "eval" / "questions.yaml").write_text(text, encoding="utf-8")
    monkeypatch.setattr("mnemosyne.eval.get_pack", lambda name: SimpleNamespace(directory=tmp_path))


def test_load_questions_excludes_fetched_by_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _pack_with_questions(monkeypatch, tmp_path, _CORPUS_FIXTURE)
    questions = load_questions("demo")
    assert [q.id for q in questions] == ["cur-1"]
    assert questions[0].corpus == "curated"


def test_load_questions_include_fetched_returns_all(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _pack_with_questions(monkeypatch, tmp_path, _CORPUS_FIXTURE)
    questions = load_questions("demo", include_fetched=True)
    assert [q.id for q in questions] == ["cur-1", "fet-1"]
    assert [q.corpus for q in questions] == ["curated", "fetched"]


def test_load_questions_rejects_unknown_corpus_even_when_filtered(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Validation runs before filtering: a bad tag fails the default (excluding) load too.
    _pack_with_questions(
        monkeypatch, tmp_path, _CORPUS_FIXTURE.replace("corpus: fetched", "corpus: served")
    )
    with pytest.raises(ValueError, match="fet-1"):
        load_questions("demo")


def test_load_questions_rejects_explicit_curated(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Single-spelling contract (ADR-0020): curated is expressed by omitting the field.
    _pack_with_questions(
        monkeypatch, tmp_path, _CORPUS_FIXTURE.replace("corpus: fetched", "corpus: curated")
    )
    with pytest.raises(ValueError, match="invalid corpus"):
        load_questions("demo", include_fetched=True)


def test_load_questions_rejects_non_string_expected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # An unquoted YAML number loads as an int and would crash scoring at .lower().
    text = "questions:\n  - id: q-num\n    question: how many?\n    expected:\n      - 42\n"
    _pack_with_questions(monkeypatch, tmp_path, text)
    with pytest.raises(ValueError, match="q-num"):
        load_questions("demo")


def test_load_questions_rejects_non_string_in_or_group(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # A non-string alternative inside an OR-group is rejected the same way.
    text = (
        "questions:\n  - id: q-or\n    question: which?\n    expected:\n      - - ok\n        - 7\n"
    )
    _pack_with_questions(monkeypatch, tmp_path, text)
    with pytest.raises(ValueError, match="q-or"):
        load_questions("demo")


def test_load_questions_rejects_duplicate_ids(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    text = (
        "questions:\n"
        "  - id: dup\n    question: first?\n    expected:\n      - alpha\n"
        "  - id: dup\n    question: second?\n    expected:\n      - beta\n"
    )
    _pack_with_questions(monkeypatch, tmp_path, text)
    with pytest.raises(ValueError, match="dup"):
        load_questions("demo")


def test_load_questions_rejects_duplicate_ids_before_fetched_filter(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Validation runs before the corpus filter: a duplicate whose second copy is fetched
    # still fails the default (excluding) load.
    text = (
        "questions:\n"
        "  - id: dup\n    question: first?\n    expected:\n      - alpha\n"
        "  - id: dup\n    question: second?\n    expected:\n      - beta\n    corpus: fetched\n"
    )
    _pack_with_questions(monkeypatch, tmp_path, text)
    with pytest.raises(ValueError, match="dup"):
        load_questions("demo", include_fetched=False)


def test_shipped_default_population_is_unchanged_by_adr_0020() -> None:
    # The CI gate's population: exactly the 28 curated questions, none tagged.
    questions = load_questions("ubiquiti")
    assert len(questions) == 28
    assert all(q.corpus == "curated" for q in questions)


def test_ubiquiti_ships_no_fetched_questions_after_the_harvest_decline() -> None:
    # The fetched help.ui.com harvest was declined on licensing grounds (ADR-0026), so the pack
    # is curated-only: even with include_fetched=True the shipped set is the 28 curated
    # questions and nothing is tagged `corpus: fetched`. The generic `corpus`/`--include-fetched`
    # loader machinery (ADR-0020) is exercised by the synthetic `demo` fixture below, not here.
    all_questions = load_questions("ubiquiti", include_fetched=True)
    assert len(all_questions) == 28
    assert all(q.corpus == "curated" for q in all_questions)


def test_score_copies_corpus_onto_results() -> None:
    questions = [
        EvalQuestion(id="c", question="q1?", expected=["alpha"]),
        EvalQuestion(id="f", question="q2?", expected=["beta"], corpus="fetched"),
    ]
    report = score(questions, _retrieve_from("alpha beta"), k=1)
    assert [r.corpus for r in report.results] == ["curated", "fetched"]


def test_run_retrieval_eval_include_fetched_widens_the_population_offline(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # Generic loader behavior on the synthetic fixture (ADR-0020): include_fetched widens the
    # scored population from the curated question to the full set. Proven on the demo fixture
    # rather than a shipped pack so it stays true regardless of any pack's corpus (ubiquiti is
    # curated-only after ADR-0026).
    _pack_with_questions(monkeypatch, tmp_path, _CORPUS_FIXTURE)
    curated = run_retrieval_eval("demo", k=5, retrieve=lambda q, k: [])
    assert curated.total == 1
    widened = run_retrieval_eval("demo", k=5, retrieve=lambda q, k: [], include_fetched=True)
    assert widened.total == 2


def test_eval_include_fetched_refuses_gate() -> None:
    # No monkeypatch: the posture check dies before any eval work happens (ADR-0020).
    result = runner.invoke(app, ["eval", "demo", "--include-fetched", "--gate"])
    assert result.exit_code == 1
    assert "--include-fetched" in result.output


def test_eval_include_fetched_refuses_min_hit_rate() -> None:
    result = runner.invoke(app, ["eval", "demo", "--include-fetched", "--min-hit-rate", "0.5"])
    assert result.exit_code == 1
    assert "--include-fetched" in result.output


def test_eval_include_fetched_threads_to_the_eval(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, bool] = {}

    def fake_run(pack: str, k: int | None = None, include_fetched: bool = False) -> EvalReport:
        captured["include_fetched"] = include_fetched
        return _json_report()

    monkeypatch.setattr("mnemosyne.cli.run_retrieval_eval", fake_run)
    result = runner.invoke(app, ["eval", "demo", "--include-fetched"])
    assert result.exit_code == 0
    assert captured["include_fetched"] is True


def test_eval_include_fetched_threads_to_the_faithfulness_eval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Pins that `-f --include-fetched` scores both metrics over ONE population: a refactor
    # that stopped threading the kwarg to the faithfulness path would silently split the
    # retrieval and faithfulness populations.
    captured: dict[str, bool] = {}

    def fake_faith(
        pack: str, k: int | None = None, include_fetched: bool = False
    ) -> FaithfulnessReport:
        captured["include_fetched"] = include_fetched
        return FaithfulnessReport(pack=pack, k=5, n=2, total=0, mean_faithfulness=0.0, results=[])

    monkeypatch.setattr(
        "mnemosyne.cli.run_retrieval_eval",
        lambda pack, k=None, include_fetched=False: _json_report(),
    )
    monkeypatch.setattr("mnemosyne.cli.run_faithfulness_eval", fake_faith)
    result = runner.invoke(app, ["eval", "demo", "--faithfulness", "--include-fetched"])
    assert result.exit_code == 0
    assert captured["include_fetched"] is True


def test_eval_json_combines_with_include_fetched_and_results_carry_corpus(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_json_eval(monkeypatch, meta=_META)
    result = runner.invoke(app, ["eval", "demo", "--json", "--include-fetched"])
    assert result.exit_code == 0
    payload = json.loads(result.output.strip())
    assert [r["corpus"] for r in payload["results"]] == ["curated", "fetched"]
