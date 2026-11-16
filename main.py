import json
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

# Pasta onde ficam os arquivos: ao lado do .exe (ou do .py, se rodar direto)
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent

ARQUIVO = BASE_DIR / "Porcentagem.txt"
HISTORICO = BASE_DIR / "Historico.txt"


# ---------- Dados: regras ----------
def criar_arquivos():
    ARQUIVO.touch(exist_ok=True)
    HISTORICO.touch(exist_ok=True)


def ler_regras():
    regras = {}
    with open(ARQUIVO, "r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha:
                continue
            try:
                nome, valor = linha.rsplit(";", 1)
                regras[nome] = float(valor)
            except ValueError:
                continue  # ignora linha corrompida
    return regras


def salvar_regras(regras):
    with open(ARQUIVO, "w", encoding="utf-8") as f:
        for nome, valor in regras.items():
            f.write(f"{nome};{valor}\n")


# ---------- Dados: histórico ----------
def ler_historico():
    itens = []
    with open(HISTORICO, "r", encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if not linha:
                continue
            try:
                itens.append(json.loads(linha))
            except json.JSONDecodeError:
                continue
    return itens


def salvar_historico(itens):
    with open(HISTORICO, "w", encoding="utf-8") as f:
        for item in itens:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def registrar_historico(valor, partes):
    item = {
        "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "valor": valor,
        "partes": partes,
    }
    with open(HISTORICO, "a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")


# ---------- Máscaras e conversões ----------
def formatar_porcentagem(valor):
    return f"{valor:.1f}".replace(".", ",") + "%"


def formatar_valor(valor):
    texto = f"{valor:,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


def parse_numero(texto):
    """Aceita '50', '50%', '50,5', '1.000,50' e devolve float."""
    texto = texto.replace("%", "").replace("R$", "").strip()
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    return float(texto)


# ---------- Interface ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Divisão por Porcentagem")
        self.geometry("680x520")
        self.minsize(600, 460)

        barra = ttk.Frame(self)
        barra.pack(side="bottom", fill="x", padx=8, pady=(0, 8))
        ttk.Button(barra, text="Atualizar (F5)", command=self.atualizar_tudo).pack(side="right")
        self.lbl_status = ttk.Label(barra, text="")
        self.lbl_status.pack(side="left")
        self.bind("<F5>", lambda e: self.atualizar_tudo())

        abas = ttk.Notebook(self)
        abas.pack(fill="both", expand=True, padx=8, pady=8)

        self.aba_dividir = ttk.Frame(abas, padding=12)
        self.aba_regras = ttk.Frame(abas, padding=12)
        self.aba_historico = ttk.Frame(abas, padding=12)
        abas.add(self.aba_dividir, text="Dividir")
        abas.add(self.aba_regras, text="Regras")
        abas.add(self.aba_historico, text="Histórico")

        self.montar_dividir()
        self.montar_regras()
        self.montar_historico()

        self.atualizar_regras()
        self.atualizar_historico()

    def atualizar_tudo(self):
        """Recarrega regras e histórico a partir dos arquivos."""
        criar_arquivos()
        self.atualizar_regras()
        self.atualizar_historico()
        self.lbl_status.config(text="Atualizado às " + datetime.now().strftime("%H:%M:%S"))

    # ----- Aba Dividir -----
    def montar_dividir(self):
        topo = ttk.Frame(self.aba_dividir)
        topo.pack(fill="x")

        ttk.Label(topo, text="Valor (R$):").pack(side="left")
        self.var_valor = tk.StringVar()
        entrada = ttk.Entry(topo, textvariable=self.var_valor, width=20)
        entrada.pack(side="left", padx=8)
        entrada.bind("<Return>", lambda e: self.calcular())
        entrada.focus_set()
        ttk.Button(topo, text="Calcular", command=self.calcular).pack(side="left")

        colunas = ("regra", "pct", "valor")
        self.tree_calc = ttk.Treeview(self.aba_dividir, columns=colunas,
                                      show="headings", height=10)
        self.tree_calc.heading("regra", text="Regra")
        self.tree_calc.heading("pct", text="%")
        self.tree_calc.heading("valor", text="Valor")
        self.tree_calc.column("regra", width=260)
        self.tree_calc.column("pct", width=90, anchor="e")
        self.tree_calc.column("valor", width=160, anchor="e")
        self.tree_calc.pack(fill="both", expand=True, pady=12)

        self.lbl_resumo = ttk.Label(self.aba_dividir, text="")
        self.lbl_resumo.pack(anchor="w")

    def calcular(self):
        regras = ler_regras()
        if not regras:
            messagebox.showinfo("Sem regras", "Cadastre regras na aba 'Regras' primeiro.")
            return

        try:
            valor = parse_numero(self.var_valor.get())
        except ValueError:
            messagebox.showerror("Valor inválido", "Digite apenas números.")
            return
        if valor < 0:
            messagebox.showerror("Valor inválido", "O valor não pode ser negativo.")
            return

        self.tree_calc.delete(*self.tree_calc.get_children())
        partes = []
        total_pct = 0
        for nome, pct in regras.items():
            parte = valor * pct / 100
            total_pct += pct
            partes.append({"nome": nome, "pct": pct, "valor": round(parte, 2)})
            self.tree_calc.insert("", "end", values=(
                nome, formatar_porcentagem(pct), formatar_valor(parte)))

        resumo = f"Total distribuído: {formatar_porcentagem(total_pct)}"
        if total_pct > 100:
            resumo += "  |  Atenção: a soma passa de 100%!"
        elif total_pct < 100:
            sobra = valor * (100 - total_pct) / 100
            resumo += f"  |  Sobra: {formatar_valor(sobra)} ({formatar_porcentagem(100 - total_pct)})"
        self.lbl_resumo.config(text=resumo + "  |  salvo no histórico")

        registrar_historico(valor, partes)
        self.atualizar_historico()

    # ----- Aba Regras -----
    def montar_regras(self):
        colunas = ("nome", "pct")
        self.tree_regras = ttk.Treeview(self.aba_regras, columns=colunas,
                                        show="headings", height=10,
                                        selectmode="browse")
        self.tree_regras.heading("nome", text="Regra")
        self.tree_regras.heading("pct", text="Porcentagem")
        self.tree_regras.column("nome", width=320)
        self.tree_regras.column("pct", width=120, anchor="e")
        self.tree_regras.pack(fill="both", expand=True)
        self.tree_regras.bind("<<TreeviewSelect>>", self.ao_selecionar_regra)

        self.lbl_soma = ttk.Label(self.aba_regras, text="")
        self.lbl_soma.pack(anchor="w", pady=(6, 0))

        form = ttk.Frame(self.aba_regras)
        form.pack(fill="x", pady=10)

        ttk.Label(form, text="Nome:").grid(row=0, column=0, sticky="w")
        self.var_nome = tk.StringVar()
        ttk.Entry(form, textvariable=self.var_nome, width=28).grid(row=0, column=1, padx=6)

        ttk.Label(form, text="Porcentagem:").grid(row=0, column=2, sticky="w")
        self.var_pct = tk.StringVar()
        ttk.Entry(form, textvariable=self.var_pct, width=10).grid(row=0, column=3, padx=6)

        botoes = ttk.Frame(self.aba_regras)
        botoes.pack(fill="x")
        ttk.Button(botoes, text="Cadastrar", command=self.cadastrar_regra).pack(side="left")
        ttk.Button(botoes, text="Alterar selecionada", command=self.alterar_regra).pack(side="left", padx=6)
        ttk.Button(botoes, text="Excluir selecionada", command=self.excluir_regra).pack(side="left")

    def atualizar_regras(self):
        regras = ler_regras()
        self.tree_regras.delete(*self.tree_regras.get_children())
        for nome, pct in regras.items():
            self.tree_regras.insert("", "end", iid=nome, values=(nome, formatar_porcentagem(pct)))
        self.lbl_soma.config(text=f"Soma das regras: {formatar_porcentagem(sum(regras.values()))}")

    def ao_selecionar_regra(self, _evento=None):
        sel = self.tree_regras.selection()
        if not sel:
            return
        nome = sel[0]
        regras = ler_regras()
        if nome in regras:
            self.var_nome.set(nome)
            self.var_pct.set(f"{regras[nome]:g}".replace(".", ","))

    def ler_formulario(self):
        """Valida nome e porcentagem. Devolve (nome, pct) ou None."""
        nome = self.var_nome.get().strip().replace(";", "")
        if not nome:
            messagebox.showerror("Erro", "O nome não pode ser vazio.")
            return None
        try:
            pct = parse_numero(self.var_pct.get())
        except ValueError:
            messagebox.showerror("Erro", "Porcentagem inválida. Digite apenas números.")
            return None
        if not 0 <= pct <= 100:
            messagebox.showerror("Erro", "A porcentagem deve estar entre 0 e 100.")
            return None
        return nome, pct

    def limpar_formulario(self):
        self.var_nome.set("")
        self.var_pct.set("")
        self.tree_regras.selection_remove(self.tree_regras.selection())

    def cadastrar_regra(self):
        dados = self.ler_formulario()
        if dados is None:
            return
        nome, pct = dados
        regras = ler_regras()
        if nome in regras:
            messagebox.showerror("Erro", "Já existe uma regra com esse nome. Use 'Alterar'.")
            return
        regras[nome] = pct
        salvar_regras(regras)
        self.atualizar_regras()
        self.limpar_formulario()

    def alterar_regra(self):
        sel = self.tree_regras.selection()
        if not sel:
            messagebox.showinfo("Alterar", "Selecione uma regra na lista.")
            return
        antigo = sel[0]

        dados = self.ler_formulario()
        if dados is None:
            return
        nome, pct = dados

        regras = ler_regras()
        if nome != antigo and nome in regras:
            messagebox.showerror("Erro", "Já existe uma regra com esse nome.")
            return

        # reconstrói mantendo a ordem original
        novas = {}
        for n, v in regras.items():
            if n == antigo:
                novas[nome] = pct
            else:
                novas[n] = v
        salvar_regras(novas)
        self.atualizar_regras()
        self.limpar_formulario()

    def excluir_regra(self):
        sel = self.tree_regras.selection()
        if not sel:
            messagebox.showinfo("Excluir", "Selecione uma regra na lista.")
            return
        nome = sel[0]
        if not messagebox.askyesno("Excluir", f"Excluir a regra '{nome}'?"):
            return
        regras = ler_regras()
        regras.pop(nome, None)
        salvar_regras(regras)
        self.atualizar_regras()
        self.limpar_formulario()

    # ----- Aba Histórico -----
    def montar_historico(self):
        painel = ttk.Frame(self.aba_historico)
        painel.pack(fill="both", expand=True)

        esquerda = ttk.Frame(painel)
        esquerda.pack(side="left", fill="both", expand=True)

        colunas = ("data", "valor")
        self.tree_hist = ttk.Treeview(esquerda, columns=colunas, show="headings",
                                      height=12, selectmode="extended")
        self.tree_hist.heading("data", text="Data")
        self.tree_hist.heading("valor", text="Valor")
        self.tree_hist.column("data", width=130)
        self.tree_hist.column("valor", width=120, anchor="e")
        self.tree_hist.pack(fill="both", expand=True)
        self.tree_hist.bind("<<TreeviewSelect>>", self.mostrar_detalhe)

        self.txt_detalhe = tk.Text(painel, width=34, state="disabled", wrap="word")
        self.txt_detalhe.pack(side="left", fill="both", padx=(10, 0))

        botoes = ttk.Frame(self.aba_historico)
        botoes.pack(fill="x", pady=(10, 0))
        ttk.Button(botoes, text="Remover selecionados", command=self.remover_historico).pack(side="left")
        ttk.Button(botoes, text="Limpar tudo", command=self.limpar_historico).pack(side="left", padx=6)

    def atualizar_historico(self):
        self.itens_hist = ler_historico()
        self.tree_hist.delete(*self.tree_hist.get_children())
        # mais recente primeiro; iid = posição real na lista
        for i in reversed(range(len(self.itens_hist))):
            item = self.itens_hist[i]
            self.tree_hist.insert("", "end", iid=str(i),
                                  values=(item["data"], formatar_valor(item["valor"])))
        self.escrever_detalhe("")

    def escrever_detalhe(self, texto):
        self.txt_detalhe.config(state="normal")
        self.txt_detalhe.delete("1.0", "end")
        self.txt_detalhe.insert("1.0", texto)
        self.txt_detalhe.config(state="disabled")

    def mostrar_detalhe(self, _evento=None):
        sel = self.tree_hist.selection()
        if len(sel) != 1:
            self.escrever_detalhe("")
            return
        item = self.itens_hist[int(sel[0])]
        linhas = [f"{item['data']}", f"Valor: {formatar_valor(item['valor'])}", ""]
        for p in item["partes"]:
            linhas.append(f"{p['nome']} ({formatar_porcentagem(p['pct'])})")
            linhas.append(f"    {formatar_valor(p['valor'])}")
        self.escrever_detalhe("\n".join(linhas))

    def remover_historico(self):
        sel = self.tree_hist.selection()
        if not sel:
            messagebox.showinfo("Remover", "Selecione um ou mais itens do histórico.")
            return
        if not messagebox.askyesno("Remover", f"Remover {len(sel)} item(ns) do histórico?"):
            return
        remover = {int(i) for i in sel}
        restantes = [it for i, it in enumerate(self.itens_hist) if i not in remover]
        salvar_historico(restantes)
        self.atualizar_historico()

    def limpar_historico(self):
        if not self.itens_hist:
            messagebox.showinfo("Histórico", "O histórico já está vazio.")
            return
        if messagebox.askyesno("Limpar tudo", "Apagar TODO o histórico?"):
            salvar_historico([])
            self.atualizar_historico()


if __name__ == "__main__":
    criar_arquivos()
    App().mainloop()