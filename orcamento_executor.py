# orcamento_executor.py
from __future__ import annotations

from datetime import datetime, timedelta, date
from decimal import Decimal
import pandas as pd

from db import conectar_db
from txt_builder import to_decimal  # reaproveita conversões
from parsing import parse_data_br
from decimal import Decimal


def _coerce_date(d) -> date | None:
    if d is None or d == "":
        return None
    if isinstance(d, date) and not isinstance(d, datetime):
        return d
    if isinstance(d, datetime):
        return d.date()
    # tenta parsing
    try:
        return pd.to_datetime(str(d), dayfirst=True).date()
    except Exception:
        return None


def _get_data_base(itens: list[dict]) -> date:
    for it in itens:
        if it.get("data_orcamento"):
            d = _coerce_date(it["data_orcamento"])
            if d:
                return d
    # fallback: hoje
    return datetime.now().date()


def _get_vendedor_fixo(itens: list[dict], fallback: int = 4) -> int:
    # se quiser, no futuro pode pegar do TXT, mas hoje você usa fixo
    return int(fallback)


def get_next_pedido(conn) -> int:
    """
    Gera um 'pedido' simples usando MAX+1.
    Se você tiver sequence própria, a gente troca aqui depois.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT COALESCE(MAX(pedido), 0) + 1 FROM cabecalho_orcamento;")
        return int(cur.fetchone()[0])


def criar_orcamento_no_banco(itens: list[dict], cliente: int, pedido: int | None = None) -> dict:
    """
    Cria cabeçalho + itens + transforma orçamento. Tudo em transação.
    Retorna um dict com infos úteis (pedido, qtd_itens, retorno_transforma).
    """
    if not itens:
        raise ValueError("Lista de itens vazia.")

    data_base = _get_data_base(itens)
    vendedor = _get_vendedor_fixo(itens, fallback=4)

    data_ts = datetime.combine(data_base, datetime.min.time())
    validade_ts = datetime.combine(data_base + timedelta(days=10), datetime.min.time())

    with conectar_db() as conn:
        conn.autocommit = False
        try:
            with conn.cursor() as cur:
                # 1) setar usuário
                cur.execute("SELECT get_usuario(1);")

                # pedido
                if pedido is None:
                    pedido = get_next_pedido(conn)

                # 2) cabeçalho
                cur.execute(
                    """
                    INSERT INTO cabecalho_orcamento
                    (pedido, vendedor, cliente, data, validade,
                     transportador, redespacho, frete, acrescimo, desconto,
                     seguro, outras, subst_parcela, especie)
                    VALUES
                    (%s, %s, %s, %s, %s,
                     NULL, NULL, 0, 0, 0,
                     0, 0, TRUE, NULL);
                    """,
                    (pedido, vendedor, cliente, data_ts, validade_ts)
                )

                # 3) itens
                qtd_itens = 0
                for it in itens:
                    tipo = (it.get("tipo") or "").strip()
                    if tipo not in ("BASE", "CORANTE"):
                        continue

                    produto = int(str(it.get("codigo_produto")).strip())
                    descricao = str(it.get("descricao_produto") or "").strip()

                    qtd = to_decimal(it.get("quantidade"))
                    if qtd <= 0:
                        # se quiser permitir 0, remova isso
                        raise ValueError(f"Quantidade inválida para '{descricao}': {qtd}")

                    cfop = int(str(it.get("cfop")).strip())

                    custo = to_decimal(it.get("custo"))

                    # regra corante: unitário 1.00 quando começa com P-
                    if descricao.startswith("P-"):
                        unit = Decimal("1.00")
                    else:
                        unit = to_decimal(it.get("preco_venda"))

                    total = (qtd * unit)

                    cur.execute(
                        """
                        INSERT INTO itens_orcamento
                        (produto, descricao, vendedor, quantidade,
                         valor_unit, total, desconto, tipo_desconto,
                         preco_custo, custo_medio, orcamento, cfop,
                         consumo_proprio, acrescimo)
                        VALUES
                        (%s, %s, %s, %s,
                         %s, %s, 0, 'V',
                         %s, %s, %s, %s,
                         'False', 0);
                        """,
                        (produto, descricao, vendedor, qtd, unit, total, custo, custo, pedido, cfop)
                    )
                    qtd_itens += 1

                # 4) transforma
                cur.execute("SELECT * FROM Transforma_Orcamento(%s, FALSE, 0, '', 1);", (pedido,))
                retorno = cur.fetchall()

            conn.commit()
            return {"pedido": pedido, "qtd_itens": qtd_itens, "retorno_transforma": retorno}

        except Exception:
            conn.rollback()
            raise
def criar_venda_so_base_e_baixar_corantes(itens, cliente, pedido=None, pedido_tintometro=None):
    """
    1) SELECT get_usuario(1)
    2) Cria cabecalho_orcamento
    3) Insere SOMENTE itens tipo BASE em itens_orcamento
    4) Baixa estoque dos CORANTES (entrada_saida_manual tipo 'S') via INSERT...SELECT
    5) Chama Transforma_Orcamento
    """
    if not itens:
        raise ValueError("Lista de itens vazia.")

    if not pedido_tintometro:
        raise ValueError("pedido_tintometro não informado (não foi possível extrair do nome do arquivo).")

    data_base = _get_data_base(itens)
    vendedor = _get_vendedor_fixo(itens, fallback=4)

    data_ts = datetime.combine(data_base, datetime.min.time())
    validade_ts = datetime.combine(data_base + timedelta(days=10), datetime.min.time())

    bases = [it for it in itens if (it.get("tipo") or "").strip().upper() == "BASE"]
    corantes = [it for it in itens if (it.get("tipo") or "").strip().upper() == "CORANTE"]

    if not bases:
        raise ValueError("Não há itens do tipo BASE para criar a venda/orçamento.")

    with conectar_db() as conn:
        conn.autocommit = False
        try:
            with conn.cursor() as cur:
                # 1) setar usuário
                cur.execute("SELECT get_usuario(1);")

                # pedido (orcamento)
                if pedido is None:
                    pedido = get_next_pedido(conn)

                # 2) cabeçalho do orçamento  ✅ (aqui era onde estava errado)
                cur.execute(
                    """
                    INSERT INTO cabecalho_orcamento
                    (pedido, vendedor, cliente, data, validade,
                     transportador, redespacho, frete, acrescimo, desconto,
                     seguro, outras, subst_parcela, especie)
                    VALUES
                    (%s, %s, %s, %s, %s,
                     NULL, NULL, 0, 0, 0,
                     0, 0, TRUE, NULL);
                    """,
                    (pedido, vendedor, cliente, data_ts, validade_ts)
                )

                # 3) itens: SOMENTE BASE
                qtd_itens_base = 0
                for it in bases:
                    produto = int(str(it.get("codigo_produto")).strip())
                    descricao = str(it.get("descricao_produto") or "").strip()

                    qtd = to_decimal(it.get("quantidade"))
                    if qtd <= 0:
                        raise ValueError(f"Quantidade inválida (BASE) para '{descricao}': {qtd}")

                    cfop = int(str(it.get("cfop")).strip())
                    custo = to_decimal(it.get("custo"))
                    unit = to_decimal(it.get("preco_venda"))
                    total = (qtd * unit)

                    cur.execute(
                        """
                        INSERT INTO itens_orcamento
                        (produto, descricao, vendedor, quantidade,
                         valor_unit, total, desconto, tipo_desconto,
                         preco_custo, custo_medio, orcamento, cfop,
                         consumo_proprio, acrescimo)
                        VALUES
                        (%s, %s, %s, %s,
                         %s, %s, 0, 'V',
                         %s, %s, %s, %s,
                         'False', 0);
                        """,
                        (produto, descricao, vendedor, qtd, unit, total, custo, custo, pedido, cfop)
                    )
                    qtd_itens_base += 1

                # 4) baixa estoque dos CORANTES
                qtd_baixas = 0
                motivo_txt = f"TINTOMETRO {pedido_tintometro}"

                for it in corantes:
                    cod_prod = int(str(it.get("codigo_produto")).strip())

                    qtd = to_decimal(it.get("quantidade"))
                    if qtd <= 0:
                        raise ValueError(f"Quantidade inválida (CORANTE) para código {cod_prod}: {qtd}")

                    cur.execute(
                        """
                        INSERT INTO entrada_saida_manual
                            (tipo, cd_produto, data, quantidade, usuario, motivo,
                             preco_custo, preco_venda, nmotivo, hora_lancamento)
                        SELECT
                            'S',
                            codigo,
                            current_date,
                            %s,
                            1,
                            %s,
                            precocusto,
                            precovenda,
                            1,
                            now()
                        FROM produtos
                        WHERE codigo = %s;
                        """,
                        (qtd, motivo_txt, cod_prod)
                    )

                    if cur.rowcount == 0:
                        raise ValueError(f"Produto (corante) não encontrado em produtos.codigo = {cod_prod}")

                    qtd_baixas += 1

                # 5) transforma
                cur.execute("SELECT * FROM Transforma_Orcamento(%s, FALSE, 0, '', 1);", (pedido,))
                retorno = cur.fetchall()

            conn.commit()
            return {
                "pedido": pedido,
                "qtd_itens_base": qtd_itens_base,
                "qtd_baixas_corantes": qtd_baixas,
                "retorno_transforma": retorno
            }

        except Exception:
            conn.rollback()
            raise