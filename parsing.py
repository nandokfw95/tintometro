# parsing.py
import csv
from datetime import datetime


def parse_data_br(data_str: str):
    if not data_str:
        return None
    try:
        return datetime.strptime(data_str.strip(), "%d/%m/%Y").date()
    except Exception:
        return None


def parse_txt_itens(caminho_txt: str):
    itens = []
    ultima_base_data = None
    ultima_base_vendedor = None

    # blindado contra encoding
    with open(caminho_txt, "r", encoding="latin1", errors="ignore", newline="") as f:
        reader = csv.reader(f, delimiter=";", quotechar='"')
        for row in reader:
            if not row:
                continue
            tipo = (row[0] or "").strip()

            if tipo.startswith("CAB_"):
                continue

            if tipo == "BASE":
                vendedor = (row[5] or "").strip()
                nome_produto = (row[6] or "").strip()
                qtd_emb = row[10]
                total_avista = row[11]
                data_prod = row[13]

                try:
                    quantidade = float(str(qtd_emb).replace(",", "."))
                except Exception:
                    quantidade = None

                try:
                    preco_venda = float(str(total_avista).replace(",", "."))
                except Exception:
                    preco_venda = None

                data_orc = parse_data_br(data_prod)

                ultima_base_data = data_orc
                ultima_base_vendedor = vendedor

                itens.append({
                    "codigo_cliente": "",
                    "codigo_produto": "",
                    "descricao_produto": nome_produto,
                    "data_orcamento": data_orc,
                    "quantidade": quantidade,
                    "cfop": "",
                    "custo": "",
                    "preco_venda": preco_venda,
                    "vendedor": vendedor,
                    "tipo": "BASE"
                })

            elif tipo == "CORANTE":
                nome_corante = (row[3] or "").strip()
                qtd_mls = row[4] if len(row) > 4 else None

                try:
                    quantidade = float(str(qtd_mls).replace(",", "."))
                except Exception:
                    quantidade = None

                itens.append({
                    "codigo_cliente": "",
                    "codigo_produto": "",
                    "descricao_produto": nome_corante,
                    "data_orcamento": ultima_base_data,
                    "quantidade": quantidade,
                    "cfop": "",
                    "custo": "",
                    "preco_venda": "",
                    "vendedor": ultima_base_vendedor or "",
                    "tipo": "CORANTE"
                })

    return itens
