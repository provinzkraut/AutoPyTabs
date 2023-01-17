from __future__ import annotations

from typing import List

from auto_pytabs.types import VersionTuple


def get_version_requirements(
    min_version: VersionTuple, max_version: VersionTuple
) -> List[VersionTuple]:
    min_major, min_minor = min_version
    max_major, max_minor = max_version
    return [
        (major, minor)
        for major in range(min_major, max_major + 1)
        for minor in range(min_minor, max_minor + 1)
    ]


def parse_version_tuple(version: str) -> VersionTuple:
    major, minor = version.split(".")
    return int(major), int(minor)


def parse_version_requirements(
    min_version: str, max_version: str
) -> List[VersionTuple]:
    return get_version_requirements(
        parse_version_tuple(min_version), parse_version_tuple(max_version)
    )
