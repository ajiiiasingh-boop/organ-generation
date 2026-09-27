"""
All the drawing code: matplotlib charts + the Plotly 3D organ viewer.

matplotlib draws the 2D charts (radar, dashboard). The 3D model uses Plotly
because matplotlib's 3D plots turn into flat pictures in a web page, while
Plotly lets you drag to rotate and scroll to zoom.
"""

import matplotlib

matplotlib.use("Agg")  # draw without a window (needed on a web server)

import matplotlib.pyplot as plt
import numpy as np
import plotly.graph_objects as go
import streamlit as st

from core.glb import load_mesh_parts, model_stats, normalize_parts
from core.organs import ORGANS, ROOT, STEPS

# ---------- colours ----------

# One fixed colour per organ for every chart (colour follows the organ, never its rank).
ORGAN_COLORS = {
    "light": {"brain": "#2a78d6", "heart": "#eb6834", "lung": "#1baf7a"},
    "dark": {"brain": "#3987e5", "heart": "#d95926", "lung": "#199e70"},
}

INK = {
    "light": {"text": "#2B302A", "muted": "#6B7466", "grid": "#E4E1D9", "axis": "#C9C6BC", "surface": "#F8F7F3", "band_alpha": 0.3},
    "dark": {"text": "#EDEFEA", "muted": "#A7B0A1", "grid": "#34362F", "axis": "#4A4D44", "surface": "#1B1C19", "band_alpha": 0.5},
}


def theme_mode():
    """'light' or 'dark', following the theme the visitor is using."""
    try:
        return "dark" if st.context.theme.type == "dark" else "light"
    except Exception:
        return "light"


def _style_axes(ax, ink):
    ax.set_facecolor("none")
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(ink["axis"])
    ax.tick_params(colors=ink["muted"], labelsize=9.5, length=0)
    ax.grid(axis="x", color=ink["grid"], linewidth=0.8)
    ax.set_axisbelow(True)


def _new_figure(width, height, mode, **kwargs):
    fig = plt.figure(figsize=(width, height), dpi=200, **kwargs)
    fig.patch.set_alpha(0)   # transparent, so it sits on the page background
    return fig, INK[mode]


# ---------- radar charts (result page) ----------

def radar_chart(organ_key, answers, scores, mode):
    """Radar for one organ: a spoke reaches the edge when that organ agrees with your answer."""
    color = ORGAN_COLORS[mode][organ_key]
    fig, ink = _new_figure(3.6, 3.7, mode)
    ax = fig.add_subplot(1, 1, 1, projection="polar")

    labels = [s["short"] for s in STEPS]
    angles = np.linspace(0, 2 * np.pi, len(STEPS), endpoint=False)
    profile = ORGANS[organ_key]["profile"]
    values = np.array([1.0 if answers.get(s["key"]) == profile[s["key"]] else 0.0 for s in STEPS])

    ax.set_theta_offset(np.pi / 2)      # first spoke at the top
    ax.set_theta_direction(-1)          # go clockwise
    ax.set_ylim(0, 1.08)
    ax.set_facecolor("none")
    ax.spines["polar"].set_color(ink["grid"])
    ax.grid(color=ink["grid"], linewidth=0.8)
    ax.set_yticks([0.5, 1.0])
    ax.set_yticklabels([])
    ax.set_xticks(angles)
    ax.set_xticklabels(labels, color=ink["muted"], fontsize=9)
    ax.tick_params(pad=6)

    closed_angles = np.append(angles, angles[0])
    closed_values = np.append(values, values[0])
    ax.fill(closed_angles, closed_values, color=color, alpha=0.16, linewidth=0)
    ax.plot(closed_angles, closed_values, color=color, linewidth=2, solid_joinstyle="round")
    hit = values > 0
    ax.scatter(angles[hit], values[hit], s=34, color=color, edgecolors=ink["surface"], linewidths=1.5, zorder=3)

    row = scores.set_index("organ").loc[organ_key]
    ax.set_title(f"{ORGANS[organ_key]['label']}  \u00b7  {int(row.matched)}/{int(row.answered)} match",
                 color=ink["text"], fontsize=10.5, fontweight="bold", pad=18)
    fig.subplots_adjust(left=0.16, right=0.84, top=0.8, bottom=0.1)
    return fig


# ---------- dashboard charts ----------

