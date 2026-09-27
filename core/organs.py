"""
Organ data + scoring.

Everything the app knows about the 7 steps and the 3 organ profiles lives in
data/organs.json. Here we load it with `json`, put the profiles into a pandas
DataFrame, and score the user's answers with NumPy.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = json.loads((ROOT / "data" / "organs.json").read_text(encoding="utf-8"))

STEPS = DATA["steps"]                       # list of 7 step dicts
STEP_KEYS = [s["key"] for s in STEPS]       # ["tissue", "structure", ...]
ORGANS = DATA["organs"]                     # {"brain": {...}, "heart": {...}, "lung": {...}}

# Rows = organs, columns = parameters. This is the "anatomical matrix".
PROFILES = pd.DataFrame({key: organ["profile"] for key, organ in ORGANS.items()}).T[STEP_KEYS]


def option_label(step_key, value):
    """Human-readable label for an option value, e.g. ('tissue', 'cardiac') -> 'Cardiac muscle'."""
    step = next(s for s in STEPS if s["key"] == step_key)
    return step["options"].get(value, value)


def score_organs(answers):
    """
    Compare the answers with every organ profile.

    Returns a DataFrame sorted from best to worst match with columns:
        organ, label, matched, answered, score (0..1)
    """
    answered = [k for k in STEP_KEYS if answers.get(k)]
    user = np.array([answers[k] for k in answered])          # shape (n,)
    matrix = PROFILES[answered].to_numpy()                   # shape (3, n)

    matches = matrix == user                                  # True where organ agrees with you
    matched = matches.sum(axis=1)                             # how many agree, per organ
    score = matched / len(answered) if answered else np.zeros(len(PROFILES))

    result = pd.DataFrame({
        "organ": PROFILES.index,
        "label": [ORGANS[k]["label"] for k in PROFILES.index],
        "matched": matched if answered else 0,
        "answered": len(answered),
        "score": score,
    })
    # stable sort keeps brain -> heart -> lung order when two organs tie
    return result.sort_values("score", ascending=False, kind="stable").reset_index(drop=True)


def match_table(answers):
    """Parameter-by-parameter comparison: your answer vs each organ's expected value."""
    rows = []
    for step in STEPS:
        key = step["key"]
        yours = answers.get(key)
        row = {"Parameter": step["short"], "Your answer": option_label(key, yours) if yours else "—"}
        for organ_key, organ in ORGANS.items():
            expected = organ["profile"][key]
            tick = "✅" if yours == expected else "❌"
            row[organ["label"]] = f"{tick} {option_label(key, expected)}"
        rows.append(row)
    return pd.DataFrame(rows)


# ---------- saving / loading answers as JSON ----------

def answers_to_json(answers, best=None):
    payload = {
        "app": "Anatomical Matrix Generator",
        "version": 1,
        "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "answers": {k: answers[k] for k in STEP_KEYS if answers.get(k)},
    }
    if best is not None:
        payload["best_match"] = best
    return json.dumps(payload, indent=2)


def answers_from_json(raw_bytes):
    """Read an uploaded .json file and keep only valid answers. Returns (answers, skipped)."""
    payload = json.loads(raw_bytes.decode("utf-8"))
    source = payload.get("answers", payload) if isinstance(payload, dict) else {}

    answers, skipped = {}, []
    for step in STEPS:
        value = source.get(step["key"])
        if value in step["options"]:
            answers[step["key"]] = value
        elif value is not None:
            skipped.append(step["key"])
    return answers, skipped
