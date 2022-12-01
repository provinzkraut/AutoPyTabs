import re
from typing import Any, Dict, List, Literal, Optional, Set, Tuple, cast

import autoflake  # type: ignore
import markdown
from markdown import Extension
from markdown.preprocessors import Preprocessor
from pyupgrade._main import Settings as PyUpgradeSettings, _fix_plugins  # type: ignore

VersionTuple = Tuple[int, int]
VersionedCode = Dict[VersionTuple, str]

RGX_BLOCK_TOKENS = re.compile(r"(.*```py[\w\W]*)|(.*```)")
RGX_PYTABS_DIRECTIVE = re.compile(r"<!-- ?autopytabs: ?(.*)-->")

PyTabDirective = Literal["disable", "enable", "disable-block"]
PYTAB_DIRECTIVES: Set[PyTabDirective] = {"disable", "enable", "disable-block"}


def _upgrade(code: str, min_version: VersionTuple) -> str:
    return autoflake.fix_code(  # type: ignore[no-any-return]
        _fix_plugins(
            code,
            settings=PyUpgradeSettings(
                min_version=min_version,
                keep_percent_format=True,
                keep_mock=True,
                keep_runtime_typing=True,
            ),
        ),
        remove_all_unused_imports=True,
    )


def _build_tabs(versioned_code: VersionedCode) -> str:
    out = []
    for version, code in versioned_code.items():
        version_string = f"{version[0]}.{version[1]}"
        lines = ["```python", *code.splitlines(), "```"]
        code = "\n".join("    " + line for line in lines)
        out.append(f'=== "Python {version_string}+"\n{code}\n')
    return "\n".join(out)


def _wrap_in_code_block(code: str) -> str:
    return f"```python\n{code}\n```"


def _parse_version_tuple(version: str) -> VersionTuple:
    major, minor = version.split(".")
    return int(major), int(minor)


def _strip_indentation(lines: List[str]) -> Tuple[str, str]:
    if not lines:
        return "", ""
    first_line = lines[0]
    indent_char = ""
    if first_line[0] in [" ", "\t"]:
        indent_char = first_line[0]
    indent = indent_char * (len(first_line) - len(first_line.lstrip(indent_char)))
    return "\n".join(line.removeprefix(indent) for line in lines), indent


def _add_indentation(code: str, indentation: str) -> str:
    return "\n".join(indentation + line for line in code.splitlines())


def _get_pytabs_directive(line: str) -> Optional[PyTabDirective]:
    match = RGX_PYTABS_DIRECTIVE.match(line)
    if match:
        matched_directive = match.group(1).strip()
        if matched_directive in PYTAB_DIRECTIVES:
            return cast(PyTabDirective, matched_directive)
        raise RuntimeError(f"Invalid AutoPytabs directive: {matched_directive!r}")
    return None


class UpgradePreprocessor(Preprocessor):
    def __init__(
        self,
        *args: Any,
        min_version: VersionTuple,
        max_version: VersionTuple,
        **kwargs: Any,
    ) -> None:
        self.min_version = min_version
        self.max_version = max_version
        self.versions = [
            (major, minor)
            for major in range(min_version[0], max_version[0] + 1)
            for minor in range(min_version[1], max_version[1] + 1)
        ]
        super().__init__(*args, **kwargs)

    def convert_blocks(self, block: List[str]) -> str:
        versioned_code: VersionedCode = {}
        code, indentation = _strip_indentation(block)
        latest_code = code
        versioned_code[self.versions[0]] = code

        for version in self.versions:
            upgraded_code = _upgrade(latest_code, version)
            if upgraded_code != latest_code:
                versioned_code[version] = upgraded_code
                latest_code = upgraded_code

        if len(versioned_code) > 1:
            code = _build_tabs(versioned_code)
        else:
            code = _wrap_in_code_block(versioned_code[self.versions[0]])

        code = _add_indentation(code, indentation)

        return code

    def run(self, lines: List[str]) -> List[str]:
        in_block = False
        enabled = True
        new_lines: List[str] = []
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
                        block = self.convert_blocks(block[1:-1]).splitlines()
                    new_lines.extend(block)
                else:
                    new_lines.append(line)
            elif not in_block and not is_comment_line:
                new_lines.append(line)
        return new_lines


class UpgradeExtension(Extension):
    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize."""

        self.config = {
            "min_version": ["3.7", "minimum version"],
            "max_version": ["3.11", "maximum version"],
        }
        super().__init__(*args, **kwargs)

    def extendMarkdown(self, md: markdown.Markdown) -> None:
        """Register the extension."""

        self.md = md
        md.registerExtension(self)
        config = self.getConfigs()
        md.preprocessors.register(
            UpgradePreprocessor(
                min_version=_parse_version_tuple(config["min_version"]),
                max_version=_parse_version_tuple(config["max_version"]),
            ),
            "auto-pytabs",
            32,
        )


def makeExtension(**kwargs: Any) -> UpgradeExtension:
    return UpgradeExtension(**kwargs)
