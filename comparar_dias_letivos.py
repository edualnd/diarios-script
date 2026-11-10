#!/usr/bin/env python3
"""Compara os dias letivos de cada sala com o calendário oficial e gera um PDF.

Uso:
    python3 comparar_dias_letivos.py [CALENDARIO] [SALAS] [PDF_SAIDA]

Padrões:
    CALENDARIO = dias-letivos.json         (calendário oficial do bimestre)
    SALAS      = dias-letivos-salas.json   (gerado por extrair_dias_letivos.py)
    PDF_SAIDA  = comparacao-dias-letivos.pdf

- Faltando: dia que está no calendário mas não foi lançado no diário da sala.
- Sobrando: dia lançado no diário da sala que não está no calendário.
- OK: sala com os dias idênticos ao calendário.
Requer: reportlab (pip install reportlab).
"""
import datetime
import json
import sys

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

MESES = ["JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO", "JULHO",
         "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]
SEMANA = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]


def carregar(caminho):
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def conjunto_datas(meses):
    """Converte [{'mes': 'AGOSTO', 'dias': [3, 4]}] em {(8, 3), (8, 4)}."""
    return {(MESES.index(m["mes"].upper()) + 1, d) for m in meses for d in m["dias"]}


def dia_semana(ano, mes, dia):
    try:
        return SEMANA[datetime.date(ano, mes, dia).weekday()]
    except ValueError:
        return "data inválida"


def linhas_por_mes(datas, ano):
    """Retorna uma linha por mês: 'Agosto: 06 (qui), 07 (sex)'."""
    por_mes = {}
    for mes, dia in sorted(datas):
        por_mes.setdefault(mes, []).append(f"{dia:02d} ({dia_semana(ano, mes, dia)})")
    return [f"{MESES[m - 1].capitalize()}: {', '.join(d)}" for m, d in por_mes.items()]


def main():
    cal_path = sys.argv[1] if len(sys.argv) > 1 else "dias-letivos.json"
    salas_path = sys.argv[2] if len(sys.argv) > 2 else "dias-letivos-salas.json"
    saida = sys.argv[3] if len(sys.argv) > 3 else "comparacao-dias-letivos.pdf"

    oficial = conjunto_datas(carregar(cal_path)["meses"])
    salas = carregar(salas_path)

    # Layout compacto: salas em uma grade de 2 colunas para caber em 1 folha A4.
    estilos = getSampleStyleSheet()
    titulo = ParagraphStyle("t", parent=estilos["Title"], fontSize=14, spaceAfter=6)
    sala_st = ParagraphStyle("s", parent=estilos["Normal"], fontName="Helvetica-Bold",
                             fontSize=12, leading=15, spaceAfter=3)
    topico = ParagraphStyle("tp", parent=estilos["Normal"], fontSize=9.5, leading=13,
                            spaceBefore=2)
    item = ParagraphStyle("i", parent=estilos["Normal"], fontSize=9.5, leading=13,
                          leftIndent=0.35 * cm)

    margem = 1.2 * cm
    doc = SimpleDocTemplate(saida, pagesize=A4, leftMargin=margem, rightMargin=margem,
                            topMargin=margem, bottomMargin=margem,
                            title="Comparação de dias letivos")
    el = [Paragraph("Comparação de Dias Letivos por Sala", titulo)]

    celulas = []
    for s in salas:
        lancados = conjunto_datas(s["meses"])
        faltando = oficial - lancados
        sobrando = lancados - oficial

        if not faltando and not sobrando:
            bloco = [Paragraph(f"Sala {s['sala']} — OK", sala_st)]
            status = "OK"
        else:
            bloco = [Paragraph(f"Sala {s['sala']}", sala_st)]
            for nome, datas in (("Faltando", faltando), ("Sobrando", sobrando)):
                bloco.append(Paragraph(f"<b>{nome}:</b>", topico))
                for linha in linhas_por_mes(datas, s["ano"]) or ["—"]:
                    bloco.append(Paragraph(linha, item))
            status = f"faltando {len(faltando)}, sobrando {len(sobrando)}"
        celulas.append(bloco)
        print(f"{s['sala']}: {status}")

    colunas = 2
    if len(celulas) % colunas:
        celulas += [""] * (colunas - len(celulas) % colunas)
    grade = [celulas[i:i + colunas] for i in range(0, len(celulas), colunas)]
    largura = (A4[0] - 2 * margem) / colunas
    t = Table(grade, colWidths=[largura] * colunas)
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#BBBBBB")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    el.append(t)

    doc.build(el)
    print(f"\nPDF gerado: {saida}")


if __name__ == "__main__":
    main()
