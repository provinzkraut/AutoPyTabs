from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from auto_pytabs.markdown_ext import UpgradePreprocessor

if TYPE_CHECKING:
    from pytest_regressions.file_regression import FileRegressionFixture

TEST_DATA_DIR = Path("test/md_ext_test_data")


@pytest.fixture()
def preprocessor() -> UpgradePreprocessor:
    return UpgradePreprocessor(
        min_version="3.7", max_version="3.11", default_tab_strategy="highest"
    )


def get_test_data(name: str) -> tuple[list[str], Path]:
    in_file = TEST_DATA_DIR / f"{name}_in.md"
    out_file = TEST_DATA_DIR / f"{name}_out.md"
    return in_file.read_text().splitlines(), out_file


def test_upgrade_single_version(file_regression: FileRegressionFixture):
    source, expected_output_path = get_test_data("upgrade_single")
    preprocessor = UpgradePreprocessor(
        min_version="3.9", max_version="3.11", default_tab_strategy="highest"
    )

    output = "\n".join(preprocessor.run(source))
    file_regression.check(output, fullpath=expected_output_path)


@pytest.mark.parametrize(
    "reverse_order", [False, True], ids=lambda item: f"reverse:{item}"
)
@pytest.mark.parametrize("default_tab_strategy", ["highest", "lowest"])
def test_upgrade(
    default_tab_strategy: str,
    reverse_order: bool,
    file_regression: FileRegressionFixture,
):
    source = TEST_DATA_DIR.joinpath("upgrade_in.md").read_text()
    file_stem = f"upgrade_out_default_{default_tab_strategy}"
    if reverse_order:
        file_stem += "_reversed"
    expected_output = TEST_DATA_DIR.joinpath(file_stem + ".md")

    preprocessor = UpgradePreprocessor(
        min_version="3.7",
        max_version="3.11",
        default_tab_strategy=default_tab_strategy,
        reverse_order=reverse_order,
    )
    file_regression.force_regen = True
    output = "\n".join(preprocessor.run(source.splitlines()))
    file_regression.check(output, fullpath=expected_output)


def test_upgrade_custom_tab_title(file_regression: FileRegressionFixture):
    preprocessor = UpgradePreprocessor(
        min_version="3.7",
        max_version="3.11",
        tab_title_template="Python {min_version} and above",
        default_tab_strategy="highest",
    )
    source, expected_output_path = get_test_data("custom_tab_title")

    output = "\n".join(preprocessor.run(source))
    file_regression.check(output, fullpath=expected_output_path)


def test_nested_tabs(
    preprocessor: UpgradePreprocessor, file_regression: FileRegressionFixture
):
    source, expected_output_path = get_test_data("nested_tabs")

    output = "\n".join(preprocessor.run(source))
    file_regression.check(output, fullpath=expected_output_path)


def test_disable_block(
    preprocessor: UpgradePreprocessor, file_regression: FileRegressionFixture
):
    source, expected_output_path = get_test_data("disable_block")

    output = "\n".join(preprocessor.run(source))
    file_regression.check(output, fullpath=expected_output_path)


def test_disable_section(
    preprocessor: UpgradePreprocessor, file_regression: FileRegressionFixture
):
    source, expected_output_path = get_test_data("disable_section")

    output = "\n".join(preprocessor.run(source))
    file_regression.check(output, fullpath=expected_output_path)


def test_ignore_fenced_block(preprocessor: UpgradePreprocessor):
    source = """```json
{"foo": "bar"}
```"""

    output = "\n".join(preprocessor.run(source.splitlines()))
    assert output == source
