from pathlib import Path

from auto_pytabs.markdown_ext import UpgradePreprocessor
import pytest

TEST_DATA_DIR = Path("test/md_ext_test_data")


@pytest.fixture()
def preprocessor() -> UpgradePreprocessor:
    return UpgradePreprocessor(min_version="3.7", max_version="3.11", no_cache=True)


def get_test_data(name: str) -> tuple[str, str]:
    in_file = TEST_DATA_DIR / f"{name}_in.md"
    out_file = TEST_DATA_DIR / f"{name}_out.md"
    return in_file.read_text(), out_file.read_text()


def test_upgrade_single_version(file_regression):
    source, expected_output = get_test_data("upgrade_single")
    preprocessor = UpgradePreprocessor(
        min_version="3.9", max_version="3.11", no_cache=True
    )

    output = "\n".join(preprocessor.run(source.splitlines()))
    assert output == expected_output


def test_upgrade(preprocessor: UpgradePreprocessor):
    source, expected_output = get_test_data("upgrade")

    output = "\n".join(preprocessor.run(source.splitlines()))
    assert output == expected_output


def test_upgrade_custom_tab_title():
    preprocessor = UpgradePreprocessor(
        min_version="3.7",
        max_version="3.11",
        tab_title_template="Python {min_version} and above",
        no_cache=True,
    )
    source, expected_output = get_test_data("custom_tab_title")

    output = "\n".join(preprocessor.run(source.splitlines()))
    assert output == expected_output


def test_nested_tabs(preprocessor: UpgradePreprocessor):
    source, expected_output = get_test_data("nested_tabs")

    output = "\n".join(preprocessor.run(source.splitlines()))
    assert output == expected_output


def test_disable_block(preprocessor: UpgradePreprocessor):
    source, expected_output = get_test_data("disable_block")

    output = "\n".join(preprocessor.run(source.splitlines()))
    assert output == expected_output


def test_disable_section(preprocessor: UpgradePreprocessor):
    source, expected_output = get_test_data("disable_section")

    output = "\n".join(preprocessor.run(source.splitlines()))
    assert output == expected_output


def test_ignore_fenced_block(preprocessor: UpgradePreprocessor):
    source = """```json
{"foo": "bar"}
```"""

    output = "\n".join(preprocessor.run(source.splitlines()))
    assert output == source
