"""Discovery — find knowledge packs in-tree and out-of-tree.

In-tree:   any subpackage of ``mnemosyne.packs`` with a ``manifest.yaml``.
Out-of-tree: any installed distribution exposing a ``mnemosyne.knowledge_packs`` entry
             point (a ``KnowledgePack`` subclass or an instance). Mirrors how Argus
             discovers vendor packs (ADR-0003).
"""

from __future__ import annotations

import importlib
import logging
from importlib.metadata import entry_points
from pathlib import Path

from .base import KnowledgePack

ENTRY_POINT_GROUP = "mnemosyne.knowledge_packs"

_log = logging.getLogger(__name__)


def _builtin_root() -> Path:
    return Path(__file__).parent


def _load_builtin(directory: Path) -> KnowledgePack:
    """Instantiate an in-tree pack, using its ``pack.py`` subclass if present."""
    cls: type[KnowledgePack] = KnowledgePack
    module_name = f"{__package__}.{directory.name}.pack"
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError:
        module = None
    if module is not None:
        for value in vars(module).values():
            if (
                isinstance(value, type)
                and issubclass(value, KnowledgePack)
                and value is not KnowledgePack
            ):
                cls = value
                break
    return cls.from_directory(directory)


def _load_entry_point(obj: object) -> KnowledgePack | None:
    """Coerce an entry-point object into a KnowledgePack instance."""
    if isinstance(obj, KnowledgePack):
        return obj
    if isinstance(obj, type) and issubclass(obj, KnowledgePack):
        module = importlib.import_module(obj.__module__)
        directory = Path(module.__file__).parent if module.__file__ else Path.cwd()
        return obj.from_directory(directory)
    return None


def discover_packs() -> dict[str, KnowledgePack]:
    """Return all discoverable packs keyed by name (in-tree + entry points)."""
    packs: dict[str, KnowledgePack] = {}

    for child in sorted(_builtin_root().iterdir()):
        if child.is_dir() and (child / "manifest.yaml").exists():
            pack = _load_builtin(child)
            packs[pack.name] = pack

    for ep in entry_points(group=ENTRY_POINT_GROUP):
        try:
            ep_pack = _load_entry_point(ep.load())
        except Exception:
            _log.warning("Failed to load knowledge pack from entry point %r", ep.name)
            continue
        if ep_pack is not None:
            packs[ep_pack.name] = ep_pack

    return packs


def get_pack(name: str) -> KnowledgePack:
    """Return the pack named ``name`` or raise with the available options."""
    packs = discover_packs()
    if name not in packs:
        available = ", ".join(sorted(packs)) or "(none)"
        raise KeyError(f"Unknown knowledge pack '{name}'. Available: {available}")
    return packs[name]
