import os
import re
from PIL import Image, ImageDraw
import pandas as pd

PASTA_PREVIEW = r"C:\Users\caset\Documents\Tintometro\preview_cores"
ARQUIVO_EXCEL = r"C:\Users\caset\Documents\Tintometro\planilhas_tintas\iquinecor.xlsx"

os.makedirs(PASTA_PREVIEW, exist_ok=True)

# Famílias base aproximadas
FAMILIAS = {
    "BB": "#2f4f7f",  # azul
    "BG": "#2f6f73",  # azul esverdeado
    "GG": "#4d7f4d",  # verde
    "GY": "#7a8f4d",  # verde amarelado / oliva
    "YY": "#d6b85a",  # amarelo
    "YR": "#d88a6a",  # pêssego / salmão / terracota clara
    "RR": "#b85c6b",  # vermelho / rosa queimado
    "RB": "#7a4f7a",  # vinho / roxo
    "NN": "#9a9a9a",  # neutro / cinza
}


def clamp(v):
    return max(0, min(255, int(v)))


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def misturar(hex1, hex2, proporcao=0.5):
    """
    Mistura duas cores hex.
    proporcao=0.0 => mantém hex1
    proporcao=1.0 => vira hex2
    """
    r1, g1, b1 = hex_to_rgb(hex1)
    r2, g2, b2 = hex_to_rgb(hex2)

    r = clamp(r1 * (1 - proporcao) + r2 * proporcao)
    g = clamp(g1 * (1 - proporcao) + g2 * proporcao)
    b = clamp(b1 * (1 - proporcao) + b2 * proporcao)

    return rgb_to_hex((r, g, b))


def ajustar_cor(base_hex, luminosidade=50, croma=200, nome_cor=""):
    """
    Gera uma cor aproximada baseada em:
    - família do código
    - luminosidade do código
    - croma do código
    - palavras do nome da cor
    """
    r, g, b = hex_to_rgb(base_hex)

    # brilho: quanto menor a luminosidade, mais escura a cor
    fator_luz = 0.45 + (luminosidade / 100.0) * 0.9
    r, g, b = r * fator_luz, g * fator_luz, b * fator_luz

    # saturação simples
    media = (r + g + b) / 3.0
    fator_sat = 0.55 + min(croma, 999) / 999.0
    r = media + (r - media) * fator_sat
    g = media + (g - media) * fator_sat
    b = media + (b - media) * fator_sat

    nome = (nome_cor or "").strip().lower()

    # =============================
    # Ajustes semânticos por nome
    # =============================
    if "rosa" in nome:
        r += 18
        g += 4
        b += 10

    if "fantasia" in nome:
        r += 8
        b += 6

    if "pink" in nome:
        r += 22
        b += 12

    if "vermelh" in nome:
        r += 18
        g -= 4
        b -= 4

    if "vinho" in nome or "bordô" in nome or "bordo" in nome:
        r += 8
        b += 6
        g -= 10

    if "roxo" in nome or "violeta" in nome or "lilás" in nome or "lilas" in nome:
        r += 8
        b += 18

    if "azul" in nome:
        b += 18
        r -= 4

    if "marinho" in nome:
        b += 10
        r -= 6
        g -= 4

    if "verde" in nome:
        g += 16

    if "oliva" in nome:
        r += 8
        g += 10
        b -= 8

    if "amarel" in nome or "ouro" in nome:
        r += 10
        g += 10

    if "laranja" in nome:
        r += 14
        g += 6

    if "salm" in nome or "pêssego" in nome or "pessego" in nome:
        r += 12
        g += 6

    if "terracota" in nome:
        r += 14
        g += 3
        b -= 8

    if "areia" in nome or "bege" in nome:
        r += 12
        g += 10
        b += 4

    if "creme" in nome or "baunilha" in nome:
        r += 18
        g += 16
        b += 8

    if "marfim" in nome:
        r += 22
        g += 20
        b += 10

    if "branco" in nome or "neve" in nome or "gelo" in nome:
        r += 35
        g += 35
        b += 35

    if "palha" in nome:
        r += 16
        g += 14
        b += 8

    if "cinza" in nome:
        media = (r + g + b) / 3.0
        r = media + (r - media) * 0.25
        g = media + (g - media) * 0.25
        b = media + (b - media) * 0.25

    if "grafite" in nome or "chumbo" in nome:
        r *= 0.72
        g *= 0.72
        b *= 0.72

    if "preto" in nome or "ébano" in nome or "ebano" in nome:
        r *= 0.50
        g *= 0.50
        b *= 0.50

    if "escurid" in nome or "noite" in nome:
        r *= 0.65
        g *= 0.65
        b *= 0.65

    if "claro" in nome or "suave" in nome:
        r += 14
        g += 14
        b += 14

    # clamp final
    return rgb_to_hex((clamp(r), clamp(g), clamp(b)))


