"""Baixa o documento de Habilidades de todos os professores de cada sala.

Faz o mesmo que: Documentos > Habilidades > escolher bimestre e professor > Continuar,
repetido para cada professor. Em vez de clicar, monta direto o endereço que o
botão "Continuar" abriria.
"""
import os
import re
import shutil

from playwright.sync_api import Error as PWError
from playwright.sync_api import TimeoutError as PWTimeout
from playwright.sync_api import sync_playwright

from navegador import BASE, MARGENS, fundo_branco, sessao

URL_SALA = BASE + "/atividade/sala/{sala}/diario"
URL_DOC = BASE + "/documentos/sala/{sala}/bimestre/{bim}/professor/{prof}/disciplina/{disc}/habilidades"


def limpar(texto):
    """Deixa o texto seguro para nome de arquivo."""
    texto = re.sub(r"\s+", " ", texto).strip()
    return re.sub(r'[\\/:*?"<>|]', "-", texto)


def _sala_carregou(page, url):
    page.goto(url, wait_until="networkidle", timeout=60000)
    try:
        page.locator("#professores").wait_for(state="attached", timeout=15000)
        return True
    except PWTimeout:
        return False


def _professores(page):
    """Opções do select 'Selecione o professor' do modal Habilidades."""
    return page.eval_on_selector_all(
        "#professores option",
        """ops => ops.filter(o => o.value).map(o => ({
                prof: o.value, disc: o.dataset.disciplina, nome: o.textContent}))""")


def _salvar(page, url, destino):
    """Abre o link do documento. Se o site mandar um arquivo, salva ele;
    se abrir uma página, gera o PDF dela."""
    downloads = []

    def ao_baixar(download):
        downloads.append(download)

    page.on("download", ao_baixar)
    try:
        page.goto(url, wait_until="networkidle", timeout=90000)
    except PWError as e:
        if "Download is starting" not in str(e) and "ERR_ABORTED" not in str(e):
            raise
        page.wait_for_timeout(2000)
    finally:
        page.remove_listener("download", ao_baixar)
    if downloads:
        d = downloads[0]
        d.save_as(destino + (os.path.splitext(d.suggested_filename)[1] or ".pdf"))
        return
    if "/login" in page.url:
        raise RuntimeError("o login expirou")
    fundo_branco(page)
    page.pdf(path=destino + ".pdf", format="A4", print_background=True, margin=MARGENS)


def baixar(bim, salas, pasta):
    """`salas`: {número_da_sala: nome ('1A'...)}. Salva em pasta/<nome>/.
    Retorna o conjunto de nomes de sala em que todos os documentos deram certo."""
    completas = set()
    if not salas:
        return completas
    primeira = next(iter(salas))

    with sync_playwright() as p:
        ctx, page = sessao(p, URL_SALA.format(sala=primeira), _sala_carregou)
        for i, (sala, nome) in enumerate(salas.items()):
            if i > 0 and not _sala_carregou(page, URL_SALA.format(sala=sala)):
                print(f"{nome}: ERRO - a página da sala não abriu")
                continue
            professores = _professores(page)
            print(f"{nome}: {len(professores)} professor(es)")
            pasta_sala = os.path.join(pasta, nome)
            shutil.rmtree(pasta_sala, ignore_errors=True)   # tira arquivos de rodadas antigas
            os.makedirs(pasta_sala)

            tudo_certo = bool(professores)
            for pr in professores:
                rotulo = limpar(pr["nome"])
                print(f"   {rotulo}: ", end="", flush=True)
                try:
                    _salvar(page, URL_DOC.format(sala=sala, bim=bim, prof=pr["prof"],
                                                 disc=pr["disc"]),
                            os.path.join(pasta_sala, rotulo))
                    print("ok")
                except Exception as e:
                    print(f"ERRO - {e}")
                    tudo_certo = False
            if tudo_certo:
                completas.add(nome)
        ctx.close()
    return completas
