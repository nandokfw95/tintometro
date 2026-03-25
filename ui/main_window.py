import os
import json
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkinter import filedialog, messagebox
from ui.mixins_pedido import PedidoTintasMixin

from ui.base_app import App  # sua tela atual

CONFIG_APP_FILE = "app_settings.json"


class MainWindow(tb.Window, PedidoTintasMixin):

    def __init__(self):
        super().__init__(themename="flatly")

        self.title("Tintômetro • Menu Principal")
        self.geometry("450x500")
        self.minsize(450, 420)

        self._build_ui()

    # ================= UI =================
    
    def centralizar_janela(self, win, largura, altura):
        win.update_idletasks()

        # tamanho da tela
        screen_w = win.winfo_screenwidth()
        screen_h = win.winfo_screenheight()

        # calcula posição central
        x = (screen_w // 2) - (largura // 2)
        y = (screen_h // 2) - (altura // 2)

        win.geometry(f"{largura}x{altura}+{x}+{y}")

    def _build_ui(self):
        container = tb.Frame(self, padding=40)
        container.pack(expand=True)

        tb.Label(
            container,
            text="TINTÔMETRO",
            font=("Segoe UI", 22, "bold")
        ).pack(pady=(0, 40))

        tb.Button(
            container,
            text="🔄 Criar Pedido",
            width=30,
            bootstyle=SUCCESS,
            command=self.abrir_tela_pedido
        ).pack(pady=10)
        
        tb.Button(
            container,
            text="🔄 Transformar",
            width=30,
            bootstyle=SUCCESS,
            command=self.abrir_transformar
        ).pack(pady=10)

        tb.Button(
            container,
            text="⚙ Config Padrão",
            width=30,
            bootstyle=INFO,
            command=self.configurar_padrao
        ).pack(pady=10)

        tb.Button(
            container,
            text="🗄 Config Banco",
            width=30,
            bootstyle=WARNING,
            command=self.configurar_banco
        ).pack(pady=10)
        
        # --- Automação (card bonito) ---
        # --- Automação (layout vertical mais elegante) ---
        cfg = self._load_config()
        self.automacao_var = tb.BooleanVar(value=bool(cfg.get("automacao_ligada", False)))

        card = tb.Labelframe(
            container,
            text="  Automação  ",
            padding=(18, 14),
            bootstyle="secondary"
        )
        card.pack(fill=X, pady=(22, 0))

        # Texto principal
        tb.Label(
            card,
            text="Transformar em vendas automaticamente.",
            font=("Segoe UI", 11, "bold")
        ).pack(anchor="w", pady=(4, 12))

        # Linha inferior (switch + status)
        bottom = tb.Frame(card)
        bottom.pack()

        self.sw_automacao = tb.Checkbutton(
            bottom,
            text="",
            variable=self.automacao_var,
            bootstyle="success-round-toggle"
        )
        self.sw_automacao.pack(side=LEFT, padx=(0, 12))

        self.lbl_auto_badge = tb.Label(
            bottom,
            text="OFF",
            font=("Segoe UI", 10, "bold"),
            padding=(10, 4),
            bootstyle="danger"
        )
        self.lbl_auto_badge.pack(side=LEFT)

        def _refresh_automacao():
            ligado = bool(self.automacao_var.get())
            self.lbl_auto_badge.config(
                text=("ON" if ligado else "OFF"),
                bootstyle=("success" if ligado else "danger"),
            )
            self.sw_automacao.configure(
                bootstyle=("success-round-toggle" if ligado else "danger-round-toggle")
            )

        def _salvar_automacao():
            cfg2 = self._load_config()
            cfg2["automacao_ligada"] = bool(self.automacao_var.get())
            self._save_config(cfg2)
            _refresh_automacao()

        _refresh_automacao()
        self.sw_automacao.configure(command=_salvar_automacao)

    # ================= FUNÇÕES =================

    def abrir_transformar(self):
        from ui.transformar_window import TransformarWindow
        win = TransformarWindow(self)
        win.transient(self)
        win.grab_set()
        win.focus_force()

    def configurar_pasta(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta padrão")
        if not pasta:
            return

        cfg = self._load_config()
        cfg["pasta_padrao"] = pasta
        self._save_config(cfg)

        messagebox.showinfo("OK", f"Pasta salva:\n{pasta}")

    def configurar_padrao(self):
        from ui.config_padrao_schema import criar_schema_tabelas_fks, abrir_tela_importacao

        win = tb.Toplevel(self)
        win.title("Configuração Padrão")
        self.centralizar_janela(win, 420, 320)
        win.grab_set()

        frm = tb.Frame(win, padding=20)
        frm.pack(fill=BOTH, expand=True)

        cfg = self._load_config()

        cliente_var = tb.StringVar(value=cfg.get("cliente_padrao", ""))
        schema_var = tb.StringVar(value=cfg.get("schema_tintometrico", "tintometrico"))

        tb.Label(frm, text="Cliente padrão:").pack(anchor="w")
        tb.Entry(frm, textvariable=cliente_var).pack(fill=X, pady=(6, 12))

        tb.Label(frm, text="Schema para Tabelas (Firebird → Postgres):").pack(anchor="w")
        tb.Entry(frm, textvariable=schema_var).pack(fill=X, pady=(6, 10))

        tb.Separator(frm).pack(fill=X, pady=12)

        def salvar():
            cfg["cliente_padrao"] = cliente_var.get()
            cfg["schema_tintometrico"] = schema_var.get().strip() or "tintometrico"
            self._save_config(cfg)
            messagebox.showinfo("OK", "Configuração salva.")

        def criar_e_importar():
            schema = schema_var.get().strip() or "tintometrico"
            cfg["schema_tintometrico"] = schema
            self._save_config(cfg)

            if not messagebox.askyesno("Confirmar", f"Criar schema/tabelas/FKs e importar Excels?\n\nSchema: {schema}"):
                return

            try:
                criar_schema_tabelas_fks(schema)
                messagebox.showinfo("OK", "Schema + tabelas + FKs criados!")
                abrir_tela_importacao(self, schema)
            except Exception as e:
                messagebox.showerror("Erro", f"Falha:\n{e}")

        btns = tb.Frame(frm)
        btns.pack(fill=X, pady=(8, 0))

        tb.Button(btns, text="Salvar", bootstyle=SUCCESS, command=salvar).pack(side=LEFT)
        tb.Button(btns, text="Criar e Importar Excels", bootstyle=INFO, command=criar_e_importar).pack(side=RIGHT)

    def configurar_banco(self):
        win = tb.Toplevel(self)
        win.title("Configurar Banco")
        self.centralizar_janela(win, 360, 280)
        win.grab_set()

        frm = tb.Frame(win, padding=20)
        frm.pack(fill=BOTH, expand=True)

        cfg = self._load_config()

        host = tb.StringVar(value=cfg.get("DB_HOST", "127.0.0.1"))
        port = tb.StringVar(value=str(cfg.get("DB_PORT", "7586")))
        name = tb.StringVar(value=cfg.get("DB_NAME", "hidraufer"))
        user = tb.StringVar(value=cfg.get("DB_USER", "postgres"))
        password = tb.StringVar(value=cfg.get("DB_PASS", ""))

        campos = [
            ("Host/IP", host),
            ("Porta", port),
            ("Banco", name),
            ("Usuário", user),
            ("Senha", password),
        ]

        for i, (label, var) in enumerate(campos):
            tb.Label(frm, text=label).grid(row=i, column=0, sticky="w", pady=5)
            tb.Entry(frm, textvariable=var).grid(row=i, column=1, sticky="ew", pady=5)

        frm.columnconfigure(1, weight=1)

        def salvar():
            cfg.update({
                "DB_HOST": host.get(),
                "DB_PORT": int(port.get()),
                "DB_NAME": name.get(),
                "DB_USER": user.get(),
                "DB_PASS": password.get(),
            })
            self._save_config(cfg)
            messagebox.showinfo("OK", "Configuração salva.")
            win.destroy()

        tb.Button(frm, text="Salvar", bootstyle=SUCCESS, command=salvar).grid(
            row=len(campos), column=0, columnspan=2, pady=20
        )
    
    # ================= JSON CONFIG =================

    def _load_config(self):
        if not os.path.exists(CONFIG_APP_FILE):
            return {}
        with open(CONFIG_APP_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_config(self, cfg):
        with open(CONFIG_APP_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4)