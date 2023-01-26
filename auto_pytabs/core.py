from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import md5
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Set

import autoflake  # type: ignore
from pyupgrade._data import Settings as PyUpgradeSettings  # type: ignore
from pyupgrade._main import _fix_plugins  # type: ignore


class VersionTuple(NamedTuple):
    major: int
    minor: int

    @classmethod
    def from_string(cls, version: str) -> VersionTuple:
        major, minor = version.split(".")
        return VersionTuple(major=int(major), minor=int(minor))


VersionedCode = Dict[VersionTuple, str]


class Cache:
    _initialised = False
    _cache: Dict[str, str] = {}
    _touched: Set[str] = set()
    cache_dir = Path(".auto_pytabs_cache")

    @classmethod
    def _initialise(cls) -> None:
        if cls._initialised:
            return

        cls.cache_dir.mkdir(exist_ok=True)

        cache: Dict[str, str] = {}
        with ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(file.read_text): file.name
                for file in cls.cache_dir.iterdir()
            }
            for future in as_completed(futures):
                cache[futures[future]] = future.result()
        cls._cache.update(cache)
        cls._initialised = True

    @staticmethod
    def make_cache_key(*parts: Any) -> str:
        return md5("".join(map(str, parts)).encode()).hexdigest()

    @classmethod
    def get(cls, key: str) -> Optional[str]:
        cls._initialise()
        cls._touched.add(key)
        return cls._cache.get(key)

    @classmethod
    def set(cls, key: str, content: str) -> None:
        cls._initialise()
        cls._cache[key] = content
        cls._touched.add(key)
        cls.cache_dir.joinpath(key).write_text(content)

    @classmethod
    def clear_all(cls) -> None:
        cls._cache = {}
        cls._touched = set()
        cls._initialised = False

        if not cls.cache_dir.exists():
            return

        for file in cls.cache_dir.iterdir():
            file.unlink()

    @classmethod
    def evict_unused(cls) -> None:
        if not cls.cache_dir.exists():
            return

        with ThreadPoolExecutor() as executor:
            for key in cls._cache.keys() - cls._touched:
                executor.submit(cls.cache_dir.joinpath(key).unlink, missing_ok=True)
                if key in cls._cache:
                    del cls._cache[key]


def get_version_requirements(
    min_version: VersionTuple, max_version: VersionTuple
) -> List[VersionTuple]:
    min_major, min_minor = min_version
    max_major, max_minor = max_version
    return [
        VersionTuple(major=major, minor=minor)
        for major in range(min_major, max_major + 1)
        for minor in range(min_minor, max_minor + 1)
    ]


def upgrade_code(code: str, min_version: VersionTuple, no_cache: bool = False) -> str:
    cache_key: str | None = None
    if not no_cache:
        cache_key = Cache.make_cache_key(code, min_version)

        if cached_code := Cache.get(cache_key):
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

    if cache_key:
        Cache.set(cache_key, code)

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
