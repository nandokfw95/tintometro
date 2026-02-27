# ui/mixins_tree.py
from tkinter import messagebox
import ttkbootstrap as tb
from db import buscar_codigo_por_descricao, buscar_cfop_custo


class TreeItensMixin:
    """
    Mixin responsável por:
      - preencher/atualizar Treeview (tabela)
      - sincronizar Tree->itens
      - lógica de clique na coluna "acao"
      - overlay de "botão" (imagem) na coluna Ação
    """

    def atualizar_tree(self):
        self.tree.delete(*self.tree.get_children())
        self._clear_add_buttons()

        for i, item in enumerate(self.itens):
            tag = "even" if i % 2 == 0 else "odd"

            cod = str(item.get("codigo_produto") or "").strip()
            precisa_add = (not cod) or (not cod.isdigit())

            # IMPORTANTE: não mostrar texto (senão aparece "Adicionar")
            acao = " " if precisa_add else ""

            self.tree.insert(
                "",
                "end",
                iid=str(i),
                tags=(tag,),
                values=(
                    item.get("tipo", ""),
                    item.get("codigo_produto", ""),
                    item.get("descricao_produto", ""),
                    item.get("quantidade", ""),
                    item.get("data_orcamento", ""),
                    item.get("preco_venda", ""),
                    item.get("vendedor", ""),
                    item.get("cfop", ""),
                    item.get("custo", ""),
                    acao,
                )
            )

        # se tinha overlay e a lista mudou, some com ele
        self._destroy_acao_overlay()
        self.tree.update_idletasks()
        self._render_add_buttons()

    def sync_tree_para_itens(self):
        for iid in self.tree.get_children():
            idx = int(iid)
            vals = self.tree.item(iid, "values")
            self.itens[idx]["tipo"] = vals[0]
            self.itens[idx]["codigo_produto"] = (vals[1] or "").strip()

    def bind_tree_actions(self):
        self.tree.bind("<Button-1>", self._on_tree_click)

        # cache de "botões" por linha
        self._acao_buttons = {}

        # redesenha quando rolar / redimensionar
        self.tree.bind("<Configure>", lambda e: self._render_add_buttons())
        self.tree.bind("<Expose>", lambda e: self._render_add_buttons())

    def _on_tree_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return

        row_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        if not row_id or not col_id:
            return

        col_index = int(col_id.replace("#", "")) - 1
        col_name = self.tree["columns"][col_index]

        if col_name != "acao":
            return

        # valida pelo item real, não pelo texto
        try:
            idx = int(row_id)
            item = self.itens[idx]
        except Exception:
            return

        cod = str(item.get("codigo_produto") or "").strip()
        precisa_add = (not cod) or (not cod.isdigit())
        if not precisa_add:
            return

        self.abrir_fluxo_adicionar_produto(idx)

    # ===== Overlay (imagem) na célula "acao" =====

    def _destroy_acao_overlay(self):
        if getattr(self, "_acao_overlay", None):
            try:
                self._acao_overlay.place_forget()
                self._acao_overlay.destroy()
            except Exception:
                pass
            self._acao_overlay = None

    def _on_tree_leave(self, event=None):
        self.tree.config(cursor="")
        self._destroy_acao_overlay()

    def _on_tree_motion(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            self.tree.config(cursor="")
            self._destroy_acao_overlay()
            return

        row_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        if not row_id or not col_id:
            self.tree.config(cursor="")
            self._destroy_acao_overlay()
            return

        col_index = int(col_id.replace("#", "")) - 1
        col_name = self.tree["columns"][col_index]

        if col_name != "acao":
            self.tree.config(cursor="")
            self._destroy_acao_overlay()
            return

        # decide se precisa mostrar botão olhando o item real
        try:
            idx = int(row_id)
            item = self.itens[idx]
        except Exception:
            self.tree.config(cursor="")
            self._destroy_acao_overlay()
            return

        cod = str(item.get("codigo_produto") or "").strip()
        precisa_add = (not cod) or (not cod.isdigit())
        if not precisa_add:
            self.tree.config(cursor="")
            self._destroy_acao_overlay()
            return

        # pega a posição da célula
        x, y, w, h = self.tree.bbox(row_id, col_id)
        if w <= 0 or h <= 0:
            self._destroy_acao_overlay()
            return

        self.tree.config(cursor="hand2")

        # cria overlay se ainda não existe
        if not getattr(self, "_acao_overlay", None):
            self._acao_overlay = tb.Label(self.tree, image=self.ico_add, cursor="hand2")

            # clique no ícone abre o fluxo
            self._acao_overlay.bind(
                "<Button-1>",
                lambda e, rid=row_id: self.abrir_fluxo_adicionar_produto(int(rid))
            )

        # centraliza o ícone dentro da célula
        icon_w = self.ico_add.width()
        icon_h = self.ico_add.height()
        px = x + (w - icon_w) // 2
        py = y + (h - icon_h) // 2

        self._acao_overlay.place(x=px, y=py, width=icon_w, height=icon_h)

    # ===== Função existente no seu mixin =====

    def preencher_cfop_custo(self):
        if not self.itens:
            messagebox.showwarning("Atenção", "Carregue um TXT primeiro.")
            return

        self.set_status("Buscando código pela descrição e preenchendo CFOP/Custo...")

        nao_encontrados = []
        preenchidos = 0
        encontrados_debug = []

        for i, item in enumerate(self.itens):
            descricao = (item.get("descricao_produto") or "").strip()
            if not descricao:
                continue

            try:
                codigo = buscar_codigo_por_descricao(descricao)
                if not codigo:
                    nao_encontrados.append(f"Linha {i+1}: '{descricao}'")
                    continue

                item["codigo_produto"] = codigo

                cfop, custo = buscar_cfop_custo(codigo)
                item["cfop"] = cfop if cfop else ""
                item["custo"] = custo if custo is not None else ""

                preenchidos += 1
                if len(encontrados_debug) < 5:
                    encontrados_debug.append(f"{descricao} -> {codigo}")

            except Exception as e:
                nao_encontrados.append(f"Linha {i+1}: '{descricao}' -> erro: {e}")

        self.atualizar_tree()
        self.set_status("Busca finalizada.")

        msg = f"Preenchidos: {preenchidos}"
        if encontrados_debug:
            msg += "\n\nExemplos encontrados:\n" + "\n".join(encontrados_debug)

        if nao_encontrados:
            msg += "\n\nNão encontrados (primeiros 15):\n" + "\n".join(nao_encontrados[:15])
            if len(nao_encontrados) > 15:
                msg += f"\n... (+{len(nao_encontrados)-15})"

        messagebox.showinfo("Resultado", msg)
        
    def _clear_add_buttons(self):
        if getattr(self, "_acao_buttons", None):
            for w in self._acao_buttons.values():
                try:
                    w.destroy()
                except Exception:
                    pass
        self._acao_buttons = {}

    def _render_add_buttons(self):
        # se não existir ainda, ok
        if not hasattr(self, "_acao_buttons"):
            self._acao_buttons = {}

        # remove botões que não existem mais
        existing_iids = set(self.tree.get_children())
        for iid in list(self._acao_buttons.keys()):
            if iid not in existing_iids:
                try:
                    self._acao_buttons[iid].destroy()
                except Exception:
                    pass
                del self._acao_buttons[iid]

        # cria/posiciona botões para linhas que precisam
        for iid in self.tree.get_children():
            try:
                idx = int(iid)
                item = self.itens[idx]
            except Exception:
                continue

            cod = str(item.get("codigo_produto") or "").strip()
            precisa_add = (not cod) or (not cod.isdigit())
            if not precisa_add:
                # se tinha botão e agora não precisa, remove
                if iid in self._acao_buttons:
                    try:
                        self._acao_buttons[iid].destroy()
                    except Exception:
                        pass
                    del self._acao_buttons[iid]
                continue

            # bbox da célula "acao"
            try:
                x, y, w, h = self.tree.bbox(iid, "acao")
            except Exception:
                continue

            if w <= 0 or h <= 0:
                continue

            # cria se não existe
            if iid not in self._acao_buttons:
                btn = tb.Label(self.tree, image=self.ico_add, cursor="hand2")
                btn.bind("<Button-1>", lambda e, rid=iid: self.abrir_fluxo_adicionar_produto(int(rid)))
                self._acao_buttons[iid] = btn

            btn = self._acao_buttons[iid]

            # centraliza dentro da célula
            icon_w = self.ico_add.width()
            icon_h = self.ico_add.height()
            px = x + (w - icon_w) // 2
            py = y + (h - icon_h) // 2
            btn.place(x=px, y=py, width=icon_w, height=icon_h)