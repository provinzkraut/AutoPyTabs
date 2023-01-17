from __future__ import annotations

from typing import Dict, List

from hashlib import sha1
from pathlib import Path

import autoflake  # type: ignore
from pyupgrade._data import Settings as PyUpgradeSettings  # type: ignore
from pyupgrade._main import _fix_plugins  # type: ignore

from auto_pytabs.types import VersionTuple, VersionedCode

CACHE_DIR = Path(".auto_pytabs_cache")

_CODE_CACHE: Dict[str, str] = {}


def upgrade_code(code: str, min_version: VersionTuple, no_cache: bool = False) -> str:
    cache_file: Path | None = None
    cache_key: str | None = None
    if not no_cache:
        cache_key = sha1((code + str(min_version)).encode()).hexdigest()

        if cached_code := _CODE_CACHE.get(cache_key):
            return cached_code

        cache_file = CACHE_DIR / cache_key
        CACHE_DIR.mkdir(exist_ok=True)

        if cache_file.exists():
            cached_code = cache_file.read_text()
            _CODE_CACHE[cache_key] = cached_code
            return cached_code

    upgraded_code = _fix_plugins(
        code,
        settings=PyUpgradeSettings(
            min_version=min_version,
            keep_percent_format=True,
            keep_mock=True,
            keep_runtime_typing=True,
        ),
    )
    if upgraded_code != code:
        code = autoflake.fix_code(upgraded_code, remove_all_unused_imports=True)

    if cache_file and cache_key:
        _CODE_CACHE[cache_key] = code
        cache_file.write_text(code)

    return code


def version_code(
    code: str, version_requirements: List[VersionTuple], no_cache: bool = False
) -> VersionedCode:
    latest_code = code
    versioned_code: VersionedCode = {version_requirements[0]: code}

    for version in version_requirements:
        upgraded_code = upgrade_code(latest_code, version, no_cache=no_cache)
        if upgraded_code != latest_code:
            versioned_code[version] = upgraded_code
            latest_code = upgraded_code

    return versioned_code
