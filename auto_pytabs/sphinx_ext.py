from __future__ import annotations

import importlib
import importlib.metadata
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, Literal

from docutils.nodes import Node, container, section
from docutils.parsers.rst import directives
from docutils.statemachine import StringList
from sphinx.directives.code import CodeBlock, LiteralInclude
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import nested_parse_with_titles

from auto_pytabs.core import (
    Cache,
    VersionedCode,
    get_version_requirements,
    version_code,
)

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.config import Config
    from sphinx.environment import BuildEnvironment


def indent(
    text: str | Iterable[str], indent_char: str = " ", level: int = 4
) -> list[str]:
    lines = text.splitlines() if isinstance(text, str) else text
    return list((indent_char * level) + line for line in lines)


def _render_directive(
    *,
    name: str,
    argument: str = "",
    options: dict[str, Any] | None = None,
    body: str | Iterable[str],
) -> list[str]:
    directive = [f".. {name}:: {argument}"]
    if options:
        rendered_options = [
            f":{option}: {value if (value is not True and value) else ''}"
            for option, value in options.items()
            if value is not False
        ]
        directive.extend(indent(rendered_options))

    directive.append("")
    directive.extend(indent(body))

    return directive


class UpgradeMixin(SphinxDirective):
    compat: bool = False

    def _get_directive_options(self) -> dict[str, Any]:
        options: dict[str, Any] = {}
        if not self.compat:
            options["no-upgrade"] = True
        for option, value in self.options.items():
            if option not in CodeBlock.option_spec:
                continue
            if self.option_spec and self.option_spec[option] is directives.flag:
                value = True
            if isinstance(value, Iterable) and not isinstance(value, str):
                value = "\n".join(value)
            options[option] = value
        return options

    def _create_tabs(
        self,
        versioned_code: VersionedCode,
        tab_title_template: str,
    ) -> list[str]:
        directive_options = self._get_directive_options()
        if len(versioned_code) == 1:
            return _render_directive(
                name="code-block",
                argument="python",
                body=versioned_code.popitem()[1],
                options=directive_options,
            )

        default_tab_strategy: Literal["highest", "lowest"] = self.config[
            "auto_pytabs_default_tab"
        ]
        versions = list(versioned_code.keys())
        default_selected_version = versions[
            -1 if default_tab_strategy == "highest" else 0
        ]

        tab_set_body = []
        if self.config["auto_pytabs_reverse_order"]:
            versioned_code = dict(reversed(versioned_code.items()))

        for version, code in versioned_code.items():
            version_string = f"{version[0]}.{version[1]}"
            code_block = _render_directive(
                name="code-block",
                argument="python",
                options=directive_options,
                body=code,
            )
            tab_item = _render_directive(
                name="tab-item",
                argument=tab_title_template.format(min_version=version_string),
                options={
                    "sync": version_string,
                    "selected": version == default_selected_version,
                },
                body=code_block,
            )
            tab_set_body.extend(tab_item)

        return _render_directive(name="tab-set", body=tab_set_body)

    @property
    def cache(self) -> Cache | None:
        return getattr(self.env, "auto_pytabs_cache", None)

    def _create_py_tab_nodes(self, code: str) -> list[Node]:
        version_requirements = self.config["auto_pytabs_versions"]
        versioned_code = version_code(code, version_requirements, cache=self.cache)
        tabs = self._create_tabs(
            versioned_code, self.env.config["auto_pytabs_tab_title_template"]
        )

        rst = StringList()
        source, lineno = self.get_source_info()
        for line in tabs:
            rst.append(line, source, lineno)

        node = section()
        node.document = self.state.document

        nested_parse_with_titles(self.state, rst, node)
        return node.children


class PyTabsCodeBlock(CodeBlock, UpgradeMixin):
    compat = True

    def run(self) -> list[Node]:
        if not self.arguments or self.arguments[0] != "python":
            return super().run()

        self.assert_has_content()
        return self._create_py_tab_nodes("\n".join(self.content))


class PyTabsLiteralInclude(LiteralInclude, UpgradeMixin):
    compat = True

    def run(self) -> list[Node]:
        base_node = super().run()[0]
        if self.options.get("language") != "python":
            return [base_node]
        if isinstance(base_node, container):
            base_node = base_node.children[1]
        return self._create_py_tab_nodes(base_node.rawsource)  # type: ignore[attr-defined]


class CodeBlockOverride(PyTabsCodeBlock):
    compat = False
    option_spec = {**CodeBlock.option_spec, "no-upgrade": directives.flag}  # type: ignore[misc]  # noqa: RUF012

    def run(self) -> list[Node]:
        if "no-upgrade" in self.options:
            return CodeBlock.run(self)

        return super().run()


class LiteralIncludeOverride(PyTabsLiteralInclude):
    compat = False
    option_spec = {  # type: ignore[misc]  # noqa: RUF012
        **LiteralInclude.option_spec,
        "no-upgrade": directives.flag,
    }

    def run(self) -> list[Node]:
        if "no-upgrade" in self.options:
            return LiteralInclude.run(self)
        return super().run()


def on_config_inited(app: Sphinx, config: Config) -> None:
    config["auto_pytabs_versions"] = get_version_requirements(
        config["auto_pytabs_min_version"], config["auto_pytabs_max_version"]
    )

    if not config["auto_pytabs_compat_mode"]:
        app.add_directive("code-block", CodeBlockOverride, override=True)
        app.add_directive("literalinclude", LiteralIncludeOverride, override=True)


def on_build_finished(app: Sphinx, exception: Exception | None) -> None:
    if cache := getattr(app.env, "auto_pytabs_cache", None):
        cache.persist()


def on_env_before_read_docs(
    app: Sphinx, env: BuildEnvironment, docnames: list[str]
) -> None:
    if not app.config["auto_pytabs_no_cache"]:
        env.auto_pytabs_cache = Cache()  # type: ignore[attr-defined]


def on_env_merge_info(
    app: Sphinx, env: BuildEnvironment, docnames: list[str], other: BuildEnvironment
) -> None:
    cache: Cache | None = getattr(env, "auto_pytabs_cache", None)
    other_cache: Cache | None = getattr(other, "auto_pytabs_cache", None)
    if cache and other_cache:
        cache._touched.update(other_cache._touched)
        cache._cache.update(other_cache._cache)


def setup(app: Sphinx) -> dict[str, bool | str]:
    app.add_directive("pytabs-code-block", PyTabsCodeBlock)
    app.add_directive("pytabs-literalinclude", PyTabsLiteralInclude)

    app.add_config_value(
        "auto_pytabs_tab_title_template",
        default="Python {min_version}+",
        rebuild="html",
    )
    app.add_config_value("auto_pytabs_min_version", default=(3, 7), rebuild="html")
    app.add_config_value("auto_pytabs_max_version", default=(3, 12), rebuild="html")
    app.add_config_value("auto_pytabs_no_cache", default=False, rebuild="html")
    app.add_config_value("auto_pytabs_compat_mode", default=False, rebuild="html")
    app.add_config_value("auto_pytabs_default_tab", default="highest", rebuild="html")
    app.add_config_value("auto_pytabs_reverse_order", default=False, rebuild="html")

    app.connect("config-inited", on_config_inited)
    app.connect("build-finished", on_build_finished)
    app.connect("env-before-read-docs", on_env_before_read_docs)
    app.connect("env-merge-info", on_env_merge_info)

    return {
        "version": importlib.metadata.version("auto_pytabs"),
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
