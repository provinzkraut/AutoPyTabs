from pathlib import Path
from typing import Callable

import pytest

from test.conftest import SphinxBuilder
from pytest_regressions.file_regression import FileRegressionFixture

SphinxBuilderFixture = Callable[..., SphinxBuilder]

TEST_DATA_DIR = Path("test/sphinx_ext_test_data")
SOURCE_CONTENT = (TEST_DATA_DIR / "test.rst").read_text()


@pytest.mark.parametrize("no_cache", [True, False])
def test_upgrade_tabs_all_versions(
    sphinx_builder: SphinxBuilderFixture,
    file_regression: FileRegressionFixture,
    no_cache: bool,
):
    builder = sphinx_builder(auto_pytabs_no_cache=no_cache)
    builder.src_path.joinpath("index.rst").write_text(SOURCE_CONTENT)

    builder.build()

    pformat = builder.get_doctree("index").pformat()
    file_regression.check(pformat, fullpath=TEST_DATA_DIR / "tabs_all_versions.xml")


def test_upgrade_single_version(
    sphinx_builder: SphinxBuilderFixture, file_regression: FileRegressionFixture
):
    builder = sphinx_builder(auto_pytabs_min_version=(3, 11))
    builder.src_path.joinpath("index.rst").write_text(SOURCE_CONTENT)

    builder.build()

    pformat = builder.get_doctree("index").pformat()
    file_regression.check(pformat, fullpath=TEST_DATA_DIR / "tabs_single_version.xml")


@pytest.mark.parametrize(
    "min_version,max_version",
    [((3, i), (3, j)) for i in range(8, 12) for j in range(7, 12) if i <= j],
)
def test_upgrade_min_version(
    min_version: tuple[int, int],
    max_version: tuple[int, int],
    sphinx_builder: SphinxBuilderFixture,
    file_regression: FileRegressionFixture,
) -> None:
    if min_version > max_version:
        pytest.skip()
    builder = sphinx_builder(
        auto_pytabs_min_version=min_version, auto_pytabs_max_version=max_version
    )
    builder.src_path.joinpath("index.rst").write_text(SOURCE_CONTENT)

    builder.build()

    pformat = builder.get_doctree("index").pformat()

    comp_data_file = TEST_DATA_DIR / (
        f"tabs_versions_min-{min_version[0]}{min_version[1]}_"
        f"max-{max_version[0]}{max_version[1]}.xml"
    )

    file_regression.check(
        pformat,
        fullpath=comp_data_file,
    )