def _range_row(ax, y, low, high, mean, color, ink, unit, label_mean=True):
    """A soft bar from min to max with a dot at the mean."""
    if low is not None and high is not None:
        ax.plot([low, high], [y, y], color=color, linewidth=9, alpha=ink["band_alpha"], solid_capstyle="round")
        ax.annotate(f"{low:g}", (low, y), xytext=(-8, 0), textcoords="offset points",
                    ha="right", va="center", fontsize=9, color=ink["muted"])
        ax.annotate(f"{high:g}", (high, y), xytext=(8, 0), textcoords="offset points",
                    ha="left", va="center", fontsize=9, color=ink["muted"])
    if mean is not None:
        ax.scatter([mean], [y], s=70, color=color, edgecolors=ink["surface"], linewidths=2, zorder=3)
        if label_mean:
            ax.annotate(f"mean {mean:g} {unit}", (mean, y), xytext=(0, 11), textcoords="offset points",
                        ha="center", va="bottom", fontsize=9, color=ink["text"], fontweight="bold")


def vitals_ranges(vitals_df, mode):
    """Small multiples: heart rate, respiratory rate, blood pressure — each on its own axis."""
    colors = ORGAN_COLORS[mode]
    fig, ink = _new_figure(6.2, 5.6, mode)
    grid = fig.add_gridspec(3, 1, height_ratios=[1, 1, 2.4], hspace=1.0, left=0.2, right=0.95, top=0.95, bottom=0.06)

    panels = [
        ("Heart rate (bpm)", ["Heart rate"], "bpm"),
        ("Respiratory rate (breaths/min)", ["Respiratory rate"], "breaths/min"),
        ("Blood pressure (mmHg)", ["Systolic BP", "Mean arterial pressure", "Diastolic BP"], "mmHg"),
    ]
    by_name = vitals_df.set_index("measure")

    for i, (title, measures, unit) in enumerate(panels):
        ax = fig.add_subplot(grid[i])
        _style_axes(ax, ink)
        lows, highs = [], []
        for y, name in enumerate(reversed(measures)):
            r = by_name.loc[name]
            low = None if np.isnan(r["min"]) else float(r["min"])
            high = None if np.isnan(r["max"]) else float(r["max"])
            _range_row(ax, y, low, high, float(r["mean"]), colors[r["organ"]], ink, unit)
            lows += [v for v in (low, float(r["mean"])) if v is not None]
            highs += [v for v in (high, float(r["mean"])) if v is not None]
        pad = (max(highs) - min(lows)) * 0.18
        ax.set_xlim(min(lows) - pad, max(highs) + pad)
        ax.set_ylim(-0.6, len(measures) - 0.25)
        ax.set_yticks(range(len(measures)))
        short = {"Systolic BP": "Systolic", "Mean arterial pressure": "Mean arterial", "Diastolic BP": "Diastolic"}
        ax.set_yticklabels([short.get(m, "") for m in reversed(measures)], fontsize=9.5, color=ink["text"])
        ax.set_title(title, loc="left", fontsize=10.5, color=ink["text"], fontweight="bold", pad=6)

    return fig


def signal_panels(summary, mode):
    """ECG rhythm split, EEG amplitude range and peak airflow range."""
    colors = ORGAN_COLORS[mode]
    fig, ink = _new_figure(6.2, 4.8, mode)
    grid = fig.add_gridspec(3, 1, hspace=1.5, left=0.05, right=0.95, top=0.92, bottom=0.07)

    # ECG: part-to-whole of two groups -> one 100% bar
    ecg = summary["ecg"]
    ax = fig.add_subplot(grid[0])
    _style_axes(ax, ink)
    normal = ecg["normal_pct"]
    ax.barh([0], [normal], color=colors["heart"], height=0.5)
    ax.barh([0], [100 - normal - 0.6], left=[normal + 0.6], color=ink["axis"], height=0.5)
    ax.text(normal / 2, 0, f"Normal rhythm {normal:g}%", ha="center", va="center", fontsize=9, color="white", fontweight="bold")
    ax.text(normal + (100 - normal) / 2, 0, f"Other {100 - normal:.1f}%", ha="center", va="center", fontsize=8.5, color=ink["text"])
    ax.set_xlim(0, 100)
    ax.set_yticks([])
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax.set_title(f"ECG beats · {ecg['n_beats']:,} MIT-BIH beats (heart)", loc="left", fontsize=10.5,
                 color=ink["text"], fontweight="bold", pad=6)

    # EEG amplitude range
    eeg = summary["eeg"]
    ax = fig.add_subplot(grid[1])
    _style_axes(ax, ink)
    _range_row(ax, 0, eeg["min"], eeg["max"], None, colors["brain"], ink, eeg["unit"])
    ax.set_xlim(0, 300)
    ax.set_yticks([])
    ax.set_title(f"EEG amplitude ({eeg['unit']}) · {eeg['n']:,} recordings (brain)", loc="left", fontsize=10.5,
                 color=ink["text"], fontweight="bold", pad=6)

    # Peak airflow range
    air = summary["airflow"]
    ax = fig.add_subplot(grid[2])
    _style_axes(ax, ink)
    _range_row(ax, 0, air["min"], air["max"], None, colors["lung"], ink, air["unit"])
    ax.set_xlim(0, 500)
    ax.set_yticks([])
    ax.set_title(f"Peak airflow ({air['unit']}) · {air['n']:,} patients (lung)", loc="left", fontsize=10.5,
                 color=ink["text"], fontweight="bold", pad=6)

    return fig


