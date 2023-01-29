from __future__ import annotations

from typing import Any, Dict, Iterable, List, TYPE_CHECKING, cast

from docutils.nodes import Node, container, section
from docutils.parsers.rst import directives
from docutils.statemachine import ViewList
from sphinx.config import Config
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


def indent(string: str, indent_char: str = " ", level: int = 4) -> List[str]:
    return list((indent_char * level) + line for line in string.splitlines())


class UpgradeMixin(SphinxDirective):
    compat: bool = False

    def _render_directive_options(self) -> str:
        ret = ""
        options: Dict[str, Any] = {
            k: v for k, v in self.options.items() if k in CodeBlock.option_spec
        }
        if not self.compat:
            options["no-upgrade"] = True
        for option, value in options.items():
            if self.option_spec[option] is directives.flag:
                value = None
            if isinstance(value, Iterable) and not isinstance(value, str):
                value = "\n".join(value)
            ret += f":{option}: {value if value is not None else ''}\n"
        return ret

    def _create_tabs(
        self,
        versioned_code: VersionedCode,
        tab_title_template: str,
    ) -> List[str]:
        if len(versioned_code) == 1:
            return [
                ".. code-block:: python",
                *indent(self._render_directive_options()),
                "",
                *indent(versioned_code.popitem()[1]),
                "",
            ]

        out = [".. tab-set::", ""]
        for version, code in versioned_code.items():
            version_string = f"{version[0]}.{version[1]}"
            out.extend(
                [
                    f"    .. tab-item:: {tab_title_template.format(min_version=version_string)}",  # noqa: E501
                    f"        :sync: {version_string}",
                    "",
                    "        .. code-block:: python",
                    *indent(self._render_directive_options(), level=12),
                    "",
                    *indent(code, level=12),
                    "",
                ]
            )
        return out

    def _create_py_tab_nodes(self, code: str) -> List[Node]:
        version_requirements = self.config["auto_pytabs_versions"]
        versioned_code = version_code(
            code, version_requirements, cache=self.config["auto_pytabs_cache"]
        )
        tabs = self._create_tabs(
            versioned_code, self.env.config["auto_pytabs_tab_title_template"]
        )

        rst = ViewList()
        source, lineno = self.get_source_info()
        for line in tabs:
            rst.append(line, source, lineno)

        node = section()
        node.document = self.state.document

        nested_parse_with_titles(self.state, rst, node)
        nodes = node.children

        return cast(List[Node], nodes)


class PyTabsCodeBlock(CodeBlock, UpgradeMixin):
    compat = True

    def run(self) -> list[Node]:
        if not self.arguments or self.arguments[0] != "python":
            return super().run()

        self.assert_has_content()
        return self._create_py_tab_nodes("\n".join(self.content))


class PyTabsLiteralInclude(LiteralInclude, UpgradeMixin):
    compat = True

    def run(self) -> List[Node]:
        base_node = super().run()[0]
        if self.options.get("language") != "python":
            return [base_node]
        if isinstance(base_node, container):
            base_node = base_node.children[1]
        return self._create_py_tab_nodes(base_node.rawsource)  # type: ignore[attr-defined]  # noqa: E501


class CodeBlockOverride(PyTabsCodeBlock):
    compat = False
    option_spec = {**CodeBlock.option_spec, "no-upgrade": directives.flag}

    def run(self) -> List[Node]:
        if "no-upgrade" in self.options:
            return CodeBlock.run(self)

        return super().run()


class LiteralIncludeOverride(PyTabsLiteralInclude):
    compat = False
    option_spec = {**LiteralInclude.option_spec, "no-upgrade": directives.flag}

    def run(self) -> List[Node]:
        if "no-upgrade" in self.options:
            return LiteralInclude.run(self)
        return super().run()


def on_config_inited(app: Sphinx, config: Config) -> None:
    config["auto_pytabs_versions"] = get_version_requirements(
        config["auto_pytabs_min_version"], config["auto_pytabs_max_version"]
    )
    app.config["auto_pytabs_cache"] = (
        Cache() if not config["auto_pytabs_no_cache"] else None
    )

    if not config["auto_pytabs_compat_mode"]:
        app.add_directive("code-block", CodeBlockOverride, override=True)
        app.add_directive("literalinclude", LiteralIncludeOverride, override=True)


def on_build_finished(app: Sphinx, exception: Exception | None) -> None:
    if cache := app.config["auto_pytabs_cache"]:
        cache.persist()


def setup(app: Sphinx) -> Dict[str, bool | str]:
    app.add_directive("pytabs-code-block", PyTabsCodeBlock)
    app.add_directive("pytabs-literalinclude", PyTabsLiteralInclude)

    app.add_config_value(
        "auto_pytabs_tab_title_template",
        default="Python {min_version}+",
        rebuild="html",
    )
    app.add_config_value("auto_pytabs_min_version", default=(3, 7), rebuild="html")
    app.add_config_value("auto_pytabs_max_version", default=(3, 11), rebuild="html")
    app.add_config_value("auto_pytabs_no_cache", default=False, rebuild="html")
    app.add_config_value("auto_pytabs_compat_mode", default=False, rebuild="html")

    app.connect("config-inited", on_config_inited)

    app.connect("build-finished", on_build_finished)

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
