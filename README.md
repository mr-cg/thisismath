
# Parametric Cube Wireframe + Absolute 3D Text — V2

This version fixes the two interaction/geometry issues:

## 1. Text rotation is absolute

Cube rotation and text rotation now use independent rotation matrices.

Conceptually:

```python
cube_R = rotation_matrix(cube_tilt, cube_pan, cube_roll)
text_R = rotation_matrix(text_x, text_y, text_z)

cube_2d = project(cube_points, cube_R)
text_2d = project(text_points, text_R)
```

There is deliberately **no**:

```python
text_R = cube_R @ text_R
```

So changing cube pan, tilt, or roll does not change the text orientation.

## 2. Sliders are genuinely live while dragging

Native `st.slider()` values are sent from the browser to Python as Streamlit widget
interactions; they are not designed as a 60-fps graphics control.

V2 moves the interactive preview and its sliders into a browser-side HTML/JavaScript
component. Each range input listens to the browser's `input` event and redraws through
`requestAnimationFrame`.

That means the cube/text visibly rotate **during the drag**, not only after mouse-up.

## Other behavior

- Black wireframe on white.
- Wireframe is drawn after the text, so lines remain continuous through the text.
- Depth-based line thinning.
- Perspective/FOV and camera-distance controls.
- Absolute X/Y/Z text rotation.
- Local `.ttf` / `.otf` font loading.
- Client-side high-resolution PNG export.
- No JavaScript package build step is required.

## Run

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

## Files

- `app.py` — tiny Streamlit shell.
- `live_cube.html` — all live controls and browser-side rendering.
- `renderer.py` — optional Python/Pillow reference renderer with the same absolute-text fix.
- `requirements.txt`
