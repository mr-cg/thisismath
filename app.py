
from __future__ import annotations

from pathlib import Path

import streamlit as st
from matplotlib import font_manager

from renderer import RenderParams, render_scene, image_to_png_bytes


st.set_page_config(
    page_title="Parametric Cube + 3D Text",
    page_icon="◫",
    layout="wide",
)

st.title("Parametric Cube Wireframe + 3D Text")
st.caption(
    "Text size is geometric and relative to the cube face, rather than tied to raster pixels."
)


@st.cache_data(show_spinner=False)
def discover_fonts():
    found = {}
    try:
        for path in font_manager.findSystemFonts(fontext="ttf"):
            try:
                prop = font_manager.FontProperties(fname=path)
                name = prop.get_name()
                prev = found.get(name)
                if prev is None or (
                    "bold" in Path(path).stem.lower()
                    and "bold" not in Path(prev).stem.lower()
                ):
                    found[name] = path
            except Exception:
                pass
    except Exception:
        pass

    items = [("Default Bold", None)]
    items += sorted(found.items(), key=lambda x: x[0].lower())
    return items


fonts = discover_fonts()
font_labels = [name for name, _ in fonts]
font_lookup = dict(fonts)

with st.sidebar:
    st.header("Output")

    preset = st.selectbox(
        "Canvas preset",
        ["16:9 — 1600×900", "Full HD — 1920×1080", "4:3 — 1600×1200", "Custom"],
    )

    if preset == "16:9 — 1600×900":
        width, height = 1600, 900
    elif preset == "Full HD — 1920×1080":
        width, height = 1920, 1080
    elif preset == "4:3 — 1600×1200":
        width, height = 1600, 1200
    else:
        c1, c2 = st.columns(2)
        width = c1.number_input("Width", 400, 4096, 1600, 50)
        height = c2.number_input("Height", 400, 4096, 900, 50)

    st.divider()
    st.header("Cube / camera")

    cube_scale = st.slider("Cube size", 0.4, 1.6, 1.0, 0.01)
    pan_deg = st.slider("Pan / yaw (°)", -75.0, 75.0, 0.0, 0.5)
    tilt_deg = st.slider("Tilt / pitch (°)", -75.0, 75.0, 0.0, 0.5)
    roll_deg = st.slider("Roll (°)", -45.0, 45.0, 0.0, 0.5)
    camera_distance = st.slider("Camera distance", 3.0, 10.0, 5.0, 0.05)
    fov_deg = st.slider("Perspective / FOV (°)", 15.0, 80.0, 38.0, 0.5)

    st.divider()
    st.header("Wireframe")

    line_thickness = st.slider("Line thickness", 1.0, 30.0, 8.0, 0.5)
    thinning_strength = st.slider(
        "Perspective thinning",
        0.0,
        2.0,
        0.75,
        0.05,
        help="0 = constant width; larger values exaggerate near/far stroke differences.",
    )

    st.divider()
    st.header("Text")

    text = st.text_area("Text", "THIS\nIS\nMATH", height=120)
    selected_font = st.selectbox("Font", font_labels, index=0)
    font_path = font_lookup[selected_font]

    text_size_pct = st.slider(
        "Text block size (% of cube face)",
        10,
        130,
        80,
        1,
        help=(
            "This is the actual geometric size. 80% means the text block's largest "
            "dimension occupies about 80% of one cube-face edge."
        ),
    )

    line_spacing = st.slider("Line spacing", 0.75, 1.80, 1.05, 0.01)

    st.subheader("Text rotation")
    text_rx_deg = st.slider("X rotation (°)", -90.0, 90.0, 0.0, 0.5)
    text_ry_deg = st.slider("Y rotation (°)", -90.0, 90.0, 0.0, 0.5)
    text_rz_deg = st.slider("Z rotation (°)", -180.0, 180.0, 0.0, 0.5)

    st.divider()
    aa = st.select_slider(
        "Render quality",
        options=[1, 2, 3],
        value=2,
        format_func=lambda x: f"{x}× antialias",
    )


params = RenderParams(
    width=int(width),
    height=int(height),
    cube_scale=float(cube_scale),
    pan_deg=float(pan_deg),
    tilt_deg=float(tilt_deg),
    roll_deg=float(roll_deg),
    camera_distance=float(camera_distance),
    fov_deg=float(fov_deg),
    line_thickness=float(line_thickness),
    thinning_strength=float(thinning_strength),
    text=text,
    font_path=font_path,
    text_face_fraction=float(text_size_pct) / 100.0,
    line_spacing=float(line_spacing),
    text_rx_deg=float(text_rx_deg),
    text_ry_deg=float(text_ry_deg),
    text_rz_deg=float(text_rz_deg),
    antialias=int(aa),
)

with st.spinner("Rendering…"):
    img = render_scene(params)

left, right = st.columns([4, 1])

with left:
    st.image(img, use_container_width=True)

with right:
    st.markdown("#### Export")

    st.download_button(
        "Download PNG",
        data=image_to_png_bytes(img),
        file_name="parametric_cube.png",
        mime="image/png",
        use_container_width=True,
    )

    st.markdown("#### Current view")
    st.code(
        f"""pan = {pan_deg:.1f}°
tilt = {tilt_deg:.1f}°
roll = {roll_deg:.1f}°
FOV = {fov_deg:.1f}°
line = {line_thickness:.1f}px
text = {text_size_pct}% face
text XYZ = ({text_rx_deg:.1f}°, {text_ry_deg:.1f}°, {text_rz_deg:.1f}°)""",
        language=None,
    )

st.info(
    "The text block is now sized in the same 3D units as the cube. "
    "Its raster font size is only used internally for sharp rendering."
)
