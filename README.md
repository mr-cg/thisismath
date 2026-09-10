# Parametric Cube Wireframe + 3D Text — v3

This revision fixes two deployment issues.

## Font discovery on Streamlit Cloud

The previous version only used `font_manager.findSystemFonts()`. Streamlit Community Cloud may expose very few OS fonts, so the selector could collapse to only `Default Bold`.

v3 also scans Matplotlib's own bundled font directory:

```python
Path(matplotlib.get_data_path()) / "fonts" / "ttf"
```

That normally provides DejaVu and STIX families in the deployed Python environment. The app also scans an optional `./fonts` folder in your repo and lets you upload a `.ttf` or `.otf` from the sidebar.

No font files are included in this ZIP.

## Text sizing

The renderer now crops the text texture to the actual alpha/ink bounds before scaling the 3D text plane. So `80% of cube face` is based on the visible lettering, not transparent padding around it.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```
