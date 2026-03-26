from __future__ import annotations

from pathlib import Path
from typing import Tuple

from PIL import Image, ImageChops, ImageDraw, ImageFilter


def _hex_to_rgb(color: str) -> Tuple[int, int, int]:
    color = str(color or "").strip().lstrip("#")
    if len(color) != 6:
        return (180, 180, 180)
    try:
        return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        return (180, 180, 180)


def _clamp(v: float) -> int:
    return max(0, min(255, int(v)))


def _blend_rgb(a: Tuple[int, int, int], b: Tuple[int, int, int], t: float) -> Tuple[int, int, int]:
    return tuple(_clamp(a[i] * (1 - t) + b[i] * t) for i in range(3))


def _wall_bounds(size: Tuple[int, int]) -> tuple[int, int]:
    _, h = size
    y_wall_end = int(h * 0.64)
    y_baseboard_top = int(h * 0.618)
    return y_wall_end, y_baseboard_top


def _make_soft_light_mask(size: Tuple[int, int], box, blur=80, strength=255) -> Image.Image:
    m = Image.new("L", size, 0)
    d = ImageDraw.Draw(m)
    d.ellipse(box, fill=strength)
    return m.filter(ImageFilter.GaussianBlur(blur))


def _draw_background(size: Tuple[int, int]) -> Image.Image:
    w, h = size
    img = Image.new("RGB", size, (228, 224, 218))
    draw = ImageDraw.Draw(img)

    y_wall_end, y_baseboard_top = _wall_bounds(size)

    # ---------------------------------------------------------
    # PAREDE BASE
    # ---------------------------------------------------------
    wall_top = (226, 223, 218)
    wall_bottom = (214, 210, 204)

    for y in range(y_wall_end):
        t = y / max(1, y_wall_end - 1)
        cor = _blend_rgb(wall_top, wall_bottom, t)
        draw.line([0, y, w, y], fill=cor)

    # luz vindo da esquerda
    luz_esquerda = _make_soft_light_mask(size, (-260, 20, 620, 700), blur=120, strength=175)
    img = Image.composite(
        Image.new("RGB", size, (247, 245, 241)),
        img,
        luz_esquerda.point(lambda p: int(p * 0.30)),
    )

    # leve sombra superior
    sombra_topo = Image.new("L", size, 0)
    st = ImageDraw.Draw(sombra_topo)
    st.rectangle([0, 0, w, int(h * 0.16)], fill=95)
    sombra_topo = sombra_topo.filter(ImageFilter.GaussianBlur(85))
    img = Image.composite(
        Image.new("RGB", size, (188, 188, 188)),
        img,
        sombra_topo.point(lambda p: int(p * 0.20)),
    )

    # sombra atrás do sofá
    sombra_sofa = _make_soft_light_mask(size, (250, 290, 900, 620), blur=80, strength=95)
    img = Image.composite(
        Image.new("RGB", size, (178, 176, 173)),
        img,
        sombra_sofa.point(lambda p: int(p * 0.18)),
    )

    # sombra canto direito
    sombra_direita = _make_soft_light_mask(size, (930, 180, 1330, 620), blur=90, strength=70)
    img = Image.composite(
        Image.new("RGB", size, (182, 180, 178)),
        img,
        sombra_direita.point(lambda p: int(p * 0.14)),
    )

    # ---------------------------------------------------------
    # RODAPÉ
    # ---------------------------------------------------------
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, y_baseboard_top, w, y_wall_end], fill=(240, 238, 234))
    draw.line([0, y_baseboard_top, w, y_baseboard_top], fill=(208, 204, 198), width=2)

    # ---------------------------------------------------------
    # PISO
    # ---------------------------------------------------------
    floor_top = (198, 180, 160)
    floor_bottom = (179, 160, 140)

    for y in range(y_wall_end, h):
        t = (y - y_wall_end) / max(1, h - y_wall_end)
        cor = _blend_rgb(floor_top, floor_bottom, t)
        draw.line([0, y, w, y], fill=cor)

    # paginação sutil do piso
    for yy in range(y_wall_end + 32, h, 48):
        draw.line([0, yy, w, yy], fill=(168, 151, 132), width=1)

    # brilho suave no piso
    brilho = _make_soft_light_mask(size, (80, y_wall_end + 10, 1040, h + 80), blur=90, strength=90)
    img = Image.composite(
        Image.new("RGB", size, (214, 200, 184)),
        img,
        brilho.point(lambda p: int(p * 0.12)),
    )

    # sombra geral no piso
    sombra_piso = Image.new("L", size, 0)
    sp = ImageDraw.Draw(sombra_piso)
    sp.rectangle([0, y_wall_end, w, h], fill=30)
    sp.ellipse([150, y_wall_end + 30, 980, h + 90], fill=46)
    sp.ellipse([960, y_wall_end + 45, 1200, h + 40], fill=28)
    sombra_piso = sombra_piso.filter(ImageFilter.GaussianBlur(50))
    img = Image.composite(
        Image.new("RGB", size, (126, 111, 96)),
        img,
        sombra_piso.point(lambda p: int(p * 0.20)),
    )

    return img


