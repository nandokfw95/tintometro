from __future__ import annotations

from pathlib import Path
from typing import Tuple

from PIL import Image, ImageChops, ImageFilter


# =========================================================
# CONFIGURAÇÃO DE ASSETS
# =========================================================
BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets" / "ambiente"

ASSET_BASE = ASSETS_DIR / "base.png"
ASSET_SOFA = ASSETS_DIR / "sofa.png"
ASSET_MESA = ASSETS_DIR / "mesa.png"
ASSET_PLANTA = ASSETS_DIR / "planta.png"
ASSET_QUADRO = ASSETS_DIR / "quadro.png"
ASSET_LUMINARIA = ASSETS_DIR / "luminaria.png"

# =========================================================
# HELPERS GERAIS
# =========================================================
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


def _safe_open_rgba(path: str | Path) -> Image.Image | None:
    p = Path(path)
    if not p.exists():
        return None
    try:
        return Image.open(p).convert("RGBA")
    except Exception:
        return None


def _resize_asset(img: Image.Image | None, scale: float) -> Image.Image | None:
    if img is None:
        return None
    w, h = img.size
    nw = max(1, int(w * scale))
    nh = max(1, int(h * scale))
    return img.resize((nw, nh), Image.LANCZOS)


def _alpha_bbox(img: Image.Image) -> tuple[int, int, int, int] | None:
    alpha = img.getchannel("A")
    return alpha.getbbox()


def _crop_to_alpha(img: Image.Image | None, padding: int = 0) -> Image.Image | None:
    if img is None:
        return None

    bbox = _alpha_bbox(img)
    if not bbox:
        return img

    x1, y1, x2, y2 = bbox
    x1 = max(0, x1 - padding)
    y1 = max(0, y1 - padding)
    x2 = min(img.width, x2 + padding)
    y2 = min(img.height, y2 + padding)
    return img.crop((x1, y1, x2, y2))


def _make_shadow_from_alpha(
    img: Image.Image,
    blur: int = 18,
    opacity: int = 90,
    expand: int = 60,
) -> Image.Image:
    """
    Cria uma sombra usando o alpha do PNG.
    """
    alpha = img.getchannel("A")

    shadow_alpha = Image.new(
        "L",
        (img.width + expand * 2, img.height + expand * 2),
        0,
    )
    shadow_alpha.paste(alpha, (expand, expand))
    shadow_alpha = shadow_alpha.filter(ImageFilter.GaussianBlur(blur))
    shadow_alpha = shadow_alpha.point(lambda p: int(p * (opacity / 255.0)))

    shadow = Image.new("RGBA", shadow_alpha.size, (0, 0, 0, 0))
    shadow.putalpha(shadow_alpha)
    return shadow


def _paste_centered(
    canvas: Image.Image,
    obj: Image.Image,
    center_x: int,
    baseline_y: int,
) -> tuple[int, int]:
    """
    Cola o objeto centralizado horizontalmente, usando a base inferior como referência.
    """
    x = int(center_x - obj.width / 2)
    y = int(baseline_y - obj.height)
    canvas.alpha_composite(obj, (x, y))
    return x, y


def _paste_with_shadow(
    canvas: Image.Image,
    obj: Image.Image | None,
    center_x: int,
    baseline_y: int,
    shadow_blur: int = 18,
    shadow_opacity: int = 90,
    shadow_dx: int = 10,
    shadow_dy: int = 12,
    shadow_expand: int = 60,
) -> tuple[int | None, int | None]:
    if obj is None:
        return None, None

    shadow = _make_shadow_from_alpha(
        obj,
        blur=shadow_blur,
        opacity=shadow_opacity,
        expand=shadow_expand,
    )

    obj_x = int(center_x - obj.width / 2)
    obj_y = int(baseline_y - obj.height)

    shadow_x = obj_x - shadow_expand + shadow_dx
    shadow_y = obj_y - shadow_expand + shadow_dy

    canvas.alpha_composite(shadow, (shadow_x, shadow_y))
    canvas.alpha_composite(obj, (obj_x, obj_y))

    return obj_x, obj_y

def _resize_to_width(img: Image.Image | None, target_w: int) -> Image.Image | None:
    if img is None or target_w <= 0:
        return img
    w, h = img.size
    scale = target_w / max(1, w)
    return img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)


def _resize_to_height(img: Image.Image | None, target_h: int) -> Image.Image | None:
    if img is None or target_h <= 0:
        return img
    w, h = img.size
    scale = target_h / max(1, h)
    return img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)


# =========================================================
# BASE / FUNDO
# =========================================================
def _wall_bounds(size: Tuple[int, int]) -> tuple[int, int]:
    """
    Mantém a lógica da parede para pintar a cor no mesmo layout do preview.
    """
    _, h = size
    y_wall_end = int(h * 0.66)
    y_baseboard_top = int(h * 0.64)
    return y_wall_end, y_baseboard_top


