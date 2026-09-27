"""
Anatomical Matrix Generator — Biomolecule Toxicity Detective (mini project)

Run it with:
    python run.py            (installs anything missing, then starts the app)
or
    streamlit run app.py

This file only sets up the page and the navigation bar.
Each page lives in the app_pages/ folder.
"""

import streamlit as st

st.set_page_config(
    page_title="Anatomical Matrix Generator",
    page_icon="🧬",
    layout="wide",
)

pages = [
    st.Page("app_pages/generator.py", title="Organ generator", icon=":material/biotech:", default=True),
    st.Page("app_pages/dashboard.py", title="Data dashboard", icon=":material/monitoring:", url_path="dashboard"),
    st.Page("app_pages/how_it_works.py", title="How it works", icon=":material/school:", url_path="how-it-works"),
]

st.navigation(pages, position="top").run()
