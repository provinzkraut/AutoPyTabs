from __future__ import annotations

import concurrent.futures
import secrets
import shutil
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING, List

import markdown
from mkdocs.config import Config, config_options
from mkdocs.config.defaults import MkDocsConfig
from mkdocs.plugins import BasePlugin
from mkdocs.structure.files import File, Files

from auto_pytabs.markdown_ext import (
    PendingTransformation,
    convert_block,
    extract_code_blocks,
)
from auto_pytabs.types import VersionTuple
from auto_pytabs.util import get_version_requirements, parse_version_tuple

if TYPE_CHECKING:
    from pymdownx.snippets import SnippetPreprocessor  # type: ignore


class PluginConfig(Config):  # type: ignore[no-untyped-call]
    min_version = config_options.Type(str, default="3.7")
    max_version = config_options.Type(str, default="3.11")
    tmp_path = config_options.Type(Path, default=Path(".autopytabs_tmp"))
    tab_title_template = config_options.Type(str, default="Python {min_version}+")
    no_cache = config_options.Type(bool, default=False)


class AutoPyTabsPlugin(BasePlugin[PluginConfig]):  # type: ignore[no-untyped-call]
    def __init__(self) -> None:
        self.versions: List[VersionTuple] = []
        self.snippets_processor: SnippetPreprocessor | None = None

    def on_config(self, config: MkDocsConfig) -> Config | None:
        min_version = parse_version_tuple(self.config.min_version)
        max_version = parse_version_tuple(self.config.max_version)
        self.versions = get_version_requirements(min_version, max_version)

        if "pymdownx.snippets" in config.markdown_extensions:
            md = markdown.Markdown(
                extensions=config["markdown_extensions"],
                extension_configs=config["mdx_configs"] or {},
            )
            self.snippets_processor = md.preprocessors["snippet"]
        return None

    def _convert_block(self, block: List[str]) -> str:
        return convert_block(
            block=block,
            versions=self.versions,
            tab_title_template=self.config.tab_title_template,
            no_cache=self.config.no_cache,
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
            if pending := extract_blocks_from_file(
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


def extract_blocks_from_file(
    docs_file: File,
    tmp_path: Path,
    snippets_preprocessor: SnippetPreprocessor | None = None,
) -> PendingTransformation | None:
    content = Path(docs_file.abs_src_path).read_text().splitlines()
    if snippets_preprocessor:
        content = snippets_preprocessor.run(content)

    new_lines, to_upgrade = extract_code_blocks(content)
    if not to_upgrade:
        return None

    tmp_docs_file = tmp_path / secrets.token_hex()
    docs_file.abs_src_path = str(tmp_docs_file)

    return PendingTransformation(
        tmp_docs_file=tmp_docs_file,
        new_lines=new_lines,
        to_upgrade=to_upgrade,
    )
