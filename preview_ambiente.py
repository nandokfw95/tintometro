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


def _wall_bounds(size: Tuple[int, int]) -> tuple[int, int]:
    w, h = size
    y_wall_end = int(h * 0.66)
    y_baseboard_top = int(h * 0.64)
    return y_wall_end, y_baseboard_top


def _draw_background(size: Tuple[int, int]) -> Image.Image:
    """
    Desenha apenas o fundo do ambiente:
    parede, rodapé, piso e sombras suaves.
    """
    w, h = size
    img = Image.new("RGB", size, (236, 234, 230))
    draw = ImageDraw.Draw(img)

    y_wall_end, y_baseboard_top = _wall_bounds(size)

    # parede base neutra
    draw.rectangle([0, 0, w, y_wall_end], fill=(226, 223, 218))

    # leve gradiente/sombra superior
    topo = Image.new("L", size, 0)
    dtop = ImageDraw.Draw(topo)
    dtop.rectangle([0, 0, w, int(h * 0.18)], fill=70)
    topo = topo.filter(ImageFilter.GaussianBlur(55))
    img = Image.composite(Image.new("RGB", size, (205, 205, 205)), img, topo.point(lambda p: int(p * 0.45)))

    # sombras suaves na parede para dar profundidade
    sombra_parede = Image.new("L", size, 0)
    sd = ImageDraw.Draw(sombra_parede)
    sd.ellipse([260, 365, 760, 610], fill=40)    # região atrás do sofá
    sd.ellipse([980, 330, 1165, 510], fill=34)   # atrás da planta
    sd.rectangle([0, y_wall_end - 24, w, y_wall_end], fill=28)  # sombra perto do rodapé
    sombra_parede = sombra_parede.filter(ImageFilter.GaussianBlur(42))
    img = Image.composite(Image.new("RGB", size, (185, 185, 185)), img, sombra_parede.point(lambda p: int(p * 0.33)))

    # rodapé
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, y_baseboard_top, w, y_wall_end], fill=(243, 241, 236))

    # piso
    draw.rectangle([0, y_wall_end, w, h], fill=(191, 173, 152))

    # textura/sombra suave do piso
    sombra_piso = Image.new("L", size, 0)
    sdp = ImageDraw.Draw(sombra_piso)
    sdp.rectangle([0, y_wall_end, w, h], fill=22)
    sdp.ellipse([120, y_wall_end + 40, 980, h + 60], fill=28)
    sdp.ellipse([960, y_wall_end + 50, 1180, h + 40], fill=18)
    sombra_piso = sombra_piso.filter(ImageFilter.GaussianBlur(35))
    img = Image.composite(Image.new("RGB", size, (135, 120, 104)), img, sombra_piso.point(lambda p: int(p * 0.28)))

    return img


