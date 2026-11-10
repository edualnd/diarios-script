"""Janela do programa: escolhe bimestre, salas e dias letivos e roda tudo.

Etapas:
1. baixa os diários das salas;
2. confere os dias letivos de cada diário com o calendário e gera o relatório;
3. baixa as Habilidades só das salas que estão certas;
4. junta diário + habilidades em um PDF por sala ("Diários prontos").
"""
import calendar
import datetime
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import traceback
import tkinter as tk
from tkinter import messagebox, ttk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import navegador                                   # noqa: E402
from navegador import PASTA_PROGRAMA, RAIZ, Parar  # noqa: E402

CONFIG = os.path.join(PASTA_PROGRAMA, "configuracoes.json")
PADRAO = {"bimestre": 1, "sala_inicio": 780, "sala_fim": 789, "disciplina": 10,
          "apagar_baixados": False, "calendarios": {}}
MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho",
         "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
ETAPAS = 4

COR_LETIVO, COR_LETIVO_ATIVO = "#2e7d32", "#388e3c"
COR_NAO, COR_NAO_ATIVO = "#e6e6e6", "#d0d0d0"


# =================================================================== dados

def carregar_config():
    cfg = json.loads(json.dumps(PADRAO))
    try:
        with open(CONFIG, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except (OSError, ValueError):
        pass
    return cfg


def salvar_config(cfg):
    with open(CONFIG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def chave_calendario(ano, bim):
    return f"{ano}-{bim}"


def pasta_resultados(bim, ano):
    return os.path.join(RAIZ, "Resultados", f"{bim}º Bimestre {ano}")


def abrir_pasta(pasta):
    os.makedirs(pasta, exist_ok=True)
    subprocess.Popen(["xdg-open", pasta], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def fmt(d):
    return d.strftime("%d/%m/%Y")


def ler_data(texto, ano):
    """Aceita '27/07/2026' ou '27/07' (usa o ano escolhido)."""
    partes = texto.strip().replace("-", "/").split("/")
    if len(partes) == 2:
        partes.append(str(ano))
    dia, mes, a = (int(x) for x in partes)
    return datetime.date(a if a > 100 else 2000 + a, mes, dia)


# =================================================================== processo

def processar(bim, ano, salas, disciplina, calendario, apagar_baixados, etapa):
    """Roda as 4 etapas. `etapa(n, texto)` avisa a janela. Retorna um resumo."""
    if not shutil.which("pdftotext"):
        raise Parar("Falta instalar o programa 'pdftotext'.\n\n"
                    "No terminal: sudo apt install poppler-utils")
    import diarios
    import habilidades
    import juntar
    import relatorio

    pasta = pasta_resultados(bim, ano)
    p_baixados = os.path.join(pasta, "Arquivos baixados")
    p_diarios = os.path.join(p_baixados, "Diários")
    p_hab = os.path.join(p_baixados, "Habilidades")
    p_prontos = os.path.join(pasta, "Diários prontos")
    p_relatorio = os.path.join(pasta, "Relatório de dias letivos.pdf")

    etapa(1, "Baixando os diários")
    baixadas = diarios.baixar(bim, salas, disciplina, p_diarios)
    if not baixadas:
        raise Parar("Nenhum diário foi baixado.\n\nConfira os números das salas.")

    etapa(2, "Conferindo os dias letivos")
    lidos = {}
    for nome in baixadas.values():
        try:
            lidos[nome] = diarios.dias_letivos(os.path.join(p_diarios, f"{nome}.pdf"))
        except Exception as e:
            print(f"{nome}: ERRO ao ler o diário - {e}")
    oficial = {(d.month, d.day) for d in calendario}
    resultado = relatorio.comparar(oficial, lidos, ano,
                                   f"Dias letivos — {bim}º Bimestre {ano}", p_relatorio)
    certas = {s: n for s, n in baixadas.items() if resultado.get(n)}

    etapa(3, "Baixando as habilidades das salas certas")
    if certas:
        completas = habilidades.baixar(bim, certas, p_hab)
    else:
        print("Nenhuma sala está com os dias letivos certos.")
        completas = set()

    etapa(4, "Montando os PDFs finais")
    feitas = juntar.juntar(completas, p_diarios, p_hab, p_prontos) if completas else []
    for nome in baixadas.values():          # tira PDF antigo de sala que não ficou pronta
        antigo = os.path.join(p_prontos, f"{nome}.pdf")
        if nome not in feitas and os.path.exists(antigo):
            os.remove(antigo)

    if apagar_baixados:
        shutil.rmtree(p_baixados, ignore_errors=True)
        print("\nArquivos baixados apagados (ficaram só os diários prontos e o relatório).")

    return {
        "pasta": pasta,
        "prontas": sorted(feitas),
        "diferenca": sorted(n for n in baixadas.values() if not resultado.get(n)),
        "erro_habilidades": sorted(n for n in certas.values() if n not in completas),
    }


# =================================================================== calendário

class EditorCalendario(tk.Toplevel):
    """Janela para marcar os dias letivos do bimestre clicando nos dias."""

    def __init__(self, master, ano, bim, datas, ao_salvar):
        super().__init__(master)
        self.title(f"Dias letivos — {bim}º Bimestre {ano}")
        self.transient(master)
        self.ano, self.ao_salvar = ano, ao_salvar
        self.marcados = set(datas)
        self.botoes = {}
        self.inicio = min(datas) if datas else None
        self.fim = max(datas) if datas else None

        corpo = ttk.Frame(self, padding=14)
        corpo.pack(fill="both", expand=True)

        ttk.Label(corpo, justify="left", text=(
            "1. Informe o primeiro e o último dia do bimestre e clique em "
            "\"Marcar segunda a sexta\".\n"
            "2. Depois clique nos dias para tirar feriados e recessos, "
            "ou para incluir um sábado letivo.\n"
            "    Verde = dia letivo.   Cinza = não é dia letivo.")).pack(anchor="w")

        linha = ttk.Frame(corpo)
        linha.pack(anchor="w", pady=10)
        ttk.Label(linha, text="Primeiro dia:").pack(side="left")
        self.e_inicio = ttk.Entry(linha, width=12)
        self.e_inicio.pack(side="left", padx=(4, 14))
        ttk.Label(linha, text="Último dia:").pack(side="left")
        self.e_fim = ttk.Entry(linha, width=12)
        self.e_fim.pack(side="left", padx=(4, 14))
        ttk.Button(linha, text="Marcar segunda a sexta", command=self.marcar_uteis) \
            .pack(side="left")
        ttk.Label(linha, text="  (ex.: 27/07/2026)", foreground="#777").pack(side="left")
        if self.inicio:
            self.e_inicio.insert(0, fmt(self.inicio))
            self.e_fim.insert(0, fmt(self.fim))

        self.area = ttk.Frame(corpo)
        self.area.pack(fill="both", expand=True)

        rodape = ttk.Frame(corpo)
        rodape.pack(fill="x", pady=(12, 0))
        self.contador = ttk.Label(rodape, font=("TkDefaultFont", 11, "bold"))
        self.contador.pack(side="left")
        ttk.Button(rodape, text="Cancelar", command=self.destroy).pack(side="right")
        ttk.Button(rodape, text="Salvar", command=self.salvar).pack(side="right", padx=6)

        self.desenhar()
        self.grab_set()

    def _periodo(self):
        try:
            ini, fim = ler_data(self.e_inicio.get(), self.ano), ler_data(self.e_fim.get(), self.ano)
        except (ValueError, TypeError):
            messagebox.showerror("Data inválida",
                                 "Escreva as datas no formato dia/mês/ano, ex.: 27/07/2026.",
                                 parent=self)
            return None
        if fim < ini:
            ini, fim = fim, ini
        if (fim - ini).days > 200:
            messagebox.showerror("Período muito longo",
                                 "O período tem mais de 200 dias. Confira as datas.", parent=self)
            return None
        return ini, fim

    def marcar_uteis(self):
        periodo = self._periodo()
        if not periodo:
            return
        self.inicio, self.fim = periodo
        self.marcados = set()
        d = self.inicio
        while d <= self.fim:
            if d.weekday() < 5:
                self.marcados.add(d)
            d += datetime.timedelta(days=1)
        self.desenhar()

    def desenhar(self):
        for w in self.area.winfo_children():
            w.destroy()
        self.botoes = {}
        if not self.inicio:
            ttk.Label(self.area, foreground="#777",
                      text="\nNenhum período escolhido ainda.\n").pack()
            self.atualizar_contador()
            return

        meses, (a, m) = [], (self.inicio.year, self.inicio.month)
        while (a, m) <= (self.fim.year, self.fim.month):
            meses.append((a, m))
            a, m = (a + 1, 1) if m == 12 else (a, m + 1)

        for i, (a, m) in enumerate(meses):
            quadro = ttk.LabelFrame(self.area, text=f" {MESES[m - 1]} {a} ", padding=6)
            quadro.grid(row=i // 3, column=i % 3, padx=6, pady=6, sticky="n")
            for c, nome in enumerate(["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]):
                ttk.Label(quadro, text=nome, foreground="#555").grid(row=0, column=c)
            for r, semana in enumerate(calendar.monthcalendar(a, m), start=1):
                for c, dia in enumerate(semana):
                    if not dia:
                        continue
                    d = datetime.date(a, m, dia)
                    if self.inicio <= d <= self.fim:
                        b = tk.Button(quadro, text=str(dia), width=3, relief="flat", bd=0,
                                      highlightthickness=0, cursor="hand2",
                                      command=lambda d=d: self.alternar(d))
                        self.botoes[d] = b
                        self.pintar(d)
                    else:
                        b = tk.Label(quadro, text=str(dia), width=3, fg="#bbb")
                    b.grid(row=r, column=c, padx=1, pady=1)
        self.atualizar_contador()

    def pintar(self, d):
        b = self.botoes[d]
        if d in self.marcados:
            b.configure(bg=COR_LETIVO, fg="white", activebackground=COR_LETIVO_ATIVO,
                        activeforeground="white")
        else:
            b.configure(bg=COR_NAO, fg="#444", activebackground=COR_NAO_ATIVO,
                        activeforeground="#444")

    def alternar(self, d):
        self.marcados ^= {d}
        self.pintar(d)
        self.atualizar_contador()

    def atualizar_contador(self):
        self.contador.configure(text=f"{len(self.marcados)} dias letivos")

    def salvar(self):
        if not self.marcados:
            messagebox.showerror("Sem dias letivos", "Marque pelo menos um dia letivo.",
                                 parent=self)
            return
        self.ao_salvar(sorted(self.marcados))
        self.destroy()


# =================================================================== janela

class SaidaNaJanela:
    """Manda o que o programa escreve (print) para a caixa de mensagens da janela."""

    def __init__(self, fila):
        self.fila = fila

    def write(self, texto):
        if texto:
            self.fila.put(("log", texto))

    def flush(self):
        pass


class App:
    def __init__(self, root):
        self.root = root
        self.cfg = carregar_config()
        self.fila = queue.Queue()
        self.rodando = False

        root.title("Diários de Classe")
        root.minsize(640, 560)
        root.protocol("WM_DELETE_WINDOW", self.fechar)
        estilo = ttk.Style()
        estilo.configure("Titulo.TLabel", font=("TkDefaultFont", 16, "bold"))
        estilo.configure("Secao.TLabelframe.Label", font=("TkDefaultFont", 11, "bold"))
        estilo.configure("Grande.TButton", font=("TkDefaultFont", 12, "bold"), padding=8)

        c = ttk.Frame(root, padding=16)
        c.pack(fill="both", expand=True)

        ttk.Label(c, text="Diários de Classe", style="Titulo.TLabel").pack(anchor="w")
        ttk.Label(c, foreground="#555", text=(
            "Baixa os diários, confere os dias letivos e monta o PDF final "
            "(diário + habilidades) de cada sala.")).pack(anchor="w", pady=(0, 10))

        # 1. bimestre
        s1 = ttk.LabelFrame(c, text=" 1. Bimestre ", style="Secao.TLabelframe", padding=10)
        s1.pack(fill="x", pady=4)
        self.bim = tk.IntVar(value=self.cfg["bimestre"])
        for b in (1, 2, 3, 4):
            ttk.Radiobutton(s1, text=f"{b}º bimestre", variable=self.bim, value=b,
                            command=self.atualizar_calendario).pack(side="left", padx=(0, 12))
        self.ano = tk.IntVar(value=datetime.date.today().year)
        ttk.Spinbox(s1, from_=2020, to=2100, width=6, textvariable=self.ano,
                    command=self.atualizar_calendario).pack(side="right")
        ttk.Label(s1, text="Ano:").pack(side="right", padx=4)

        # 2. salas
        s2 = ttk.LabelFrame(c, text=" 2. Salas ", style="Secao.TLabelframe", padding=10)
        s2.pack(fill="x", pady=4)
        linha = ttk.Frame(s2)
        linha.pack(anchor="w")
        ttk.Label(linha, text="Da sala nº").pack(side="left")
        self.e_ini = ttk.Entry(linha, width=7)
        self.e_ini.insert(0, str(self.cfg["sala_inicio"]))
        self.e_ini.pack(side="left", padx=6)
        ttk.Label(linha, text="até a sala nº").pack(side="left")
        self.e_fim = ttk.Entry(linha, width=7)
        self.e_fim.insert(0, str(self.cfg["sala_fim"]))
        self.e_fim.pack(side="left", padx=6)
        ttk.Label(s2, foreground="#777", text=(
            "É o número que aparece no endereço da sala no sistema, "
            "ex.: .../atividade/sala/780/diario")).pack(anchor="w", pady=(4, 0))

        # 3. dias letivos
        s3 = ttk.LabelFrame(c, text=" 3. Dias letivos oficiais ", style="Secao.TLabelframe",
                            padding=10)
        s3.pack(fill="x", pady=4)
        self.lbl_cal = ttk.Label(s3)
        self.lbl_cal.pack(side="left")
        ttk.Button(s3, text="Escolher dias letivos…", command=self.editar_calendario) \
            .pack(side="right")

        # opção de limpeza
        self.apagar = tk.BooleanVar(value=self.cfg["apagar_baixados"])
        self.c_apagar = ttk.Checkbutton(
            c, variable=self.apagar,
            text="No final, apagar os diários e habilidades baixados "
                 "(deixar só os diários prontos e o relatório)")
        self.c_apagar.pack(anchor="w", pady=(8, 0))

        # botões
        botoes = ttk.Frame(c)
        botoes.pack(fill="x", pady=(8, 6))
        self.b_comecar = ttk.Button(botoes, text="▶  Começar", style="Grande.TButton",
                                    command=self.comecar)
        self.b_comecar.pack(side="left")
        ttk.Button(botoes, text="Abrir pasta de resultados",
                   command=lambda: abrir_pasta(pasta_resultados(self.bim.get(),
                                                                self._ano()))) \
            .pack(side="right")

        # progresso
        self.status = ttk.Label(c, text="Pronto para começar.")
        self.status.pack(anchor="w")
        self.barra = ttk.Progressbar(c, maximum=ETAPAS)
        self.barra.pack(fill="x", pady=(2, 8))

        caixa = ttk.Frame(c)
        caixa.pack(fill="both", expand=True)
        self.log = tk.Text(caixa, height=12, wrap="word", state="disabled",
                           font=("TkFixedFont", 9), bg="#fafafa", relief="solid", bd=1)
        rolagem = ttk.Scrollbar(caixa, command=self.log.yview)
        self.log.configure(yscrollcommand=rolagem.set)
        self.log.pack(side="left", fill="both", expand=True)
        rolagem.pack(side="right", fill="y")

        self.entradas = [self.e_ini, self.e_fim, self.c_apagar]
        self.atualizar_calendario()
        self.root.after(100, self.ler_fila)

    # ------------------------------------------------------------ calendário
    def _ano(self):
        try:
            return int(self.ano.get())
        except (tk.TclError, ValueError):
            return datetime.date.today().year

    def datas_calendario(self):
        chave = chave_calendario(self._ano(), self.bim.get())
        return [datetime.date.fromisoformat(d) for d in self.cfg["calendarios"].get(chave, [])]

    def atualizar_calendario(self):
        datas = self.datas_calendario()
        if datas:
            self.lbl_cal.configure(foreground="#2e7d32", text=(
                f"✔ {len(datas)} dias letivos, de {fmt(min(datas))} a {fmt(max(datas))}"))
        else:
            self.lbl_cal.configure(foreground="#c62828",
                                   text="✘ Ainda não escolhidos para este bimestre")

    def editar_calendario(self):
        ano, bim = self._ano(), self.bim.get()

        def ao_salvar(datas):
            self.cfg["calendarios"][chave_calendario(ano, bim)] = [d.isoformat() for d in datas]
            salvar_config(self.cfg)
            self.atualizar_calendario()

        EditorCalendario(self.root, ano, bim, self.datas_calendario(), ao_salvar)

    # ------------------------------------------------------------ rodar
    def comecar(self):
        try:
            ini, fim = int(self.e_ini.get()), int(self.e_fim.get())
        except ValueError:
            messagebox.showerror("Salas", "Os números das salas devem ter só números.")
            return
        ini, fim = min(ini, fim), max(ini, fim)
        calendario = self.datas_calendario()
        bim, ano = self.bim.get(), self._ano()
        if not calendario:
            messagebox.showwarning("Dias letivos", (
                f"Escolha primeiro os dias letivos do {bim}º bimestre de {ano}\n"
                "(botão \"Escolher dias letivos…\")."))
            return

        apagar = self.apagar.get()
        self.cfg.update(bimestre=bim, sala_inicio=ini, sala_fim=fim, apagar_baixados=apagar)
        salvar_config(self.cfg)
        aviso = ("No final, os diários e habilidades baixados serão apagados.\n\n"
                 if apagar else "")
        if not messagebox.askyesno("Começar", (
                f"{bim}º bimestre de {ano}, salas {ini} a {fim} ({fim - ini + 1} salas).\n\n"
                f"{aviso}"
                "Isso pode levar alguns minutos. Pode continuar usando o computador.\n\n"
                "Começar?")):
            return

        self.limpar_log()
        self.travar(True)
        args = (bim, ano, range(ini, fim + 1), self.cfg["disciplina"], calendario, apagar)
        threading.Thread(target=self.trabalhar, args=args, daemon=True).start()

    def trabalhar(self, *args):
        saida = SaidaNaJanela(self.fila)
        antigo = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = saida
        navegador.aguardar_login = self.pedir_login
        try:
            resumo = processar(*args, etapa=lambda n, t: self.fila.put(("etapa", n, t)))
            self.fila.put(("fim", resumo, None))
        except Parar as e:
            self.fila.put(("fim", None, str(e)))
        except Exception as e:
            traceback.print_exc()
            self.fila.put(("fim", None, f"Aconteceu um erro inesperado:\n\n{e}"))
        finally:
            sys.stdout, sys.stderr = antigo

    def pedir_login(self):
        """Chamado pelo processo (fora da janela): espera a pessoa fazer login."""
        pronto = threading.Event()
        self.fila.put(("login", pronto))
        pronto.wait()

    def ler_fila(self):
        try:
            while True:
                msg = self.fila.get_nowait()
                tipo = msg[0]
                if tipo == "log":
                    self.escrever(msg[1])
                elif tipo == "etapa":
                    _, n, texto = msg
                    self.barra.configure(value=n - 1)
                    self.status.configure(text=f"Etapa {n} de {ETAPAS}: {texto}…")
                    self.escrever(f"\n── {texto} ──\n")
                elif tipo == "login":
                    messagebox.showinfo("Entrar no sistema", (
                        "O Chrome foi aberto.\n\n"
                        "Faça o login no Gestão Escolar nele e, quando a página da sala "
                        "aparecer, clique em OK aqui."))
                    msg[1].set()
                elif tipo == "fim":
                    self.terminar(msg[1], msg[2])
        except queue.Empty:
            pass
        self.root.after(100, self.ler_fila)

    def terminar(self, resumo, erro):
        self.travar(False)
        if erro:
            self.status.configure(text="Parou com erro.")
            self.escrever(f"\n{erro}\n")
            messagebox.showerror("Não deu certo", erro)
            return

        self.barra.configure(value=ETAPAS)
        self.status.configure(text="Concluído.")
        partes = [f"PDFs prontos: {', '.join(resumo['prontas']) or 'nenhum'}"]
        if resumo["diferenca"]:
            partes.append(f"Dias letivos diferentes do calendário: "
                          f"{', '.join(resumo['diferenca'])}\n"
                          "(veja o \"Relatório de dias letivos\")")
        if resumo["erro_habilidades"]:
            partes.append(f"Erro ao baixar habilidades: {', '.join(resumo['erro_habilidades'])}")
        texto = "\n\n".join(partes)
        self.escrever(f"\n══ RESUMO ══\n{texto}\n")
        if messagebox.askyesno("Pronto!", texto + "\n\nAbrir a pasta com os resultados?"):
            abrir_pasta(resumo["pasta"])

    # ------------------------------------------------------------ utilidades
    def escrever(self, texto):
        self.log.configure(state="normal")
        self.log.insert("end", texto)
        self.log.see("end")
        self.log.configure(state="disabled")

    def limpar_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def travar(self, sim):
        self.rodando = sim
        estado = "disabled" if sim else "normal"
        self.b_comecar.configure(state=estado)
        for e in self.entradas:
            e.configure(state=estado)

    def fechar(self):
        if self.rodando and not messagebox.askyesno(
                "Sair", "O programa ainda está trabalhando. Quer sair mesmo assim?"):
            return
        self.root.destroy()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
