# 23. Help Center harvest, batch 1: nine articles landed against a measured dilution bar

Date: 2026-07-07

## Status

Accepted

## Context

The v0.x roadmap's corpus item carried a stale caveat: "a first-party harvest of official
UniFi docs is still outstanding (help.ui.com 403s from some networks)". The 403 caveat was
disproven from the serving host on 2026-07-07 by two clean 14-URL fetches (the Step-7
scratch build and the production re-ingest, receipts in ADR-0022), and this step's fetch
health explains it: the 403 is a CDN challenge served to bare HTTP clients, so it is
client-header-dependent, not network-dependent; the shipped loader's browser-like headers
pass. A broader corpus is also ADR-0021's revisit trigger ("materially larger question set
or matured corpus") and direct product value: more of the UniFi expert domain answerable
for Argus.

The tension the step had to respect: ADR-0017 measured that adding fetched breadth can
LOWER curated recall (dilution: near-topic chunks displace curated answer chunks;
`poe-cycle` and `port-profiles` are the standing victims). So the batch did not land on
faith: Phase A ingested it into a scratch index and measured the full 32-question set
per-question against the 30/32 production baseline before anything shipped. Jon approved
the domain list and batch size, and the dilution bar as written, at the gate.

## Decision

Batch 1 is nine Network-domain help.ui.com articles across five areas the corpus did not
cover (VPN; console management and lifecycle; DNS services; advanced WiFi; traffic
management), appended to the ubiquiti pack's `sources.yaml`. Article text never enters
git: the standing corpus rule, only the URL references are tracked (D5). The batch landed
under a pinned dilution bar (D2): land iff the scratch 32-question eval stays at or above
30/32 AND every individual hit->miss flip is examined; a displacer that genuinely answers
the question better in different words is an OR-group ground-truth wording gap flagged for
a later step (the ADR-0017 `trunk-vs-access` lesson), while a noise displacer trims the
offending article from the batch by per-article ablation. Trimming a candidate addition is
not ADR-0017's rejected "corpus pruning", which deleted good existing content to game the
metric. Corpus-only (D3): no new eval questions this step, `questions.yaml` locked
byte-identical, no `src/` code, config, floor, or chunking changes. Scratch-first (D4):
production stays untouched until the Jon-gated follow-through under the Step-7 protocol.

### Phase A receipt (Sage, 2026-07-07 UTC, on the Spark; scratch indices only, production and repo tree untouched and verified clean after)

**The batch (Nova appends to `sources.yaml` `urls:` exactly; 9 articles, comments
included):**

```yaml
  # VPN (remote access & site-to-site)
  - https://help.ui.com/hc/en-us/articles/7951513517079-UniFi-Gateway-Introduction-to-VPNs
  - https://help.ui.com/hc/en-us/articles/115005445768-UniFi-Gateway-WireGuard-VPN-Server
  - https://help.ui.com/hc/en-us/articles/5246403561495-UniFi-Gateway-Teleport-VPN
  # Console management & lifecycle
  - https://help.ui.com/hc/en-us/articles/360008976393-Backups-and-Migration-in-UniFi
  - https://help.ui.com/hc/en-us/articles/205143490-How-to-Reset-UniFi-Devices-to-Factory-Defaults
  # DNS & DHCP services
  - https://help.ui.com/hc/en-us/articles/15179064940439-UniFi-DNS-Records-and-Local-Hostnames
  - https://help.ui.com/hc/en-us/articles/17484948645015-UniFi-DNS-Troubleshooting-Guide
  # Advanced WiFi
  - https://help.ui.com/hc/en-us/articles/221029967-Optimizing-WiFi-Connectivity-and-Reducing-Latency
  # Traffic management
  - https://help.ui.com/hc/en-us/articles/204911354-UniFi-QoS-and-Traffic-Shaping
```

**Fetch health (via the shipped loader, 10/10 clean; titles verified):** Introduction to
VPNs 3172 chars, WireGuard VPN Server 3194, Teleport VPN 3325, Backups and Migration
9407, Reset to Factory Defaults 4618, DNS Records and Local Hostnames 4452, DNS
Troubleshooting 2800, Optimizing WiFi Connectivity 7127, Maximizing Wireless Speeds
5766, QoS and Traffic Shaping 6426. Note for the ADR: bare HTTP clients get a CDN
challenge (403 "Just a moment") on the same URLs; the loader's browser-like headers
pass. This explains the old "help.ui.com 403s from some networks" caveat: it is
client-header-dependent, not purely network-dependent.

**Dilution measurement (per-question, 32-set, vs the 30/32 production baseline):**

```
full 10-article batch:  28 docs / 438 chunks   29/32  <- BAR TRIPPED
  flip: channel-2-4ghz (curated) hit -> miss
  examination (D2): top-5 becomes ranks 1-2 Maximizing-Wireless-Speeds,
  ranks 3-4 Optimizing-WiFi, rank 5 the primer's 5 GHz chunk. Rank 2 genuinely
  answers the channels half in different words ("only select from channels 1, 6,
  and 11") while the expected item is welded to the primer phrasing
  ("non-overlapping channels: 1, 6, and 11"). Verdict: the trunk-vs-access case,
  an OR-group ground-truth wording gap, NOT noise; the article is not junk.

ablation (hold out Maximizing-Wireless-Speeds only):
                        27 docs / 421 chunks   30/32  <- BAR MET
  misses: port-profiles, poe-cycle (the standing ADR-0021 rank problems only);
  zero flips; fetched-coverage 13/13; Optimizing-WiFi stays in the batch.
```

**Disposition (within the pinned D2 rules):** batch 1 = the 9 articles above.
`Maximizing-Wireless-Speeds` is DEFERRED, not rejected: it answers real questions and
must land together with the `channel-2-4ghz` OR-group fix (a `questions.yaml` change,
locked out of this step by D3) in a small follow-up step with its own gate. That
follow-up inherits the receipt above as its justification.

Spark repo tree restored via `git checkout` (porcelain 0) and all scratch knowledge
dirs removed. `questions.yaml` untouched throughout.

## Consequences

- The bar mechanism worked as designed: it tripped once on the 10-article draft, the
  pinned examination classified the flip as a genuine-better-answer case, and the
  per-article ablation resolved it. Batch 1 lands as 9 articles: 27 docs / 421 chunks
  scratch, 30/32, zero flips, fetched coverage 13/13, the only misses the standing
  ADR-0021 rank problems.
- **Deferred, not rejected:** `Maximizing-Wireless-Speeds` answers the `channel-2-4ghz`
  question in different words ("only select from channels 1, 6, and 11" vs the primer's
  "non-overlapping channels: 1, 6, and 11"), so it must land together with that question's
  OR-group fix, a `questions.yaml` change locked out of this step by D3. That small
  follow-up step has its own gate and inherits this receipt as its justification.
- Coverage questions for the new articles follow the ADR-0020 pattern in a later step;
  until then the batch adds answerable breadth that the eval does not yet measure for
  coverage.
- Production follow-through (post-merge, Jon-gated, the Step-7 protocol): backup, sync,
  production re-ingest, count sanity vs the scratch build (expect ~421 chunks / 27 docs),
  `eval-served.sh` history line (expect 30/32), timer check, restore on degrade. The
  ADR-0019 drift posture applies to the new history line.
- The ROADMAP harvest bullet drops the stale "help.ui.com 403s from some networks" caveat
  in favor of the header-dependent finding recorded in the receipt.
