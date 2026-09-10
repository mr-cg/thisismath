
"""
Optional server-side reference renderer.

Important V2 change:
- Cube rotation uses cube_R.
- Text rotation uses text_R directly.
- text_R is NOT multiplied by cube_R.

That makes text X/Y/Z absolute with respect to the camera/world, rather than relative
to the cube orientation.

The Streamlit UI itself uses live_cube.html for browser-side live rendering.
"""

from __future__ import annotations
from dataclasses import dataclass
from io import BytesIO
from typing import Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont


@dataclass
class RenderParams:
    width: int = 1600
    height: int = 900
    cube_scale: float = 1.0

    pan_deg: float = -25.0
    tilt_deg: float = 18.0
    roll_deg: float = 0.0
    camera_distance: float = 5.0
    fov_deg: float = 38.0

    line_thickness: float = 8.0
    thinning_strength: float = 0.75

    text: str = "THIS\nIS\nMATH"
    font_path: str | None = None
    font_size: int = 92
    text_rx_deg: float = 0.0
    text_ry_deg: float = 0.0
    text_rz_deg: float = 0.0
    text_world_per_px: float = 0.0040
    line_spacing: float = 1.05

    background_rgb: Tuple[int, int, int] = (255, 255, 255)
    wire_rgb: Tuple[int, int, int] = (0, 0, 0)
    text_rgb: Tuple[int, int, int] = (0, 0, 0)
    antialias: int = 2


def _rx(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], float)


def _ry(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], float)


def _rz(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], float)


def rotation_matrix(rx_deg=0.0, ry_deg=0.0, rz_deg=0.0):
    rx, ry, rz = map(np.deg2rad, (rx_deg, ry_deg, rz_deg))
    return _rz(rz) @ _ry(ry) @ _rx(rx)


def project(points, p: RenderParams, object_R):
    """Project points after applying ONLY the rotation supplied for that object."""
    pts = (object_R @ points.T).T.copy()
    pts[:, 2] += p.camera_distance

    aa = p.antialias
    f = (p.height * aa * 0.5) / np.tan(np.deg2rad(p.fov_deg) * 0.5)
    cx, cy = p.width * aa * 0.5, p.height * aa * 0.5
    z = np.maximum(pts[:, 2], 1e-4)

    return np.column_stack([
        cx + f * pts[:, 0] / z,
        cy - f * pts[:, 1] / z,
    ]), pts[:, 2]


def cube_vertices(scale):
    vals = (-scale, scale)
    return np.array([(x, y, z) for x in vals for y in vals for z in vals], float)


def cube_edges():
    verts = [(-1, -1, -1), (-1, -1, 1), (-1, 1, -1), (-1, 1, 1),
             (1, -1, -1), (1, -1, 1), (1, 1, -1), (1, 1, 1)]
    edges = []
    for i, a in enumerate(verts):
        for j in range(i + 1, len(verts)):
            b = verts[j]
            if sum(a[k] != b[k] for k in range(3)) == 1:
                edges.append((i, j))
    return edges


def _font(path, size):
    candidates = [
        path,
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            return ImageFont.truetype(candidate, size)
        except Exception:
            pass
    return ImageFont.load_default()


def _text_texture(p):
    aa = p.antialias
    font = _font(p.font_path, p.font_size * aa)
    lines = p.text.splitlines() or [""]

    probe = Image.new("L", (16, 16))
    d = ImageDraw.Draw(probe)
    boxes = [d.textbbox((0, 0), line or " ", font=font) for line in lines]
    widths = [b[2] - b[0] for b in boxes]
    line_h = max(b[3] - b[1] for b in boxes)
    step = int(line_h * p.line_spacing)
    pad = max(10 * aa, int(p.font_size * aa * .15))

    w = max(widths) + 2 * pad
    h = line_h + (len(lines) - 1) * step + 2 * pad
    tex = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tex)

    y = pad
    for line, box in zip(lines, boxes):
        lw = box[2] - box[0]
        x = (w - lw) / 2 - box[0]
        draw.text((x, y - box[1]), line, font=font, fill=(*p.text_rgb, 255))
        y += step
    return tex


def _homography(src, dst):
    A, b = [], []
    for (x, y), (u, v) in zip(src, dst):
        A += [
            [x, y, 1, 0, 0, 0, -u*x, -u*y],
            [0, 0, 0, x, y, 1, -v*x, -v*y],
        ]
        b += [u, v]
    h = np.linalg.solve(np.asarray(A, float), np.asarray(b, float))
    return np.append(h, 1.0).reshape(3, 3)


def _warp(texture, quad, size):
    tw, th = texture.size
    src = np.array([[0, 0], [tw-1, 0], [tw-1, th-1], [0, th-1]], float)
    H = np.linalg.inv(_homography(src, quad))
    H /= H[2, 2]
    coeffs = (*H[0], *H[1], H[2, 0], H[2, 1])
    return texture.transform(
        size,
        Image.Transform.PERSPECTIVE,
        data=coeffs,
        resample=Image.Resampling.BICUBIC,
    )


def render_scene(p: RenderParams):
    aa = p.antialias
    W, H = p.width * aa, p.height * aa
    canvas = Image.new("RGBA", (W, H), (*p.background_rgb, 255))

    # Independent rotations:
    cube_R = rotation_matrix(p.tilt_deg, p.pan_deg, p.roll_deg)
    text_R = rotation_matrix(p.text_rx_deg, p.text_ry_deg, p.text_rz_deg)

    # TEXT: absolute rotation. It does NOT inherit cube_R.
    tex = _text_texture(p)
    tw, th = tex.size
    world_per_px = p.text_world_per_px / aa
    hw, hh = tw * world_per_px / 2, th * world_per_px / 2
    plane = np.array([
        [-hw,  hh, 0],
        [ hw,  hh, 0],
        [ hw, -hh, 0],
        [-hw, -hh, 0],
    ], float)

    text_quad, _ = project(plane, p, text_R)
    # An edge-on text plane has no visible area and no invertible homography.
    area = 0.5 * abs(np.dot(text_quad[:, 0], np.roll(text_quad[:, 1], 1))
                     - np.dot(text_quad[:, 1], np.roll(text_quad[:, 0], 1)))
    if area > 1e-6:
        canvas = Image.alpha_composite(canvas, _warp(tex, text_quad, (W, H)))

    # CUBE: independent cube_R. Draw AFTER text to keep lines continuous.
    verts = cube_vertices(p.cube_scale)
    pts2d, depths = project(verts, p, cube_R)
    draw = ImageDraw.Draw(canvas)

    ordered = []
    for i, j in cube_edges():
        ordered.append(((depths[i] + depths[j]) / 2, i, j))
    ordered.sort(reverse=True)

    base = p.line_thickness * aa
    for z, i, j in ordered:
        ratio = p.camera_distance / max(z, 1e-4)
        width = max(1, round(base * ratio ** p.thinning_strength))
        draw.line(
            [tuple(pts2d[i]), tuple(pts2d[j])],
            fill=(*p.wire_rgb, 255),
            width=width,
        )

    if aa > 1:
        canvas = canvas.resize((p.width, p.height), Image.Resampling.LANCZOS)
    return canvas.convert("RGB")


def image_to_png_bytes(img):
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
