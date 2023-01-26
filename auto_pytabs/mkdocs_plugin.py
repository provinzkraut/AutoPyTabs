from __future__ import annotations

from mkdocs.config import Config, config_options
from mkdocs.config.defaults import MkDocsConfig
from mkdocs.plugins import BasePlugin

from auto_pytabs.core import Cache


class PluginConfig(Config):  # type: ignore[no-untyped-call]
    min_version = config_options.Type(str, default="3.7")
    max_version = config_options.Type(str, default="3.11")
    tab_title_template = config_options.Type(str, default="Python {min_version}+")
    no_cache = config_options.Type(bool, default=False)


class AutoPyTabsPlugin(BasePlugin[PluginConfig]):  # type: ignore[no-untyped-call]
    def on_config(self, config: MkDocsConfig) -> Config | None:
        config.markdown_extensions.append("auto_pytabs")
        config["mdx_configs"].update(
            {
                "auto_pytabs": {
                    "min_version": self.config.min_version,
                    "max_version": self.config.max_version,
                    "tab_title_template": self.config.tab_title_template,
                    "no_cache": self.config.no_cache,
                }
            }
        )
        return None

    def on_post_build(self, config: MkDocsConfig) -> None:
        Cache.evict_unused()

    def on_build_error(self, error: Exception) -> None:
        Cache.evict_unused()
