# db.py
import re
import psycopg2
from settings import load_db_settings


def conectar_db():
    cfg = load_db_settings()
    return psycopg2.connect(
        host=cfg["DB_HOST"],
        port=cfg["DB_PORT"],
        dbname=cfg["DB_NAME"],
        user=cfg["DB_USER"],
        password=cfg["DB_PASS"]
    )


def normalizar_codigo(valor):
    """
    Recebe int/decimal/str e devolve int.
    Aceita '34,057' -> 34057
    """
    if valor is None:
        return None
    s = str(valor).strip()
    s = re.sub(r"[^\d]", "", s)  # fica só números
    return int(s) if s else None


def buscar_codigo_por_descricao(descricao_txt: str):
    sql = """
        SELECT codigo
        FROM produtos
        WHERE descricao ILIKE %s
        LIMIT 1;
    """
    with conectar_db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (f"%{descricao_txt}%",))
            row = cur.fetchone()
            if not row:
                return None
            return normalizar_codigo(row[0])


def buscar_cfop_custo(codigo_produto: int):
    if not codigo_produto:
        return None, None

    sql = """
        SELECT CONCAT('5', cfop_venda) AS cfop, precocusto
        FROM produtos
        WHERE codigo = %s
        LIMIT 1;
    """
    with conectar_db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (codigo_produto,))
            row = cur.fetchone()
            if not row:
                return None, None
            return row[0], row[1]


def buscar_clientes_por_nome(termo: str, limit: int = 30):
    termo = (termo or "").strip()
    if not termo:
        return []

    sql = """
        SELECT codigo, nome
        FROM clientes
        WHERE nome ILIKE %s
        ORDER BY
            CASE WHEN nome ILIKE %s THEN 0 ELSE 1 END,
            nome
        LIMIT %s;
    """
    like_contains = f"%{termo}%"
    like_starts = f"{termo}%"

    with conectar_db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (like_contains, like_starts, limit))
            return cur.fetchall()
def listar_unidades_produtos(limit: int = 200):
    """Lista unidades distintas da tabela produtos."""
    sql = """
        SELECT DISTINCT unidade
        FROM produtos
        WHERE unidade IS NOT NULL AND TRIM(unidade) <> ''
        ORDER BY unidade
        LIMIT %s;
    """
    with conectar_db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (limit,))
            return [r[0] for r in cur.fetchall()]


def listar_produtos_por_unidade(unidade: str, termo: str | None = None, limit: int = 200):
    """Retorna (codigo, descricao) filtrando por unidade e opcionalmente por termo."""
    unidade = (unidade or "").strip()
    termo = (termo or "").strip()

    if not unidade:
        return []

    if termo:
        sql = """
            SELECT codigo, descricao
            FROM produtos
            WHERE unidade = %s
              AND descricao ILIKE %s
            ORDER BY descricao
            LIMIT %s;
        """
        params = (unidade, f"%{termo}%", limit)
    else:
        sql = """
            SELECT codigo, descricao
            FROM produtos
            WHERE unidade = %s
            ORDER BY descricao
            LIMIT %s;
        """
        params = (unidade, limit)

    with conectar_db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def get_next_codigo_produto() -> int:
    """Gera próximo código (MAX+1). Ajuste se houver sequence."""
    sql = "SELECT COALESCE(MAX(codigo), 0) + 1 FROM produtos;"
    with conectar_db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            return int(cur.fetchone()[0])
        
