
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Iterable, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont


@dataclass
class RenderParams:
    width: int = 1600
    height: int = 900

    # Cube / camera
    cube_scale: float = 1.0
    pan_deg: float = 0.0
    tilt_deg: float = 0.0
    roll_deg: float = 0.0
    camera_distance: float = 5.0
    fov_deg: float = 38.0

    # Wireframe
    line_thickness: float = 8.0
    thinning_strength: float = 0.75

    # Text
    text: str = "THIS\nIS\nMATH"
    font_path: str | None = None
    font_size: int = 92
    text_rx_deg: float = 0.0
    text_ry_deg: float = 0.0
    text_rz_deg: float = 0.0
    text_world_per_px: float = 0.0040
    line_spacing: float = 1.05

    # Appearance
    background_rgb: Tuple[int, int, int] = (255, 255, 255)
    wire_rgb: Tuple[int, int, int] = (0, 0, 0)
    text_rgb: Tuple[int, int, int] = (0, 0, 0)
    antialias: int = 2


def _rx(a: float) -> np.ndarray:
    c, s = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], dtype=float)


def _ry(a: float) -> np.ndarray:
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=float)


def _rz(a: float) -> np.ndarray:
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=float)


def rotation_matrix(rx_deg=0.0, ry_deg=0.0, rz_deg=0.0) -> np.ndarray:
    rx = np.deg2rad(rx_deg)
    ry = np.deg2rad(ry_deg)
    rz = np.deg2rad(rz_deg)
    # Intrinsic-style X -> Y -> Z rotation.
    return _rz(rz) @ _ry(ry) @ _rx(rx)


def _project(points: np.ndarray, p: RenderParams, scene_R: np.ndarray):
    """
    Perspective-project Nx3 world points to image pixels.
    Camera is at the origin looking along +Z; the object is translated forward.
    """
    pts = (scene_R @ points.T).T.copy()
    pts[:, 2] += p.camera_distance

    f = (p.height * p.antialias * 0.5) / np.tan(np.deg2rad(p.fov_deg) * 0.5)
    cx = p.width * p.antialias * 0.5
    cy = p.height * p.antialias * 0.5

    z = np.maximum(pts[:, 2], 1e-4)
    sx = cx + f * pts[:, 0] / z
    sy = cy - f * pts[:, 1] / z
    return np.column_stack([sx, sy]), pts[:, 2]


def _cube_vertices(scale: float) -> np.ndarray:
    # 8 vertices of a cube centered at the origin.
    vals = (-scale, scale)
    return np.array([(x, y, z) for x in vals for y in vals for z in vals], dtype=float)


def _cube_edges() -> list[tuple[int, int]]:
    verts = [(-1, -1, -1), (-1, -1, 1), (-1, 1, -1), (-1, 1, 1),
             (1, -1, -1), (1, -1, 1), (1, 1, -1), (1, 1, 1)]
    edges = []
    for i, a in enumerate(verts):
        for j in range(i + 1, len(verts)):
            b = verts[j]
            if sum(int(a[k] != b[k]) for k in range(3)) == 1:
                edges.append((i, j))
    return edges


def _default_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    for c in candidates:
        try:
            return ImageFont.truetype(c, size=size)
        except Exception:
            pass
    return ImageFont.load_default()


def _load_font(path: str | None, size: int):
    if path:
        try:
            return ImageFont.truetype(path, size=size)
        except Exception:
            pass
    return _default_font(size)


