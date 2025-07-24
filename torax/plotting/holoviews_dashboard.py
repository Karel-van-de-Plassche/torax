"""Basic post-run plotting tool. Plot a single run or comparison of two runs.

Includes a time slider. Reads output files with xarray data or legacy h5 data.

Plots are configured by a plot_config module.
"""
from os import path
from absl import app
from absl import logging
from absl.flags import argparse_flags
from bokeh.io import show
from bokeh.layouts import layout as blayout
import matplotlib
import holoviews as hv
from holoviews.plotting.bokeh.renderer import BokehRenderer
from holoviews.plotting.bokeh import GridSpace
from itertools import zip_longest
import numpy as np
import pandas as pd
import panel as pn
from panel.pane.holoviews import HoloViews
from panel.widgets.slider import IntSlider
from torax._src.config import config_loader
from torax._src.plotting import plotruns_lib as prl
from torax._src.plotting.plotruns_lib import FigureProperties, PlotData, PlotType
from typing import Any, List, Tuple, Sequence


hv.extension('bokeh')
renderer: BokehRenderer = hv.renderer("bokeh").instance(mode="server")

def parse_flags(_):
  """Parse flags for the plotting tool."""
  parser = argparse_flags.ArgumentParser(description='Plot finished run')
  parser.add_argument(
      '--outfile',
      nargs='*',
      help=(
          'Relative location of output files (if two are provided, a'
          ' comparison is done)'
      ),
  )
  parser.add_argument(
      '--plot_config',
      default='plotting/configs/default_plot_config.py',
      help='Name of the plot config module.',
  )
  return parser.parse_args()


def modify_doc(doc):
    hvplot = renderer.get_plot(dmap, doc)

def get_curves(
    plot_config: FigureProperties,
    plotdata: PlotData,
    layout: Any,
    comp_plot: bool = False,
):
  """Gets curves for all plots."""
  curves = []
  # If comparison, first curves labeled (1) and solid, second set (2) and dashed
  suffix = f' ({1 if not comp_plot else 2})'
  dashed = '--' if comp_plot else ''

  #hvs: HoloViews = layout[0]
  gs = layout
  #gs: GridSpace = hvs.object # Gridspace we made before
  from IPython import embed; embed()
  assert len(plot_config.axes)
  for (coord, curve), cfg in zip_longest(gs.items(), plot_config.axes):
    line_idx = 0  # Reset color selection cycling for each plot.
    print(coord, curve, cfg)
    for attr, label in zip(cfg.attrs, cfg.labels):
      if cfg.plot_type == PlotType.SPATIAL:
        data = getattr(plotdata, attr)
        if cfg.suppress_zero_values and np.all(data == 0):
          continue
        rho = get_rho(plotdata, attr)
        # Our data should be cast to a pd.DataFrame
        ls: Str = plot_config.colors[line_idx % len(plot_config.colors)] + dashed
        label: Str = f'{label}{suffix}',
        df: DataFrame = pd.DataFrame({"rho": rho, attr: data[0, :]})
        # Only 2D plots
        vdim = curve.vdims[0]
        vdim.label = vdim.name = attr
        kdim = curve.kdims[0]
        kdim.label = kdim.name = "rho"
        curve.data = df
        curves.append(curve)
        line_idx += 1
      elif cfg.plot_type == PlotType.TIME_SERIES:
        data = getattr(plotdata, attr)
        if cfg.suppress_zero_values and np.all(data == 0):
          continue
        # No need to return a line since this will not need to be updated.
        vdim = curve.vdims[0]
        vdim.label = vdim.name = attr
        kdim = curve.kdims[0]
        kdim.label = kdim.name = "t"
        ls: Str = plot_config.colors[line_idx % len(plot_config.colors)] + dashed
        label: Str = f'{label}{suffix}',
        df: DataFrame = pd.DataFrame({"t": plotdata.t, attr: data})
        curve.data = df
        line_idx += 1
      else:
        raise ValueError(f'Unknown plot type: {cfg.plot_type}')

  return curves