def _foreground_layer(size: Tuple[int, int]) -> Image.Image:
    """
    Desenha tudo que deve ficar NA FRENTE da parede:
    quadro, luminária, sofá, almofadas, mesa e planta.
    """
    w, h = size
    fg = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(fg)

    # -------------------------
    # quadro
    # -------------------------
    draw.rectangle([844, 114, 1126, 292], fill=(241, 239, 234, 255), outline=(92, 89, 86, 255), width=5)
    draw.rectangle([865, 132, 1105, 274], fill=(216, 212, 206, 255))
    draw.rectangle([904, 156, 1068, 248], fill=(206, 202, 196, 255))

    # sombra do quadro
    shadow = Image.new("RGBA", size, (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.rectangle([858, 126, 1138, 304], fill=(0, 0, 0, 46))
    shadow = shadow.filter(ImageFilter.GaussianBlur(10))
    fg = Image.alpha_composite(shadow, fg)

    # -------------------------
    # luminária
    # -------------------------
    draw = ImageDraw.Draw(fg)
    draw.rectangle([156, 150, 170, 488], fill=(68, 66, 65, 255))
    draw.ellipse([106, 128, 226, 224], fill=(234, 223, 192, 255), outline=(151, 142, 116, 255), width=3)

    # brilho leve da cúpula
    glow = Image.new("RGBA", size, (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    gdraw.ellipse([116, 138, 216, 214], fill=(255, 248, 225, 36))
    glow = glow.filter(ImageFilter.GaussianBlur(10))
    fg = Image.alpha_composite(fg, glow)

    # -------------------------
    # sofá
    # -------------------------
    draw = ImageDraw.Draw(fg)

    # sombra do sofá no piso
    shadow = Image.new("RGBA", size, (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.ellipse([240, 530, 820, 700], fill=(0, 0, 0, 55))
    shadow = shadow.filter(ImageFilter.GaussianBlur(28))
    fg = Image.alpha_composite(fg, shadow)

    draw = ImageDraw.Draw(fg)
    draw.rounded_rectangle([260, 380, 742, 592], radius=28, fill=(214, 208, 201, 255), outline=(154, 147, 140, 255))
    draw.rounded_rectangle([218, 432, 304, 574], radius=22, fill=(206, 200, 193, 255), outline=(154, 147, 140, 255))
    draw.rounded_rectangle([698, 432, 784, 574], radius=22, fill=(206, 200, 193, 255), outline=(154, 147, 140, 255))

    # almofadas
    draw.rounded_rectangle([340, 428, 418, 508], radius=12, fill=(194, 189, 182, 255))
    draw.rounded_rectangle([454, 423, 536, 507], radius=12, fill=(182, 190, 198, 255))
    draw.rounded_rectangle([568, 428, 650, 508], radius=12, fill=(209, 196, 177, 255))

    # brilho leve no assento
    brilho_sofa = Image.new("RGBA", size, (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(brilho_sofa)
    bdraw.ellipse([320, 400, 700, 520], fill=(255, 255, 255, 18))
    brilho_sofa = brilho_sofa.filter(ImageFilter.GaussianBlur(18))
    fg = Image.alpha_composite(fg, brilho_sofa)

    # -------------------------
    # mesa de centro
    # -------------------------
    draw = ImageDraw.Draw(fg)
    draw.rounded_rectangle([448, 584, 682, 664], radius=14, fill=(110, 84, 61, 255))
    draw.rectangle([483, 658, 504, 718], fill=(74, 58, 45, 255))
    draw.rectangle([624, 658, 645, 718], fill=(74, 58, 45, 255))

    # -------------------------
    # planta / vaso
    # -------------------------
    # sombra da planta
    shadow = Image.new("RGBA", size, (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(shadow)
    sdraw.ellipse([978, 310, 1156, 458], fill=(0, 0, 0, 42))
    sdraw.ellipse([1005, 530, 1130, 660], fill=(0, 0, 0, 36))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    fg = Image.alpha_composite(fg, shadow)

    draw = ImageDraw.Draw(fg)
    draw.ellipse([1020, 470, 1112, 612], fill=(186, 182, 173, 255), outline=(126, 124, 120, 255))
    draw.rectangle([1054, 368, 1073, 488], fill=(110, 136, 96, 255))
    draw.ellipse([1018, 320, 1112, 404], fill=(125, 151, 106, 255))
    draw.ellipse([1000, 344, 1092, 428], fill=(112, 138, 98, 255))
    draw.ellipse([1042, 298, 1146, 394], fill=(128, 156, 111, 255))

    return fg


def _wall_mask(size: Tuple[int, int]) -> Image.Image:
    """
    Máscara da parede somente para o fundo.
    Aqui ela cobre apenas a área da parede.
    Os objetos da frente serão redesenhados depois.
    """
    w, h = size
    y_wall_end, _ = _wall_bounds(size)

    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rectangle([0, 0, w, y_wall_end], fill=255)

    # borda suave perto do rodapé
    mask = mask.filter(ImageFilter.GaussianBlur(1))
    return mask


def _wall_shading_from_background(bg: Image.Image, mask: Image.Image) -> Image.Image:
    """
    Extrai a luminosidade só do fundo da parede.
    Isso preserva sombras e sensação de volume.
    """
    gray = bg.convert("L")
    blur1 = gray.filter(ImageFilter.GaussianBlur(10))
    blur2 = gray.filter(ImageFilter.GaussianBlur(24))

    mixed = Image.blend(blur1, blur2, 0.45)
    shaded = ImageChops.multiply(mixed, mask)

    # um pequeno boost para não escurecer demais
    shaded = shaded.point(lambda p: max(92, min(255, int(p * 1.03))))
    return shaded


def _paint_wall(background: Image.Image, hex_color: str) -> Image.Image:
    """
    Pinta a parede preservando luz e sombra do fundo.
    """
    rgb = _hex_to_rgb(hex_color)
    mask = _wall_mask(background.size)
    shading = _wall_shading_from_background(background, mask)

    solid = Image.new("RGB", background.size, rgb)
    shading_rgb = shading.convert("RGB")

    painted_wall = ImageChops.multiply(solid, shading_rgb)

    # clareia um pouco para manter aparência de tinta interna
    brighten = Image.new("RGB", background.size, (236, 236, 236))
    painted_wall = Image.blend(
        painted_wall,
        ImageChops.screen(painted_wall, brighten),
        0.34,
    )

    # mistura de volta apenas na área da parede
    result = Image.composite(painted_wall, background, mask)
    return result


def _flatten_base_environment(size: Tuple[int, int]) -> Image.Image:
    """
    Gera uma imagem base completa do ambiente:
    fundo + objetos frontais.
    Serve para salvar a base, se necessário.
    """
    bg = _draw_background(size).convert("RGBA")
    fg = _foreground_layer(size)
    return Image.alpha_composite(bg, fg).convert("RGB")


def _ensure_base_environment(base_path: Path, size: Tuple[int, int] = (1280, 720)) -> Path:
    """
    Mantém compatibilidade com seu fluxo atual.
    Se a base não existir, cria uma base achatada.
    """
    base_path.parent.mkdir(parents=True, exist_ok=True)
    if base_path.exists():
        return base_path

    img = _flatten_base_environment(size)
    img.save(base_path)
    return base_path


def render_color_preview(
    hex_color: str,
    output_path: str | Path,
    base_image_path: str | Path | None = None,
    texture_path: str | Path | None = None,
) -> Path:
    """
    Gera o preview do ambiente com a parede atrás
    e sofá/planta/quadro/luminária na frente.
    """
    output_path = Path(output_path)

    if base_image_path is None:
        base_image_path = Path.cwd() / "preview_assets" / "ambiente_render.png"
    else:
        base_image_path = Path(base_image_path)

    # mantém compatibilidade com seu projeto:
    # garante que exista uma imagem base salva, mas a renderização
    # é feita por camadas para evitar sobreposição da parede no sofá.
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

def _paint_wall_with_texture(background: Image.Image, texture_path: str | Path) -> Image.Image:
    """
    Usa a imagem da cor como textura da parede,
    preservando iluminação do ambiente.
    """
    texture = Image.open(texture_path).convert("RGB")
    texture = texture.resize(background.size)

    mask = _wall_mask(background.size)
    shading = _wall_shading_from_background(background, mask).convert("RGB")

    # aplica iluminação do ambiente na textura
    textured_wall = ImageChops.multiply(texture, shading)

    # leve clareada (simula tinta real)
    brighten = Image.new("RGB", background.size, (236, 236, 236))
    textured_wall = Image.blend(
        textured_wall,
        ImageChops.screen(textured_wall, brighten),
        0.25,
    )

    # aplica só na parede
    result = Image.composite(textured_wall, background, mask)
    return result


if __name__ == "__main__":
    destino = Path.cwd() / "preview_ambiente" / "preview_parede.png"
    render_color_preview("#A8A29A", destino)
    print(f"Preview gerado em: {destino}")