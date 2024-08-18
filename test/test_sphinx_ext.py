from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Callable

import pytest

from test.conftest import SphinxBuilder

if TYPE_CHECKING:
    from pytest_regressions.file_regression import FileRegressionFixture

SphinxBuilderFixture = Callable[..., SphinxBuilder]

TEST_DATA_DIR = Path("test/sphinx_ext_test_data")
SOURCE_CONTENT = (TEST_DATA_DIR / "test.rst").read_text()
SOURCE_CONTENT_COMPAT = (TEST_DATA_DIR / "test_compat.rst").read_text()


@pytest.fixture(params=[True, False], ids=lambda item: f"compat:{item}")
def compat(request) -> bool:
    return request.param


@pytest.fixture
def source(compat: bool) -> str:
    if compat:
        return SOURCE_CONTENT_COMPAT
    return SOURCE_CONTENT


@pytest.mark.parametrize("no_cache", [True, False], ids=lambda item: f"nocache:{item}")
def test_upgrade_tabs_all_versions(
    sphinx_builder: SphinxBuilderFixture,
    file_regression: FileRegressionFixture,
    no_cache: bool,
    compat: bool,
    source: str,
    mock_cache_persist,
):
    builder = sphinx_builder(
        source=source, auto_pytabs_no_cache=no_cache, compat=compat
    )

    builder.build()

    pformat = builder.get_doctree("index").pformat()
    file_regression.check(pformat, fullpath=TEST_DATA_DIR / "tabs_all_versions.xml")

    if no_cache:
        mock_cache_persist.assert_not_called()
    else:
        mock_cache_persist.assert_called_once_with()


def test_upgrade_reverse_order(
    sphinx_builder: SphinxBuilderFixture,
    file_regression: FileRegressionFixture,
    compat: bool,
    source: str,
):
    builder = sphinx_builder(
        source=source,
        auto_pytabs_no_cache=True,
        auto_pytabs_reverse_order=True,
        compat=compat,
    )

    builder.build()

    file_regression.force_regen = True
    pformat = builder.get_doctree("index").pformat()
    file_regression.check(
        pformat, fullpath=TEST_DATA_DIR / "tabs_all_versions_reversed.xml"
    )


def test_upgrade_single_version(
    sphinx_builder: SphinxBuilderFixture,
    file_regression: FileRegressionFixture,
    compat: bool,
    source: str,
):
    builder = sphinx_builder(
        source=source, compat=compat, auto_pytabs_min_version=(3, 12)
    )

    builder.build()

    pformat = builder.get_doctree("index").pformat()
    file_regression.check(pformat, fullpath=TEST_DATA_DIR / "tabs_single_version.xml")


@pytest.mark.parametrize(
    "min_version,max_version",
    [
        pytest.param((3, i), (3, j), id=f"min:3.{i}-max:3.{j}")
        for i in range(8, 13)
        for j in range(7, 13)
        if i <= j
    ],
)
def test_upgrade_versions(
    min_version: tuple[int, int],
    max_version: tuple[int, int],
    sphinx_builder: SphinxBuilderFixture,
    file_regression: FileRegressionFixture,
    compat: bool,
    source: str,
) -> None:
    if min_version > max_version:
        pytest.skip()
    builder = sphinx_builder(
        source=source,
        compat=compat,
        auto_pytabs_min_version=min_version,
        auto_pytabs_max_version=max_version,
    )

    builder.build()

    pformat = builder.get_doctree("index").pformat()

    file_regression.check(
        pformat,
        fullpath=TEST_DATA_DIR.joinpath(
            f"tabs_versions_min-{min_version[0]}{min_version[1]}_max-{max_version[0]}{max_version[1]}.xml"
        ),
    )


@pytest.mark.parametrize("reverse_order", [True, False])
@pytest.mark.parametrize("default_tab_version", ["highest", "lowest"])
def test_upgrade_default_tab(
    default_tab_version: str,
    sphinx_builder: SphinxBuilderFixture,
    file_regression: FileRegressionFixture,
    source: str,
    compat: bool,
    reverse_order: bool,
) -> None:
    builder = sphinx_builder(
        source=source,
        compat=compat,
        auto_pytabs_default_tab=default_tab_version,
        auto_pytabs_min_version=(3, 7),
        auto_pytabs_max_version=(3, 10),
        auto_pytabs_reverse_order=reverse_order,
    )
    builder.build()

    pformat = builder.get_doctree("index").pformat()

    file_stem = f"tabs_default_tab_{default_tab_version}"
    if reverse_order:
        file_stem += "_reversed"

    file_regression.check(pformat, fullpath=TEST_DATA_DIR.joinpath(file_stem + ".xml"))