def histogram(series, mode, title):
    """Histogram for the 'explore your own CSV' tool."""
    fig, ink = _new_figure(12, 3.4, mode)
    ax = fig.add_subplot(1, 1, 1)
    _style_axes(ax, ink)
    ax.grid(axis="y", color=ink["grid"], linewidth=0.8)
    ax.grid(axis="x", visible=False)
    values = series.dropna().to_numpy()
    ax.hist(values, bins=min(40, max(10, int(np.sqrt(len(values))))), color="#5B7F4F", edgecolor=ink["surface"], linewidth=1)
    ax.axvline(values.mean(), color=ink["text"], linewidth=1.2, linestyle="-")
    ax.annotate(f"mean {values.mean():.1f}", (values.mean(), 1), xycoords=("data", "axes fraction"),
                xytext=(4, -4), textcoords="offset points", va="top", fontsize=9, color=ink["text"])
    ax.set_title(title, loc="left", fontsize=10.5, color=ink["text"], fontweight="bold")
    ax.set_ylabel("count", color=ink["muted"], fontsize=9)
    fig.tight_layout()
    return fig


# ---------- 3D organ viewer ----------

# Friendly names and colours for the parts inside the lung model
PART_STYLES = [
    ("Lung_Geo_Right", "Right lung", "#E2A98F", 0.33),
    ("Lung_Geo_Left", "Left lung", "#E2A98F", 0.33),
    ("Bronchi_Geo_Right", "Right bronchial tree", "#F1D9C2", 1.0),
    ("Bronchi_Geo_Left", "Left bronchial tree", "#F1D9C2", 1.0),
    ("Trachea", "Trachea", "#EAD0B6", 1.0),
    ("Cricothyroid", "Cricothyroid ligament", "#D8BFA3", 1.0),
    ("Epiglotis_Inner", "Epiglottis (inner)", "#D8BFA3", 1.0),
    ("Epiglotis", "Epiglottis", "#D8BFA3", 1.0),
    ("Thyroid_Membrane", "Thyroid membrane", "#D8BFA3", 1.0),
    ("Thyroid_Cartliage", "Thyroid cartilage", "#D8BFA3", 1.0),
    ("Vocal_Fold_Geo_Left", "Left vocal fold", "#D8BFA3", 1.0),
    ("Vocal_Fold_Geo_Right", "Right vocal fold", "#D8BFA3", 1.0),
]


@st.cache_data(show_spinner=False)
def load_organ_model(organ_key):
    """Parse the .glb once per organ and keep the result in memory."""
    path = ROOT / ORGANS[organ_key]["model"]
    parts = normalize_parts(load_mesh_parts(path))
    return parts, model_stats(parts, path)


def organ_figure(organ_key, height=470):
    parts, _ = load_organ_model(organ_key)
    organ = ORGANS[organ_key]
    traces = []

    for part in parts:
        name, color, opacity = organ["label"], organ["mesh_color"], 1.0
        for needle, nice, c, o in PART_STYLES:
            if needle in part["name"]:
                name, color, opacity = nice, c, o
                break

        v, f = part["vertices"], part["faces"]
        traces.append(go.Mesh3d(
            # glTF is "Y-up"; Plotly is "Z-up", so we swap axes here
            x=v[:, 0], y=-v[:, 2], z=v[:, 1],
            i=f[:, 0], j=f[:, 1], k=f[:, 2],
            color=color, opacity=opacity, name=name,
            hovertemplate=name + "<extra></extra>",
            flatshading=False,
            lighting=dict(ambient=0.5, diffuse=0.8, specular=0.25, roughness=0.55, fresnel=0.15),
            lightposition=dict(x=120, y=-220, z=260),
        ))

    fig = go.Figure(traces)
    hidden_axis = dict(visible=False, showbackground=False)
    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        scene=dict(
            xaxis=hidden_axis, yaxis=hidden_axis, zaxis=hidden_axis,
            aspectmode="data",
            dragmode="turntable",
            camera=dict(eye=dict(x=0.35, y=-1.55, z=0.35), up=dict(x=0, y=0, z=1)),
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    return fig
