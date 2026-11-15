"""The picture of the demo check: where a few probes fire on the 2D map of a build."""

import numpy as np

from pipelines.probes.evaluate import LEVELS
from pipelines.probes.plots import GRID, plt, save

# The probes drawn: frequent ones and rare ones, from different families.
DRAWN = ("political", "loaded_language", "contempt", "theme:sport", "lang:de",
         "commercial_promo", "attack_addressee", "urgency_framing")  # fmt: skip
# One hue, light then dark: `possible`, then `probable`.
COLOURS = {"possible": "#86b6ef", "probable": "#1c5cab"}


def picture(run: str, build: str, found: dict, positions: np.ndarray) -> None:
    """Small multiples of the 2D map: every point in grey, the flagged ones in blue."""
    rng = np.random.default_rng(0)
    base = rng.choice(len(positions), size=min(len(positions), 120_000), replace=False)
    drawn = [name for name in DRAWN if name in found]
    fig, axes = plt.subplots(2, 4, figsize=(13, 6.8))
    for ax, name in zip(axes.flat, drawn, strict=False):
        ax.scatter(*positions[base].T, s=0.15, color=GRID, linewidths=0, rasterized=True)
        for level in reversed(LEVELS):
            mask = found[name].get(level)
            if mask is not None:
                ax.scatter(*positions[mask].T, s=0.6, color=COLOURS[level], linewidths=0,
                           rasterized=True, label=level)  # fmt: skip
        widest = max(found[name].values(), key=lambda mask: mask.sum())
        ax.set_title(f"{name}  ({100 * widest.mean():.2f}% of posts)", fontsize=9, pad=4)
        # A few stray points would shrink the cloud: the frame keeps the bulk of the map.
        ax.set_xlim(*np.percentile(positions[:, 0], [0.2, 99.8]))
        ax.set_ylim(*np.percentile(positions[:, 1], [0.2, 99.8]))
        ax.set_xticks([])
        ax.set_yticks([])
        for side in ax.spines.values():
            side.set_visible(False)
    for ax in axes.flat[len(drawn) :]:
        ax.set_visible(False)
    handles = [
        plt.Line2D([], [], marker="o", linestyle="", color=c, label=lv) for lv, c in COLOURS.items()
    ]
    fig.legend(handles=handles, loc="lower center", ncol=2, fontsize=9)
    fig.suptitle(
        f"Where eight probes fire on the map of {build}", x=0.01, ha="left", fontweight="bold"
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
    save(fig, f"demo-{run}")
