from __future__ import annotations

from typing import Literal

import pytest
import yaml
from auto_pytabs.core import Cache
from auto_pytabs.mkdocs_plugin import AutoPyTabsPlugin
from mkdocs.config.base import Config, load_config


@pytest.fixture()
def setup_mkdocs(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(exist_ok=True)
    docs_dir.joinpath("index.md").write_text("# Test\n")


@pytest.fixture()
def create_mkdocs_config(request, tmp_path, setup_mkdocs):
    def _create_mkdocs_config(
        *,
        min_version: str | None = None,
        max_version: str | None = None,
        tab_title_template: str | None = None,
        no_cache: bool = False,
        default_tab: Literal["highest", "lowest"] | None = None,
        reverse_order: bool | None = None,
    ) -> Config:
        auto_pytabs_config = {}
        if min_version:
            auto_pytabs_config["min_version"] = min_version
        if max_version:
            auto_pytabs_config["max_version"] = max_version
        if tab_title_template:
            auto_pytabs_config["tab_title_template"] = tab_title_template
        if no_cache:
            auto_pytabs_config["no_cache"] = no_cache
        if default_tab:
            auto_pytabs_config["default_tab"] = default_tab
        if reverse_order is not None:
            auto_pytabs_config["reverse_order"] = reverse_order

        config = {
            "site_name": "Test docs",
            "markdown_extensions": [{"pymdownx.tabbed": None}],
            "plugins": [{"auto_pytabs": auto_pytabs_config}],
        }

        config_file = tmp_path / "mkdocs.yaml"
        config_file.write_text(yaml.dump(config))

        request.addfinalizer(config_file.unlink)

        return load_config(str(config_file))

    return _create_mkdocs_config


@pytest.fixture()
def configured_plugin(create_mkdocs_config) -> tuple[AutoPyTabsPlugin, Config]:
    config = create_mkdocs_config()
    plugin = config["plugins"]["auto_pytabs"]
    plugin.on_config(config)
    return plugin, config


@pytest.mark.parametrize(
    "reverse_order,expected_reverse_order_value",
    [(None, False), (True, True), (False, False)],
)
@pytest.mark.parametrize(
    "default_tab,expected_default_tab_value",
    [(None, "highest"), ("highest", "highest"), ("lowest", "lowest")],
)
@pytest.mark.parametrize("no_cache", [True, False])
@pytest.mark.parametrize(
    "tab_title_template", ("{min_version}", "Python {min_version} and higher")
)
@pytest.mark.parametrize("min_version,max_version", [("3.7", "3.11"), ("3.8", "3.10")])
def test_config(
    min_version,
    max_version,
    no_cache,
    tab_title_template,
    create_mkdocs_config,
    default_tab: str | None,
    expected_default_tab_value: str,
    reverse_order: bool | None,
    expected_reverse_order_value: bool,
) -> None:
    config = create_mkdocs_config(
        min_version=min_version,
        max_version=max_version,
        tab_title_template=tab_title_template,
        no_cache=no_cache,
        default_tab=default_tab,
        reverse_order=reverse_order,
    )
    plugin = config["plugins"]["auto_pytabs"]

    assert plugin
    assert isinstance(plugin, AutoPyTabsPlugin)

    plugin.on_config(config)

    received_config = config["mdx_configs"]["auto_pytabs"]

    assert "auto_pytabs" in config["markdown_extensions"]
    assert received_config["min_version"] == min_version
    assert received_config["max_version"] == max_version
    assert received_config["tab_title_template"] == tab_title_template
    assert received_config["cache"] is plugin.cache
    assert received_config["default_tab"] == expected_default_tab_value
    assert received_config["reverse_order"] == expected_reverse_order_value

    if no_cache:
        assert plugin.cache is None
    else:
        assert isinstance(plugin.cache, Cache)


def test_on_post_build(configured_plugin, mock_cache_persist) -> None:
    plugin, config = configured_plugin

    plugin.on_post_build(config)

    mock_cache_persist.assert_called_once_with()


def test_on_build_error(configured_plugin, mock_cache_persist) -> None:
    plugin, config = configured_plugin

    plugin.on_build_error(ValueError())

    mock_cache_persist.assert_called_once_with(evict=False)
