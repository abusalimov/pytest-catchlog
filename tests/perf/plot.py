from __future__ import absolute_import, division, print_function

import pygal
from pygal.style import DefaultStyle

try:
    import pygaljs
except ImportError:
    opts = {}
else:
    opts = {"js": [pygaljs.uri("2.0.x", "pygal-tooltips.js")]}

opts["css"] = [
    "file://style.css",
    "file://graph.css",
    """inline:
        .axis.x text {
            text-anchor: middle !important;
        }
        .tooltip .value {
            font-size: 1em !important;
        }
    """
]


def make_plot(trial_names, history, history2, expr, expr2):
    style = DefaultStyle(colors=[
            '#ED1D27',  # 2
            '#ED6C1D',  # 3
            '#EDC51E',  # 4
            '#BCED1E',  # 5
            '#63ED1F',  # 6
            '#1FED34',  # 7
        ][:len(history)] + [
            '#1FEDE4',  # -7
            '#1F9EED',  # -6
            '#1E45ED',  # -5
            '#4F1EED',  # -4
            '#A71DED',  # -3
            '#ED1DDA',  # -2
        ][:len(history2)]
    )

    plot = pygal.Line(
        title="Speed in seconds",
        x_title="Trial",
        x_labels=trial_names,
        include_x_axis=True,
        human_readable=True,
        truncate_legend=8,
        style=style,
        stroke_style={'width': 2, 'dasharray': '20, 4'},
        **opts
    )

    format_name = '{0} ({1})'.format

    for mode in sorted(history):
        serie = history[mode]
        plot.add(format_name(mode, expr), serie,
                 stroke_style={'dasharray': 'none'})

    for mode in sorted(history2):
        serie = history2[mode]
        plot.add(format_name(mode, expr2), serie, secondary=True)

    return plot
