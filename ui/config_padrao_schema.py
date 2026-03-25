# ui/config_padrao_schema.py
import io
import pandas as pd
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox

from db import conectar_db  # <-- usa sua conexão existente


TABELAS = {
    "tintometricoproduto": ["id_produto", "produto", "inativo", "export", "loteexport"],
    "tintometricoembalagem": ["id_embalagem", "embalagem", "capacidade", "export", "loteexport"],
    "tintometricocor": ["id_cor", "id_colecao", "id_produto", "cod_cor", "nome_cor", "base", "export", "loteexport"],
    "tintometricoformula": ["id_cor", "id_embalagem", "item", "corante", "mls", "export", "loteexport"],
}

ORDEM_IMPORT = [
    "tintometricoproduto",
    "tintometricoembalagem",
    "tintometricocor",
    "tintometricoformula",
]


def criar_schema_tabelas_fks(schema: str):
    schema = (schema or "").strip() or "tintometrico"

    ddl = f"""
    CREATE SCHEMA IF NOT EXISTS {schema};

    CREATE TABLE IF NOT EXISTS {schema}.tintometricoproduto (
        id_produto   INTEGER PRIMARY KEY,
        produto      VARCHAR(100),
        inativo      VARCHAR(1),
        export       VARCHAR(1),
        loteexport   INTEGER
    );

    CREATE TABLE IF NOT EXISTS {schema}.tintometricoembalagem (
        id_embalagem INTEGER PRIMARY KEY,
        embalagem    VARCHAR(20),
        capacidade   INTEGER,
        export       VARCHAR(1),
        loteexport   INTEGER
    );

    CREATE TABLE IF NOT EXISTS {schema}.tintometricocor (
        id_cor       INTEGER PRIMARY KEY,
        id_colecao   INTEGER,
        id_produto   INTEGER,
        cod_cor      VARCHAR(50),
        nome_cor     VARCHAR(50),
        base         VARCHAR(2),
        export       VARCHAR(1),
        loteexport   INTEGER
    );

    CREATE TABLE IF NOT EXISTS {schema}.tintometricoformula (
        id_cor       INTEGER NOT NULL,
        id_embalagem INTEGER NOT NULL,
        item         INTEGER NOT NULL,
        corante      VARCHAR(10),
        mls          DOUBLE PRECISION,
        export       VARCHAR(1),
        loteexport   INTEGER,
        CONSTRAINT pk_tintometricoformula PRIMARY KEY (id_cor, id_embalagem, item)
    );
    """

    fks = f"""
    DO $$
    BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_tintometricoformula_embalagem') THEN
        ALTER TABLE {schema}.tintometricoformula
          ADD CONSTRAINT fk_tintometricoformula_embalagem
          FOREIGN KEY (id_embalagem)
          REFERENCES {schema}.tintometricoembalagem (id_embalagem)
          ON UPDATE CASCADE ON DELETE RESTRICT;
      END IF;

      IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_tintometricoformula_cor') THEN
        ALTER TABLE {schema}.tintometricoformula
          ADD CONSTRAINT fk_tintometricoformula_cor
          FOREIGN KEY (id_cor)
          REFERENCES {schema}.tintometricocor (id_cor)
          ON UPDATE CASCADE ON DELETE RESTRICT;
      END IF;

      IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_tintometricocor_produto') THEN
        ALTER TABLE {schema}.tintometricocor
          ADD CONSTRAINT fk_tintometricocor_produto
          FOREIGN KEY (id_produto)
          REFERENCES {schema}.tintometricoproduto (id_produto)
          ON UPDATE CASCADE ON DELETE RESTRICT;
      END IF;
    END $$;
    """

    with conectar_db() as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
            cur.execute(fks)
        conn.commit()


