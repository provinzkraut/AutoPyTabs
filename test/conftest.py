"""
Largely adopted from
https://github.com/executablebooks/sphinx-design/blob/6df47513e9e221c61877e9308da7a41d216ae3c3/tests/conftest.py
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock

import pytest
from docutils import nodes
from sphinx.testing.path import path as sphinx_path
from sphinx.testing.util import SphinxTestApp

from auto_pytabs.core import Cache

pytest_plugins = "sphinx.testing.fixtures"


@pytest.fixture(autouse=True, scope="session")
def purge_cache():
    Cache().clear_all()
    yield
    Cache().clear_all()


@pytest.fixture()
def mock_cache_persist(mocker) -> MagicMock:
    return mocker.patch("auto_pytabs.core.Cache.persist")


class SphinxBuilder:
    def __init__(self, app: SphinxTestApp, src_path: Path):
        self.app = app
        self._src_path = src_path

    @property
    def src_path(self) -> Path:
        return self._src_path

    @property
    def out_path(self) -> Path:
        return Path(self.app.outdir)

    def build(self, assert_pass=True):
        self.app.build()
        if assert_pass:
            assert self.warnings == "", self.status
        return self

    @property
    def status(self):
        return self.app._status.getvalue()

    @property
    def warnings(self):
        return self.app._warning.getvalue()

    def get_doctree(
        self, docname: str, post_transforms: bool = False
    ) -> nodes.document:
        doctree: nodes.document = self.app.env.get_doctree(docname)
        if post_transforms:
            self.app.env.apply_post_transforms(doctree, docname)
        # make source path consistent for test comparisons
        for node in doctree.findall(include_self=True):
            if not ("source" in node and node["source"]):
                continue
            node["source"] = Path(node["source"]).relative_to(self.src_path).as_posix()
            if node["source"].endswith(".rst"):
                node["source"] = node["source"][:-4]
            elif node["source"].endswith(".md"):
                node["source"] = node["source"][:-3]
        return doctree


@pytest.fixture()
def sphinx_builder(tmp_path: Path, make_app, monkeypatch):
    def _create_project(
        source: str,
        compat: bool = False,
        **conf_kwargs: Dict[str, Any],
    ):
        if compat:
            conf_kwargs["auto_pytabs_compat_mode"] = True
        src_path = tmp_path / "srcdir"
        src_path.mkdir()
        conf_kwargs = {
            "extensions": [
                "sphinx_design",
                "auto_pytabs.sphinx_ext",
            ],
            "auto_pytabs_no_cache": True,
            **(conf_kwargs or {}),
        }
        content = "\n".join(
            [f"{key} = {value!r}" for key, value in conf_kwargs.items()]
        )
        src_path.joinpath("conf.py").write_text(content, encoding="utf8")
        app = make_app(
            srcdir=sphinx_path(os.path.abspath(str(src_path))), buildername="html"
        )
        shutil.copy(
            "test/sphinx_ext_test_data/example.py", src_path.joinpath("example.py")
        )
        shutil.copy(
            "test/sphinx_ext_test_data/example.js", src_path.joinpath("example.js")
        )

        src_path.joinpath("index.rst").write_text(source)
        return SphinxBuilder(app, src_path)

    yield _create_project
