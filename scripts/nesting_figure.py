"""Why the grid must nest: a hexagon's children straddle it; a square's children partition it.

    uv run python scripts/nesting_figure.py        # writes docs/img/nesting.jpg
"""
from __future__ import annotations

import math

import plotly.graph_objects as go
from plotly.subplots import make_subplots


def hexagon(cx, cy, r, rot=0.0):
    pts = [(cx + r * math.cos(rot + math.radians(60 * i)), cy + r * math.sin(rot + math.radians(60 * i))) for i in range(7)]
    return [p[0] for p in pts], [p[1] for p in pts]


def square(cx, cy, s):
    h = s / 2
    return [cx - h, cx + h, cx + h, cx - h, cx - h], [cy - h, cy - h, cy + h, cy + h, cy - h]


def main() -> None:
    fig = make_subplots(rows=1, cols=2, subplot_titles=("hexagon, aperture 7: the children straddle the parent", "square, aperture 9: the children partition the parent"), horizontal_spacing=0.06)
    # aperture-7 hexagon: child circumradius R/sqrt(7); the six outer children sit on a ring rotated by atan(sqrt(3)/5) ≈ 19.1°
    R = 1.0
    rc = R / math.sqrt(7)
    ring = math.sqrt(3) * rc
    rot = math.atan(math.sqrt(3) / 5)
    for i in range(6):
        a = rot + math.radians(30 + 60 * i)
        x, y = hexagon(ring * math.cos(a), ring * math.sin(a), rc, rot)
        fig.add_trace(go.Scatter(x=x, y=y, fill="toself", mode="lines", line={"color": "#e45756", "width": 1.5}, fillcolor="rgba(228,87,86,0.25)", showlegend=False), row=1, col=1)
    x, y = hexagon(0, 0, rc, rot)
    fig.add_trace(go.Scatter(x=x, y=y, fill="toself", mode="lines", line={"color": "#e45756", "width": 1.5}, fillcolor="rgba(228,87,86,0.25)", showlegend=False), row=1, col=1)
    x, y = hexagon(0, 0, R)
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line={"color": "#1b1b3a", "width": 3.5}, showlegend=False), row=1, col=1)
    # aperture-9 square
    for i in range(3):
        for j in range(3):
            x, y = square(-1 + i, -1 + j, 1.0)
            fig.add_trace(go.Scatter(x=x, y=y, fill="toself", mode="lines", line={"color": "#54a24b", "width": 1.5}, fillcolor="rgba(84,162,75,0.25)", showlegend=False), row=1, col=2)
    x, y = square(0, 0, 3.0)
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line={"color": "#1b1b3a", "width": 3.5}, showlegend=False), row=1, col=2)
    fig.add_annotation(x=0, y=-1.32, text="every roll-up is another crossing: parent ≠ its children", showarrow=False, font={"size": 13, "color": "#e45756"}, row=1, col=1)
    fig.add_annotation(x=0, y=-1.95, text="parent = its nine children, exactly: roll-up is free, forever", showarrow=False, font={"size": 13, "color": "#54a24b"}, row=1, col=2)
    fig.update_xaxes(visible=False, range=[-1.5, 1.5], row=1, col=1); fig.update_yaxes(visible=False, range=[-1.5, 1.4], scaleanchor="x", row=1, col=1)
    fig.update_xaxes(visible=False, range=[-2.2, 2.2], row=1, col=2); fig.update_yaxes(visible=False, range=[-2.2, 2.05], scaleanchor="x2", row=1, col=2)
    fig.update_layout(height=480, width=1100, margin={"l": 10, "r": 10, "t": 50, "b": 10}, template="plotly_white")
    fig.write_image("docs/img/nesting.jpg", scale=2)
    print("wrote docs/img/nesting.jpg")


if __name__ == "__main__":
    main()
