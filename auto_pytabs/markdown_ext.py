from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Literal, NamedTuple, cast, Set, List, Dict, Tuple

import markdown
from markdown import Extension
from markdown.preprocessors import Preprocessor

from auto_pytabs.core import version_code
from auto_pytabs.util import parse_version_requirements
from auto_pytabs.types import VersionTuple, VersionedCode


RGX_BLOCK_TOKENS = re.compile(r"(.*```py[\w\W]*)|(.*```)")
RGX_PYTABS_DIRECTIVE = re.compile(r"<!-- ?autopytabs: ?(.*)-->")

PyTabDirective = Literal["disable", "enable", "disable-block"]
PYTAB_DIRECTIVES: Set[PyTabDirective] = {"disable", "enable", "disable-block"}


class PendingTransformation(NamedTuple):
    tmp_docs_file: Path
    new_lines: List[str]
    to_upgrade: Dict[int, List[str]]


def _strip_indentation(lines: List[str]) -> Tuple[List[str], str]:
    if not lines:
        return [], ""
    first_line = lines[0]
    indent_char = ""
    if first_line[0] in [" ", "\t"]:
        indent_char = first_line[0]
    indent = indent_char * (len(first_line) - len(first_line.lstrip(indent_char)))
    if indent:
        return [line.split(indent, 1)[1] for line in lines], indent
    return lines, indent


def _add_indentation(code: str, indentation: str) -> str:
    return "\n".join(indentation + line for line in code.splitlines())


def _get_pytabs_directive(line: str) -> PyTabDirective | None:
    match = RGX_PYTABS_DIRECTIVE.match(line)
    if match:
        matched_directive = match.group(1).strip()
        if matched_directive in PYTAB_DIRECTIVES:
            return cast(PyTabDirective, matched_directive)
        raise RuntimeError(f"Invalid AutoPytabs directive: {matched_directive!r}")
    return None


def extract_code_blocks(lines: List[str]) -> Tuple[List[str], Dict[int, List[str]]]:
    in_block = False
    enabled = True
    new_lines: List[str] = []

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


def _build_tabs(
    *, versioned_code: VersionedCode, head: str, tail: str, tab_title_template: str
) -> str:
    out = []
    for version, code in versioned_code.items():
        version_string = f"{version[0]}.{version[1]}"
        lines = [head, *code.splitlines(), tail]
        code = "\n".join("    " + line for line in lines)
        tab_title = tab_title_template.format(min_version=version_string)
        out.append(f'=== "{tab_title}"\n{code}\n')
    return "\n".join(out)


def convert_block(
    *,
    block: List[str],
    versions: List[VersionTuple],
    tab_title_template: str,
    no_cache: bool,
) -> str:
    block, indentation = _strip_indentation(block)
    head, *code_lines, tail = block
    code = "\n".join(code_lines)
    versioned_code = version_code(code, versions, no_cache=no_cache)

    if len(versioned_code) > 1:
        code = _build_tabs(
            versioned_code=versioned_code,
            head=head,
            tail=tail,
            tab_title_template=tab_title_template,
        )
    else:
        code = "\n".join([head, versioned_code[versions[0]], tail])

    code = _add_indentation(code, indentation)

    return code


class UpgradePreprocessor(Preprocessor):
    def __init__(
        self,
        *args: Any,
        min_version: str,
        max_version: str,
        tab_title_template: str | None = None,
        no_cache: bool = False,
        **kwargs: Any,
    ) -> None:
        self.versions = parse_version_requirements(min_version, max_version)
        self.tab_title_template = tab_title_template or "Python {min_version}+"
        self.no_cache = no_cache
        super().__init__(*args, **kwargs)

    def run(self, lines: List[str]) -> List[str]:
        new_lines, to_transform = extract_code_blocks(lines)

        output_lines = []
        for i, line in enumerate(new_lines):
            block_to_transform = to_transform.get(i)
            if block_to_transform:
                transformed_block = convert_block(
                    block=block_to_transform,
                    versions=self.versions,
                    tab_title_template=self.tab_title_template,
                    no_cache=self.no_cache,
                ).splitlines()
                output_lines.extend(transformed_block)
            else:
                output_lines.append(line)

        return output_lines


class AutoPyTabsExtension(Extension):
    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize."""

        self.config = {
            "min_version": ["3.7", "minimum version"],
            "max_version": ["3.11", "maximum version"],
            "tab_title_template": ["", "tab title format-string"],
            "no_cache": [False, "disable caching"],
        }
        super().__init__(*args, **kwargs)

    def extendMarkdown(self, md: markdown.Markdown) -> None:
        """Register the extension."""

        self.md = md
        md.registerExtension(self)
        config = self.getConfigs()
        md.preprocessors.register(
            UpgradePreprocessor(
                min_version=config["min_version"],
                max_version=config["max_version"],
                tab_title_template=config["tab_title_template"],
            ),
            "auto_pytabs",
            32,
        )


def makeExtension(**kwargs: Any) -> AutoPyTabsExtension:
    return AutoPyTabsExtension(**kwargs)
