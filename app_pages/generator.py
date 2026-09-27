"""
Organ generator page: landing screen -> 7-step wizard -> result with a 3D model.

Which screen is showing is stored in st.session_state, so the page
remembers where you are every time Streamlit re-runs the script.
"""

import json

import matplotlib.pyplot as plt
import streamlit as st

from core.charts import load_organ_model, organ_figure, radar_chart, theme_mode
from core.organs import (
    ORGANS,
    STEPS,
    answers_from_json,
    answers_to_json,
    match_table,
    option_label,
    score_organs,
)

ss = st.session_state
ss.setdefault("screen", "landing")    # "landing" | "wizard" | "result"
ss.setdefault("step", 0)              # which of the 7 steps is open
ss.setdefault("answers", {})          # {"tissue": "cardiac", ...}
ss.setdefault("nonce", 0)             # changing this resets the option widgets


# ---------- button callbacks ----------

def start():
    ss.step = 0
    ss.screen = "wizard"


def go_back():
    if ss.step == 0:
        ss.screen = "landing"
    else:
        ss.step -= 1


def go_next():
    if ss.step < len(STEPS) - 1:
        ss.step += 1
    else:
        ss.screen = "result"
        ss.just_generated = True


def jump_to(index):
    ss.step = index
    ss.screen = "wizard"


def pick(step_key, widget_key):
    ss.answers[step_key] = ss[widget_key]


def adjust():
    ss.step = 0
    ss.nonce += 1
    ss.screen = "wizard"


def start_over():
    ss.answers = {}
    ss.step = 0
    ss.nonce += 1
    ss.screen = "landing"


def load_saved(uploader_key):
    uploaded = ss.get(uploader_key)
    if uploaded is None:
        return
    try:
        answers, skipped = answers_from_json(uploaded.getvalue())
    except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
        ss.load_message = ("error", "That file isn't a valid answers .json file.")
        return
    if not answers:
        ss.load_message = ("error", "No answers found in that file.")
        return

    ss.answers = answers
    ss.nonce += 1
    missing = [i for i, s in enumerate(STEPS) if s["key"] not in answers]
    if missing:
        ss.step, ss.screen = missing[0], "wizard"
    else:
        ss.screen = "result"
    note = f" ({len(skipped)} unknown value(s) skipped)" if skipped else ""
    ss.load_message = ("success", f"Loaded {len(answers)} of {len(STEPS)} answers{note}.")


def show_load_message():
    message = ss.pop("load_message", None)
    if message:
        kind, text = message
        st.toast(text, icon=":material/check_circle:" if kind == "success" else ":material/error:")


# ---------- screen 1: landing ----------

def landing():
    _, middle, _ = st.columns([1, 3, 1])
    with middle:
        st.space("medium")
        st.badge("Biomolecule Toxicity Detective · Mini project", icon=":material/science:", color="green")
        st.title("Anatomical Matrix Generator")
        st.markdown(
            ":gray[Configure structural, functional and physiological parameters step by step "
            "to profile a tissue sample, then see the closest-matching organ as a real 3D model.]"
        )
        st.space("small")

        for column, organ_key in zip(st.columns(3), ORGANS):
            organ = ORGANS[organ_key]
            with column.container(border=True):
                st.markdown(f"### {organ['emoji']} {organ['label']}")
                try:
                    with st.spinner("Loading model…"):
                        _, stats = load_organ_model(organ_key)
                    st.badge("3D model ready", icon=":material/check:", color="green")
                    st.caption(f"{stats['triangles']:,} triangles · {stats['file_mb']:.1f} MB")
                except Exception as error:  # a broken file shouldn't crash the page
                    st.badge("Model failed", icon=":material/close:", color="red")
                    st.caption(str(error)[:80])

        st.space("small")
        with st.container(horizontal=True, vertical_alignment="center", gap="small"):
            st.button("Start profiling", type="primary", icon=":material/arrow_forward:",
                      icon_position="right", on_click=start)
            with st.popover("Load saved answers", icon=":material/upload_file:"):
                uploader_key = f"upload_{ss.nonce}"
                st.file_uploader("Answers file (.json)", type=["json"], key=uploader_key,
                                 on_change=load_saved, args=(uploader_key,))
                st.caption("Use a file you downloaded from the results screen.")
        st.caption("7 steps · 3 of them use values computed from real datasets · about a minute")


# ---------- screen 2: wizard ----------

def live_match_panel():
    scores = score_organs(ss.answers)
    by_organ = scores.set_index("organ")
    answered = int(scores["answered"].iloc[0])
    leader = scores["organ"].iloc[0] if answered else None
    tie = answered and scores["score"].iloc[0] == scores["score"].iloc[1]

    with st.container(border=True):
        st.markdown("**Live match**")
        st.caption("Updates as you answer" if answered else "Pick an option to see the organs react")
        for organ_key, organ in ORGANS.items():   # fixed order so bars never jump around
            row = by_organ.loc[organ_key]
            with st.container(gap="xxsmall"):
                with st.container(horizontal=True, vertical_alignment="center", gap="small"):
                    st.markdown(f"{organ['emoji']} **{organ['label']}** :gray[{int(row.matched)}/{answered}]")
                    if organ_key == leader and not tie:
                        st.badge("Leading", color="green")
                st.progress(float(row.score))

    with st.container(border=True, gap="xxsmall"):
        st.markdown("**Your answers**")
        st.caption("Click any step to jump back to it")
        for index, step in enumerate(STEPS):
            value = ss.answers.get(step["key"])
            text = f"{step['short']}: {option_label(step['key'], value)}" if value else f"{step['short']}: —"
            if index == ss.step:
                icon = ":material/edit:"
            elif value:
                icon = ":material/check_circle:"
            else:
                icon = ":material/radio_button_unchecked:"
            st.button(text, key=f"jump_{index}", type="tertiary", icon=icon, on_click=jump_to, args=(index,))


