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


# Usuário e senha do proxy, (usuario, senha). A janela preenche ao clicar em
# "Começar"; fica só na memória, nunca é salvo em arquivo.
credenciais_proxy = None


def abrir(p, headless):
    proxy = proxy_do_windows()
    if proxy and credenciais_proxy:
        proxy["username"], proxy["password"] = credenciais_proxy
    ctx = p.chromium.launch_persistent_context(
        PERFIL, channel="chrome", headless=headless, viewport={"width": 1600, "height": 1000},
        proxy=proxy)
    # A página do diário chama window.print() sozinha ao carregar. Essa impressão
    # fica "aberta" e o PDF do programa falha com "Page is already being printed".
    ctx.add_init_script("window.print = () => {};")
    return ctx


def proxy_do_windows():
    """Proxy configurado no Windows (o mesmo que o Chrome comum usa), no formato
    do Playwright. Passando ele ao Chrome do programa junto com usuário e senha,
    todas as páginas e downloads já saem autenticados, sem pedir login a cada
    janela. Fora do Windows, ou sem proxy, retorna None."""
    if os.name != "nt":
        return None
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings") as k:
            if not winreg.QueryValueEx(k, "ProxyEnable")[0]:
                return None
            servidor = winreg.QueryValueEx(k, "ProxyServer")[0]
            try:
                excecoes = winreg.QueryValueEx(k, "ProxyOverride")[0]
            except OSError:
                excecoes = ""
    except OSError:
        return None
    if "=" in servidor:   # formato "http=host:porta;https=host:porta"
        partes = dict(p.split("=", 1) for p in servidor.split(";") if "=" in p)
        servidor = partes.get("https") or partes.get("http") or next(iter(partes.values()), "")
    if not servidor:
        return None
    if "://" not in servidor:
        servidor = "http://" + servidor
    excecoes = [e.strip() for e in excecoes.split(";") if e.strip() and e.strip() != "<local>"]
    return {"server": servidor, "bypass": ",".join(excecoes) or None}


def _carregou(pagina_ok, page, url):
    """Chama `pagina_ok`, mas trata "o site não respondeu" como "não carregou"."""
    try:
        return pagina_ok(page, url), True
    except Exception as e:
        if "Timeout" not in str(e) and "net::" not in str(e):
            raise
        print(f"O site não respondeu: {str(e).splitlines()[0]}")
        return False, False


def _senha_proxy_errada():
    global credenciais_proxy
    credenciais_proxy = None          # pede de novo no próximo "Começar"
    return Parar("O proxy da rede recusou o usuário ou a senha.\n\n"
                 "Clique em Começar de novo para digitar outra vez.")


def ir(page, url, timeout=70000):
    """Abre a página sem exigir que a rede fique parada: em redes com proxy
    algum recurso externo (estatística, fontes) pode ficar travado para sempre."""
    recusou = []

    def ver_resposta(r):
        if r.status == 407:           # 407 = o proxy pediu login e não aceitou
            recusou.append(r.url)

    page.on("response", ver_resposta)
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=timeout)
    except Exception as e:
        if recusou or "PROXY_AUTH" in str(e):
            raise _senha_proxy_errada()
        raise
    finally:
        page.remove_listener("response", ver_resposta)
    if recusou:
        raise _senha_proxy_errada()
    rede_parada(page)


def rede_parada(page, timeout=10000):
    """Espera a página parar de carregar coisas, mas desiste depois de `timeout`."""
    try:
        page.wait_for_load_state("networkidle", timeout=timeout)
    except Exception:
        pass


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
    ok, _ = _carregou(pagina_ok, page, url)
    if ok:
        return ctx, page
    ctx.close()

    print("\nÉ preciso entrar no sistema. O Chrome vai abrir: faça o login nele.")
    ctx = abrir(p, headless=False)
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    try:
        pg.goto(url, wait_until="commit", timeout=60000)   # a pessoa vê a página carregar
    except Exception as e:
        print(f"O site não abriu no Chrome: {str(e).splitlines()[0]}")
    aguardar_login()
    ctx.close()

    ctx = abrir(p, headless=True)
    page = ctx.new_page()
    ok, respondeu = _carregou(pagina_ok, page, url)
    if ok:
        print("Login feito.\n")
        return ctx, page
    ctx.close()
    if not respondeu:
        raise Parar("O Chrome aberto pelo programa não conseguiu acessar o site.\n\n"
                    "Provavelmente o proxy da rede está bloqueando. Confira se o site "
                    "abriu na janela do Chrome que apareceu para o login.")
    raise Parar("Não foi possível entrar no sistema.\n\n"
                "Confira se o login deu certo e se os números das salas estão corretos.")
