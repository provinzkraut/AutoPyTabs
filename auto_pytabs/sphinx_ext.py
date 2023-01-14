from __future__ import annotations

import pickle
from hashlib import sha1
from pathlib import Path
from typing import Any, Iterable, TYPE_CHECKING

from docutils.nodes import Node, section
from docutils.parsers.rst import directives
from docutils.statemachine import ViewList
from sphinx.config import Config
from sphinx.directives.code import CodeBlock, LiteralInclude
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import nested_parse_with_titles

from auto_pytabs.core import create_versioned_code

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from auto_pytabs.types import VersionedCode


CACHE_DIR = Path(".auto_pytabs_cache")


def indent(string: str, indent_char: str = " ", level: int = 4) -> list[str]:
    return list((indent_char * level) + line for line in string.splitlines())


class UpgradeMixin(SphinxDirective):
    def _render_directive_options(self) -> str:
        ret = ""
        options: dict[str, Any] = {**self.options, "no-upgrade": True}
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
    ) -> list[str]:
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
                    f"    .. tab-item:: {tab_title_template.format(min_version=version_string)}",
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

    def _create_py_tab_nodes(self, code: str) -> list[Node]:
        version_requirements = self.config["auto_pytabs_versions"]
        cache_file: Path | None = None
        if not self.config["auto_pytabs_no_cache"]:
            cache_filename = sha1(
                (code + str(version_requirements)).encode()
            ).hexdigest()
            cache_file = CACHE_DIR / cache_filename
            if cache_file.exists():
                return pickle.loads(cache_file.read_bytes())

        versioned_code = create_versioned_code(code, version_requirements)
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

        if cache_file:
            cache_file.write_bytes(pickle.dumps(nodes))

        return nodes


class UpgradeCodeBlock(CodeBlock, UpgradeMixin):
    option_spec = {**CodeBlock.option_spec, "no-upgrade": directives.flag}

    def run(self) -> list[Node]:
        if "no-upgrade" in self.options or self.arguments[0] != "python":
            return super().run()

        return self._create_py_tab_nodes("\n".join(self.content))


class UpgradeLiteralInclude(LiteralInclude, UpgradeMixin):
    option_spec = {**LiteralInclude.option_spec, "no-upgrade": directives.flag}

    def run(self) -> list[Node]:
        base_node = super().run()[0]
        if "no-upgrade" in self.options or self.options.get("language") != "python":
            return [base_node]
        return self._create_py_tab_nodes(base_node.rawsource)


def on_config_inited(app: Sphinx, config: Config) -> None:
    min_major, min_minor = config["auto_pytabs_min_version"]
    max_major, max_minor = config["auto_pytabs_max_version"]
    config["auto_pytabs_versions"] = [
        (major, minor)
        for major in range(min_major, max_major + 1)
        for minor in range(min_minor, max_minor + 1)
    ]

    CACHE_DIR.mkdir(exist_ok=True)


def setup(app: Sphinx) -> dict[str, bool | str]:
    app.add_directive("code-block", UpgradeCodeBlock, override=True)
    app.add_directive("literalinclude", UpgradeLiteralInclude, override=True)

    app.add_config_value(
        "auto_pytabs_tab_title_template",
        default="Python {min_version}+",
        rebuild="html",
    )
    app.add_config_value("auto_pytabs_min_version", default=(3, 7), rebuild="html")
    app.add_config_value("auto_pytabs_max_version", default=(3, 11), rebuild="html")
    app.add_config_value("auto_pytabs_no_cache", default=False, rebuild="html")

    app.connect("config-inited", on_config_inited)

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
