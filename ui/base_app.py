# ui/base_app.py
import tkinter as tk
import ttkbootstrap as tb
from ttkbootstrap.constants import *
import os
from tkinter import messagebox

from ui.widgets import EditTreeview
from ui.mixins_clientes import ClientesAutocompleteMixin
from ui.mixins_tree import TreeItensMixin
from ui.mixins_produto import ProdutoAddFlowMixin
from ui.mixins_operacoes import OperacoesMixin
from settings import load_db_settings, save_db_settings
from resources import resource_path
from ui.mixins_pedido import PedidoTintasMixin


class App(
    tb.Window,
    ClientesAutocompleteMixin,
    TreeItensMixin,
    ProdutoAddFlowMixin,
    OperacoesMixin,
    PedidoTintasMixin,
):


    def __init__(self):
        super().__init__(themename="flatly")
        style = tb.Style()

        style.configure(
            "Custom.Treeview",
            rowheight=26,
            borderwidth=1,
            relief="solid"
        )
        style.configure(
            "Custom.Treeview.Heading",
            font=("Segoe UI", 10, "bold"),
            relief="solid",
            borderwidth=1
        )

        self.title("Tintometro •")
        self.geometry("1180x650")
        self.minsize(1050, 600)

        try:
            self.state("zoomed")
        except Exception:
            pass

        self._is_fullscreen = False
        self.bind("<F11>", self._toggle_fullscreen)
        self.bind("<Escape>", self._exit_fullscreen)

        self.txt_path = None
        self.itens = []

        self._build_ui()
        # ícone do botão "Adicionar" (guarde em self para não sumir)
        icon_path = resource_path(r"ui\assets\add.png")
        img = tk.PhotoImage(file=icon_path)
        self.ico_add = img.subsample(20, 20)  # quanto maior o numero menor a imagem
        
        # liga features
        self._clientes_init()
        self.bind_tree_actions()

    def _toggle_fullscreen(self, event=None):
        self._is_fullscreen = not getattr(self, "_is_fullscreen", False)
        self.attributes("-fullscreen", self._is_fullscreen)

    def _exit_fullscreen(self, event=None):
        self._is_fullscreen = False
        self.attributes("-fullscreen", False)

    def set_status(self, text: str):
        self.status.set(text)

    def _build_ui(self):
        header = tb.Frame(self, padding=16)
        header.pack(fill=X)

        title = tb.Label(header, text="Transformar em pedido de venda", font=("Segoe UI", 16, "bold"))
        subtitle = tb.Label(header, text="Selecione o TXT, informe cliente e transforme em venda.",
                            font=("Segoe UI", 10))
        title.pack(anchor=W)
        subtitle.pack(anchor=W, pady=(4, 0))

        controls = tb.Frame(self, padding=(16, 0, 16, 12))
        controls.pack(fill=X)

        self.btn_txt = tb.Button(controls, text="Selecionar TXT", bootstyle=PRIMARY, command=self.selecionar_txt)
        self.btn_txt.grid(row=0, column=0, padx=(0, 12), pady=6)

        tb.Label(controls, text="Cliente (digite nome):", font=("Segoe UI", 10, "bold")).grid(row=0, column=1, sticky=W)

        self.codigo_cliente = tb.StringVar()
        self.cliente_busca_var = tb.StringVar()
        self.codigo_cliente.set("1")          # cliente padrão
        self.cliente_busca_var.set("1")  

        self.ent_cliente = tb.Entry(controls, textvariable=self.cliente_busca_var, width=34)
        self.ent_cliente.grid(row=0, column=2, padx=(8, 12), pady=6, sticky=W)

        self.lst_clientes = tk.Listbox(
            controls,
            height=6,
            bg="white",
            fg="black",
            relief="solid",
            borderwidth=1
        )
        self.lst_clientes.grid(row=1, column=2, padx=(8, 12), sticky="we")
        self.lst_clientes.grid_remove()

        self.btn_aplicar_cliente = tb.Button(
            controls, text="Aplicar clientes", bootstyle=SECONDARY, command=self.aplicar_cliente
        )
        self.btn_aplicar_cliente.grid(row=0, column=3, padx=(0, 12), pady=6)

        self.btn_excel = tb.Button(
            controls, text="Converter em Vendas", bootstyle=SUCCESS, command=self.gerar_orcamento_banco
        )
        self.btn_excel.grid(row=0, column=4, padx=(0, 12), pady=6)

        self.btn_venda_base = tb.Button(
            controls,
            text="Venda só BASE + baixa CORANTES",
            bootstyle=WARNING,
            command=self.gerar_venda_base_baixar_corantes
        )
        self.btn_venda_base.grid(row=0, column=5, padx=(0, 12), pady=6)
        
        self.btn_cfg_db = tb.Button(
            controls,
            text="⚙",
            bootstyle="outline-secondary",
            command=self._acesso_config_banco
        )
        self.btn_cfg_db.grid(row=0, column=7, padx=(0, 0), pady=6, sticky="e")

        controls.columnconfigure(6, weight=1)

        summary = tb.Frame(self, padding=(16, 0, 16, 10))
        summary.pack(fill=X)

        self.lbl_arquivo = tb.Label(summary, text="Arquivo: (nenhum)", font=("Segoe UI", 10))
        self.lbl_itens = tb.Label(summary, text="Itens: 0", font=("Segoe UI", 10))
        self.lbl_arquivo.pack(side=LEFT)
        self.lbl_itens.pack(side=LEFT, padx=18)

        table_wrap = tb.Frame(self, padding=(16, 0, 16, 16))
        table_wrap.pack(fill=BOTH, expand=True)

        cols = ["tipo", "codigo_produto", "descricao_produto", "quantidade",
                "data_orcamento", "preco_venda", "vendedor", "cfop", "custo", "acao"]

        self.tree = EditTreeview(
            table_wrap,
            editable_cols=["codigo_produto"],
            columns=cols,
            show="headings",
            height=18,
            style="Custom.Treeview"
        )

        headings = {
            "tipo": "Tipo",
            "codigo_produto": "Código Produto",
            "descricao_produto": "Descrição",
            "quantidade": "Quantidade",
            "data_orcamento": "Data",
            "preco_venda": "Preço Venda",
            "vendedor": "Vendedor",
            "cfop": "CFOP",
            "custo": "Custo",
            "acao": "Ação",
        }

        widths = {
            "tipo": 80,
            "codigo_produto": 220,
            "descricao_produto": 360,
            "quantidade": 110,
            "data_orcamento": 110,
            "preco_venda": 120,
            "vendedor": 100,
            "cfop": 90,
            "custo": 110,
            "acao": 100,
        }

        anchors = {
            "tipo": "center",
            "codigo_produto": "center",
            "descricao_produto": "w",
            "quantidade": "center",
            "data_orcamento": "center",
            "preco_venda": "center",
            "vendedor": "center",
            "cfop": "center",
            "custo": "center",
            "acao": "center",
        }

        for c in cols:
            self.tree.heading(c, text=headings[c], anchor="center")
            self.tree.column(c, width=widths[c], anchor=anchors.get(c, "center"))

        vsb = tb.Scrollbar(table_wrap, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side=LEFT, fill=BOTH, expand=True)
        vsb.pack(side=RIGHT, fill=Y)

        self.tree.tag_configure("odd", background="#f7f7f7")
        self.tree.tag_configure("even", background="#ffffff")
        #self.tree.tag_configure("btn_acao", foreground="#0d6efd", font=("Segoe UI", 10, "underline"))

        self.status = tb.StringVar(value="Pronto.")
        status_bar = tb.Frame(self, padding=(16, 6))
        status_bar.pack(fill=X)
        tb.Separator(self).pack(fill=X)
        tb.Label(status_bar, textvariable=self.status, font=("Segoe UI", 9)).pack(anchor=W)
        
    def abrir_config_banco(self):
        cfg = load_db_settings()

        win = tb.Toplevel(self)
        win.title("Configurar Banco PostgreSQL")
        largura = 460
        altura = 300

        win.update_idletasks()

        # centraliza em relação ao app principal
        x = self.winfo_rootx() + (self.winfo_width() // 2) - (largura // 2)
        y = self.winfo_rooty() + (self.winfo_height() // 2) - (altura // 2)

        win.geometry(f"{largura}x{altura}+{x}+{y}")
        win.transient(self)
        win.grab_set()

        frm = tb.Frame(win, padding=14)
        frm.pack(fill=BOTH, expand=True)

        grid = tb.Frame(frm)
        grid.pack(fill=X)
        grid.columnconfigure(1, weight=1)

        v_host = tb.StringVar(value=str(cfg["DB_HOST"]))
        v_port = tb.StringVar(value=str(cfg["DB_PORT"]))
        v_name = tb.StringVar(value=str(cfg["DB_NAME"]))
        v_user = tb.StringVar(value=str(cfg["DB_USER"]))
        v_pass = tb.StringVar(value=str(cfg["DB_PASS"]))

        tb.Label(grid, text="Host/IP:").grid(row=0, column=0, sticky=W, pady=6)
        tb.Entry(grid, textvariable=v_host).grid(row=0, column=1, sticky="ew", pady=6)

        tb.Label(grid, text="Porta:").grid(row=1, column=0, sticky=W, pady=6)
        tb.Entry(grid, textvariable=v_port, width=10).grid(row=1, column=1, sticky=W, pady=6)

        tb.Label(grid, text="Base (DB_NAME):").grid(row=2, column=0, sticky=W, pady=6)
        tb.Entry(grid, textvariable=v_name).grid(row=2, column=1, sticky="ew", pady=6)

        tb.Label(grid, text="Usuário:").grid(row=3, column=0, sticky=W, pady=6)
        tb.Entry(grid, textvariable=v_user).grid(row=3, column=1, sticky="ew", pady=6)

        tb.Label(grid, text="Senha:").grid(row=4, column=0, sticky=W, pady=6)
        tb.Entry(grid, textvariable=v_pass, show="*").grid(row=4, column=1, sticky="ew", pady=6)

        btns = tb.Frame(frm)
        btns.pack(fill=X, pady=(14, 0))

        def salvar():
            host = v_host.get().strip()
            port = v_port.get().strip()
            name = v_name.get().strip()
            user = v_user.get().strip()
            passwd = v_pass.get().strip()

            if not host or not name or not user:
                messagebox.showerror("Erro", "Host, Base e Usuário são obrigatórios.")
                return
            if not port.isdigit():
                messagebox.showerror("Erro", "Porta precisa ser numérica.")
                return

            save_db_settings({
                "DB_HOST": host,
                "DB_PORT": int(port),
                "DB_NAME": name,
                "DB_USER": user,
                "DB_PASS": passwd,
            })

            messagebox.showinfo("OK", "Configuração salva! As próximas conexões usarão esses dados.")
            win.destroy()

        tb.Button(btns, text="Cancelar", bootstyle=SECONDARY, command=win.destroy).pack(side=RIGHT)
        tb.Button(btns, text="Salvar", bootstyle=SUCCESS, command=salvar).pack(side=RIGHT, padx=(0, 8))
        
    def _acesso_config_banco(self):
        win = tb.Toplevel(self)
        win.title("Acesso restrito")

        largura = 360
        altura = 200

        # Centralizar na tela
        win.update_idletasks()
        screen_w = win.winfo_screenwidth()
        screen_h = win.winfo_screenheight()
        x = (screen_w // 2) - (largura // 2)
        y = (screen_h // 2) - (altura // 2)
        win.geometry(f"{largura}x{altura}+{x}+{y}")

        win.transient(self)
        win.grab_set()

        frm = tb.Frame(win, padding=20)
        frm.pack(fill="both", expand=True)

        frm.columnconfigure(0, weight=1)

        v_user = tb.StringVar()
        v_pass = tb.StringVar()

        tb.Label(frm, text="Usuário:", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 4))
        ent_user = tb.Entry(frm, textvariable=v_user)
        ent_user.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        tb.Label(frm, text="Senha:", font=("Segoe UI", 10, "bold")).grid(row=2, column=0, sticky="w", pady=(0, 4))
        ent_pass = tb.Entry(frm, textvariable=v_pass, show="*")
        ent_pass.grid(row=3, column=0, sticky="ew", pady=(0, 15))

        def validar(event=None):
            user = v_user.get().strip()
            senha = v_pass.get().strip()

            if user == "1" and senha == "super":
                win.destroy()
                self.abrir_config_banco()
            else:
                messagebox.showerror("Erro", "Usuário ou senha inválidos.")
                ent_pass.delete(0, "end")
                ent_pass.focus()

        btns = tb.Frame(frm)
        btns.grid(row=4, column=0, sticky="e")

        tb.Button(btns, text="Cancelar", bootstyle="secondary", command=win.destroy).pack(side="right")
        tb.Button(btns, text="Entrar", bootstyle="success", command=validar).pack(side="right", padx=(0, 8))

        # 🔥 ENTER inteligente
        def _go_pass(e):
            ent_pass.focus()
            return "break"   # impede o Enter de subir pro bind da janela

        def _do_validate(e):
            validar()
            return "break"

        ent_user.bind("<Return>", _go_pass)   # Enter no usuário -> vai pra senha
        ent_pass.bind("<Return>", _do_validate)  # Enter na senha -> valida

        ent_user.focus()
