import autoflake
from pyupgrade._data import Settings as PyUpgradeSettings
from pyupgrade._main import _fix_plugins

from auto_pytabs.types import VersionTuple, VersionedCode


def upgrade(code: str, min_version: VersionTuple) -> str:
    upgraded_code = _fix_plugins(
        code,
        settings=PyUpgradeSettings(
            min_version=min_version,
            keep_percent_format=True,
            keep_mock=True,
            keep_runtime_typing=True,
        ),
    )
    if upgraded_code == code:
        return code
    return autoflake.fix_code(  # type: ignore[no-any-return]
        upgraded_code,
        remove_all_unused_imports=True,
    )


def create_versioned_code(
    code: str, version_requirements: list[VersionTuple]
) -> VersionedCode:
    latest_code = code
    versioned_code: VersionedCode = {version_requirements[0]: code}

    for version in version_requirements:
        upgraded_code = upgrade(latest_code, version)
        if upgraded_code != latest_code:
            versioned_code[version] = upgraded_code
            latest_code = upgraded_code

    return versioned_code
