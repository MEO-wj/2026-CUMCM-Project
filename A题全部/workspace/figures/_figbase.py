# -*- coding: utf-8 -*-
"""Shared bootstrap for all gen_fig_*.py scripts of this paper."""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
UTILS = os.path.join(ROOT, "_utils")
CODE = os.path.join(ROOT, "code")
for _p in (UTILS, HERE, CODE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import plot_utils as pu  # noqa: E402
from plot_utils import (  # noqa: E402,F401
    COLORS,
    auto_legend,
    consolidate_shared_legends,
    declutter_axes,
    draw_vector_heatmap,
    dynamic_limits,
    save_fig,
    set_paper_placement,
    shared_legend,
    smart_labels,
    uncertainty_band,
)

pu.setup_style(palette="dutch_field")

import matplotlib.pyplot as plt  # noqa: E402

# ---------------------------------------------------------------- constants
R_OUT_CM = np.array([0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0,
                     1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 2.0])
C_TH = 0.15          # kg/kg dry basis, terminal moisture threshold
R0_CM = 2.0
H_TO_S = 3600.0

_GLYPH_MAP = {
    "≤": "<=", "≥": ">=", "≠": "!=", "≈": "~=",
    "⛔": "", "✔": "", "✓": "", "⚠": "", "✗": "x",
    "→": "->", "←": "<-", "×": "x",
}


def cn(text):
    """Strip/替换 字体缺字形的符号, 避免 PDF 出现豆腐块."""
    out = str(text)
    for bad, good in _GLYPH_MAP.items():
        out = out.replace(bad, good)
    return out


# ---------------------------------------------------------------- data access
def load_json(name):
    with open(os.path.join(HERE, name), "r", encoding="utf-8") as fh:
        return json.load(fh)


_CACHE = {}


def results(tag):
    """tag in {'all','p1','p2','p3','p4','sens','plot'}"""
    fmap = {
        "all": "all_results.json",
        "p1": "problem_1_results.json",
        "p2": "problem_2_results.json",
        "p3": "problem_3_results.json",
        "p4": "problem_4_results.json",
        "sens": "sensitivity_results.json",
        "plot": "_plot_data.json",
    }
    if tag not in _CACHE:
        _CACHE[tag] = load_json(fmap[tag])
    return _CACHE[tag]


def read_excel(fname, sheet=0):
    import pandas as pd
    return pd.read_excel(os.path.join(ROOT, fname), sheet_name=sheet)


def field_matrix(fname, sheet=0):
    """Return (t_hours, r_cm, values MxN) from a result*.xlsx sheet."""
    df = read_excel(fname, sheet)
    t = df.iloc[:, 0].to_numpy(dtype=float) / H_TO_S
    vals = df.iloc[:, 1:].to_numpy(dtype=float)
    return t, R_OUT_CM[: vals.shape[1]].copy(), vals


def user_xlsx(fname):
    import pandas as pd
    return pd.read_excel(os.path.join(ROOT, "user_data", fname))


# ---------------------------------------------------------------- helpers
def log_floor(*arrays, frac=0.5):
    """Positive lower bound for log axes, derived from the real data."""
    vals = np.concatenate([np.asarray(a, dtype=float).ravel() for a in arrays])
    vals = vals[np.isfinite(vals) & (vals > 0)]
    if vals.size == 0:
        return 1e-12
    return float(vals.min()) * frac


PRINT_MAX_W_IN = 5.5      # = plot_utils.PAGE_MAX_W_IN，成品显示宽度硬上限
SAFETY_IN = 0.09          # 画布四边安全内缩，防 mathtext 轴标签出界


def native_figsize(width_fraction=1.0, aspect=0.55):
    """原生画布 = 论文实际显示尺寸，使插图缩放比≈1（字号不被缩小）。"""
    wf = float(np.clip(width_fraction, 0.20, 1.0))
    a = float(np.clip(aspect, 0.42, 1.10))
    w = PRINT_MAX_W_IN * wf
    return (w, w * a)


def fit_layout(fig, pad=0.45, safety_in=SAFETY_IN):
    """把 axes 连轴标签一起收进画布内缩区，避免文字出界。"""
    W, H = fig.get_size_inches()
    dx = min(safety_in / max(W, 1e-6), 0.12)
    dy = min(safety_in / max(H, 1e-6), 0.12)
    try:
        fig.tight_layout(pad=pad, rect=(dx, dy, 1.0 - dx, 1.0 - dy))
    except Exception:
        try:
            fig.tight_layout(pad=pad)
        except Exception:
            pass


def panel(nrows=1, ncols=1, *, width_fraction=1.0, height_fraction=0.55,
          aspect=None, sharex=False, sharey=False, figsize=None, **kw):
    """height_fraction 按「高/宽」比解释（历史签名保留）。"""
    a = aspect if aspect is not None else height_fraction
    if figsize is None:
        figsize = native_figsize(width_fraction, a)
    fig, axes = plt.subplots(nrows, ncols, figsize=figsize,
                             sharex=sharex, sharey=sharey, **kw)
    fig._mh_placement = width_fraction
    return fig, axes


def finish(fig, out, *, width_fraction=None, height_fraction=0.88, axes=None):
    wf = getattr(fig, "_mh_placement", 1.0)
    if width_fraction is not None:
        wf = width_fraction
    if axes is not None:
        try:
            consolidate_shared_legends(fig, axes)
        except Exception:
            pass
    set_paper_placement(fig, wf, height_fraction=height_fraction)
    fit_layout(fig)
    save_fig(fig, os.path.join(HERE, out))
    plt.close(fig)
    print("OK", out)


def label_panels(axes, labels=None, *, dy=1.02):
    axs = np.atleast_1d(np.asarray(axes, dtype=object)).ravel()
    labels = labels or ["(a)", "(b)", "(c)", "(d)", "(e)", "(f)"]
    for ax, lab in zip(axs, labels):
        ax.set_title(lab, loc="left", fontsize=9, fontweight="bold", y=dy)
