import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import messagebox
import tkinter as tk
from PIL import Image, ImageTk
import os

from db import (
    listar_cores_tintometrico,
    listar_opcoes_por_cor,
    listar_produtos_por_cor_embalagem,
    buscar_formula_por_filtros,
)

PASTA_PREVIEW = r"C:\Users\caset\Documents\Tintometro\preview_cores"

class PedidoTintasMixin:
    def abrir_tela_pedido(self):
        win = tb.Toplevel(self)
        win.title("Criar Pedido • Tintométrico")
        win.geometry("1180x720")
        win.transient(self)
        win.grab_set()

        root = tb.Frame(win, padding=14)
        root.pack(fill=BOTH, expand=True)

        tb.Label(
            root,
            text="Criar Pedido (Tintométrico)",
            font=("Segoe UI", 14, "bold")
        ).pack(anchor=W, pady=(0, 10))

        emb_cache = []
        prod_cache = []
        nome_cor_atual = None
        after_id = {"cor": None}
        carrinho = []
        sugestoes_cache = []

        # =========================================================
        # FILTROS
        # =========================================================
        filtros = tb.Labelframe(root, text="Filtros", padding=12)
        filtros.pack(fill=X, pady=(0, 10))

        filtros.columnconfigure(1, weight=1)
        filtros.columnconfigure(3, weight=1)
        filtros.columnconfigure(5, weight=1)

        v_cor = tb.StringVar()
        v_emb = tb.StringVar()
        v_prod = tb.StringVar()

        tb.Label(filtros, text="Cor (COD_COR / Nome):").grid(
            row=0, column=0, sticky=W, padx=(0, 8), pady=6
        )
        ent_cor = tb.Entry(filtros, textvariable=v_cor)
        ent_cor.grid(row=0, column=1, sticky="ew", pady=6)

        tb.Label(filtros, text="Embalagem:").grid(
            row=0, column=2, sticky=W, padx=(14, 8), pady=6
        )
        cb_emb = tb.Combobox(filtros, textvariable=v_emb, state="readonly")
        cb_emb.grid(row=0, column=3, sticky="ew", pady=6)

        tb.Label(filtros, text="Produto:").grid(
            row=0, column=4, sticky=W, padx=(14, 8), pady=6
        )
        cb_prod = tb.Combobox(filtros, textvariable=v_prod, state="readonly")
        cb_prod.grid(row=0, column=5, sticky="ew", pady=6)

        info = tb.Label(filtros, text="", font=("Segoe UI", 9))
        info.grid(row=1, column=0, columnspan=6, sticky=W, pady=(6, 8))

        filtros_btns = tb.Frame(filtros)
        filtros_btns.grid(row=2, column=0, columnspan=6, sticky="w", pady=(4, 0))

        # =========================================================
        # AUTOCOMPLETE DE COR (Entry + Listbox)
        # =========================================================
        sugest_box = tb.Frame(root)

        sugest_border = tk.Frame(
            sugest_box,
            bd=1,
            relief="solid",
            background="#cfd6e4"
        )
        sugest_inner = tk.Frame(
            sugest_border,
            background="white"
        )

        lst_cores = tk.Listbox(
            sugest_inner,
            height=6,
            font=("Segoe UI", 11),
            activestyle="none",
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            selectmode=tk.SINGLE
        )

        sb_cores = tb.Scrollbar(sugest_inner, orient=VERTICAL, command=lst_cores.yview)
        lst_cores.configure(yscrollcommand=sb_cores.set)

        # começa escondido
        sugest_visivel = {"on": False}

        def _mostrar_sugestoes():
            if not sugest_visivel["on"]:
                sugest_box.pack(fill=X, pady=(0, 10), before=pedido_box)
                sugest_border.pack(fill=X, padx=2)
                sugest_inner.pack(fill=BOTH, expand=True, padx=1, pady=1)
                lst_cores.pack(side=LEFT, fill=BOTH, expand=True, padx=(8, 0), pady=8)
                sb_cores.pack(side=RIGHT, fill=Y, pady=8, padx=(0, 8))
                sugest_visivel["on"] = True

        def _esconder_sugestoes():
            if sugest_visivel["on"]:
                lst_cores.pack_forget()
                sb_cores.pack_forget()
                sugest_inner.pack_forget()
                sugest_border.pack_forget()
                sugest_box.pack_forget()
                sugest_visivel["on"] = False

        def mostrar_preview(cod_cor):

            arquivo = cod_cor.replace(" ", "_").replace("/", "_") + ".png"
            caminho = os.path.join(PASTA_PREVIEW, arquivo)

            if not os.path.exists(caminho):
                return

            img = Image.open(caminho)
            img = img.resize((420, 260))

            tkimg = ImageTk.PhotoImage(img)

            lbl_preview.config(image=tkimg)
            lbl_preview.image = tkimg

        # =========================================================
        # PEDIDO / CARRINHO
        # =========================================================
        pedido_box = tb.Labelframe(root, text="Tintas adicionadas ao pedido", padding=10)
        pedido_box.pack(fill=BOTH, expand=True, pady=(0, 10))

        # =========================================================
        # PREVIEW DA COR
        # =========================================================

        preview_frame = tb.Labelframe(root, text="Preview da cor", padding=8)
        preview_frame.pack(fill=X, pady=(0, 10))

        lbl_preview = tb.Label(preview_frame)
        lbl_preview.pack()
        
        pedido_wrap = tb.Frame(pedido_box)
        pedido_wrap.pack(fill=BOTH, expand=True)

        

        tree_pedido = tb.Treeview(
            pedido_wrap,
            columns=("embalagem", "capacidade", "cor", "mls"),
            show="tree headings",
            height=16
        )

        tree_pedido.heading("#0", text="Produto / Corante")
        tree_pedido.heading("embalagem", text="Embalagem")
        tree_pedido.heading("capacidade", text="Capacidade")
        tree_pedido.heading("cor", text="Cor")
        tree_pedido.heading("mls", text="MLS")

        tree_pedido.column("#0", width=320, anchor="w")
        tree_pedido.column("embalagem", width=130, anchor="center")
        tree_pedido.column("capacidade", width=110, anchor="center")
        tree_pedido.column("cor", width=290, anchor="w")
        tree_pedido.column("mls", width=90, anchor="e")

        vsb_pedido = tb.Scrollbar(pedido_wrap, orient=VERTICAL, command=tree_pedido.yview)
        tree_pedido.configure(yscrollcommand=vsb_pedido.set)

        tree_pedido.pack(side=LEFT, fill=BOTH, expand=True)
        vsb_pedido.pack(side=RIGHT, fill=Y)

        # =========================================================
        # HELPERS
        # =========================================================
        def _format_emb_row(r):
            return f"{r[1]} • {r[2]}"

        def _limpar_tree_pedido():
            for item in tree_pedido.get_children():
                tree_pedido.delete(item)

        def _resolver_ids():
            cod = (v_cor.get() or "").strip()
            emb_txt = (v_emb.get() or "").strip()
            prod_txt = (v_prod.get() or "").strip()

            id_emb = None
            for r in emb_cache:
                if _format_emb_row(r) == emb_txt:
                    id_emb = int(r[0])
                    break

            id_prod = None
            for r in prod_cache:
                if r[1] == prod_txt:
                    id_prod = int(r[0])
                    break

            return cod, id_emb, id_prod

        def _renderizar_carrinho():
            _limpar_tree_pedido()

            for idx, item in enumerate(carrinho, start=1):
                header = item["header"]
                linhas = item["linhas"]

                pai = tree_pedido.insert(
                    "",
                    "end",
                    text=f'{idx}. {header["produto"]}',
                    values=(
                        header["embalagem"],
                        header["capacidade"],
                        f'{header["cod_cor"]} | {header["nome_cor"]}',
                        ""
                    ),
                    open=False
                )

                for ln in linhas:
                    tree_pedido.insert(
                        pai,
                        "end",
                        text=ln["corante"],
                        values=("", "", "", ln["mls"])
                    )

        def _carregar_sugestoes_cor():
            termo = (v_cor.get() or "").strip()

            lst_cores.delete(0, tk.END)
            sugestoes_cache.clear()

            if len(termo) < 2:
                _esconder_sugestoes()
                return

            try:
                cores = listar_cores_tintometrico(termo, limit=50)
            except Exception as e:
                _esconder_sugestoes()
                messagebox.showerror("Erro", f"Falha ao listar cores:\n{e}")
                return

            vistos = set()
            for cod_cor, nome_cor in cores:
                cod = str(cod_cor or "").strip()
                nome = str(nome_cor or "").strip()
                chave = (cod, nome)
                if not cod or chave in vistos:
                    continue
                vistos.add(chave)
                sugestoes_cache.append((cod, nome))
                texto = f"{cod}    -    {nome}" if nome else cod
                lst_cores.insert(tk.END, texto)

            if sugestoes_cache:
                _mostrar_sugestoes()
            else:
                _esconder_sugestoes()

        def _carregar_opcoes_por_cor(cod):
            nonlocal emb_cache, prod_cache, nome_cor_atual

            try:
                emb_cache, prod_cache, nome_cor_atual = listar_opcoes_por_cor(cod)
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao carregar opções:\n{e}")
                return

            cb_emb["values"] = [_format_emb_row(r) for r in emb_cache]
            cb_prod["values"] = [r[1] for r in prod_cache]

            if emb_cache:
                v_emb.set(_format_emb_row(emb_cache[0]))
            else:
                v_emb.set("")

            if prod_cache:
                v_prod.set(prod_cache[0][1])
            else:
                v_prod.set("")

            info.config(
                text=f"Nome da cor: {nome_cor_atual or ''} | Embalagens: {len(emb_cache)} | Produtos: {len(prod_cache)}"
            )

        def _selecionar_indice_lista(indice):
            if indice is None or indice < 0 or indice >= len(sugestoes_cache):
                return

            cod, _nome = sugestoes_cache[indice]
            v_cor.set(cod)
            _esconder_sugestoes()
            _carregar_opcoes_por_cor(cod)
            ent_cor.icursor(tk.END)
            ent_cor.focus_set()
            mostrar_preview(cod)

        # =========================================================
        # AÇÕES
        # =========================================================
        def adicionar_ao_pedido():
            nonlocal nome_cor_atual
            cod, id_emb, id_prod = _resolver_ids()
            if not cod or not id_emb or not id_prod:
                messagebox.showwarning("Atenção", "Selecione uma cor, embalagem e produto.")
                return

            try:
                header, linhas = buscar_formula_por_filtros(cod, id_emb, id_prod)
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao buscar fórmula:\n{e}")
                return

            if not header:
                messagebox.showinfo("Aviso", "Nenhuma fórmula encontrada.")
                return

            for item in carrinho:
                h = item["header"]
                if (
                    h["cod_cor"] == header["cod_cor"]
                    and h["embalagem"] == header["embalagem"]
                    and h["produto"] == header["produto"]
                ):
                    messagebox.showwarning("Duplicado", "Essa tinta já foi adicionada ao pedido.")
                    return

            carrinho.append({
                "header": header,
                "linhas": linhas
            })
            _renderizar_carrinho()
            # volta a tela para o estado inicial
            v_cor.set("")
            v_emb.set("")
            v_prod.set("")

            cb_emb["values"] = []
            cb_prod["values"] = []

            emb_cache.clear()
            prod_cache.clear()
            nome_cor_atual = None
            info.config(text="")

            lst_cores.delete(0, tk.END)
            sugestoes_cache.clear()
            _esconder_sugestoes()

            ent_cor.focus_set()

        def remover_do_pedido():
            sel = tree_pedido.focus()
            if not sel:
                messagebox.showwarning("Atenção", "Selecione um item do pedido para remover.")
                return

            pai = sel
            if tree_pedido.parent(sel):
                pai = tree_pedido.parent(sel)

            item_text = tree_pedido.item(pai, "text")
            if not item_text:
                return

            try:
                indice = int(str(item_text).split(".")[0]) - 1
            except Exception:
                return

            if 0 <= indice < len(carrinho):
                carrinho.pop(indice)
                _renderizar_carrinho()

        # =========================================================
        # EVENTOS
        # =========================================================
        def _ao_digitar_cor(_=None):
            if after_id["cor"]:
                win.after_cancel(after_id["cor"])
            after_id["cor"] = win.after(220, _carregar_sugestoes_cor)

        def _ao_mudar_embalagem(_=None):
            cod = (v_cor.get() or "").strip()
            emb_txt = (v_emb.get() or "").strip()

            if not cod or not emb_txt:
                return

            id_emb = None
            for r in emb_cache:
                if _format_emb_row(r) == emb_txt:
                    id_emb = int(r[0])
                    break

            if not id_emb:
                return

            try:
                produtos_filtrados = listar_produtos_por_cor_embalagem(cod, id_emb)
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao filtrar produtos:\n{e}")
                return

            cb_prod["values"] = [r[1] for r in produtos_filtrados]

            if produtos_filtrados:
                v_prod.set(produtos_filtrados[0][1])
                prod_cache.clear()
                prod_cache.extend(produtos_filtrados)
            else:
                v_prod.set("")
                prod_cache.clear()

        def _ao_click_lista(_=None):
            sel = lst_cores.curselection()
            if not sel:
                return
            _selecionar_indice_lista(sel[0])

        def _ao_enter_lista(_=None):
            sel = lst_cores.curselection()
            if not sel and sugestoes_cache:
                _selecionar_indice_lista(0)
                return
            if sel:
                _selecionar_indice_lista(sel[0])

        def _ao_seta_baixo_no_entry(_=None):
            if not sugestoes_cache:
                return
            _mostrar_sugestoes()
            lst_cores.focus_set()
            if lst_cores.size() > 0:
                lst_cores.selection_clear(0, tk.END)
                lst_cores.selection_set(0)
                lst_cores.activate(0)
            return "break"

        def _ao_escape_lista(_=None):
            _esconder_sugestoes()
            ent_cor.focus_set()
            return "break"

        def _ao_focus_out_entry(_=None):
            def _verificar_focus():
                try:
                    foco = win.focus_get()
                except Exception:
                    foco = None

                if foco != lst_cores:
                    _esconder_sugestoes()

            win.after(150, _verificar_focus)

        ent_cor.bind("<KeyRelease>", _ao_digitar_cor)
        ent_cor.bind("<Down>", _ao_seta_baixo_no_entry)
        ent_cor.bind("<FocusOut>", _ao_focus_out_entry)

        lst_cores.bind("<<ListboxSelect>>", _ao_click_lista)
        lst_cores.bind("<Double-Button-1>", _ao_click_lista)
        lst_cores.bind("<Return>", _ao_enter_lista)
        lst_cores.bind("<Escape>", _ao_escape_lista)

        cb_emb.bind("<<ComboboxSelected>>", _ao_mudar_embalagem)

        # =========================================================
        # BOTÕES
        # =========================================================
        tb.Button(
            filtros_btns,
            text="➕ Adicionar ao pedido",
            bootstyle=SUCCESS,
            command=adicionar_ao_pedido
        ).pack(side=LEFT)

        tb.Button(
            filtros_btns,
            text="❌ Remover selecionado",
            bootstyle=DANGER,
            command=remover_do_pedido
        ).pack(side=LEFT, padx=(8, 0))

        tb.Button(
            root,
            text="Fechar",
            bootstyle=SECONDARY,
            command=win.destroy
        ).pack(anchor="e", pady=(4, 0))