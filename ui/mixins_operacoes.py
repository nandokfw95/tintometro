# ui/mixins_operacoes.py
import os
from tkinter import filedialog, messagebox
import pandas as pd

from config import COLUNAS_EXCEL
from parsing import parse_txt_itens
from validation import validate_itens_before_export
from orcamento_executor import criar_orcamento_no_banco, criar_venda_so_base_e_baixar_corantes
from import_history import get_status_by_txt


class OperacoesMixin:
    """
    Mixin responsável por:
      - carregar TXT
      - aplicar cliente
      - exportar excel (se você usar)
      - criar orçamento / venda no banco

    Pressupõe que o App tenha:
      - self.txt_path
      - self.itens
      - self.codigo_cliente (StringVar)
      - self.set_status(text)
      - self.atualizar_tree()
      - self.sync_tree_para_itens()
      - self.preencher_cfop_custo()
    """

    def selecionar_txt(self):
        path = filedialog.askopenfilename(
            title="Selecione o TXT",
            filetypes=[("TXT", "*.txt"), ("Todos", "*.*")]
        )
        if not path:
            return

        self.txt_path = path
        st = get_status_by_txt(self.txt_path)
        if st and st.get("importado"):
            messagebox.showwarning(
                "Atenção",
                f"Esse arquivo já foi importado!\n\n"
                f"Arquivo: {st.get('arquivo')}\n"
                f"Pedido: {st.get('pedido')}\n"
                f"Modo: {st.get('modo')}\n"
                f"Quando: {st.get('quando')}\n\n"
                f"Se você continuar e gerar de novo, pode duplicar venda."
            )
        try:
            self.itens = parse_txt_itens(path)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao ler TXT:\n{e}")
            return

        self.atualizar_tree()
        self.lbl_arquivo.config(text=f"Arquivo: {os.path.basename(path)}")
        self.lbl_itens.config(text=f"Itens: {len(self.itens)}")
        self.set_status("TXT carregado. Buscando CFOP/Custo automaticamente...")

        self.after(150, self.preencher_cfop_custo)

    def aplicar_cliente(self):
        if not self.itens:
            messagebox.showwarning("Atenção", "Carregue um TXT primeiro.")
            return
        cod = self.codigo_cliente.get().strip()
        for item in self.itens:
            item["codigo_cliente"] = cod
        self.set_status("Código do cliente aplicado em todas as linhas.")
        messagebox.showinfo("OK", "Código do cliente aplicado em todas as linhas.")

    def gerar_excel(self):
        if not self.itens:
            messagebox.showwarning("Atenção", "Carregue um TXT primeiro.")
            return

        self.sync_tree_para_itens()

        cod_cliente = self.codigo_cliente.get().strip()
        if cod_cliente:
            for item in self.itens:
                item["codigo_cliente"] = cod_cliente

        out_path = filedialog.asksaveasfilename(
            title="Salvar Excel",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")]
        )
        if not out_path:
            return

        linhas = []
        for item in self.itens:
            linhas.append({
                "codigo_cliente": item.get("codigo_cliente", ""),
                "codigo_produto": item.get("codigo_produto", ""),
                "descricao_produto": item.get("descricao_produto", ""),
                "data_orcamento": item.get("data_orcamento", ""),
                "quantidade": item.get("quantidade", ""),
                "cfop": item.get("cfop", ""),
                "custo": item.get("custo", ""),
                "preco_venda": item.get("preco_venda", ""),
                "vendedor": item.get("vendedor", ""),
            })

        df = pd.DataFrame(linhas, columns=COLUNAS_EXCEL)
        with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="dados")

        self.set_status("Excel gerado com sucesso.")
        messagebox.showinfo("OK", f"Excel gerado:\n{out_path}")

    def extrair_pedido_tintometro(self):
        """
        Extrai o número do pedido do nome do arquivo.
        Ex: BBFCoresTI-677-1.txt -> 677
        """
        if not self.txt_path:
            return None

        nome = os.path.basename(self.txt_path)
        nome = os.path.splitext(nome)[0]
        partes = nome.split("-")
        if len(partes) >= 2 and partes[1].isdigit():
            return partes[1]
        return None

    def gerar_orcamento_banco(self):
        if not self.itens:
            messagebox.showwarning("Atenção", "Carregue um TXT primeiro.")
            return

        self.sync_tree_para_itens()

        cod_cliente = self.codigo_cliente.get().strip()
        if not cod_cliente or not cod_cliente.isdigit():
            messagebox.showerror("Erro", "Selecione um cliente na lista (ou informe um código numérico).")
            return

        for item in self.itens:
            item["codigo_cliente"] = cod_cliente

        erros = validate_itens_before_export(self.itens)
        if erros:
            preview = "\n".join(erros[:20])
            if len(erros) > 20:
                preview += f"\n... (+{len(erros)-20} erros)"
            messagebox.showerror("Validação falhou", preview)
            return

        try:
            self.set_status("Criando orçamento no banco...")

            resultado = criar_orcamento_no_banco(
                itens=self.itens,
                cliente=int(cod_cliente),
                pedido=None
            )

            self.set_status("Pedido criado com sucesso.")
            messagebox.showinfo(
                "OK",
                f"Orçamento criado!\n\nPedido: {resultado['pedido']}\nItens: {resultado['qtd_itens']}"
            )
            self.itens = []
            self.atualizar_tree()
            self.lbl_arquivo.config(text="Arquivo: (nenhum)")
            self.lbl_itens.config(text="Itens: 0")
            self.txt_path = None
            self.set_status("Pronto. Venda/Orçamento gerado e tela limpa.")

        except Exception as e:
            self.set_status("Erro ao criar orçamento no banco.")
            messagebox.showerror("Erro", f"Falha ao criar orçamento no banco:\n{e}")

    def gerar_venda_base_baixar_corantes(self):
        if not self.itens:
            messagebox.showwarning("Atenção", "Carregue um TXT primeiro.")
            return

        self.sync_tree_para_itens()

        pedido_tintometro = self.extrair_pedido_tintometro()
        if not pedido_tintometro:
            messagebox.showerror("Erro", "Não foi possível extrair o pedido do nome do arquivo.")
            return

        cod_cliente = self.codigo_cliente.get().strip()
        if not cod_cliente or not cod_cliente.isdigit():
            messagebox.showerror("Erro", "Selecione um cliente na lista (ou informe um código numérico).")
            return

        for item in self.itens:
            item["codigo_cliente"] = cod_cliente

        erros = validate_itens_before_export(self.itens)
        if erros:
            preview = "\n".join(erros[:20])
            if len(erros) > 20:
                preview += f"\n... (+{len(erros)-20} erros)"
            messagebox.showerror("Validação falhou", preview)
            return

        try:
            self.set_status("Criando venda só BASE e baixando CORANTES no estoque...")

            resultado = criar_venda_so_base_e_baixar_corantes(
                itens=self.itens,
                cliente=int(cod_cliente),
                pedido=None,
                pedido_tintometro=pedido_tintometro
            )

            self.set_status("Processo concluído com sucesso.")
            messagebox.showinfo(
                "OK",
                f"Concluído!\n\n"
                f"Pedido: {resultado['pedido']}\n"
                f"Itens BASE inseridos: {resultado['qtd_itens_base']}\n"
                f"Baixas CORANTES: {resultado['qtd_baixas_corantes']}\n"
                f"Transforma_Orcamento retornou {len(resultado['retorno_transforma'])} linha(s)."
            )
            self.itens = []
            self.atualizar_tree()
            self.lbl_arquivo.config(text="Arquivo: (nenhum)")
            self.lbl_itens.config(text="Itens: 0")
            self.txt_path = None
            self.set_status("Pronto. Venda gerada e tela limpa.")

        except Exception as e:
            self.set_status("Erro no processo.")
            messagebox.showerror("Erro", f"Falha ao criar venda/baixa:\n{e}")
