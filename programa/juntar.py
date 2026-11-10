"""Junta, para cada sala, o diário + os documentos de Habilidades em um único PDF.

Ordem: diário, Polivalente, Inglês, Educação Física,
Educação para as Relações Étnico-Raciais, Educação Financeira.
"""
import os
import unicodedata

from pypdf import PdfWriter

# (nome mostrado, palavra que identifica a disciplina no nome do arquivo)
ORDEM = [
    ("Polivalente", "polivalente"),
    ("Inglês", "ingles"),
    ("Educação Física", "fisica"),
    ("Relações Étnico-Raciais", "etnico"),
    ("Educação Financeira", "financeira"),
]


def _normalizar(texto):
    """Minúsculas, sem acento e com '_' virando espaço."""
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.lower().replace("_", " ")


def _disciplina(arquivo):
    """'FULANA - Ed_Física.pdf' -> 'ed fisica'."""
    return _normalizar(os.path.splitext(arquivo)[0].rsplit(" - ", 1)[-1])


def juntar(salas, pasta_diarios, pasta_habilidades, saida):
    """Gera saida/<sala>.pdf para cada nome de sala em `salas`. Retorna as que foram geradas."""
    os.makedirs(saida, exist_ok=True)
    feitas = []
    for sala in sorted(salas):
        partes, faltando = [], []

        diario = os.path.join(pasta_diarios, f"{sala}.pdf")
        if os.path.exists(diario):
            partes.append(diario)
        else:
            faltando.append("Diário")

        pasta_sala = os.path.join(pasta_habilidades, sala)
        arquivos = sorted(a for a in os.listdir(pasta_sala) if a.lower().endswith(".pdf")) \
            if os.path.isdir(pasta_sala) else []
        usados = set()
        for rotulo, chave in ORDEM:
            achados = [a for a in arquivos if chave in _disciplina(a)]
            if not achados:
                faltando.append(rotulo)
            for a in achados:
                partes.append(os.path.join(pasta_sala, a))
                usados.add(a)

        if not partes:
            print(f"{sala}: nada para juntar")
            continue
        writer = PdfWriter()
        for arq in partes:
            writer.append(arq)
        with open(os.path.join(saida, f"{sala}.pdf"), "wb") as f:
            writer.write(f)
        writer.close()
        feitas.append(sala)

        print(f"{sala}: pronto")
        if faltando:
            print(f"   faltando: {', '.join(faltando)}")
        sobras = sorted(set(arquivos) - usados)
        if sobras:
            print(f"   não incluídos (disciplina fora da lista): {', '.join(sobras)}")
    return feitas
