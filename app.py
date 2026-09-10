
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(
    page_title="Parametric Cube + Absolute 3D Text",
    page_icon="◫",
    layout="wide",
)

st.title("Parametric Cube Wireframe + Absolute 3D Text")
st.caption(
    "The preview is rendered directly in the browser, so sliders update continuously while you drag them. "
    "Choose independent text or text that follows the cube, and enable 3D thickness."
)

st.markdown(
    """<style>
    [data-testid="stMainBlockContainer"] { padding-top: 2rem; padding-bottom: 0; }
    iframe { height: calc(100dvh - 190px); min-height: 320px; }
    </style>""",
    unsafe_allow_html=True,
)
html_path = Path(__file__).with_name("live_cube.html")
components.html(
    html_path.read_text(encoding="utf-8"),
    height=1180,
    scrolling=False,
)
