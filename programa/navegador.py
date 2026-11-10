"""Coisas comuns de acesso ao site do Gestão Escolar (Chrome, login, PDF)."""
import os

BASE = "https://gestao-escolar.educacao.caraguatatuba.sp.gov.br"
PASTA_PROGRAMA = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(PASTA_PROGRAMA)
PERFIL = os.path.join(PASTA_PROGRAMA, ".perfil-chrome")   # login fica salvo aqui

MARGENS = {"top": "1cm", "bottom": "1cm", "left": "0.8cm", "right": "0.8cm"}


class Parar(Exception):
    """Erro que interrompe o processo, com uma mensagem para mostrar ao usuário."""


def _aguardar_login_terminal():
    input("Depois de entrar no sistema, aperte Enter aqui para continuar... ")


# A janela do programa troca isto por uma caixa de diálogo.
aguardar_login = _aguardar_login_terminal


def abrir(p, headless):
    return p.chromium.launch_persistent_context(
        PERFIL, channel="chrome", headless=headless, viewport={"width": 1600, "height": 1000})


def fundo_branco(page):
    """O site tem fundo cinza em volta do documento; no PDF ele aparece como um
    bloco cinza no fim das páginas. Deixa tudo branco antes de imprimir."""
    page.add_style_tag(content="""
        html, body, body > *, main, #wrapper, #content-wrapper, #content, .container,
        .container-fluid { background: #fff !important; background-image: none !important;
                           box-shadow: none !important; }
    """)


def sessao(p, url, pagina_ok):
    """Abre o Chrome invisível já logado. Se o login tiver expirado, abre o Chrome
    visível para a pessoa entrar e tenta de novo. `pagina_ok(page, url)` diz se carregou."""
    ctx = abrir(p, headless=True)        # gerar PDF só funciona no modo invisível
    page = ctx.new_page()
    if pagina_ok(page, url):
        return ctx, page
    ctx.close()

    print("\nÉ preciso entrar no sistema. O Chrome vai abrir: faça o login nele.")
    ctx = abrir(p, headless=False)
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    pg.goto(url)
    aguardar_login()
    ctx.close()

    ctx = abrir(p, headless=True)
    page = ctx.new_page()
    if pagina_ok(page, url):
        print("Login feito.\n")
        return ctx, page
    ctx.close()
    raise Parar("Não foi possível entrar no sistema.\n\n"
                "Confira se o login deu certo e se os números das salas estão corretos.")
