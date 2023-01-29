from __future__ import annotations

from typing import Optional

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
    def __init__(self) -> None:
        self.cache: Optional[Cache] = None

    def on_config(self, config: MkDocsConfig) -> Config | None:
        if not self.config.no_cache:
            self.cache = Cache()

        config.markdown_extensions.append("auto_pytabs")
        config["mdx_configs"].update(
            {
                "auto_pytabs": {
                    "min_version": self.config.min_version,
                    "max_version": self.config.max_version,
                    "tab_title_template": self.config.tab_title_template,
                    "cache": self.cache,
                }
            }
        )
        return None

    def on_post_build(self, config: MkDocsConfig) -> None:
        if self.cache:
            self.cache.persist()

    def on_build_error(self, error: Exception) -> None:
        if self.cache:
            self.cache.persist(evict=False)
