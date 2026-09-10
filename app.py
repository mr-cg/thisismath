from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

import matplotlib
from matplotlib import font_manager
from PIL import ImageFont
import streamlit as st

from renderer import RenderParams, render_scene, image_to_png_bytes


st.set_page_config(
    page_title="Parametric Cube + 3D Text",
    page_icon="◫",
    layout="wide",
)


def _font_label(path: Path) -> str:
    """Return a readable family/style label for a TTF/OTF file."""
    try:
        prop = font_manager.FontProperties(fname=str(path))
        family = prop.get_name() or path.stem
        stem = path.stem.lower()

        style_bits = []
        if "bold" in stem or stem.endswith("bol") or "semibold" in stem:
            style_bits.append("Bold")
        if "italic" in stem or "oblique" in stem or stem.endswith("ita"):
            style_bits.append("Italic")
        if "mono" in stem:
            style_bits.append("Mono")

        style_bits = list(dict.fromkeys(style_bits))
        return f"{family} — {' '.join(style_bits)}" if style_bits else family
    except Exception:
        return path.stem


def _font_loads(path: Path) -> bool:
    try:
        ImageFont.truetype(str(path), size=32)
        return True
    except Exception:
        return False


@st.cache_data(show_spinner=False)
def discover_fonts() -> list[tuple[str, str]]:
    """Find fonts that are actually available in the deployed Python environment."""
    candidates: set[Path] = set()

    # 1. Crucial for Streamlit Cloud: fonts bundled with matplotlib itself.
    mpl_fonts = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    if mpl_fonts.exists():
        candidates.update(mpl_fonts.glob("*.ttf"))
        candidates.update(mpl_fonts.glob("*.otf"))

    # 2. Optional fonts the user later commits to a ./fonts directory.
    local_fonts = Path(__file__).parent / "fonts"
    if local_fonts.exists():
        candidates.update(local_fonts.rglob("*.ttf"))
        candidates.update(local_fonts.rglob("*.otf"))

    # 3. OS fonts, where available.
    for ext in ("ttf", "otf"):
        try:
            candidates.update(Path(p) for p in font_manager.findSystemFonts(fontext=ext))
        except Exception:
            pass

    rows: list[tuple[str, str]] = []
    seen_paths: set[str] = set()

    for path in sorted(candidates, key=lambda p: str(p).lower()):
        if not path.is_file() or not _font_loads(path):
            continue
        resolved = str(path.resolve())
        if resolved in seen_paths:
            continue
        seen_paths.add(resolved)
        rows.append((_font_label(path), str(path)))

    # Make duplicate labels selectable.
    counts: dict[str, int] = {}
    unique_rows = []
    for label, path in sorted(rows, key=lambda x: (x[0].lower(), x[1].lower())):
        counts[label] = counts.get(label, 0) + 1
        shown = label if counts[label] == 1 else f"{label} ({counts[label]})"
        unique_rows.append((shown, path))

    return unique_rows


def save_uploaded_font(uploaded_file) -> str | None:
    if uploaded_file is None:
        return None

    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in {".ttf", ".otf"}:
        return None

    data = uploaded_file.getvalue()
    digest = hashlib.sha256(data).hexdigest()[:12]
    target = Path(tempfile.gettempdir()) / f"cube_font_{digest}{suffix}"
    if not target.exists():
        target.write_bytes(data)

    return str(target) if _font_loads(target) else None


st.title("Parametric Cube Wireframe + 3D Text")
st.caption(
    "Fonts are loaded from Matplotlib's bundled font library, local repo fonts, "
    "and optionally an uploaded TTF/OTF."
)

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

    uploaded_font = st.file_uploader(
        "Upload custom font (optional)",
        type=["ttf", "otf"],
        help="For a specific school/brand typeface. The font is used by the renderer in this app session.",
    )
    uploaded_font_path = save_uploaded_font(uploaded_font)

    discovered = discover_fonts()
    font_options: list[str] = []
    font_lookup: dict[str, str | None] = {}

    if uploaded_font_path:
        uploaded_label = f"Uploaded — {Path(uploaded_font.name).stem}"
        font_options.append(uploaded_label)
        font_lookup[uploaded_label] = uploaded_font_path

    for label, path in discovered:
        if label not in font_lookup:
            font_options.append(label)
            font_lookup[label] = path

    if not font_options:
        font_options = ["Renderer fallback"]
        font_lookup["Renderer fallback"] = None

    preferred_index = 0
    if not uploaded_font_path:
        for i, label in enumerate(font_options):
            if "dejavu sans" in label.lower() and "bold" in label.lower():
                preferred_index = i
                break

    selected_font = st.selectbox("Font", font_options, index=preferred_index)
    font_path = font_lookup[selected_font]
    st.caption(f"{len(discovered)} bundled/system font files detected")

    text_size_pct = st.slider(
        "Text block size (% of cube face)",
        10,
        130,
        80,
        1,
        help=(
            "Measured from the actual visible glyph bounds. At 80%, the visible text block "
            "occupies about 80% of one cube-face edge."
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
font = {selected_font}
text XYZ = ({text_rx_deg:.1f}°, {text_ry_deg:.1f}°, {text_rz_deg:.1f}°)""",
        language=None,
    )

st.info(
    "v3 fixes font discovery on Streamlit Cloud and sizes the text from the actual visible letter bounds."
)