def create_figure(plot_config: prl.FigureProperties):
  rows = plot_config.rows
  cols = plot_config.cols
  nplots = rows * cols
  #curve_dict_2D = {(p,f):sine_curve(p,f) for p in phases for f in frequencies}

  # Create the GridSpace - Adjust height ratios to include the slider
  # in the plot, only if a slider is required:
  if plot_config.contains_spatial_plot_type:
    # Add an extra smaller is a spatial plottypeider
    height_ratios = [1] * rows + [0.2]
    # Create a dictionairy with our dummy plots
    # This is where we plot _over_ soon
    # We only know what to plot where later, so use default ax names
    # In matplotlib, they are just all called "rectilinear", we
    # can be a bit smarter
    def fake_plot(phase, freq):
        xvals = [0.1* i for i in range(100)]
        return hv.Curve((xvals, [np.sin(phase+freq*x) for x in xvals]))
    phases      = [0, np.pi/2, np.pi, 3*np.pi/2]
    frequencies = [0.5, 0.75, 1.0, 1.25]
    # Curves can have different dimensions later, so make a hetrogeneous grid,
    # e.g. no GridSpace
    curve_dict = {(p,f): fake_plot(p,f) for p in phases for f in frequencies}
    #holomap: HoloMap = hv.HoloMap(kdims=['x', 'y'])
    gridspace = hv.GridSpace(curve_dict, kdims=["x", "y"])
    # slider spans all columns
    slider: Intslider = IntSlider(name='rolling_window', start=1, end=100, value=50)
    #pn.panel(slider)
    #layout = pn.Column(gridspace, slider) # Does not work with bokeh yet
    layout = gridspace
    #layout = hv.Layout(items=[gridspace, slider])
  else:
    raise Exception
    gs = gridspec.GridSpec(rows, cols, figure=fig)
    slider_ax = None
  return layout

def get_rho(
    plotdata: PlotData,
    data_attr: str,
) -> np.ndarray:
  """Gets the correct rho coordinate for the data."""
  datalen = len(getattr(plotdata, data_attr)[0, :])
  if datalen == len(plotdata.rho_cell_norm):
    return plotdata.rho_cell_norm
  elif datalen == len(plotdata.rho_face_norm):
    return plotdata.rho_face_norm
  elif datalen == len(plotdata.rho_norm):
    return plotdata.rho_norm
  else:
    raise ValueError(
        f'Data {datalen} does not coincide with either the cell or face grids.'
    )


def plot_dashboard(
    plot_config: FigureProperties, outfile: str, outfile2: str | None = None
):
  if not path.exists(outfile):
    raise ValueError(f'File {outfile} does not exist.')
  if outfile2 is not None and not path.exists(outfile2):
    raise ValueError(f'File {outfile2} does not exist.')
  plotdata1 = prl.load_data(outfile)
  plotdata2 = prl.load_data(outfile2) if outfile2 else None

  # Attribute check. Sufficient to check one PlotData object.
  plotdata_attrs = set(
      plotdata1.__dataclass_fields__
  )  # Get PlotData attributes
  for cfg in plot_config.axes:
    for attr in cfg.attrs:
      if attr not in plotdata_attrs:
        raise ValueError(
            f"Attribute '{attr}' in plot_config does not exist in PlotData"
        )

  print("Creating layout")
  layout = create_figure(plot_config)

  # Title handling:
  title_lines = [f'(1)={outfile}']
  if outfile2:
    title_lines.append(f'(2)={outfile2}')
  #fig.suptitle('\n'.join(title_lines))

  curves1 = get_curves(plot_config, plotdata1, layout)
  curves2 = (
      get_curves(plot_config, plotdata2, layout, comp_plot=True)
      if plotdata2
      else None
  )

  # show plot



def main(args: Sequence[str]) -> None:
  print("Preparing plot config")
  plot_config_module_path = args.plot_config
  try:
    plot_config = config_loader.import_module(plot_config_module_path)[
        'PLOT_CONFIG'
    ]
  except (ModuleNotFoundError, AttributeError) as e:
    logging.exception(
        'Error loading plot config: %s: %s', plot_config_module_path, e
    )
    raise
  if len(args.outfile) == 1:
    plot_dashboard(plot_config, args.outfile[0])
  else:
      raise Exception


# Method used by the `plot_torax` binary.
def run():
  app.run(main, flags_parser=parse_flags)


if __name__ == '__main__':
  run()
