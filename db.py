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
        password=cfg["DB_PASS"],
        options="-c client_encoding=UTF8"
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
        
def listar_cores_tintometrico(termo: str = "", limit: int = 50):
    """
    Retorna cod_cor, nome_cor.
    """
    termo = (termo or "").strip()
    sql = """
        SELECT ic.cod_cor, ic.nome_cor
        FROM tintometrico.tintometricocor ic
        WHERE (%s = '' OR ic.cod_cor ILIKE %s OR ic.nome_cor ILIKE %s)
        ORDER BY ic.cod_cor
        LIMIT %s;
    """
    like = f"%{termo}%"
    with conectar_db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (termo, like, like, limit))
            return cur.fetchall()


def listar_opcoes_por_cor(cod_cor: str):
    """
    Dado um COD_COR, retorna apenas opções que EXISTEM na fórmula:
      embalagens: list[tuple(id_embalagem, embalagem, capacidade)]
      produtos:   list[tuple(id_produto, produto)]
      nome_cor:   str | None
    """
    cod_cor = (cod_cor or "").strip()
    if not cod_cor:
        return [], [], None

    sql = """
        SELECT
            i.id_embalagem,
            ie.embalagem,
            ie.capacidade,
            ip.id_produto,
            ip.produto,
            ic.nome_cor
        FROM tintometrico.tintometricoformula i
        JOIN tintometrico.tintometricoembalagem ie
            ON ie.id_embalagem = i.id_embalagem
        JOIN tintometrico.tintometricocor ic
            ON ic.id_cor = i.id_cor
        JOIN tintometrico.tintometricoproduto ip
            ON ip.id_produto = ic.id_produto
        WHERE ic.cod_cor = %s
        ORDER BY ie.capacidade, ie.embalagem, ip.produto;
    """

    with conectar_db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (cod_cor,))
            rows = cur.fetchall()

    if not rows:
        return [], [], None

    nome_cor = rows[0][5]

    embalagens = []
    produtos = []

    emb_vistos = set()
    prod_vistos = set()

    for id_emb, emb, capacidade, id_prod, produto, _nome_cor in rows:
        if id_emb not in emb_vistos:
            embalagens.append((id_emb, emb, capacidade))
            emb_vistos.add(id_emb)

        if id_prod not in prod_vistos:
            produtos.append((id_prod, produto))
            prod_vistos.add(id_prod)

    return embalagens, produtos, nome_cor


def buscar_formula_por_filtros(cod_cor: str, id_embalagem: int, id_produto: int):
    """
    Retorna:
      header: dict(produto, embalagem, capacidade, cod_cor, nome_cor)
      linhas: list[dict(corante, mls)]
    """
    cod_cor = (cod_cor or "").strip()
    sql = """
        SELECT
            i.id_cor,
            i.id_embalagem,
            i.corante,
            ie.embalagem,
            ie.capacidade,
            ip.produto,
            ic.cod_cor,
            ic.nome_cor,
            i.mls
        FROM tintometrico.tintometricoformula i
        LEFT JOIN tintometrico.tintometricoembalagem ie ON ie.id_embalagem = i.id_embalagem
        LEFT JOIN tintometrico.tintometricocor ic ON ic.id_cor = i.id_cor
        LEFT JOIN tintometrico.tintometricoproduto ip ON ip.id_produto = ic.id_produto
        WHERE ic.cod_cor = %s
          AND i.id_embalagem = %s
          AND ip.id_produto = %s
        ORDER BY i.corante;
    """
    with conectar_db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (cod_cor, int(id_embalagem), int(id_produto)))
            rows = cur.fetchall()

    if not rows:
        return None, []

    # header vem “igual” em todas as linhas
    first = rows[0]
    header = {
        "produto": first[5],
        "embalagem": first[3],
        "capacidade": first[4],
        "cod_cor": first[6],
        "nome_cor": first[7],
    }

    linhas = [{"corante": r[2], "mls": r[8]} for r in rows]
    return header, linhas
def listar_produtos_por_cor_embalagem(cod_cor: str, id_embalagem: int):
    """
    Retorna apenas produtos que possuem fórmula para a cor + embalagem selecionadas.
    """
    cod_cor = (cod_cor or "").strip()
    if not cod_cor or not id_embalagem:
        return []

    sql = """
        SELECT DISTINCT
            ip.id_produto,
            ip.produto
        FROM tintometrico.tintometricoformula i
        JOIN tintometrico.tintometricocor ic
            ON ic.id_cor = i.id_cor
        JOIN tintometrico.tintometricoproduto ip
            ON ip.id_produto = ic.id_produto
        WHERE ic.cod_cor = %s
          AND i.id_embalagem = %s
        ORDER BY ip.produto;
    """

    with conectar_db() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (cod_cor, int(id_embalagem)))
            return cur.fetchall()
