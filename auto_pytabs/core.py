from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import md5
from pathlib import Path
from typing import Any, Dict, List, Optional

import autoflake  # type: ignore
from pyupgrade._data import Settings as PyUpgradeSettings  # type: ignore
from pyupgrade._main import _fix_plugins  # type: ignore

from auto_pytabs.types import VersionTuple, VersionedCode


class Cache:
    instance: Optional[Cache] = None

    def __new__(cls) -> Cache:
        if cls.instance is None:
            cls.instance = super().__new__(cls)
        return cls.instance

    def __init__(self) -> None:
        self.cache_dir = Path(".auto_pytabs_cache")
        self.cache_dir.mkdir(exist_ok=True)
        self._cache: Dict[str, str] = {}
        self._initialised = False
        self._load_cache()

    def _load_cache(self) -> None:
        if self._initialised:
            return
        cache: Dict[str, str] = {}
        with ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(file.read_text): file.name
                for file in self.cache_dir.iterdir()
            }
            for future in as_completed(futures):
                cache[futures[future]] = future.result()
        self._cache.update(cache)
        self._initialised = True

    @staticmethod
    def make_cache_key(*parts: Any) -> str:
        return md5("".join(map(str, parts)).encode()).hexdigest()

    def get(self, key: str) -> Optional[str]:
        return self._cache.get(key)

    def set(self, key: str, content: str) -> None:
        self._cache[key] = content
        self.cache_dir.joinpath(key).write_text(content)

    def clear(self) -> None:
        for file in self.cache_dir.iterdir():
            file.unlink()


CACHE = Cache()


def upgrade_code(code: str, min_version: VersionTuple, no_cache: bool = False) -> str:
    cache_key: str | None = None
    if not no_cache:
        cache_key = Cache.make_cache_key(code, min_version)

        if cached_code := CACHE.get(cache_key):
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
        CACHE.set(cache_key, code)

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
