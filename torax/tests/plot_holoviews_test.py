from absl.testing import absltest
import holoviews as hv
import numpy as np
from panel.tests.util import wait_until

try:
    from playwright.sync_api import expect
except ImportError:
    expect = None
import pytest

pytestmark = pytest.mark.ui


# absltest.TestCase extends unittest.TestCase and thus does not
# allow for pytest fixtures.. It'll never be implemented, see:
# https://docs.pytest.org/en/stable/how-to/unittest.html#pytest-features-in-unittest-testcase-subclasses
# We opt not to use abseil for now
def test_init():
    assert expect is not None
    assert wait_until is not None


@pytest.mark.usefixtures("bokeh_backend", "serve_hv")
def test_gridspace_toolbar(serve_hv):

    # https://github.com/holoviz/holoviews/blob/67a71f2a97f0481d7cd561fd8acad05a6de816b2/holoviews/tests/ui/bokeh/test_layout.py
    def sine_curve(phase, freq):
        xvals = [0.1 * i for i in range(100)]
        return hv.Curve((xvals, [np.sin(phase + freq * x) for x in xvals]))

    phases = [0, np.pi / 2, np.pi, 3 * np.pi / 2]
    frequencies = [0.5, 0.75, 1.0, 1.25]
    curve_dict_2D = {(p, f): sine_curve(p, f) for p in phases for f in frequencies}
    gridspace = hv.GridSpace(curve_dict_2D, kdims=["phase", "frequency"])

    page = serve_hv(gridspace)
    bokeh_logo = page.locator(".bk-logo")
    expect(bokeh_logo).to_have_count(1)