def _foreground_layer(size: Tuple[int, int]) -> Image.Image:
    w, h = size
    fg = Image.new("RGBA", size, (0, 0, 0, 0))

    def blur_layer(draw_fn, blur=16):
        lay = Image.new("RGBA", size, (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        draw_fn(d)
        return lay.filter(ImageFilter.GaussianBlur(blur))

    # =========================================================
    # QUADRO
    # =========================================================
    fg = Image.alpha_composite(
        fg,
        blur_layer(
            lambda d: d.rounded_rectangle([900, 118, 1170, 300], radius=8, fill=(0, 0, 0, 48)),
            blur=14,
        ),
    )

    draw = ImageDraw.Draw(fg)
    draw.rounded_rectangle([886, 104, 1150, 284], radius=5, fill=(242, 240, 235, 255), outline=(120, 114, 108, 255), width=3)
    draw.rectangle([906, 122, 1130, 264], fill=(218, 214, 208, 255))
    draw.rectangle([950, 148, 1088, 236], fill=(203, 198, 191, 255))
    draw.line([964, 164, 1074, 164], fill=(188, 183, 177, 255), width=2)
    draw.line([964, 222, 1074, 222], fill=(188, 183, 177, 255), width=2)

    brilho_quadro = Image.new("RGBA", size, (0, 0, 0, 0))
    bq = ImageDraw.Draw(brilho_quadro)
    bq.polygon([(900, 118), (1010, 118), (955, 282), (900, 282)], fill=(255, 255, 255, 22))
    brilho_quadro = brilho_quadro.filter(ImageFilter.GaussianBlur(12))
    fg = Image.alpha_composite(fg, brilho_quadro)

    # =========================================================
    # LUMINÁRIA
    # =========================================================
    draw = ImageDraw.Draw(fg)
    draw.rectangle([136, 176, 148, 500], fill=(68, 65, 64, 255))
    draw.ellipse([88, 140, 206, 234], fill=(229, 219, 190, 255), outline=(151, 141, 118, 255), width=3)

    glow = Image.new("RGBA", size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([72, 124, 226, 252], fill=(255, 244, 215, 16))
    gd.ellipse([96, 148, 198, 226], fill=(255, 244, 220, 28))
    glow = glow.filter(ImageFilter.GaussianBlur(18))
    fg = Image.alpha_composite(fg, glow)

    # =========================================================
    # TAPETE
    # =========================================================
    fg = Image.alpha_composite(
        fg,
        blur_layer(
            lambda d: d.rounded_rectangle([290, 522, 816, 690], radius=86, fill=(0, 0, 0, 34)),
            blur=32,
        ),
    )

    draw = ImageDraw.Draw(fg)
    draw.rounded_rectangle([316, 532, 790, 664], radius=58, fill=(210, 203, 193, 132))

    # =========================================================
    # SOFÁ - SOMBRAS
    # =========================================================
    fg = Image.alpha_composite(
        fg,
        blur_layer(
            lambda d: d.ellipse([238, 538, 852, 716], fill=(0, 0, 0, 62)),
            blur=28,
        ),
    )

    # =========================================================
    # SOFÁ - CORPO
    # =========================================================
    draw = ImageDraw.Draw(fg)
    draw.rounded_rectangle([260, 384, 780, 592], radius=34, fill=(214, 208, 202, 255), outline=(150, 145, 138, 255), width=2)
    draw.rounded_rectangle([222, 438, 306, 580], radius=22, fill=(205, 199, 192, 255), outline=(150, 145, 138, 255), width=2)
    draw.rounded_rectangle([734, 438, 818, 580], radius=22, fill=(205, 199, 192, 255), outline=(150, 145, 138, 255), width=2)

    draw.rounded_rectangle([304, 426, 736, 534], radius=22, fill=(221, 216, 210, 255))
    draw.rounded_rectangle([304, 402, 736, 468], radius=20, fill=(227, 223, 217, 255))

    draw.line([408, 428, 408, 538], fill=(176, 169, 162, 255), width=2)
    draw.line([546, 426, 546, 538], fill=(176, 169, 162, 255), width=2)
    draw.line([680, 428, 680, 538], fill=(176, 169, 162, 255), width=2)

    # brilho principal do sofá
    brilho_sofa = Image.new("RGBA", size, (0, 0, 0, 0))
    bs = ImageDraw.Draw(brilho_sofa)
    bs.ellipse([320, 392, 740, 510], fill=(255, 255, 255, 26))
    brilho_sofa = brilho_sofa.filter(ImageFilter.GaussianBlur(20))
    fg = Image.alpha_composite(fg, brilho_sofa)

    # sombra interna
    sombra_assento = Image.new("RGBA", size, (0, 0, 0, 0))
    sa = ImageDraw.Draw(sombra_assento)
    sa.ellipse([318, 468, 724, 566], fill=(0, 0, 0, 22))
    sombra_assento = sombra_assento.filter(ImageFilter.GaussianBlur(18))
    fg = Image.alpha_composite(fg, sombra_assento)

    # almofadas
    draw = ImageDraw.Draw(fg)
    draw.rounded_rectangle([350, 432, 426, 510], radius=12, fill=(198, 191, 184, 255))
    draw.rounded_rectangle([482, 428, 560, 512], radius=12, fill=(183, 190, 198, 255))
    draw.rounded_rectangle([612, 434, 690, 510], radius=12, fill=(212, 199, 179, 255))

    # =========================================================
    # MESA
    # =========================================================
    fg = Image.alpha_composite(
        fg,
        blur_layer(
            lambda d: d.ellipse([456, 618, 712, 704], fill=(0, 0, 0, 38)),
            blur=18,
        ),
    )

    draw = ImageDraw.Draw(fg)
    draw.rounded_rectangle([470, 590, 692, 668], radius=14, fill=(112, 84, 61, 255))
    draw.rectangle([508, 662, 524, 722], fill=(78, 58, 45, 255))
    draw.rectangle([638, 662, 654, 722], fill=(78, 58, 45, 255))

    brilho_mesa = Image.new("RGBA", size, (0, 0, 0, 0))
    bm = ImageDraw.Draw(brilho_mesa)
    bm.rectangle([488, 598, 666, 614], fill=(255, 255, 255, 14))
    brilho_mesa = brilho_mesa.filter(ImageFilter.GaussianBlur(10))
    fg = Image.alpha_composite(fg, brilho_mesa)

    # =========================================================
    # PLANTA / VASO
    # =========================================================
    fg = Image.alpha_composite(
        fg,
        blur_layer(
            lambda d: (
                d.ellipse([1022, 330, 1178, 470], fill=(0, 0, 0, 28)),
                d.ellipse([1038, 538, 1150, 662], fill=(0, 0, 0, 30))
            ),
            blur=18,
        ),
    )

    draw = ImageDraw.Draw(fg)
    draw.ellipse([1060, 486, 1142, 624], fill=(194, 190, 181, 255), outline=(129, 126, 121, 255))
    draw.ellipse([1074, 498, 1128, 610], fill=(212, 208, 198, 80))
    draw.rectangle([1094, 380, 1108, 500], fill=(108, 134, 95, 255))

    draw.ellipse([1032, 336, 1128, 416], fill=(118, 146, 101, 255))
    draw.ellipse([1012, 356, 1104, 438], fill=(104, 131, 91, 255))
    draw.ellipse([1062, 312, 1168, 404], fill=(130, 158, 111, 255))
    draw.ellipse([1088, 340, 1176, 430], fill=(141, 169, 121, 255))

    return fg


def _wall_mask(size: Tuple[int, int]) -> Image.Image:
    w, h = size
    y_wall_end, _ = _wall_bounds(size)

    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rectangle([0, 0, w, y_wall_end], fill=255)
    return mask.filter(ImageFilter.GaussianBlur(1))


def _wall_shading_from_background(bg: Image.Image, mask: Image.Image) -> Image.Image:
    gray = bg.convert("L")
    soft1 = gray.filter(ImageFilter.GaussianBlur(10))
    soft2 = gray.filter(ImageFilter.GaussianBlur(24))
    mixed = Image.blend(soft1, soft2, 0.50)
    shaded = ImageChops.multiply(mixed, mask)
    return shaded.point(lambda p: max(94, min(255, int(p * 1.02))))


def _paint_wall(background: Image.Image, hex_color: str) -> Image.Image:
    rgb = _hex_to_rgb(hex_color)
    mask = _wall_mask(background.size)
    shading = _wall_shading_from_background(background, mask)

    solid = Image.new("RGB", background.size, rgb)
    painted = ImageChops.multiply(solid, shading.convert("RGB"))

    soften = Image.new("RGB", background.size, (238, 238, 238))
    painted = Image.blend(
        painted,
        ImageChops.screen(painted, soften),
        0.30,
    )

    return Image.composite(painted, background, mask)


def _flatten_base_environment(size: Tuple[int, int]) -> Image.Image:
    bg = _draw_background(size).convert("RGBA")
    fg = _foreground_layer(size)
    return Image.alpha_composite(bg, fg).convert("RGB")


def _ensure_base_environment(base_path: Path, size: Tuple[int, int] = (1280, 720)) -> Path:
    base_path.parent.mkdir(parents=True, exist_ok=True)
    if base_path.exists():
        return base_path

    img = _flatten_base_environment(size)
    img.save(base_path)
    return base_path


def _paint_wall_with_texture(background: Image.Image, texture_path: str | Path) -> Image.Image:
    texture = Image.open(texture_path).convert("RGB")
    tw, th = texture.size

    x1 = int(tw * 0.18)
    x2 = int(tw * 0.82)
    y1 = int(th * 0.12)
    y2 = int(th * 0.78)
    texture = texture.crop((x1, y1, x2, y2))

    texture = texture.filter(ImageFilter.GaussianBlur(1))
    texture = texture.resize(background.size)

    mask = _wall_mask(background.size)
    shading = _wall_shading_from_background(background, mask).convert("RGB")

    shading_soft = Image.blend(
        Image.new("RGB", background.size, (245, 245, 245)),
        shading,
        0.18,
    )

    textured_wall = ImageChops.multiply(texture, shading_soft)
    textured_wall = Image.blend(texture, textured_wall, 0.25)

    return Image.composite(textured_wall, background, mask)


def render_color_preview(
    hex_color: str,
    output_path: str | Path,
    base_image_path: str | Path | None = None,
    texture_path: str | Path | None = None,
) -> Path:
    output_path = Path(output_path)

    if base_image_path is None:
        base_image_path = Path.cwd() / "preview_assets" / "ambiente_render.png"
    else:
        base_image_path = Path(base_image_path)

    _ensure_base_environment(base_image_path)

    size = (1280, 720)

    background = _draw_background(size)
    if texture_path and Path(texture_path).exists():
        painted = _paint_wall_with_texture(background, texture_path).convert("RGBA")
    else:
        painted = _paint_wall(background, hex_color).convert("RGBA")

    foreground = _foreground_layer(size)
    result = Image.alpha_composite(painted, foreground).convert("RGB")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(output_path)
    return output_path


if __name__ == "__main__":
    destino = Path.cwd() / "preview_ambiente" / "preview_parede.png"
    render_color_preview("#B2877E", destino)
    print(f"Preview gerado em: {destino}")