def abrir_tela_importacao(parent, schema: str):
    schema = (schema or "").strip() or "tintometrico"

    win = tb.Toplevel(parent)
    win.title("Importar 4 Excels (Produto / Embalagem / Cor / Fórmula)")
    win.geometry("860x460")
    win.transient(parent)
    win.grab_set()

    frm = tb.Frame(win, padding=16)
    frm.pack(fill=BOTH, expand=True)

    tb.Label(frm, text=f"Schema: {schema}", font=("Segoe UI", 11, "bold")).pack(anchor=W, pady=(0, 8))
    tb.Label(frm, text="Selecione 1 arquivo Excel para cada tabela:", font=("Segoe UI", 10)).pack(anchor=W)

    paths = {}  # tabela -> StringVar

    def pick_excel(tabela, var):
        p = filedialog.askopenfilename(
            title=f"Selecione o Excel da tabela {tabela}",
            filetypes=[("Excel", "*.xlsx;*.xls"), ("Todos", "*.*")]
        )
        if p:
            var.set(p)

    box = tb.Frame(frm)
    box.pack(fill=X, pady=12)

    for tabela in TABELAS.keys():
        row = tb.Frame(box)
        row.pack(fill=X, pady=6)

        tb.Label(row, text=tabela, width=24).pack(side=LEFT)

        v = tb.StringVar(value="")
        paths[tabela] = v

        tb.Entry(row, textvariable=v).pack(side=LEFT, fill=X, expand=True, padx=8)

        tb.Button(
            row,
            text="Adicionar Excel",
            bootstyle=PRIMARY,
            command=lambda t=tabela, vv=v: pick_excel(t, vv),
        ).pack(side=LEFT)

    status = tb.StringVar(value="")
    tb.Label(frm, textvariable=status).pack(anchor=W, pady=(6, 0))

    def importar():
        try:
            for t in ORDEM_IMPORT:
                if not paths[t].get().strip():
                    raise ValueError(f"Faltou selecionar o Excel da tabela: {t}")

            with conectar_db() as conn:
                with conn.cursor() as cur:
                    
                    # limpa tudo respeitando FK
                    cur.execute(f"TRUNCATE TABLE {schema}.tintometricoproduto CASCADE;")
                    cur.execute(f"TRUNCATE TABLE {schema}.tintometricoembalagem CASCADE;")
                    cur.execute(f"TRUNCATE TABLE {schema}.tintometricocor CASCADE;")
                    cur.execute(f"TRUNCATE TABLE {schema}.tintometricoformula CASCADE;")

                    for t in ORDEM_IMPORT:
                        status.set(f"Importando {t}...")
                        win.update_idletasks()
                        _importar_excel(cur, schema, t, paths[t].get().strip())

                conn.commit()

            messagebox.showinfo("OK", "Importação concluída com sucesso!")
            win.destroy()

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao importar:\n{e}")
            status.set("")

    tb.Button(frm, text="IMPORTAR", bootstyle=SUCCESS, command=importar).pack(anchor=E, pady=10)


def _importar_excel(cur, schema: str, tabela: str, excel_path: str):
    cols = TABELAS[tabela]

    df = pd.read_excel(excel_path)
    df.columns = [str(c).strip().lower() for c in df.columns]

    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"No Excel de {tabela} faltam colunas: {missing}")

    df = df[cols].copy()

    import csv, io, re

    # 1) NaN -> None (depois disso, nunca use astype(str) em coluna numérica)
    df = df.where(pd.notnull(df), None)

    # 2) Definições por tabela (tipos)
    # ajuste se necessário
    INT_COLS = {
        "tintometricoproduto":   {"id_produto", "loteexport"},
        "tintometricoembalagem": {"id_embalagem", "capacidade", "loteexport"},
        "tintometricocor":       {"id_cor", "id_colecao", "id_produto", "loteexport"},
        "tintometricoformula":   {"id_cor", "id_embalagem", "item", "loteexport"},
    }[tabela]

    FLOAT_COLS = {
        "tintometricoproduto":   set(),
        "tintometricoembalagem": set(),
        "tintometricocor":       set(),
        "tintometricoformula":   {"mls"},
    }[tabela]

    CHAR1_COLS = {"export", "inativo", "nativo"}  # varchar(1)

    # 3) Converte inteiros (aceita "10", "10.0", "", None)
    def to_int(v):
        if v is None:
            return None
        # se vier float do excel (10.0)
        if isinstance(v, (int,)) and not isinstance(v, bool):
            return int(v)
        if isinstance(v, float):
            if pd.isna(v):
                return None
            return int(v)
        s = str(v).strip()
        if not s or s.lower() == "nan":
            return None
        # pega só dígitos e sinal
        s2 = re.sub(r"[^\d\-]", "", s)
        return int(s2) if s2 else None

    for c in INT_COLS:
        if c in df.columns:
            df[c] = df[c].map(to_int)

    # 4) Converte floats (mls)
    def to_float(v):
        if v is None:
            return None
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v)
        s = str(v).strip().replace(",", ".")
        if not s or s.lower() == "nan":
            return None
        try:
            return float(s)
        except:
            return None

    for c in FLOAT_COLS:
        if c in df.columns:
            df[c] = df[c].map(to_float)

    # 5) varchar(1)
    for c in df.columns:
        if c.lower() in CHAR1_COLS:
            df[c] = df[c].map(lambda v: None if v is None else str(v).strip()[:1])

    # 6) Limpa apenas colunas realmente texto (object) EXCLUINDO numéricas já tratadas
    def clean_text(v):
        if v is None:
            return None
        s = str(v)
        s = s.replace("\uFFFD", "")  # remove "�"
        s = s.encode("cp1252", errors="ignore").decode("cp1252")
        return s

    for c in df.columns:
        if c in INT_COLS or c in FLOAT_COLS:
            continue
        if df[c].dtype == object:
            df[c] = df[c].map(clean_text)

    # 7) Gera CSV e copia como WIN1252
    sio = io.StringIO()
    writer = csv.writer(sio, delimiter=";", quoting=csv.QUOTE_MINIMAL, lineterminator="\n")

    for row in df.itertuples(index=False, name=None):
        writer.writerow(["" if v is None else v for v in row])

    data = sio.getvalue().encode("cp1252", errors="ignore")
    bio = io.BytesIO(data)
    bio.seek(0)

    full_table = f"{schema}.{tabela}"
    col_list = ", ".join(cols)

    cur.copy_expert(
        f"COPY {full_table} ({col_list}) FROM STDIN WITH (FORMAT CSV, DELIMITER ';', ENCODING 'WIN1252')",
        bio
    )