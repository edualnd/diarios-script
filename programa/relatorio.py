"""Compara os dias letivos de cada sala com o calendário oficial e gera um PDF.

- Faltando: dia que está no calendário mas não foi lançado no diário da sala.
- Sobrando: dia lançado no diário da sala que não está no calendário.
- OK: sala com os dias idênticos ao calendário.
"""
import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho",
         "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
SEMANA = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


def _linhas_por_mes(datas, ano):
    """Uma linha por mês: 'Agosto: 06 (qui), 07 (sex)'."""
    por_mes = {}
    for mes, dia in sorted(datas):
        try:
            sem = SEMANA[datetime.date(ano, mes, dia).weekday()]
        except ValueError:
            sem = "data inválida"
        por_mes.setdefault(mes, []).append(f"{dia:02d} ({sem})")
    return [f"{MESES[m - 1]}: {', '.join(d)}" for m, d in por_mes.items()]


def comparar(oficial, salas, ano, titulo, saida):
    """`oficial`: {(mês, dia)} do calendário. `salas`: {'1A': {(mês, dia)}, ...}.
    Gera o PDF em `saida` e retorna {'1A': True se OK, ...}."""
    estilos = getSampleStyleSheet()
    st_titulo = ParagraphStyle("t", parent=estilos["Title"], fontSize=14, spaceAfter=6)
    st_sala = ParagraphStyle("s", parent=estilos["Normal"], fontName="Helvetica-Bold",
                             fontSize=12, leading=15, spaceAfter=3)
    st_topico = ParagraphStyle("tp", parent=estilos["Normal"], fontSize=9.5, leading=13,
                               spaceBefore=2)
    st_item = ParagraphStyle("i", parent=estilos["Normal"], fontSize=9.5, leading=13,
                             leftIndent=0.35 * cm)

    margem = 1.2 * cm
    doc = SimpleDocTemplate(saida, pagesize=A4, leftMargin=margem, rightMargin=margem,
                            topMargin=margem, bottomMargin=margem, title=titulo)
    elementos = [Paragraph(titulo, st_titulo)]

    resultado, celulas = {}, []
    for sala in sorted(salas):
        lancados = salas[sala]
        faltando, sobrando = oficial - lancados, lancados - oficial
        resultado[sala] = not faltando and not sobrando

        if resultado[sala]:
            bloco = [Paragraph(f"Sala {sala} — OK", st_sala)]
            print(f"{sala}: OK")
        else:
            bloco = [Paragraph(f"Sala {sala}", st_sala)]
            for nome, datas in (("Faltando", faltando), ("Sobrando", sobrando)):
                bloco.append(Paragraph(f"<b>{nome}:</b>", st_topico))
                for linha in _linhas_por_mes(datas, ano) or ["—"]:
                    bloco.append(Paragraph(linha, st_item))
            print(f"{sala}: {len(faltando)} dia(s) faltando, {len(sobrando)} sobrando")
        celulas.append(bloco)

    # salas em uma grade de 2 colunas para caber em poucas folhas
    if len(celulas) % 2:
        celulas.append("")
    grade = [celulas[i:i + 2] for i in range(0, len(celulas), 2)]
    largura = (A4[0] - 2 * margem) / 2
    tabela = Table(grade, colWidths=[largura] * 2)
    tabela.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BBBBBB")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    elementos.append(tabela)
    doc.build(elementos)
    return resultado
