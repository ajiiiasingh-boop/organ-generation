"""
Data dashboard: the real dataset numbers behind the 'Real data' steps,
loaded with json, arranged with pandas and drawn with matplotlib.
"""

import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from core.charts import histogram, signal_panels, theme_mode, vitals_ranges
from core.organs import ORGANS, ROOT

summary = json.loads((ROOT / "data" / "dataset_summary.json").read_text(encoding="utf-8"))
vitals = pd.DataFrame(summary["vitals"]["measures"]).astype({"min": float, "max": float})
mode = theme_mode()

st.title("Data dashboard")
st.markdown(":gray[The numbers behind the three **Real data** steps of the generator, "
            "computed by our group from public medical datasets.]")

# ---------- headline numbers ----------
with st.container(horizontal=True, gap="medium"):
    st.metric("Patient vital-sign records", f"{summary['vitals']['n']:,}", border=True,
              icon=":material/monitor_heart:")
    st.metric("ECG beats analysed", f"{summary['ecg']['n_beats']:,}", border=True, icon=":material/ecg_heart:")
    st.metric("EEG recordings", f"{summary['eeg']['n']:,}", border=True, icon=":material/neurology:")
    st.metric("Airflow patients", f"{summary['airflow']['n']:,}", border=True, icon=":material/pulmonology:")

st.caption("Chart colour follows the organ each measure points to: "
           "**blue = brain**, **orange = heart**, **green = lung**.")

left, right = st.columns(2, gap="large")

with left:
    with st.container(border=True):
        st.subheader("Vital signs")
        st.caption(f"{summary['vitals']['n']:,} records · bar = observed range, dot = mean")
        fig = vitals_ranges(vitals, mode)
        st.pyplot(fig)
        plt.close(fig)

        spo2 = vitals.set_index("measure").loc["SpO2", "mean"]
        with st.container(horizontal=True, gap="small"):
            st.metric("Mean SpO₂ (lung)", f"{spo2:g}%", border=True)
            # Check the MAP value with NumPy: MAP ≈ DBP + (SBP − DBP) / 3
            sbp, dbp, map_given = vitals.set_index("measure").loc[
                ["Systolic BP", "Diastolic BP", "Mean arterial pressure"], "mean"].to_numpy()
            map_check = np.round(dbp + (sbp - dbp) / 3, 2)
            st.metric("MAP re-computed with NumPy", f"{map_check} mmHg",
                      delta=f"{map_check - map_given:+.2f} vs dataset value", delta_color="off", delta_arrow="off", border=True,
                      help="MAP ≈ diastolic + (systolic − diastolic) / 3, using the mean values")

with right:
    with st.container(border=True):
        st.subheader("Signals")
        st.caption("Which kind of signal each organ gives off")
        fig = signal_panels(summary, mode)
        st.pyplot(fig)
        plt.close(fig)

        signal_map = pd.DataFrame([
            {"Signal": "Rhythmic electrical (ECG)", "Points to": f"{ORGANS['heart']['emoji']} Heart",
             "Evidence": f"{summary['ecg']['normal_pct']}% normal rhythm"},
            {"Signal": "Variable neural (EEG)", "Points to": f"{ORGANS['brain']['emoji']} Brain",
             "Evidence": f"{summary['eeg']['min']}–{summary['eeg']['max']} {summary['eeg']['unit']}"},
            {"Signal": "Airflow, no electrical", "Points to": f"{ORGANS['lung']['emoji']} Lung",
             "Evidence": f"{summary['airflow']['min']}–{summary['airflow']['max']} {summary['airflow']['unit']}"},
        ])
        st.dataframe(signal_map, hide_index=True)

# ---------- table view ----------
with st.expander("See the vital-sign numbers as a table", icon=":material/table_chart:"):
    table = vitals.rename(columns={"measure": "Measure", "unit": "Unit", "mean": "Mean",
                                   "min": "Min", "max": "Max", "organ": "Organ"})
    table["Organ"] = table["Organ"].map(lambda k: ORGANS[k]["label"])
    st.dataframe(table, hide_index=True)
    st.download_button("Download as CSV", table.to_csv(index=False), file_name="vital_sign_summary.csv",
                       mime="text/csv", icon=":material/download:", on_click="ignore")

# ---------- bring your own data ----------
with st.expander("Explore your own CSV file", icon=":material/upload_file:"):
    st.caption("Upload any CSV (for example the full vital-signs dataset) and pandas will summarise it.")
    uploaded = st.file_uploader("CSV file", type=["csv"], label_visibility="collapsed")
    if uploaded is not None:
        try:
            df = pd.read_csv(uploaded)
        except Exception as error:
            st.error(f"Couldn't read that file: {error}")
        else:
            st.markdown(f"**{len(df):,} rows × {df.shape[1]} columns**")
            st.dataframe(df.head(50), height=240)
            numeric = df.select_dtypes("number")
            if numeric.empty:
                st.info("No numeric columns to chart.")
            else:
                st.markdown("**Summary statistics** :gray[(`df.describe()`)]")
                st.dataframe(numeric.describe().T.round(2))
                column = st.selectbox("Column to plot", numeric.columns)
                fig = histogram(numeric[column], mode, f"Distribution of {column}")
                st.pyplot(fig)
                plt.close(fig)

st.caption(":material/info: " + summary["_note"])
