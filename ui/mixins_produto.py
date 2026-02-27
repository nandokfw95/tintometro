# ui/mixins_produto.py
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from db import (
    listar_unidades_produtos,
    listar_produtos_por_unidade,
    get_next_codigo_produto,
    criar_produto_copiando,
    buscar_cfop_custo,
)


class ProdutoAddFlowMixin:
    """
    Mixin responsável por:
      - telas de "Adicionar" produto
      - criação do produto no banco copiando um modelo

    Pressupõe que o App tenha:
      - self.itens
      - self.atualizar_tree()
      - self.set_status(text)
    """
    def _centralizar_janela(self, win: tb.Toplevel, largura: int, altura: int):
        win.update_idletasks()

        screen_w = win.winfo_screenwidth()
        screen_h = win.winfo_screenheight()

        x = (screen_w // 2) - (largura // 2)
        y = (screen_h // 2) - (altura // 2)

        win.geometry(f"{largura}x{altura}+{x}+{y}")

    def abrir_fluxo_adicionar_produto(self, idx_item: int):
        if idx_item < 0 or idx_item >= len(self.itens):
            return

        item = self.itens[idx_item]
        tipo = (item.get("tipo") or "").strip().upper()
        desc_original = (item.get("descricao_produto") or "").strip()

        win = tb.Toplevel(self)
        win.title("Adicionar produto (selecionar modelo)")
        self._centralizar_janela(win, 780, 520)
        win.transient(self)
        win.grab_set()

        frm = tb.Frame(win, padding=14)
        frm.pack(fill=BOTH, expand=True)

        tb.Label(frm, text=f"Linha {idx_item+1} • {tipo} • '{desc_original}'", font=("Segoe UI", 11, "bold")).pack(anchor=W)
        tb.Label(frm, text="1) Escolha a UNIDADE (produtos.unidade) e selecione um produto MODELO para copiar.", font=("Segoe UI", 9)).pack(anchor=W, pady=(4, 10))

        top = tb.Frame(frm)
        top.pack(fill=X)

        tb.Label(top, text="Unidade:").pack(side=LEFT)
        unidade_var = tb.StringVar()
        cb_un = tb.Combobox(top, textvariable=unidade_var, width=10, state="readonly")
        cb_un.pack(side=LEFT, padx=(6, 18))

        tb.Label(top, text="Filtrar descrição:").pack(side=LEFT)
        filtro_var = tb.StringVar()
        ent_filtro = tb.Entry(top, textvariable=filtro_var, width=30)
        ent_filtro.pack(side=LEFT, padx=(6, 0))

        box = tb.Frame(frm)
        box.pack(fill=BOTH, expand=True, pady=(10, 10))

        lst = tk.Listbox(box, height=16)
        lst.pack(side=LEFT, fill=BOTH, expand=True)
        sb = tb.Scrollbar(box, orient=VERTICAL, command=lst.yview)
        sb.pack(side=RIGHT, fill=Y)
        lst.config(yscrollcommand=sb.set)

        produtos_cache = []  # [(codigo, descricao)]

        def carregar_unidades():
            try:
                unidades = listar_unidades_produtos()
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao listar unidades:\n{e}")
                unidades = []

            cb_un["values"] = unidades
            pref = None
            if tipo == "BASE" and "TIN" in unidades:
                pref = "TIN"
            if tipo == "CORANTE" and "ML" in unidades:
                pref = "COR"
            unidade_var.set(pref or (unidades[0] if unidades else ""))

        def recarregar_lista():
            lst.delete(0, "end")
            produtos_cache.clear()
            un = unidade_var.get().strip()
            termo = filtro_var.get().strip()
            if not un:
                return
            try:
                rows = listar_produtos_por_unidade(un, termo=termo, limit=300)
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao listar produtos:\n{e}")
                return
            for codigo, descricao in rows:
                produtos_cache.append((int(codigo), str(descricao)))
                lst.insert("end", f"{codigo} - {descricao}")

        def on_change_unidade(*_):
            recarregar_lista()

        def on_typing(*_):
            win.after(180, recarregar_lista)

        cb_un.bind("<<ComboboxSelected>>", on_change_unidade)
        ent_filtro.bind("<KeyRelease>", on_typing)

        btns = tb.Frame(frm)
        btns.pack(fill=X)

        def cancelar():
            win.destroy()

        def confirmar_modelo():
            sel = lst.curselection()
            if not sel:
                messagebox.showwarning("Atenção", "Selecione um produto modelo na lista.")
                return
            i = int(sel[0])
            codigo_modelo = produtos_cache[i][0]
            unidade = unidade_var.get().strip()
            win.destroy()
            self._abrir_modal_dados_produto(idx_item, codigo_modelo, unidade)

        tb.Button(btns, text="Cancelar", bootstyle=SECONDARY, command=cancelar).pack(side=RIGHT)
        tb.Button(btns, text="Selecionar modelo", bootstyle=SUCCESS, command=confirmar_modelo).pack(side=RIGHT, padx=(0, 8))

        carregar_unidades()
        recarregar_lista()
        ent_filtro.focus()

    def _abrir_modal_dados_produto(self, idx_item: int, codigo_modelo: int, unidade: str):
        item = self.itens[idx_item]
        desc_original = (item.get("descricao_produto") or "").strip()

        try:
            novo_codigo_sug = get_next_codigo_produto()
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível gerar novo código:\n{e}")
            return

        win = tb.Toplevel(self)
        win.title("Adicionar produto (dados)")
        self._centralizar_janela(win, 560, 340)
        win.transient(self)
        win.grab_set()

        frm = tb.Frame(win, padding=14)
        frm.pack(fill=BOTH, expand=True)

        tb.Label(frm, text=f"Modelo: {codigo_modelo} • Unidade: {unidade}", font=("Segoe UI", 10, "bold")).pack(anchor=W)
        tb.Label(frm, text="2) Informe os dados do novo produto. Vamos copiar o restante do modelo.", font=("Segoe UI", 9)).pack(anchor=W, pady=(4, 12))

        grid = tb.Frame(frm)
        grid.pack(fill=X)
        grid.columnconfigure(1, weight=1)

        v_codigo = tb.StringVar(value=str(novo_codigo_sug))
        v_fabrica = tb.StringVar(value="")
        v_nome = tb.StringVar(value=str(desc_original).upper())
        v_pv = tb.StringVar(value=str(item.get("preco_venda") or ""))
        v_pc = tb.StringVar(value=str(item.get("custo") or ""))

        tb.Label(grid, text="Novo código:").grid(row=0, column=0, sticky=W, pady=4)
        tb.Entry(grid, textvariable=v_codigo, width=12).grid(row=0, column=1, sticky=W, pady=4)

        tb.Label(grid, text="Código de fábrica:").grid(row=1, column=0, sticky=W, pady=4)
        tb.Entry(grid, textvariable=v_fabrica, width=18).grid(row=1, column=1, sticky=W, pady=4)

        tb.Label(grid, text="Nome/Descrição:").grid(row=2, column=0, sticky=W, pady=4)
        tb.Entry(grid, textvariable=v_nome).grid(row=2, column=1, sticky="ew", pady=4)

        tb.Label(grid, text="Preço venda:").grid(row=3, column=0, sticky=W, pady=4)
        tb.Entry(grid, textvariable=v_pv, width=14).grid(row=3, column=1, sticky=W, pady=4)

        tb.Label(grid, text="Preço custo:").grid(row=4, column=0, sticky=W, pady=4)
        tb.Entry(grid, textvariable=v_pc, width=14).grid(row=4, column=1, sticky=W, pady=4)

        btns = tb.Frame(frm)
        btns.pack(fill=X, pady=(18, 0))

        def cancelar():
            win.destroy()

        def confirmar():
            novo_codigo = (v_codigo.get() or "").strip()
            if not novo_codigo.isdigit():
                messagebox.showerror("Erro", "Novo código precisa ser numérico.")
                return

            cod_fab = (v_fabrica.get() or "").strip()
            nome = (v_nome.get() or "").strip()
            if not nome:
                messagebox.showerror("Erro", "Informe a descrição do produto.")
                return

            pv = (v_pv.get() or "").strip().replace(",", ".")
            pc = (v_pc.get() or "").strip().replace(",", ".")
            try:
                pv_val = float(pv)
                pc_val = float(pc)
            except Exception:
                messagebox.showerror("Erro", "Preço venda e custo precisam ser numéricos.")
                return

            try:
                self.set_status("Inserindo novo produto no banco...")
                novo = criar_produto_copiando(
                    codigo_modelo=int(codigo_modelo),
                    novo_codigo=int(novo_codigo),
                    codigodefabrica=cod_fab,
                    descricao=nome,
                    unidade=unidade,
                    precovenda=pv_val,
                    precocusto=pc_val,
                )

                self.itens[idx_item]["codigo_produto"] = int(novo)

                cfop, custo = buscar_cfop_custo(int(novo))
                self.itens[idx_item]["cfop"] = cfop if cfop else self.itens[idx_item].get("cfop", "")
                self.itens[idx_item]["custo"] = custo if custo is not None else self.itens[idx_item].get("custo", "")

                self.atualizar_tree()
                self.set_status("Produto criado e linha atualizada.")
                win.destroy()
                messagebox.showinfo("OK", f"Produto criado com sucesso!\n\nNovo código: {novo}")

            except Exception as e:
                self.set_status("Erro ao criar produto.")
                messagebox.showerror("Erro", f"Falha ao inserir produto:\n{e}")

        tb.Button(btns, text="Cancelar", bootstyle=SECONDARY, command=cancelar).pack(side=RIGHT)
        tb.Button(btns, text="Confirmar", bootstyle=SUCCESS, command=confirmar).pack(side=RIGHT, padx=(0, 8))
