# Copyright 2024 DeepMind Technologies Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Pytest fixture for working around UnparsedFlagAccessError when running tests."""
import contextlib
import sys

from absl import flags

# Need to import absltest to get --test_srcdir defined.
from absl.testing import absltest  # pylint: disable=unused-import
import holoviews as hv
import pytest
import panel as pn
from panel.tests.conftest import port
from panel.tests.util import serve_and_wait


CUSTOM_MARKS = ("ui", "gpu")


@pytest.fixture(scope="session", autouse=True)
def parse_flags():
    # Only pass the first item, because pytest flags shouldn't be parsed as
    # absolute flags.
    flags.FLAGS(sys.argv[:1])


def pytest_addoption(parser):
    # https://github.com/holoviz/holoviews/blob/67a71f2a97f0481d7cd561fd8acad05a6de816b2/holoviews/tests/conftest.py
    for marker in CUSTOM_MARKS:
        parser.addoption(
            f"--{marker}",
            action="store_true",
            default=False,
            help=f"Run {marker} related tests",
        )


def pytest_configure(config):
    # https://github.com/holoviz/holoviews/blob/67a71f2a97f0481d7cd561fd8acad05a6de816b2/holoviews/tests/conftest.py
    for marker in CUSTOM_MARKS:
        config.addinivalue_line("markers", f"{marker}: {marker} test marker")


def pytest_collection_modifyitems(config, items):
    # https://github.com/holoviz/holoviews/blob/67a71f2a97f0481d7cd561fd8acad05a6de816b2/holoviews/tests/conftest.py
    skipped, selected = [], []
    markers = [m for m in CUSTOM_MARKS if config.getoption(f"--{m}")]
    empty = not markers
    for item in items:
        if empty and any(m in item.keywords for m in CUSTOM_MARKS):
            skipped.append(item)
        elif empty:
            selected.append(item)
        elif not empty and any(m in item.keywords for m in markers):
            selected.append(item)
        else:
            skipped.append(item)

    config.hook.pytest_deselected(items=skipped)
    items[:] = selected


with contextlib.suppress(ImportError):
    # https://github.com/holoviz/holoviews/blob/67a71f2a97f0481d7cd561fd8acad05a6de816b2/holoviews/tests/conftest.py
    import matplotlib as mpl

    mpl.use("agg")


def _plotting_backend(backend):
    # https://github.com/holoviz/holoviews/blob/67a71f2a97f0481d7cd561fd8acad05a6de816b2/holoviews/tests/conftest.py
    pytest.importorskip(backend)
    if not hv.extension._loaded:
        hv.extension(backend)
    hv.renderer(backend)
    curent_backend = hv.Store.current_backend
    hv.Store.set_current_backend(backend)
    yield
    hv.Store.set_current_backend(curent_backend)


@pytest.fixture
def bokeh_backend():
    # https://github.com/holoviz/holoviews/blob/67a71f2a97f0481d7cd561fd8acad05a6de816b2/holoviews/tests/conftest.py
    yield from _plotting_backend("bokeh")


@pytest.fixture
def mpl_backend():
    # https://github.com/holoviz/holoviews/blob/67a71f2a97f0481d7cd561fd8acad05a6de816b2/holoviews/tests/conftest.py
    yield from _plotting_backend("matplotlib")


@pytest.fixture(autouse=True)
def reset_store():
    # https://github.com/holoviz/holoviews/blob/67a71f2a97f0481d7cd561fd8acad05a6de816b2/holoviews/tests/conftest.py
    _custom_options = {k: {} for k in hv.Store._custom_options}
    _options = hv.Store._options.copy()
    current_backend = hv.Store.current_backend
    renderers = hv.Store.renderers.copy()
    yield
    hv.Store._custom_options = _custom_options
    hv.Store._options = _options
    hv.Store._weakrefs = {}
    hv.Store.renderers = renderers
    hv.Store.set_current_backend(current_backend)


# @pytest.fixture(scope="session")
@pytest.fixture
def serve_hv(page, port):  # noqa: F811
    # https://github.com/holoviz/holoviews/blob/67a71f2a97f0481d7cd561fd8acad05a6de816b2/holoviews/tests/conftest.py
    # Uses pytest-playwright to generate a fake webpage
    def serve_and_return_page(hv_obj):
        serve_and_wait(pn.pane.HoloViews(hv_obj), port=port)
        page.goto(f"http://localhost:{port}")
        return page

    return serve_and_return_page


@pytest.fixture
def serve_panel(page, port):  # noqa: F811
    # https://github.com/holoviz/holoviews/blob/67a71f2a97f0481d7cd561fd8acad05a6de816b2/holoviews/tests/conftest.py
    # Uses pytest-playwright to generate a fake webpage
    def serve_and_return_page(pn_obj):
        serve_and_wait(pn.panel(pn_obj), port=port)
        page.goto(f"http://localhost:{port}")
        return page

    return serve_and_return_page
