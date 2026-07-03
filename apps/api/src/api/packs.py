"""Analysis pack registry — discovers and loads YAML pack definitions."""

import re
from pathlib import Path

import yaml

from api.models.analysis import AnalysisPack

_PACKS_DIR = Path(__file__).resolve().parent.parent.parent / "packs"
_cache: dict[str, AnalysisPack] | None = None

# Common unit suffixes to strip when matching column names
_UNIT_SUFFIX_RE = re.compile(r"_(pct|ppm|ppb|mg_L|ug_L|ng_L|g_L|mg_kg|ug_kg|ntu|cm|mm|um|nm|km|hr|min|s|degC|degF|mV|mA|V|W|J|Pa|kPa|MPa|bar|atm|ratio)$", re.IGNORECASE)


def normalize_column_name(name: str) -> str:
    """Strip common unit suffixes from column names for matching."""
    return _UNIT_SUFFIX_RE.sub("", name)


def _discover_packs() -> dict[str, AnalysisPack]:
    packs: dict[str, AnalysisPack] = {}
    if not _PACKS_DIR.exists():
        return packs
    for fpath in sorted(_PACKS_DIR.iterdir()):
        if fpath.suffix in (".yaml", ".yml"):
            with open(fpath) as f:
                data = yaml.safe_load(f)
            pack = AnalysisPack.model_validate(data)
            packs[pack.id] = pack
    return packs


def get_all_packs() -> list[AnalysisPack]:
    global _cache
    if _cache is None:
        _cache = _discover_packs()
    return list(_cache.values())


def get_pack(pack_id: str) -> AnalysisPack | None:
    get_all_packs()
    return _cache.get(pack_id) if _cache else None


def reload_packs() -> None:
    global _cache
    _cache = _discover_packs()


def get_compatible_packs(column_names: set[str]) -> list[AnalysisPack]:
    """Return packs whose required_columns are all present after normalizing column names."""
    normalized = {normalize_column_name(c) for c in column_names}
    return [p for p in get_all_packs() if set(p.required_columns).issubset(normalized)]