def _render_text_texture(p: RenderParams):
    aa = p.antialias
    font = _load_font(p.font_path, int(p.font_size * aa))
    lines = p.text.splitlines() or [""]

    # Measure each line.
    probe = Image.new("L", (16, 16), 0)
    d = ImageDraw.Draw(probe)
    boxes = [d.textbbox((0, 0), line if line else " ", font=font) for line in lines]
    widths = [max(1, b[2] - b[0]) for b in boxes]
    heights = [max(1, b[3] - b[1]) for b in boxes]

    line_h = max(heights) if heights else int(p.font_size * aa)
    spacing = max(1, int(line_h * p.line_spacing))
    pad = max(8 * aa, int(p.font_size * aa * 0.15))
    tex_w = max(widths) + 2 * pad
    tex_h = line_h + (len(lines) - 1) * spacing + 2 * pad

    rgba = Image.new("RGBA", (int(tex_w), int(tex_h)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(rgba)

    y = pad
    fill = (*p.text_rgb, 255)
    for line, box in zip(lines, boxes):
        w = max(1, box[2] - box[0])
        x = (tex_w - w) / 2 - box[0]
        draw.text((x, y - box[1]), line, font=font, fill=fill)
        y += spacing

    return rgba


def _homography(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    """
    Return H such that dst ~ H * src in homogeneous coordinates.
    src and dst are shape (4,2).
    """
    A = []
    b = []
    for (x, y), (u, v) in zip(src, dst):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        b.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y])
        b.append(v)
    h = np.linalg.solve(np.asarray(A, float), np.asarray(b, float))
    return np.append(h, 1.0).reshape(3, 3)


def _warp_texture_to_quad(texture: Image.Image, quad_xy: np.ndarray, canvas_size: tuple[int, int]) -> Image.Image:
    """
    Projectively warp the entire texture into the destination quadrilateral.
    quad_xy order: top-left, top-right, bottom-right, bottom-left.
    """
    tw, th = texture.size
    src = np.array([[0, 0], [tw - 1, 0], [tw - 1, th - 1], [0, th - 1]], dtype=float)
    dst = np.asarray(quad_xy, dtype=float)

    # PIL expects inverse mapping output -> input.
    H_src_to_dst = _homography(src, dst)
    H_dst_to_src = np.linalg.inv(H_src_to_dst)
    H_dst_to_src /= H_dst_to_src[2, 2]

    a, b, c = H_dst_to_src[0]
    d, e, f = H_dst_to_src[1]
    g, h, _ = H_dst_to_src[2]
    coeffs = (a, b, c, d, e, f, g, h)

    return texture.transform(
        canvas_size,
        Image.Transform.PERSPECTIVE,
        data=coeffs,
        resample=Image.Resampling.BICUBIC,
    )


def render_scene(p: RenderParams) -> Image.Image:
    aa = max(1, int(p.antialias))
    W, H = p.width * aa, p.height * aa

    bg = (*p.background_rgb, 255)
    canvas = Image.new("RGBA", (W, H), bg)

    # "Pan" = yaw around Y; "tilt" = pitch around X.
    scene_R = rotation_matrix(p.tilt_deg, p.pan_deg, p.roll_deg)

    # ---- Text plane, centered at cube's geometric center ----
    texture = _render_text_texture(p)
    tw, th = texture.size

    # Texture pixel size -> world-space size. antialias is already included in tw/th,
    # so divide it back out for stable physical scale.
    world_per_px = p.text_world_per_px / aa
    half_w = tw * world_per_px / 2.0
    half_h = th * world_per_px / 2.0

    text_plane = np.array([
        [-half_w,  half_h, 0.0],   # TL
        [ half_w,  half_h, 0.0],   # TR
        [ half_w, -half_h, 0.0],   # BR
        [-half_w, -half_h, 0.0],   # BL
    ], dtype=float)

    text_R = rotation_matrix(p.text_rx_deg, p.text_ry_deg, p.text_rz_deg)
    text_plane = (text_R @ text_plane.T).T
    text_quad_2d, _ = _project(text_plane, p, scene_R)

    warped = _warp_texture_to_quad(texture, text_quad_2d, (W, H))
    canvas = Image.alpha_composite(canvas, warped)

    # ---- Cube wireframe, drawn AFTER text so lines remain continuous ----
    verts = _cube_vertices(p.cube_scale)
    pts2d, depths = _project(verts, p, scene_R)
    edges = _cube_edges()

    draw = ImageDraw.Draw(canvas)

    # Draw far edges first, near edges last.
    sortable = []
    for i, j in edges:
        avg_z = (depths[i] + depths[j]) * 0.5
        sortable.append((avg_z, i, j))
    sortable.sort(reverse=True)

    # The camera_distance is the nominal center depth.
    base_w = max(1.0, p.line_thickness * aa)
    for avg_z, i, j in sortable:
        depth_ratio = p.camera_distance / max(avg_z, 1e-4)
        width = base_w * (depth_ratio ** p.thinning_strength)
        width = max(1.0, width)

        a = tuple(map(float, pts2d[i]))
        b = tuple(map(float, pts2d[j]))
        draw.line([a, b], fill=(*p.wire_rgb, 255), width=max(1, int(round(width))))

    if aa > 1:
        canvas = canvas.resize((p.width, p.height), Image.Resampling.LANCZOS)

    return canvas.convert("RGB")


def image_to_png_bytes(img: Image.Image) -> bytes:
    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
