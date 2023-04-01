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
        min_version: str | None = None,
        max_version: str | None = None,
        tab_title_template: str | None = None,
        no_cache: bool = False,
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


@pytest.mark.parametrize("no_cache", [True, False])
@pytest.mark.parametrize(
    "tab_title_template", ("{min_version}", "Python {min_version} and higher")
)
@pytest.mark.parametrize("min_version,max_version", [("3.7", "3.11"), ("3.8", "3.10")])
def test_config(
    min_version, max_version, no_cache, tab_title_template, create_mkdocs_config
) -> None:
    config = create_mkdocs_config(
        min_version=min_version,
        max_version=max_version,
        tab_title_template=tab_title_template,
        no_cache=no_cache,
    )
    plugin = config["plugins"]["auto_pytabs"]

    assert plugin
    assert isinstance(plugin, AutoPyTabsPlugin)

    plugin.on_config(config)

    assert "auto_pytabs" in config["markdown_extensions"]
    assert config["mdx_configs"]["auto_pytabs"]["min_version"] == min_version
    assert config["mdx_configs"]["auto_pytabs"]["max_version"] == max_version
    assert (
        config["mdx_configs"]["auto_pytabs"]["tab_title_template"] == tab_title_template
    )
    if no_cache:
        assert plugin.cache is None
    else:
        assert isinstance(plugin.cache, Cache)

    assert config["mdx_configs"]["auto_pytabs"]["cache"] is plugin.cache


def test_on_post_build(configured_plugin, mock_cache_persist) -> None:
    plugin, config = configured_plugin

    plugin.on_post_build(config)

    mock_cache_persist.assert_called_once_with()


def test_on_build_error(configured_plugin, mock_cache_persist) -> None:
    plugin, config = configured_plugin

    plugin.on_build_error(ValueError())

    mock_cache_persist.assert_called_once_with(evict=False)
