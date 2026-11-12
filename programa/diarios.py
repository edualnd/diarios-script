"""Baixa os diários de classe e lê os dias letivos de cada um."""
import os
import re

from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright
from pypdf import PdfReader

from navegador import BASE, MARGENS, fundo_branco, sessao

URL = BASE + "/diario/sala/{sala}/bimestre/{bim}/disciplina/{disc}/diario"
MARCADOR = "Diário de Classe"   # texto que só aparece na página do diário (logado)
MESES = ["JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO", "JULHO",
         "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]


# ---------------------------------------------------------------- download

def carregar(page, url):
    """Abre a página e espera o diário aparecer. Retorna True se carregou."""
    page.goto(url, wait_until="networkidle", timeout=60000)
    try:
        page.get_by_text(MARCADOR).first.wait_for(timeout=15000)
        page.get_by_text("Alunos").first.wait_for(timeout=15000)
        page.wait_for_load_state("networkidle")
        return True
    except PWTimeout:
        return False


def nome_sala(texto, sala_id):
    """Monta '1A' a partir de 'Série: 1° Ano' e 'Turma: A'."""
    serie = re.search(r"Série:\s*(\d+)\s*°", texto)
    turma = re.search(r"Turma:\s*(\w)", texto)
    if serie and turma:
        return f"{serie.group(1)}{turma.group(1)}"
    return f"sala_{sala_id}"


def baixar(bim, salas, disciplina, pasta):
    """Baixa o diário de cada sala (números do sistema) para `pasta`.
    Retorna {número_da_sala: nome ('1A'...)} das que deram certo."""
    salas = list(salas)
    os.makedirs(pasta, exist_ok=True)
    url = lambda s: URL.format(sala=s, bim=bim, disc=disciplina)  # noqa: E731

    baixadas = {}
    with sync_playwright() as p:
        ctx, page = sessao(p, url(salas[0]), carregar)
        for i, sala in enumerate(salas):
            print(f"Sala {sala}: ", end="", flush=True)
            try:
                if i > 0 and not carregar(page, url(sala)):
                    raise RuntimeError("o diário não abriu (sala não existe ou sem acesso?)")
                nome = nome_sala(page.inner_text("body"), sala)
                fundo_branco(page)
                page.pdf(path=os.path.join(pasta, f"{nome}.pdf"), format="A3",
                         print_background=True, margin=MARGENS)
                print(f"diário do {nome} baixado")
                baixadas[sala] = nome
            except Exception as e:
                print(f"ERRO - {e}")
        ctx.close()
    return baixadas


# ---------------------------------------------------------------- leitura

def _texto_pdf(caminho):
    """Texto da 1ª página do PDF mantendo o layout das colunas."""
    return PdfReader(caminho).pages[0].extract_text(extraction_mode="layout")


def _agrupar_por_mes(dias):
    """Separa a sequência de dias em meses: um novo mês começa quando o dia
    diminui (ex.: 31 -> 03) ou quando há um salto grande (ex.: 14/05 -> 27/07)."""
    grupos = [[dias[0]]]
    for anterior, atual in zip(dias, dias[1:]):
        if atual < anterior or atual - anterior > 10:
            grupos.append([atual])
        else:
            grupos[-1].append(atual)
    return grupos


def dias_letivos(caminho):
    """Lê o PDF do diário e retorna o conjunto de datas lançadas {(mês, dia), ...}."""
    nome = os.path.basename(caminho)
    linhas = _texto_pdf(caminho).splitlines()

    # Linha "Alunos  27  28  29 ..." traz os dias; a linha de meses fica acima dela.
    try:
        i = next(k for k, l in enumerate(linhas) if l.strip().startswith("Alunos"))
    except StopIteration:
        raise ValueError(f"{nome}: não achei a linha de dias no diário")
    dias = [int(x) for x in linhas[i].split()[1:] if x.isdigit()]
    if not dias:
        raise ValueError(f"{nome}: o diário não tem nenhum dia lançado")

    meses = []
    for linha in reversed(linhas[:i]):
        meses = [w.upper() for w in linha.split() if w.upper() in MESES]
        if meses:
            break

    grupos = _agrupar_por_mes(dias)
    if len(grupos) != len(meses):
        raise ValueError(f"{nome}: não consegui separar os dias por mês "
                         f"({len(meses)} meses no cabeçalho, {len(grupos)} grupos de dias)")
    return {(MESES.index(m) + 1, d) for m, g in zip(meses, grupos) for d in g}