def _draw_background(size: Tuple[int, int]) -> Image.Image:
    """
    Usa a base PNG se existir.
    Se não existir, cria um fundo neutro simples como fallback.
    """
    base = _safe_open_rgba(ASSET_BASE)
    if base is not None:
        return base.resize(size, Image.LANCZOS).convert("RGB")

    w, h = size
    y_wall_end, y_baseboard_top = _wall_bounds(size)

    img = Image.new("RGB", size, (242, 241, 238))

    # parede
    for y in range(y_wall_end):
        t = y / max(1, y_wall_end - 1)
        c = _clamp(244 - t * 10)
        for x in range(w):
            img.putpixel((x, y), (c, c, c))

    # rodapé
    for y in range(y_baseboard_top, y_wall_end):
        for x in range(w):
            img.putpixel((x, y), (236, 236, 236))

    # piso
    for y in range(y_wall_end, h):
        t = (y - y_wall_end) / max(1, h - y_wall_end)
        r = _clamp(226 - t * 18)
        g = _clamp(218 - t * 20)
        b = _clamp(206 - t * 22)
        for x in range(w):
            img.putpixel((x, y), (r, g, b))

    return img


# =========================================================
# MÁSCARA E PINTURA DA PAREDE
# =========================================================
def _wall_mask(size: Tuple[int, int]) -> Image.Image:
    """
    Máscara da área pintável da parede.
    """
    w, h = size
    y_wall_end, _ = _wall_bounds(size)

    mask = Image.new("L", size, 0)
    for y in range(y_wall_end):
        for x in range(w):
            mask.putpixel((x, y), 255)

    mask = mask.filter(ImageFilter.GaussianBlur(1))
    return mask


def _wall_shading_from_background(bg: Image.Image, mask: Image.Image) -> Image.Image:
    """
    Extrai luz/sombra do fundo para preservar realismo ao pintar a parede.
    """
    gray = bg.convert("L")
    blur1 = gray.filter(ImageFilter.GaussianBlur(10))
    blur2 = gray.filter(ImageFilter.GaussianBlur(24))
    mixed = Image.blend(blur1, blur2, 0.45)
    shaded = ImageChops.multiply(mixed, mask)
    shaded = shaded.point(lambda p: max(92, min(255, int(p * 1.03))))
    return shaded


def _paint_wall(background: Image.Image, hex_color: str) -> Image.Image:
    rgb = _hex_to_rgb(hex_color)
    mask = _wall_mask(background.size)
    shading = _wall_shading_from_background(background, mask)

    solid = Image.new("RGB", background.size, rgb)
    painted_wall = ImageChops.multiply(solid, shading.convert("RGB"))

    brighten = Image.new("RGB", background.size, (236, 236, 236))
    painted_wall = Image.blend(
        painted_wall,
        ImageChops.screen(painted_wall, brighten),
        0.34,
    )

    return Image.composite(painted_wall, background, mask)


def _paint_wall_with_texture(background: Image.Image, texture_path: str | Path) -> Image.Image:
    texture = Image.open(texture_path).convert("RGB")
    tw, th = texture.size

    x1 = int(tw * 0.18)
    x2 = int(tw * 0.82)
    y1 = int(th * 0.12)
    y2 = int(th * 0.78)
    texture = texture.crop((x1, y1, x2, y2))

    texture = texture.filter(ImageFilter.GaussianBlur(1))
    texture = texture.resize(background.size, Image.LANCZOS)

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


