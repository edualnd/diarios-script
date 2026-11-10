#!/usr/bin/env python3
"""Extrai os dias letivos dos PDFs de diário de classe e gera um JSON por sala.

Uso:
    python3 extrair_dias_letivos.py [PASTA_PDFS] [ARQUIVO_SAIDA]

Padrões: PASTA_PDFS = Diarios, ARQUIVO_SAIDA = dias-letivos-salas.json
Requer o programa pdftotext (pacote poppler-utils).
"""
import glob
import json
import os
import re
import subprocess
import sys

MESES = ["JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO", "JULHO",
         "AGOSTO", "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]


def texto_pdf(caminho):
    """Retorna o texto da 1ª página do PDF mantendo o layout das colunas."""
    r = subprocess.run(["pdftotext", "-layout", "-f", "1", "-l", "1", caminho, "-"],
                       capture_output=True, text=True, check=True)
    return r.stdout


def campo(padrao, texto, nome, arquivo):
    m = re.search(padrao, texto)
    if not m:
        raise ValueError(f"{arquivo}: campo '{nome}' não encontrado")
    return m.group(1)


def agrupar_por_mes(dias):
    """Separa a sequência de dias em meses: um novo mês começa quando o dia
    diminui (ex.: 31 -> 03) ou quando há um salto grande (ex.: 14/05 -> 27/07)."""
    grupos = [[dias[0]]]
    for anterior, atual in zip(dias, dias[1:]):
        if atual < anterior or atual - anterior > 10:
            grupos.append([atual])
        else:
            grupos[-1].append(atual)
    return grupos


def processar(caminho):
    arquivo = os.path.basename(caminho)
    texto = texto_pdf(caminho)
    linhas = texto.splitlines()

    serie = campo(r"Série:\s*(\d+)\s*°", texto, "Série", arquivo)
    turma = campo(r"Turma:\s*(\w)", texto, "Turma", arquivo)
    periodo = campo(r"Período Letivo:\s*(\d+\s*°\s*Bimestre)", texto, "Período", arquivo)
    ano = campo(r"Ano Letivo:\s*(\d{4})", texto, "Ano", arquivo)

    # Linha "Alunos  27  28  29 ..." traz os dias; a linha de meses fica acima dela.
    try:
        i = next(k for k, l in enumerate(linhas) if l.strip().startswith("Alunos"))
    except StopIteration:
        raise ValueError(f"{arquivo}: linha de dias ('Alunos') não encontrada")
    dias = [int(x) for x in linhas[i].split()[1:] if x.isdigit()]

    meses = []
    for l in reversed(linhas[:i]):
        meses = [w.upper() for w in l.split() if w.upper() in MESES]
        if meses:
            break

    grupos = agrupar_por_mes(dias)
    if len(grupos) != len(meses):
        raise ValueError(f"{arquivo}: {len(meses)} meses no cabeçalho ({meses}) "
                         f"mas {len(grupos)} grupos de dias ({grupos})")

    return {
        "sala": f"{serie}{turma}",
        "serie": f"{serie}º Ano",
        "turma": turma,
        "periodo": periodo,
        "ano": int(ano),
        "meses": [{"mes": m, "dias": g, "total": len(g)} for m, g in zip(meses, grupos)],
        "total_dias_letivos": len(dias),
    }


def main():
    pasta = sys.argv[1] if len(sys.argv) > 1 else "Diarios"
    saida = sys.argv[2] if len(sys.argv) > 2 else "dias-letivos-salas.json"

    pdfs = sorted(glob.glob(os.path.join(pasta, "*.pdf")))
    if not pdfs:
        sys.exit(f"Nenhum PDF encontrado em '{pasta}'")

    salas, erros = [], 0
    for pdf in pdfs:
        try:
            salas.append(processar(pdf))
        except Exception as e:
            erros += 1
            print(f"ERRO: {e}", file=sys.stderr)

    with open(saida, "w", encoding="utf-8") as f:
        json.dump(salas, f, ensure_ascii=False, indent=2)

    for s in salas:
        resumo = ", ".join(f"{m['mes']}: {m['total']}" for m in s["meses"])
        print(f"{s['sala']}: {resumo} | total {s['total_dias_letivos']}")
    print(f"\n{len(salas)} sala(s) salvas em {saida}" + (f" ({erros} com erro)" if erros else ""))


if __name__ == "__main__":
    main()
