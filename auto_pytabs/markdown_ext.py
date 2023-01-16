from __future__ import annotations

import concurrent.futures
import re
import secrets
import shutil
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Literal, NamedTuple, TYPE_CHECKING, cast

import markdown
from markdown import Extension
from markdown.preprocessors import Preprocessor
from mkdocs.config import Config, config_options
from mkdocs.config.defaults import MkDocsConfig
from mkdocs.plugins import BasePlugin
from mkdocs.structure.files import File, Files

from auto_pytabs.core import version_code, get_version_requirements
from auto_pytabs.types import VersionTuple, VersionedCode

if TYPE_CHECKING:
    from pymdownx.snippets import SnippetPreprocessor


RGX_BLOCK_TOKENS = re.compile(r"(.*```py[\w\W]*)|(.*```)")
RGX_PYTABS_DIRECTIVE = re.compile(r"<!-- ?autopytabs: ?(.*)-->")

PyTabDirective = Literal["disable", "enable", "disable-block"]
PYTAB_DIRECTIVES: set[PyTabDirective] = {"disable", "enable", "disable-block"}


def parse_version_tuple(version: str) -> VersionTuple:
    major, minor = version.split(".")
    return int(major), int(minor)


def parse_version_requirements(
    min_version: str, max_version: str
) -> list[VersionTuple]:
    return get_version_requirements(
        parse_version_tuple(min_version), parse_version_tuple(max_version)
    )


def strip_indentation(lines: list[str]) -> tuple[list[str], str]:
    if not lines:
        return [], ""
    first_line = lines[0]
    indent_char = ""
    if first_line[0] in [" ", "\t"]:
        indent_char = first_line[0]
    indent = indent_char * (len(first_line) - len(first_line.lstrip(indent_char)))
    return [line.removeprefix(indent) for line in lines], indent


def add_indentation(code: str, indentation: str) -> str:
    return "\n".join(indentation + line for line in code.splitlines())


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


def _convert_block(
    *,
    block: list[str],
    versions: list[tuple[int, int]],
    tab_title_template: str,
) -> str:
    block, indentation = strip_indentation(block)
    head, *code_lines, tail = block
    code = "\n".join(code_lines)
    versioned_code = version_code(code, versions)

    if len(versioned_code) > 1:
        code = _build_tabs(
            versioned_code=versioned_code,
            head=head,
            tail=tail,
            tab_title_template=tab_title_template,
        )
    else:
        code = "\n".join([head, versioned_code[versions[0]], tail])

    code = add_indentation(code, indentation)

    return code


class UpgradePreprocessor(Preprocessor):
    def __init__(
        self,
        *args: Any,
        min_version: str,
        max_version: str,
        tab_title_template: str | None = None,
        **kwargs: Any,
    ) -> None:
        self.versions = parse_version_requirements(min_version, max_version)
        self.tab_title_template = tab_title_template or "Python {min_version}+"
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
            "auto-pytabs",
            32,
        )


def makeExtension(**kwargs: Any) -> AutoPyTabsExtension:
    return AutoPyTabsExtension(**kwargs)


class PendingTransformation(NamedTuple):
    tmp_docs_file: Path
    new_lines: list[str]
    to_upgrade: dict[int, list[str]]


def _extract_blocks_from_file(
    docs_file: File,
    tmp_path: Path,
    snippets_preprocessor: SnippetPreprocessor | None = None,
) -> PendingTransformation | None:
    content = Path(docs_file.abs_src_path).read_text().splitlines()
    if snippets_preprocessor:
        content = snippets_preprocessor.run(content)

    new_lines, to_upgrade = _extract_code_blocks(content)
    if not to_upgrade:
        return None

    tmp_docs_file = tmp_path / secrets.token_hex()
    docs_file.abs_src_path = str(tmp_docs_file)

    return PendingTransformation(
        tmp_docs_file=tmp_docs_file,
        new_lines=new_lines,
        to_upgrade=to_upgrade,
    )


class _VersionTuple:
    def __init__(self, data: str) -> None:
        self.major, self.minor = parse_version_tuple(data)


class PluginConfig(Config):  # type: ignore[no-untyped-call]
    min_version = config_options.Type(str, default="3.7")
    max_version = config_options.Type(str, default="3.11")
    tmp_path = config_options.Type(Path, default=Path(".autopytabs_tmp"))
    tab_title_template = config_options.Type(str, default="Python {min_version}+")


class AutoPyTabsPlugin(BasePlugin[PluginConfig]):  # type: ignore[no-untyped-call]
    def __init__(self) -> None:
        self.versions: list[VersionTuple] = []
        self.snippets_processor: SnippetPreprocessor | None = None

    def on_config(self, config: MkDocsConfig) -> Config | None:
        min_version = parse_version_tuple(self.config.min_version)
        max_version = parse_version_tuple(self.config.max_version)
        self.versions = [
            (major, minor)
            for major in range(min_version[0], max_version[0] + 1)
            for minor in range(min_version[1], max_version[1] + 1)
        ]

        if "pymdownx.snippets" in config.markdown_extensions:
            md = markdown.Markdown(
                extensions=config["markdown_extensions"],
                extension_configs=config["mdx_configs"] or {},
            )
            self.snippets_processor = md.preprocessors["snippet"]
        return None

    def _convert_block(self, block: list[str]) -> str:
        return _convert_block(
            block=block,
            versions=self.versions,
            tab_title_template=self.config.tab_title_template,
        )

    def _transform_pending(
        self,
        transformation: PendingTransformation,
        executor: concurrent.futures.ProcessPoolExecutor,
    ) -> None:
        new_lines = transformation.new_lines
        to_transform = transformation.to_upgrade

        to_replace = {}
        fs = {
            executor.submit(self._convert_block, block): index
            for index, block in to_transform.items()
        }
        for future in as_completed(fs):
            index = fs[future]
            to_replace[index] = future.result()

        output = ""
        for i, line in enumerate(new_lines):
            line = to_replace.get(i, line)
            output += line + "\n"
        transformation.tmp_docs_file.write_text(output)

    def on_files(self, files: Files, *, config: MkDocsConfig) -> Files:
        self.config.tmp_path.mkdir(exist_ok=True)

        pending_transformations = []

        for file in files:
            if not file.is_documentation_page():
                continue
            if pending := _extract_blocks_from_file(
                file,
                self.config.tmp_path,
                self.snippets_processor,
            ):
                pending_transformations.append(pending)

        with ThreadPoolExecutor() as thread_pool, ProcessPoolExecutor() as process_pool:
            fs = [
                thread_pool.submit(
                    self._transform_pending,
                    transformation=transformation,
                    executor=process_pool,
                )
                for transformation in pending_transformations
            ]
            concurrent.futures.wait(fs, return_when=concurrent.futures.ALL_COMPLETED)

        return files

    def _cleanup_temp_files(self) -> None:
        """Cleanup temporary files."""
        if self.config.tmp_path.exists():
            shutil.rmtree(self.config.tmp_path)

    def on_post_build(self, config: MkDocsConfig) -> None:
        self._cleanup_temp_files()

    def on_build_error(self, error: Exception) -> None:
        self._cleanup_temp_files()
