"""Drawing helpers for the figures of the probe report: one look, a few chart forms."""

from collections.abc import Sequence
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.axes import Axes  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402

FIGURES = Path("docs") / "probes" / "figures"
SURFACE, INK, SECONDARY, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, AXIS = "#e1e0d9", "#c3c2b7"
# Categorical slots, always in this order: a series keeps its colour in every figure.
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
ROW = 0.24  # inches per row of a dot plot

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "text.color": INK,
        "axes.labelcolor": SECONDARY,
        "axes.edgecolor": AXIS,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelcolor": SECONDARY,
        "ytick.labelcolor": INK,
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.titlesize": 10,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "legend.frameon": False,
    }
)


def style(ax: Axes, grid: str = "x") -> None:
    ax.grid(axis=grid, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)


def save(fig: Figure, name: str) -> Path:
    FIGURES.mkdir(parents=True, exist_ok=True)
    path = FIGURES / f"{name}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def dot_rows(
    ax: Axes,
    labels: Sequence[str],
    values: Sequence[float | None],
    *,
    color: str = BLUE,
    low: Sequence[float | None] | None = None,
    high: Sequence[float | None] | None = None,
    hollow: Sequence[bool] | None = None,
    name: str | None = None,
    offset: float = 0.0,
) -> None:
    """One dot per row, top row first, with an optional interval and hollow dots for thin data."""
    for row, value in enumerate(values):
        if value is None:
            continue
        y = len(labels) - 1 - row + offset
        if low is not None and low[row] is not None:
            ax.plot([low[row], high[row]], [y, y], color=color, linewidth=1.6, alpha=0.55)
        empty = hollow is not None and hollow[row]
        face = SURFACE if empty else color
        ax.plot(value, y, "o", markersize=6, markerfacecolor=face, markeredgecolor=color,
                markeredgewidth=1.4, label=name if row == 0 or name is None else None)  # fmt: skip
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(list(reversed(labels)))
    ax.set_ylim(-0.7, len(labels) - 0.3)


def rows_figure(n_rows: int, width: float = 7.5, panels: int = 1) -> tuple[Figure, list[Axes]]:
    height = max(2.2, n_rows * ROW + 1.0)
    fig, axes = plt.subplots(1, panels, figsize=(width, height), sharey=True)
    axes = [axes] if panels == 1 else list(axes)
    for ax in axes:
        style(ax)
    return fig, axes


def unique_legend(ax: Axes, **kwargs: object) -> None:
    handles, names = ax.get_legend_handles_labels()
    seen = dict(zip(names, handles, strict=True))
    ax.legend(seen.values(), seen.keys(), **kwargs)