# =========================================================
# OBJETOS FRONTAIS
# =========================================================
def _foreground_layer(size: Tuple[int, int]) -> Image.Image:
    w, h = size
    fg = Image.new("RGBA", size, (0, 0, 0, 0))

    # carrega assets brutos
    sofa_raw = _crop_to_alpha(_safe_open_rgba(ASSET_SOFA), padding=4)
    mesa_raw = _crop_to_alpha(_safe_open_rgba(ASSET_MESA), padding=3)
    planta_raw = _crop_to_alpha(_safe_open_rgba(ASSET_PLANTA), padding=3)
    quadro_raw = _crop_to_alpha(_safe_open_rgba(ASSET_QUADRO), padding=2)
    luminaria_raw = _crop_to_alpha(_safe_open_rgba(ASSET_LUMINARIA), padding=3)

    # =========================
    # ESCALA ARQUITETÔNICA
    # =========================
    # referência visual da cena:
    # sofá real = 2,10 m
    sofa_target_w = 650
    px_por_metro = sofa_target_w / 2.10

    mesa_target_w = int(0.90 * px_por_metro)       # 0,90 m
    planta_target_h = int(1.20 * px_por_metro)     # 1,20 m
    luminaria_target_h = int(1.55 * px_por_metro)  # 1,55 m
    quadro_target_w = int(1.20 * px_por_metro)     # 0,55 m

    sofa = _resize_to_width(sofa_raw, sofa_target_w)
    mesa = _resize_to_width(mesa_raw, mesa_target_w)
    planta = _resize_to_height(planta_raw, planta_target_h)
    luminaria = _resize_to_height(luminaria_raw, luminaria_target_h)
    quadro = _resize_to_width(quadro_raw, quadro_target_w)

    y_wall_end, _ = _wall_bounds(size)

    # =========================
    # BASELINES
    # =========================
    sofa_baseline = int(h * 0.79)
    mesa_baseline = int(h * 0.84)
    planta_baseline = int(h * 0.80)
    luminaria_baseline = int(h * 0.80)

    # =========================
    # SOFÁ
    # =========================
    sofa_x = (w - sofa.width) // 2
    sofa_y = sofa_baseline - sofa.height

    shadow = _make_shadow_from_alpha(sofa, blur=22, opacity=70, expand=26)
    shadow_x = sofa_x - (shadow.width - sofa.width) // 2
    shadow_y = sofa_baseline - sofa.height // 6
    fg.alpha_composite(shadow, (shadow_x, shadow_y))
    fg.alpha_composite(sofa, (sofa_x, sofa_y))

    # =========================
    # QUADRO
    # =========================
    if quadro is not None:
        shadow = _make_shadow_from_alpha(quadro, blur=8, opacity=55, expand=18)

        # centro do sofá
        qx = sofa_x + sofa.width // 2

        # AJUSTE DE ALTURA
        espacamento = int(-0.5 * px_por_metro)   # ~10 cm
        qy = sofa_y - quadro.height - espacamento

        shadow_x = qx - shadow.width // 2 + 4
        shadow_y = qy + 4
        fg.alpha_composite(shadow, (shadow_x, shadow_y))

        obj_x = qx - quadro.width // 2
        obj_y = qy
        fg.alpha_composite(quadro, (obj_x, obj_y))

    # =========================
    # LUMINÁRIA
    # =========================
    _paste_with_shadow(
        fg,
        luminaria,
        center_x=int(w * 0.12),
        baseline_y=luminaria_baseline,
        shadow_blur=10,
        shadow_opacity=55,
        shadow_dx=4,
        shadow_dy=6,
        shadow_expand=20,
    )


    # =========================
    # MESA
    # =========================
    _paste_with_shadow(
        fg,
        mesa,
        center_x=int(w * 0.56),
        baseline_y=mesa_baseline,
        shadow_blur=10,
        shadow_opacity=55,
        shadow_dx=4,
        shadow_dy=6,
        shadow_expand=20,
    )

    # =========================
    # PLANTA
    # =========================
    _paste_with_shadow(
        fg,
        planta,
        center_x=int(w * 0.89),
        baseline_y=planta_baseline,
        shadow_blur=12,
        shadow_opacity=60,
        shadow_dx=5,
        shadow_dy=6,
        shadow_expand=22,
    )

    # =========================
    # SOMBRA SUAVE ATRÁS DO SOFÁ
    # =========================
    wall_shadow = Image.new("RGBA", size, (0, 0, 0, 0))
    mask = Image.new("L", size, 0)

    if sofa is not None:
        from PIL import ImageDraw
        d = ImageDraw.Draw(mask)
        d.ellipse(
            [
                int(w * 0.28),
                int(y_wall_end * 0.78),
                int(w * 0.74),
                int(y_wall_end * 1.03),
            ],
            fill=24,
        )
        mask = mask.filter(ImageFilter.GaussianBlur(26))
        wall_shadow.putalpha(mask)
        fg = Image.alpha_composite(wall_shadow, fg)

    return fg

# =========================================================
# BASE COMPLETA / COMPATIBILIDADE
# =========================================================
def _flatten_base_environment(size: Tuple[int, int]) -> Image.Image:
    bg = _draw_background(size).convert("RGBA")
    fg = _foreground_layer(size)
    return Image.alpha_composite(bg, fg).convert("RGB")


def _ensure_base_environment(base_path: Path, size: Tuple[int, int] = (1280, 720)) -> Path:
    """
    Mantém compatibilidade com seu fluxo atual.
    """
    base_path.parent.mkdir(parents=True, exist_ok=True)
    if base_path.exists():
        return base_path

    img = _flatten_base_environment(size)
    img.save(base_path)
    return base_path


# =========================================================
# RENDER FINAL
# =========================================================
def render_color_preview(
    hex_color: str,
    output_path: str | Path,
    base_image_path: str | Path | None = None,
    texture_path: str | Path | None = None,
) -> Path:
    """
    Mantém a mesma assinatura usada hoje no mixins_pedido.
    """
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
    render_color_preview("#CFA6A6", destino)
    print(f"Preview gerado em: {destino}")