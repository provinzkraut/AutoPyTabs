from __future__ import annotations

import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from hashlib import sha1
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
    """
    Simple hybrid file system / memory cache.

    Follows the
    `Cache Directory Tagging Specification http://www.brynosaurus.com/cachedir/>`_.
    """

    def __init__(self) -> None:
        self.cache_dir = Path(".auto_pytabs_cache")
        self.cache_content_dir = self.cache_dir / "content"
        self._cache: Dict[str, str] = {}
        self._touched: Set[str] = set()
        self._load()

    def _init_cache_dir(self) -> None:
        self.cache_content_dir.mkdir(exist_ok=True, parents=True)
        cachedir_tag = self.cache_dir / "CACHEDIR.TAG"
        gitignore_file = self.cache_dir / ".gitignore"
        if not cachedir_tag.exists():
            cachedir_tag.write_text(
                """Signature: 8a477f597d28d172789f06886806bc55
# This file is a cache directory tag created by (application name).
# For information about cache directory tags, see:
#	http://www.brynosaurus.com/cachedir/"""
            )
        if not gitignore_file.exists():
            gitignore_file.write_text("*\n")

    def _load(self) -> None:
        self._init_cache_dir()

        cache: Dict[str, str] = {}
        with ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(file.read_text): file.name
                for file in self.cache_content_dir.iterdir()
            }
            for future in as_completed(futures):
                cache[futures[future]] = future.result()
        self._cache.update(cache)

    @staticmethod
    def make_cache_key(*parts: Any) -> str:
        """Create a cache key using an md5 hash of ``parts``"""
        return sha1("".join(map(str, parts)).encode()).hexdigest()

    def get(self, key: str) -> Optional[str]:
        """Get an item specified by ``key`` the cache"""
        self._touched.add(key)
        return self._cache.get(key)

    def set(self, key: str, content: str) -> None:
        """Store an ``content``"""
        self._cache[key] = content
        self._touched.add(key)

    def persist(self, evict: bool = True) -> None:
        """
        Persist internal cache to disk. If ``evict`` is ``True``, evict unused items
        """
        with ThreadPoolExecutor() as executor:
            for key, content in self._cache.items():
                if key in self._touched:
                    executor.submit(
                        self.cache_content_dir.joinpath(key).write_text, content
                    )
                elif evict:
                    executor.submit(
                        self.cache_content_dir.joinpath(key).unlink, missing_ok=True
                    )

    def clear_all(self) -> None:
        """Clear all cached items from memory and disk"""
        self._cache = {}
        self._touched = set()

        if not self.cache_dir.exists():
            return

        shutil.rmtree(self.cache_dir)


def get_version_requirements(
    min_version: VersionTuple, max_version: VersionTuple
) -> List[VersionTuple]:
    """Given a min and max version, generate all versions in between"""
    min_major, min_minor = min_version
    max_major, max_minor = max_version
    return [
        VersionTuple(major=major, minor=minor)
        for major in range(min_major, max_major + 1)
        for minor in range(min_minor, max_minor + 1)
    ]


def _upgrade_code(
    code: str, min_version: VersionTuple, cache: Optional[Cache] = None
) -> str:
    cache_key: Optional[str] = None
    if cache:
        cache_key = cache.make_cache_key(code, min_version)

        if cached_code := cache.get(cache_key):
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

    if cache_key and cache:
        cache.set(cache_key, code)

    return code


def version_code(
    code: str, version_requirements: List[VersionTuple], cache: Optional[Cache] = None
) -> VersionedCode:
    """Create versions of ``code`` for all python versions specified in
    ``version_requirements`` and return a dictionary of version-tuples/code"""
    latest_code = code
    versioned_code: VersionedCode = {version_requirements[0]: code}

    for version in version_requirements:
        upgraded_code = _upgrade_code(latest_code, version, cache=cache)
        if upgraded_code != latest_code:
            versioned_code[version] = upgraded_code
            latest_code = upgraded_code

    return versioned_code
