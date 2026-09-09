
# Parametric Cube Wireframe + 3D Text — v2

## Main fix

Text size is now geometric, not pixel-based.

The control **Text block size (% of cube face)** scales the text block relative
to a cube face edge:

- 40%: compact
- 70–85%: good for the `THIS / IS / MATH` composition
- 100%: block spans roughly one full face edge
- above 100%: intentional oversized text

This means changing output resolution, camera FOV, or antialiasing no longer
causes the text to become mysteriously tiny.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```
