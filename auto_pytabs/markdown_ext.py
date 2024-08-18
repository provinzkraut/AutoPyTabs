from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Literal, cast

from markdown import Extension
from markdown.preprocessors import Preprocessor

from auto_pytabs.core import (
    Cache,
    VersionedCode,
    VersionTuple,
    get_version_requirements,
    version_code,
)

if TYPE_CHECKING:
    from markdown import Markdown


RGX_BLOCK_TOKENS = re.compile(r"(.*```py[\w\W]*)|(.*```)")
RGX_PYTABS_DIRECTIVE = re.compile(r"<!-- ?autopytabs: ?(.*)-->")

PyTabDirective = Literal["disable", "enable", "disable-block"]
PYTAB_DIRECTIVES: set[PyTabDirective] = {"disable", "enable", "disable-block"}


def _strip_indentation(lines: list[str]) -> tuple[list[str], str]:
    if not lines:
        return [], ""
    first_line = lines[0]
    indent_char = ""
    if first_line[0] in [" ", "\t"]:
        indent_char = first_line[0]
    indent = indent_char * (len(first_line) - len(first_line.lstrip(indent_char)))
    if indent:
        return [line.split(indent, 1)[1] if line else "" for line in lines], indent
    return lines, indent


def _add_indentation(source: str | list[str], indentation: str) -> str:
    lines = source.splitlines() if isinstance(source, str) else source
    return "\n".join(indentation + line for line in lines)


def _get_pytabs_directive(line: str) -> PyTabDirective | None:
    match = RGX_PYTABS_DIRECTIVE.match(line)
    if match:
        matched_directive = match.group(1).strip()
        if matched_directive in PYTAB_DIRECTIVES:
            return cast(PyTabDirective, matched_directive)
        raise RuntimeError(f"Invalid AutoPytabs directive: {matched_directive!r}")
    return None


def _extract_code_blocks(lines: list[str]) -> tuple[list[str], dict[int, list[str]]]:
    in_block = False
    enabled = True
    new_lines: list[str] = []

    to_transform = {}

    start = 0
    for i, line in enumerate(lines):
        is_comment_line = False
        directive = _get_pytabs_directive(line)
        if directive:
            is_comment_line = True
            if directive == "disable":
                enabled = False
            elif directive == "enable":
                enabled = True

        match = RGX_BLOCK_TOKENS.match(line)
        if match:
            if match.group(1):
                in_block = True
                start = i
            elif match.group(2) and in_block:
                in_block = False
                block = lines[start : i + 1]
                block_directive = _get_pytabs_directive(lines[start - 1])
                if enabled and block_directive != "disable-block":
                    to_transform[len(new_lines)] = block
                    new_lines.append("")
                else:
                    new_lines.extend(block)
            else:
                new_lines.append(line)
        elif not in_block and not is_comment_line:
            new_lines.append(line)

    return new_lines, to_transform


def _build_tab(title: str, body: list[str], selected: bool) -> str:
    out = f'==={"+" if selected else ""} "{title}"\n'
    out += _add_indentation(body, indentation="    ")
    out += "\n"
    return out


def _build_tabs(
    *,
    versioned_code: VersionedCode,
    head: str,
    tail: str,
    tab_title_template: str,
    default_tab_version: VersionTuple,
    reverse_order: bool,
) -> str:
    out = []
    for version, code in versioned_code.items():
        version_string = f"{version[0]}.{version[1]}"
        lines = [head, *code.splitlines(), tail]
        tab_title = tab_title_template.format(min_version=version_string)
        out.append(
            _build_tab(
                title=tab_title, body=lines, selected=version == default_tab_version
            )
        )
    if reverse_order:
        out = reversed(out)  # type: ignore[assignment]
    return "\n".join(out)


def _convert_block(
    *,
    block: list[str],
    versions: list[VersionTuple],
    tab_title_template: str,
    cache: Cache | None,
    default_tab_strategy: Literal["highest", "lowest"],
    reverse_order: bool,
) -> str:
    block, indentation = _strip_indentation(block)
    head, *code_lines, tail = block
    code = "\n".join(code_lines)
    versioned_code = version_code(code, versions, cache=cache)

    if len(versioned_code) > 1:
        versions = list(versioned_code.keys())
        default_tab_version = versions[-1 if default_tab_strategy == "highest" else 0]

        code = _build_tabs(
            versioned_code=versioned_code,
            head=head,
            tail=tail,
            tab_title_template=tab_title_template,
            default_tab_version=default_tab_version,
            reverse_order=reverse_order,
        )
    else:
        code = "\n".join([head, versioned_code[versions[0]], tail])

    return _add_indentation(code, indentation)


class UpgradePreprocessor(Preprocessor):
    def __init__(
        self,
        *args: Any,
        min_version: str,
        max_version: str,
        tab_title_template: str | None = None,
        cache: Cache | None = None,
        default_tab_strategy: Literal["highest", "lowest"] = "highest",
        reverse_order: bool = False,
        **kwargs: Any,
    ) -> None:
        self.min_version = VersionTuple.from_string(min_version)
        self.max_version = VersionTuple.from_string(max_version)
        self.versions = get_version_requirements(self.min_version, self.max_version)
        self.tab_title_template = tab_title_template or "Python {min_version}+"
        self.cache = cache
        self.default_tab_strategy = default_tab_strategy
        self.reverse_order = reverse_order
        super().__init__(*args, **kwargs)

    def run(self, lines: list[str]) -> list[str]:
        new_lines, to_transform = _extract_code_blocks(lines)

        output_lines = []
        for i, line in enumerate(new_lines):
            block_to_transform = to_transform.get(i)
            if block_to_transform:
                transformed_block = _convert_block(
                    block=block_to_transform,
                    versions=self.versions,
                    tab_title_template=self.tab_title_template,
                    cache=self.cache,
                    default_tab_strategy=self.default_tab_strategy,
                    reverse_order=self.reverse_order,
                ).splitlines()
                output_lines.extend(transformed_block)
            else:
                output_lines.append(line)

        return output_lines


class AutoPyTabsExtension(Extension):
    def __init__(self, *args: Any, cache: Cache | None, **kwargs: Any):
        self.config = {
            "min_version": ["3.7", "minimum version"],
            "max_version": ["3.12", "maximum version"],
            "tab_title_template": ["", "tab title format-string"],
            "default_tab": ["highest", "version tab to preselect"],
            "reverse_order": [False, "reverse the order of tabs"],
        }
        self.cache = cache
        super().__init__(*args, **kwargs)

    def extendMarkdown(self, md: Markdown) -> None:
        """Register the extension."""
        self.md = md
        md.registerExtension(self)
        config = self.getConfigs()

        md.preprocessors.register(
            UpgradePreprocessor(
                min_version=config["min_version"],
                max_version=config["max_version"],
                tab_title_template=config["tab_title_template"],
                cache=self.cache,
                default_tab_strategy=config["default_tab"],
                reverse_order=config["reverse_order"],
            ),
            "auto_pytabs",
            32,
        )


def makeExtension(**kwargs: Any) -> AutoPyTabsExtension:
    return AutoPyTabsExtension(**kwargs)
