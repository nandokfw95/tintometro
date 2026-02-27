# ui/widgets.py
import ttkbootstrap as tb


class EditTreeview(tb.Treeview):
    """Treeview com edição por duplo clique (colunas específicas)."""
    def __init__(self, master, editable_cols, **kw):
        super().__init__(master, **kw)
        self.editable_cols = set(editable_cols)
        self._entry = None
        self.bind("<Double-1>", self._on_double_click)

    def _on_double_click(self, event):
        region = self.identify("region", event.x, event.y)
        if region != "cell":
            return

        row_id = self.identify_row(event.y)
        col_id = self.identify_column(event.x)
        col_index = int(col_id.replace("#", "")) - 1
        col_name = self["columns"][col_index]

        if col_name not in self.editable_cols:
            return

        x, y, w, h = self.bbox(row_id, col_id)
        value = self.set(row_id, col_name)

        if self._entry:
            self._entry.destroy()

        self._entry = tb.Entry(self)
        self._entry.place(x=x, y=y, width=w, height=h)
        self._entry.insert(0, value)
        self._entry.focus()

        def salvar(*_):
            novo = self._entry.get().strip()
            self.set(row_id, col_name, novo)
            self._entry.destroy()
            self._entry = None

        self._entry.bind("<Return>", salvar)
        self._entry.bind("<FocusOut>", salvar)