def criar_produto_copiando(
    *,
    codigo_modelo: int,
    novo_codigo: int,
    codigodefabrica: str,
    descricao: str,
    unidade: str,
    precovenda,
    precocusto,
):
    """
    Cria um novo produto copiando todos os campos do produto modelo,
    sobrescrevendo os campos principais.

    Também replica tabelas auxiliares:
      - produtos_ipi
      - produtos_subst_tabelas
      - balancas
      - pis_cofins
      - produtos_adicionais
      - reforma_tributaria_regra_tributaria_produto
    """

    cols = [
        "codigodefabrica",
        "descricao",
        "unidade",
        "ativo",
        "grupo",
        "subgrupo",
        "departamento",
        "estoqueminimo",
        "estoquemaximo",
        "quantidade",
        "embalagem",
        "precovenda",
        "precocusto",
        "precocontabil",
        "icms",
        "percdesconto",
        "vendersemestoque",
        "iss",
        "codbarra",
        "garantia",
        "baixa",
        "classifica",
        "tabela_preco",
        "marca",
        "estoq_inicial",
        "class_fiscal",
        "aplicacao",
        "cod_ncm",
        "localizacao",
        "situacaotributaria",
        "comissao",
        "observacoes",
        "preco_minimo",
        "carcaca",
        "pesado",
        "dimensao",
        "medidas",
        "pi",
        "classe",
        "peso_bruto",
        "peso_liquido",
        "montado",
        "ipi",
        "dias_contato",
        "funrural",
        "cfop_venda",
        "cfop_compra",
        "st_fora",
        "importado",
        "dias_preco",
        "desc_catalogo",
        "tipo_etiqueta",
        "tipo_mercadoria",
        "genero_item",
        "conta_analitica",
        "envia_palm",
        "grade",
        "md5",
        "ipi_entrada",
        "codigo_cnae",
        "credita_icmsst",
        "codigo_anp",
        "recarga_celular",
        "paranoprecopdv",
        "cest",
        "codigo",
        "pglp",
        "pgnn",
        "pgni",
        "ind_escala_relevante",
        "unidade_tributavel",
        "beneficio",
        "codigo_anvisa",
        "embalagem_venda",
        "iss_tributacao",
        "desonerado",
        "usocte",
        "calcula_antecipacao_icms",
        "comprimento",
        "altura",
        "largura",
        "reducao_iss",
        "ficha_vale_pdv",
        "anp_aliquota_ad_rem",
        "anp_percentual_diferimento",
        "anp_descricao",
        "origem_combustivel",
        "credita_icms_x10",
        "ex_tipi",
        "observacoes_nfe",
        "usa_serial_compra",
        "posse_mercadoria_sintegra",
        "beneficio_credito_presumido",
        "item_com_beneficio",
        "tipo_item",
        "nbs",
        "percent_simples_nacional_serv",
    ]

    col_list = ", ".join(cols)

    select_list = ", ".join([
        "%s AS codigodefabrica",
        "%s AS descricao",
        "%s AS unidade",
        "ativo",
        "grupo",
        "subgrupo",
        "departamento",
        "estoqueminimo",
        "estoquemaximo",
        "0 AS quantidade",
        "embalagem",
        "%s AS precovenda",
        "%s AS precocusto",
        "precocontabil",
        "icms",
        "percdesconto",
        "vendersemestoque",
        "iss",
        "codbarra",
        "garantia",
        "baixa",
        "classifica",
        "tabela_preco",
        "marca",
        "estoq_inicial",
        "class_fiscal",
        "aplicacao",
        "cod_ncm",
        "localizacao",
        "situacaotributaria",
        "comissao",
        "observacoes",
        "preco_minimo",
        "carcaca",
        "pesado",
        "dimensao",
        "medidas",
        "pi",
        "classe",
        "peso_bruto",
        "peso_liquido",
        "montado",
        "ipi",
        "dias_contato",
        "funrural",
        "cfop_venda",
        "cfop_compra",
        "st_fora",
        "importado",
        "dias_preco",
        "desc_catalogo",
        "tipo_etiqueta",
        "tipo_mercadoria",
        "genero_item",
        "conta_analitica",
        "envia_palm",
        "grade",
        "md5",
        "ipi_entrada",
        "codigo_cnae",
        "credita_icmsst",
        "codigo_anp",
        "recarga_celular",
        "paranoprecopdv",
        "cest",
        "%s AS codigo",
        "pglp",
        "pgnn",
        "pgni",
        "ind_escala_relevante",
        "unidade_tributavel",
        "beneficio",
        "codigo_anvisa",
        "embalagem_venda",
        "iss_tributacao",
        "desonerado",
        "usocte",
        "calcula_antecipacao_icms",
        "comprimento",
        "altura",
        "largura",
        "reducao_iss",
        "ficha_vale_pdv",
        "anp_aliquota_ad_rem",
        "anp_percentual_diferimento",
        "anp_descricao",
        "origem_combustivel",
        "credita_icms_x10",
        "ex_tipi",
        "observacoes_nfe",
        "usa_serial_compra",
        "posse_mercadoria_sintegra",
        "beneficio_credito_presumido",
        "item_com_beneficio",
        "tipo_item",
        "nbs",
        "percent_simples_nacional_serv",
    ])

    insert_sql = f"""
        INSERT INTO produtos ({col_list})
        SELECT {select_list}
        FROM produtos
        WHERE codigo = %s;
    """

    with conectar_db() as conn:
        conn.autocommit = False
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT get_usuario(1);")
                
                cur.execute(
                    insert_sql,
                    (
                        codigodefabrica,
                        descricao,
                        unidade,
                        precovenda,
                        precocusto,
                        novo_codigo,
                        codigo_modelo,
                    )
                )
                if cur.rowcount == 0:
                    raise ValueError(f"Produto modelo não encontrado: {codigo_modelo}")

                cur.execute(
                    """
                    INSERT INTO produtos_ipi (cod_produto, enquadramento, cst, enquadramento_entrada, cst_entrada)
                    SELECT %s, enquadramento, cst, enquadramento_entrada, cst_entrada
                    FROM produtos_ipi
                    WHERE cod_produto = %s;
                    """,
                    (novo_codigo, codigo_modelo)
                )

                cur.execute(
                    """
                    INSERT INTO produtos_subst_tabelas (produto, tabela)
                    SELECT %s, tabela
                    FROM produtos_subst_tabelas
                    WHERE produto = %s;
                    """,
                    (novo_codigo, codigo_modelo)
                )

                cur.execute(
                    """
                    INSERT INTO balancas (produto, teclado, posicao, dias_validade)
                    SELECT %s, teclado, posicao, dias_validade
                    FROM balancas
                    WHERE produto = %s;
                    """,
                    (novo_codigo, codigo_modelo)
                )

                cur.execute(
                    """
                    INSERT INTO pis_cofins
                        (produto, cst_pis, pis_aliq, cst_pis_entrada, pis_aliq_entrada,
                         cst_cofins, cofins_aliq, cst_cofins_entrada, cofins_aliq_entrada, codigo_receita)
                    SELECT
                        %s, cst_pis, pis_aliq, cst_pis_entrada, pis_aliq_entrada,
                        cst_cofins, cofins_aliq, cst_cofins_entrada, cofins_aliq_entrada, codigo_receita
                    FROM pis_cofins
                    WHERE produto = %s;
                    """,
                    (novo_codigo, codigo_modelo)
                )

                cur.execute(
                    """
                    INSERT INTO produtos_adicionais (produto, adicional)
                    SELECT %s, adicional
                    FROM produtos_adicionais
                    WHERE produto = %s;
                    """,
                    (novo_codigo, codigo_modelo)
                )

                cur.execute(
                    """
                    INSERT INTO reforma_tributaria_regra_tributaria_produto (produto, regra_tributaria)
                    SELECT %s, regra_tributaria
                    FROM reforma_tributaria_regra_tributaria_produto
                    WHERE produto = %s;
                    """,
                    (novo_codigo, codigo_modelo)
                )

            conn.commit()
            return novo_codigo
        except Exception:
            conn.rollback()
            raise
