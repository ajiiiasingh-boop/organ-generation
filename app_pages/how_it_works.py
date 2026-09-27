"""
How it works: the method behind the generator, explained with the real code.
"""

import inspect

import pandas as pd
import streamlit as st

from core import glb
from core.charts import load_organ_model
from core.organs import ORGANS, PROFILES, STEP_KEYS, STEPS, option_label, score_organs

st.title("How it works")
st.markdown(":gray[From seven answers to a rotating 3D organ — the method, step by step, "
            "with the actual Python code that runs this site.]")

# ---------- overview ----------
st.subheader("1 · The pipeline")
st.mermaid_chart("""
flowchart LR
    A[7 answers<br/>from the wizard] --> B[Answer vector<br/>NumPy array]
    P[(organs.json<br/>3 organ profiles)] --> M[Profile matrix<br/>pandas DataFrame]
    B --> C{Compare<br/>matrix == answers}
    M --> C
    C --> D[Score = matches / answered]
    D --> E[Rank organs]
    E --> F[3D model<br/>GLB read with json + struct + NumPy]
    E --> G[Charts<br/>matplotlib]
""")

# ---------- parameters ----------
st.subheader("2 · The seven parameters")
st.markdown("Four describe the tissue itself (textbook biology). Three use values our group computed "
            "from real datasets — see the **Data dashboard** page.")
params = pd.DataFrame([{
    "#": i + 1,
    "Parameter": s["title"],
    "Options": ", ".join(s["options"].values()),
    "Real data": "✅" if s["real"] else "",
} for i, s in enumerate(STEPS)])
st.dataframe(params, hide_index=True, column_config={"#": st.column_config.NumberColumn(width="small")})

# ---------- profiles ----------
st.subheader("3 · The anatomical matrix")
st.markdown("Each organ has one expected answer per parameter. Loaded from `data/organs.json` "
            "into a pandas DataFrame, it becomes a 3 × 7 table:")
readable = PROFILES.copy()
for key in STEP_KEYS:
    readable[key] = readable[key].map(lambda value, k=key: option_label(k, value))
readable.index = [f"{ORGANS[k]['emoji']} {ORGANS[k]['label']}" for k in readable.index]
readable.columns = [s["short"] for s in STEPS]
st.dataframe(readable)

# ---------- scoring ----------
st.subheader("4 · Scoring with NumPy")
st.markdown("For each organ we count how many of your answers agree with its profile, "
            "then divide by the number of questions you answered:")
st.latex(r"\text{score}_{\text{organ}} = \frac{1}{n}\sum_{k=1}^{n} \mathbf{1}\left[\,a_k = p_{\text{organ},k}\,\right]")
st.markdown("`matrix == user` compares all three organs at once (NumPy *broadcasting*), "
            "giving a True/False table; `.sum(axis=1)` counts the Trues in each row.")
st.code(inspect.getsource(score_organs), language="python")

st.markdown("**Try it** — this uses your answers from the generator, or a sample if you haven't answered yet:")
answers = st.session_state.get("answers") or {}
if not any(answers.values()):
    answers = dict(PROFILES.loc["heart"])
    answers["regen"] = "high"          # one deliberate mismatch so the scores differ
    st.caption("Sample: a heart-like tissue that claims high regeneration.")

answered = [k for k in STEP_KEYS if answers.get(k)]
comparison = (PROFILES[answered] == pd.Series(answers)[answered])
comparison.index = [ORGANS[k]["label"] for k in comparison.index]
comparison.columns = [next(s["short"] for s in STEPS if s["key"] == k) for k in answered]
left, right = st.columns([2, 1], gap="large")
with left:
    st.markdown(":gray[`matrix == user` → True means the organ agrees]")
    st.dataframe(comparison)
with right:
    st.markdown(":gray[`score_organs(answers)`]")
    scores = score_organs(answers)[["label", "matched", "answered", "score"]]
    st.dataframe(scores, hide_index=True,
                 column_config={"score": st.column_config.ProgressColumn("score", min_value=0, max_value=1, format="percent")})

# ---------- 3D models ----------
st.subheader("5 · Reading the 3D models")
st.markdown(
    "The organ models are **.glb** files (binary glTF). A GLB file is a 12-byte header, then a **JSON** "
    "chunk that describes the meshes, then a **binary** chunk with the raw numbers. We read the header with "
    "`struct`, the description with `json`, and turn the raw bytes into vertex arrays with `numpy.frombuffer` "
    "— no 3D library needed. Plotly then draws the triangles in your browser."
)
rows = []
for key, organ in ORGANS.items():
    _, stats = load_organ_model(key)
    rows.append({"Model": f"{organ['emoji']} {organ['label']}", "Parts": stats["parts"],
                 "Vertices": stats["vertices"], "Triangles": stats["triangles"],
                 "File size (MB)": round(stats["file_mb"], 2)})
st.dataframe(pd.DataFrame(rows), hide_index=True, column_config={
    "Vertices": st.column_config.NumberColumn(format="localized"),
    "Triangles": st.column_config.NumberColumn(format="localized"),
})
with st.expander("Show the GLB reader code", icon=":material/code:"):
    st.code(inspect.getsource(glb.read_glb) + "\n\n" + inspect.getsource(glb.read_accessor), language="python")

# ---------- libraries ----------
st.subheader("6 · Libraries used")
st.dataframe(pd.DataFrame([
    {"Library": "Streamlit", "Used for": "Turns the Python script into this website (pages, buttons, layout)"},
    {"Library": "pandas", "Used for": "Organ profile matrix, score tables, dataset summaries, CSV explorer"},
    {"Library": "NumPy", "Used for": "Scoring (broadcast comparison), reading and transforming 3D vertices"},
    {"Library": "matplotlib", "Used for": "Radar charts, vital-sign ranges, signal charts, histograms"},
    {"Library": "json", "Used for": "Organ data file, dataset summary, saving and loading your answers, GLB headers"},
    {"Library": "struct", "Used for": "Reading the binary header of the .glb model files"},
    {"Library": "Plotly", "Used for": "The rotatable 3D organ (matplotlib 3D can't be rotated in a web page)"},
]), hide_index=True)

st.caption(":material/info: Educational prototype only — not a diagnostic tool and does not replace medical judgment.")
