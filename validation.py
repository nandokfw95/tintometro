# validation.py

def validate_itens_before_export(itens: list) -> list[str]:
    """
    Retorna uma lista de erros (strings). Se vazia, está OK para gerar TXT.
    """
    erros = []

    if not itens:
        return ["Não há itens carregados."]

    cliente = (itens[0].get("codigo_cliente") or "").strip()
    if not cliente or not str(cliente).isdigit():
        erros.append("Código do cliente vazio ou inválido (precisa ser numérico).")

    data_ok = None
    for it in itens:
        d = it.get("data_orcamento")
        if d:
            data_ok = d
            break
    if not data_ok:
        erros.append("Nenhuma data encontrada (data_orcamento vazia em todos os itens).")

    for idx, it in enumerate(itens, start=1):
        tipo = (it.get("tipo") or "").strip()
        desc = (it.get("descricao_produto") or "").strip()

        if tipo not in ("BASE", "CORANTE"):
            continue

        cod = str(it.get("codigo_produto") or "").strip()
        if not cod or not cod.isdigit():
            erros.append(f"Linha {idx} ({tipo}) sem CÓDIGO do produto: '{desc}'")

        cfop = str(it.get("cfop") or "").strip()
        if not cfop or not cfop.isdigit() or len(cfop) != 4:
            erros.append(f"Linha {idx} ({tipo}) sem CFOP válido (4 dígitos): '{desc}' -> '{cfop}'")

        custo = it.get("custo")
        if custo is None or (isinstance(custo, str) and custo.strip() == ""):
            erros.append(f"Linha {idx} ({tipo}) sem CUSTO: '{desc}'")

        qtd = it.get("quantidade")
        if qtd is None or str(qtd).strip() == "":
            erros.append(f"Linha {idx} ({tipo}) sem QUANTIDADE: '{desc}'")

        if tipo == "BASE":
            pv = it.get("preco_venda")
            if pv is None or (isinstance(pv, str) and pv.strip() == ""):
                erros.append(f"Linha {idx} (BASE) sem PREÇO VENDA: '{desc}'")

    return erros