def wizard():
    step = STEPS[ss.step]
    key = step["key"]
    total = len(STEPS)
    last = ss.step == total - 1

    main, side = st.columns([2.1, 1], gap="large")
    with main:
        st.progress((ss.step + 1) / total, text=f"Step {ss.step + 1} of {total}")
        with st.container(border=True):
            with st.container(horizontal=True, vertical_alignment="center", gap="small"):
                st.subheader(step["title"])
                if step["real"]:
                    st.badge("Real data", icon=":material/verified:", color="green")
            st.markdown(f":gray[{step['prompt']}]")
            st.space("small")

            widget_key = f"pick_{key}_{ss.nonce}"
            st.pills(
                step["title"],
                options=list(step["options"]),
                format_func=lambda value: step["options"][value],
                default=ss.answers.get(key),
                key=widget_key,
                on_change=pick,
                args=(key, widget_key),
                label_visibility="collapsed",
            )

            if step.get("notes"):
                with st.container(border=True, gap="xsmall"):
                    st.markdown(":material/dataset: **What the datasets show**")
                    st.markdown("\n".join(f"- {note}" for note in step["notes"]))

        with st.container(horizontal=True, horizontal_alignment="distribute"):
            st.button("Back", icon=":material/arrow_back:", on_click=go_back)
            st.button(
                "Generate organ" if last else "Continue",
                type="primary",
                icon=":material/biotech:" if last else ":material/arrow_forward:",
                icon_position="right",
                disabled=not ss.answers.get(key),
                on_click=go_next,
            )

    with side:
        live_match_panel()


# ---------- screen 3: result ----------

def result():
    scores = score_organs(ss.answers)
    if int(scores["answered"].iloc[0]) == 0:
        ss.screen = "landing"
        st.rerun()

    best = scores.iloc[0]
    organ = ORGANS[best.organ]
    tied = scores[scores["score"] == best.score]["label"].tolist()

    if ss.pop("just_generated", False):
        st.toast(f"Profile generated — closest match: {organ['label']}", icon=":material/biotech:")

    info, viewer = st.columns([1, 1.35], gap="large")

    with info:
        st.caption("Closest match")
        st.title(f"{organ['emoji']} {organ['label']}")
        with st.container(horizontal=True, gap="small"):
            st.badge(f"{round(best.score * 100)}% match", icon=":material/check_circle:", color="green")
            st.badge(f"{int(best.matched)} of {int(best.answered)} parameters", color="gray")
        if len(tied) > 1:
            st.warning(f"It's a tie between {' and '.join(tied)}. Try adjusting a parameter to separate them.",
                       icon=":material/balance:")
        st.write(organ["about"])

        with st.container(border=True):
            st.markdown("**Match scores**")
            for row in scores.itertuples():
                emoji = ORGANS[row.organ]["emoji"]
                with st.container(gap="xxsmall"):
                    st.markdown(f"{emoji} {row.label} — **{round(row.score * 100)}%** :gray[({row.matched}/{row.answered})]")
                    st.progress(float(row.score))

        with st.container(horizontal=True, gap="small"):
            st.button("Adjust parameters", icon=":material/tune:", on_click=adjust)
            st.button("Start over", type="primary", icon=":material/restart_alt:", on_click=start_over)
            st.download_button(
                "Save answers",
                data=answers_to_json(ss.answers, best=organ["label"]),
                file_name="organ_answers.json",
                mime="application/json",
                icon=":material/download:",
                on_click="ignore",
            )

    with viewer:
        with st.container(border=True):
            shown = st.segmented_control(
                "3D model",
                options=list(ORGANS),
                format_func=lambda k: f"{ORGANS[k]['emoji']} {ORGANS[k]['label']}",
                default=best.organ,
                required=True,
                key=f"model_{best.organ}_{ss.nonce}",
                label_visibility="collapsed",
            ) or best.organ
            st.plotly_chart(
                organ_figure(shown),
                theme=None,
                config={"displayModeBar": False, "scrollZoom": True},
            )
            st.caption(":material/3d_rotation: Drag to rotate · scroll to zoom · double-click to reset · hover to name parts. "
                       "Real downloaded 3D model; texture removed and a flat anatomical colour applied.")

    st.space("small")
    radar_tab, table_tab, json_tab = st.tabs(
        [":material/radar: Radar chart", ":material/table_chart: Parameter breakdown", ":material/data_object: Answers as JSON"]
    )
    with radar_tab:
        for column, organ_key in zip(st.columns(3), ORGANS):
            fig = radar_chart(organ_key, ss.answers, scores, theme_mode())
            column.pyplot(fig)
            plt.close(fig)
        st.caption("Each spoke is one parameter. It reaches the edge when that organ agrees with your answer, "
                   "so the fuller the shape, the closer the match.")
    with table_tab:
        st.dataframe(match_table(ss.answers), hide_index=True)
    with json_tab:
        st.json(json.loads(answers_to_json(ss.answers, best=organ["label"])))

    st.caption(":material/info: Educational prototype only — not a diagnostic tool and does not replace medical judgment.")


# ---------- choose which screen to draw ----------

show_load_message()
{"landing": landing, "wizard": wizard, "result": result}[ss.screen]()
