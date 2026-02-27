# txt_builder.py
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import pandas as pd

SCALE_QTD   = 10**8
SCALE_UNIT  = 10**7
SCALE_TOTAL = 10**5
SCALE_CUSTO = 100
ITEM_LEN = 254


def zfill_num(value, width: int) -> str:
    return str(value).zfill(width)


def fix_text(value: str, width: int) -> str:
    s = "" if value is None else str(value)
    return s[:width].ljust(width, " ")


def to_decimal(x) -> Decimal:
    if x is None or (isinstance(x, float) and pd.isna(x)) or (isinstance(x, str) and x.strip() == ""):
        return Decimal("0")
    if isinstance(x, (int, float, Decimal)):
        return Decimal(str(x))
    s = str(x).strip()
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    return Decimal(s)


def scaled_int(value, scale: int) -> int:
    d = to_decimal(value)
    return int((d * Decimal(scale)).to_integral_value(rounding=ROUND_HALF_UP))


def format_date_ddmmyyyy(x) -> str:
    if isinstance(x, datetime):
        return x.strftime("%d/%m/%Y")
    if hasattr(x, "strftime"):
        return x.strftime("%d/%m/%Y")

    s = str(x).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%d/%m/%Y")
        except ValueError:
            pass

    dt = pd.to_datetime(s, dayfirst=True)
    return dt.strftime("%d/%m/%Y")


def build_header_line(cliente: int, vendedor: int, data_ddmmyyyy: str) -> str:
    line = ""
    line += "01"
    line += zfill_num(int(cliente), 7)
    line += zfill_num(int(vendedor), 7)
    line += "0" * 21
    line += data_ddmmyyyy
    line += "0" * 65
    line += "True 0000000"
    return line


def build_item_line(codigo_produto, descricao, vendedor, qtd, unit, custo, cfop) -> str:
    line = ""
    # Parte A
    line += "03"
    line += zfill_num(int(codigo_produto), 7)
    line += fix_text(descricao, 120)

    # Parte B
    vendedor_bloco = zfill_num(int(vendedor), 7) + ("0" * 5)
    line += vendedor_bloco

    line += zfill_num(scaled_int(qtd, SCALE_QTD), 13)

    unit_decimal = to_decimal(unit)
    if unit_decimal == 0:
        unit_decimal = Decimal("0.0000001")

    line += zfill_num(
        int((unit_decimal * Decimal(SCALE_UNIT)).to_integral_value(rounding=ROUND_HALF_UP)),
        12
    )

    total_item = to_decimal(qtd) * to_decimal(unit)
    line += zfill_num(scaled_int(total_item, SCALE_TOTAL), 12)

    # Parte C
    line += ("0" * 10) + "V"
    line += zfill_num(scaled_int(custo, SCALE_CUSTO), 13)

    custo_total = to_decimal(custo)
    line += zfill_num(scaled_int(custo_total, SCALE_CUSTO), 13)

    line += "0" * 10

    # Parte D
    line += zfill_num(int(cfop), 4)
    line += " " * 6
    line += "False"
    line += "0" * 13

    # Força 254
    if len(line) < ITEM_LEN:
        line = line.ljust(ITEM_LEN, " ")
    elif len(line) > ITEM_LEN:
        line = line[:ITEM_LEN]

    return line


def process_itens_to_txt(itens: list, out_path: str, vendedor_fixo: int) -> tuple[str, int]:
    """
    Gera o TXT final direto de 'itens' (lista de dicts), sem Excel.
    Retorna (caminho_txt, qtd_itens_03).
    """
    first = itens[0]
    cliente = int(str(first["codigo_cliente"]).strip())

    data_ref = None
    for it in itens:
        if it.get("data_orcamento"):
            data_ref = it["data_orcamento"]
            break

    data_ddmmyyyy = format_date_ddmmyyyy(data_ref)
    vendedor = vendedor_fixo

    lines = [build_header_line(cliente, vendedor, data_ddmmyyyy)]

    count_03 = 0
    for i, it in enumerate(itens):
        descricao = str(it.get("descricao_produto") or "").strip()

        # regra do corante: unitário sempre 1.00
        if descricao.startswith("P-"):
            unit_value = Decimal("1.00")
        else:
            unit_value = it.get("preco_venda")

        item_line = build_item_line(
            codigo_produto=it.get("codigo_produto"),
            descricao=descricao,
            vendedor=vendedor,
            qtd=it.get("quantidade"),
            unit=unit_value,
            custo=it.get("custo"),
            cfop=it.get("cfop"),
        )

        if len(item_line) != ITEM_LEN:
            raise RuntimeError(f"Linha {i+1}: {len(item_line)} chars (esperado {ITEM_LEN})")

        lines.append(item_line)
        count_03 += 1

    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        for ln in lines:
            f.write(ln + "\n")

    return out_path, count_03
