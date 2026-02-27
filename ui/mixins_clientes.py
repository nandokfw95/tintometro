# ui/mixins_clientes.py
from db import buscar_clientes_por_nome


class ClientesAutocompleteMixin:
    """
    Mixin responsável APENAS por:
      - Entry (nome do cliente)
      - Listbox (sugestões)
      - debounce e seleção

    Pressupõe que o App tenha:
      - self.codigo_cliente (StringVar)
      - self.cliente_busca_var (StringVar)
      - self.ent_cliente (Entry)
      - self.lst_clientes (Listbox)
      - self.set_status(text)
    """

    def _clientes_init(self):
        self._clientes_sugestoes = []
        self._after_busca = None

        self.ent_cliente.bind("<KeyRelease>", self._on_cliente_typing)
        self.ent_cliente.bind("<Down>", self._cliente_focus_list)
        self.lst_clientes.bind("<Return>", self._cliente_select)
        self.lst_clientes.bind("<Double-1>", self._cliente_select)
        self.lst_clientes.bind("<Escape>", lambda e: self._cliente_hide_list())

    def _cliente_hide_list(self):
        self.lst_clientes.grid_remove()

    def _cliente_focus_list(self, event=None):
        if self.lst_clientes.winfo_ismapped():
            self.lst_clientes.focus()
            if self.lst_clientes.size() > 0:
                self.lst_clientes.selection_clear(0, "end")
                self.lst_clientes.selection_set(0)
                self.lst_clientes.activate(0)
        return "break"

    def _cliente_select(self, event=None):
        if not self._clientes_sugestoes:
            self._cliente_hide_list()
            return

        sel = self.lst_clientes.curselection()
        if not sel:
            return

        idx = int(sel[0])
        codigo, nome = self._clientes_sugestoes[idx]

        self.cliente_busca_var.set(nome)
        self.codigo_cliente.set(str(codigo))

        self._cliente_hide_list()
        self.ent_cliente.icursor("end")
        self.ent_cliente.focus()

    def _on_cliente_typing(self, event=None):
        termo = self.cliente_busca_var.get().strip()

        # se digitar só números, trata como código direto
        if termo.isdigit():
            self.codigo_cliente.set(termo)
            self._cliente_hide_list()
            return

        if self._after_busca:
            self.after_cancel(self._after_busca)
        self._after_busca = self.after(200, lambda: self._buscar_e_mostrar_clientes(termo))

    def _buscar_e_mostrar_clientes(self, termo: str):
        self._after_busca = None

        termo = (termo or "").strip()
        if len(termo) < 2:
            self._cliente_hide_list()
            return

        try:
            rows = buscar_clientes_por_nome(termo, limit=30)
        except Exception as e:
            self.set_status(f"Erro ao buscar clientes: {e}")
            self._cliente_hide_list()
            return

        self._clientes_sugestoes = rows
        self.lst_clientes.delete(0, "end")

        if not rows:
            self._cliente_hide_list()
            return

        for codigo, nome in rows:
            self.lst_clientes.insert("end", f"{codigo} - {nome}")

        self.lst_clientes.grid()
