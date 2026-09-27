# Anatomical Matrix Generator 🧬

A pure-Python website for the **Biomolecule Toxicity Detective** mini project.
Answer 7 questions about a tissue sample and the app finds the closest-matching
organ (brain, heart or lung), then shows it as a real, rotatable 3D model.

Built only with Python — no HTML, CSS or JavaScript files.

## Pages

| Page | What it does |
|---|---|
| **Organ generator** | 7-step wizard with a live match panel, 3D result, radar charts, parameter breakdown, save/load answers as JSON |
| **Data dashboard** | Real dataset numbers (vital signs, ECG, EEG, airflow) as matplotlib charts, plus a "bring your own CSV" explorer |
| **How it works** | The method step by step: the anatomical matrix, NumPy scoring (with the real code), how the 3D files are read |

## Libraries

- **Streamlit** – turns the Python script into a website
- **pandas** – profile matrix, tables, CSV explorer
- **NumPy** – scoring and 3D vertex maths
- **matplotlib** – radar and dashboard charts
- **json / struct** – data files, saved answers, reading the `.glb` 3D models
- **Plotly** – the rotatable 3D organ viewer

## Project layout

```
app.py                    # main file: page setup + navigation
run.py                    # one-command launcher: python run.py
app_pages/
  generator.py            # landing -> wizard -> result
  dashboard.py            # data dashboard
  how_it_works.py         # method explained
core/
  organs.py               # loads organs.json, scoring with NumPy/pandas, JSON save/load
  glb.py                  # .glb 3D model reader (json + struct + NumPy)
  charts.py               # matplotlib charts + Plotly 3D figure
data/
  organs.json             # the 7 steps and 3 organ profiles
  dataset_summary.json    # dataset numbers used on the dashboard
models/                   # heart.glb, brain.glb, lung.glb
.streamlit/config.toml    # colours, font and light/dark theme
```

## Run it on your computer

```bash
python run.py
```

`run.py` installs any missing or outdated libraries and then starts the app
(the same as `pip install -r requirements.txt` followed by `streamlit run app.py`).

## Put it online (Streamlit Community Cloud, free)

1. Push this folder to a public GitHub repository.
2. Go to <https://share.streamlit.io>, sign in with GitHub and click **Create app**.
3. Pick the repository, branch `main`, main file `app.py`, then **Deploy**.

---

*Educational prototype only — not a diagnostic tool and does not replace medical judgment.*
