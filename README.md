
# Parametric Cube Wireframe + 3D Text

A small Streamlit project for building a projector-friendly cube wireframe with:

- adjustable wireframe thickness
- depth-based perspective thinning
- pan / yaw
- tilt / pitch
- roll
- camera distance and field of view
- centered multiline text
- system font selection
- font size and line spacing
- independent X / Y / Z rotation of the text plane
- PNG export
- supersampled antialiasing

The text plane is always centered at the **geometric center of the cube**. The wireframe is rendered after the text, so the cube's lines stay continuous rather than being cut out behind the lettering.

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

## Controls

### Cube / camera
- **Cube size** changes the 3D cube extent.
- **Pan / yaw** rotates the scene around Y.
- **Tilt / pitch** rotates around X.
- **Roll** rotates around Z.
- **Camera distance** changes how close the camera is.
- **Perspective / FOV** controls perspective strength.

### Wireframe
- **Line thickness** is the nominal stroke width at the cube center depth.
- **Perspective thinning** controls how strongly stroke width changes with depth:
  - `0` = constant width
  - `~0.5–1.0` = natural perspective effect
  - `>1` = exaggerated thinning

### Text
The text is first rendered as a transparent 2D texture, then attached to a plane centered at `(0,0,0)` in the cube.

- **X rotation** tilts top/bottom of the text plane toward/away from the viewer.
- **Y rotation** turns the text plane left/right.
- **Z rotation** spins it within its own plane.

## Main files

- `app.py` — Streamlit user interface
- `renderer.py` — projection, text-plane warp, perspective stroke logic
- `requirements.txt` — Python dependencies

## Notes for anamorphic projection

For a corridor installation, place the projector as close as practical to the intended viewing point. Once the projected image is aligned to the physical surfaces, trace or tape the projected geometry without moving the projector.

This app generates the cube view itself. A later version could add an **anamorphic surface model** with separate wall/floor planes and a calibrated observer point.