def cor_aproximada(cod_cor, nome_cor=""):
    """
    Exemplo de cod_cor: 00YR 26/490
    """
    try:
        cod = str(cod_cor).strip().upper()
        m = re.match(r"^\d{2}([A-Z]{2})\s+(\d{2})/(\d{3})$", cod)

        if not m:
            return "#b0b0b0"

        familia = m.group(1)
        luminosidade = int(m.group(2))
        croma = int(m.group(3))

        base = FAMILIAS.get(familia, "#9a9a9a")
        cor = ajustar_cor(
            base_hex=base,
            luminosidade=luminosidade,
            croma=croma,
            nome_cor=nome_cor
        )

        return cor

    except Exception:
        return "#b0b0b0"


def criar_textura_parede(draw, largura, altura, hex_cor):
    """
    Cria uma textura muito suave, quase imperceptível.
    """
    r, g, b = hex_to_rgb(hex_cor)

    for y in range(0, altura - 42, 8):
        ajuste = 6 if (y // 8) % 2 == 0 else -4
        cor_linha = (
            clamp(r + ajuste),
            clamp(g + ajuste),
            clamp(b + ajuste)
        )
        draw.line((0, y, largura, y), fill=cor_linha, width=1)


def gerar_parede(hex_cor, caminho):
    largura = 420
    altura = 260

    img = Image.new("RGB", (largura, altura), hex_cor)
    draw = ImageDraw.Draw(img)

    # textura leve
    criar_textura_parede(draw, largura, altura, hex_cor)

    # sombra suave no topo
    topo = misturar(hex_cor, "#ffffff", 0.10)
    draw.rectangle([0, 0, largura, 20], fill=topo)

    # volta o campo principal da parede logo abaixo
    draw.rectangle([0, 20, largura, altura - 42], fill=hex_cor)
    criar_textura_parede(draw, largura, altura, hex_cor)

    # rodapé
    draw.rectangle([0, altura - 42, largura, altura - 20], fill="#efefef")

    # sombra entre parede e rodapé
    draw.line((0, altura - 43, largura, altura - 43), fill="#d8d8d8", width=1)

    # piso
    draw.rectangle([0, altura - 20, largura, altura], fill="#cdbba5")

    img.save(caminho)


def nome_arquivo_preview(cod_cor):
    return str(cod_cor).strip().replace(" ", "_").replace("/", "_") + ".png"


def gerar_todas():
    df = pd.read_excel(ARQUIVO_EXCEL)

    if "COD_COR" not in df.columns or "NOME_COR" not in df.columns:
        raise ValueError("A planilha precisa ter as colunas COD_COR e NOME_COR.")

    total = len(df)

    for i, (_, row) in enumerate(df.iterrows(), start=1):
        cod = str(row["COD_COR"]).strip()
        nome = str(row["NOME_COR"]).strip()

        if not cod:
            continue

        cor = cor_aproximada(cod, nome)
        arquivo = nome_arquivo_preview(cod)
        caminho = os.path.join(PASTA_PREVIEW, arquivo)

        # sobrescreve sempre para corrigir previews antigos
        gerar_parede(cor, caminho)

        print(f"[{i}/{total}] gerado: {cod} | {nome} | {cor}")


if __name__ == "__main__":
    gerar_todas()
    print("\nConcluído.")