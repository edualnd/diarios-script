#!/bin/bash
# Abre o programa dos Diários de Classe.
# Dê dois cliques neste arquivo (ou rode no terminal: ./"Abrir programa.sh").
cd "$(dirname "$0")" || exit 1

for py in "$HOME/.pyenv/shims/python3" python3 /usr/bin/python3; do
    if command -v "$py" >/dev/null 2>&1 &&
       "$py" -c "import tkinter, playwright, pypdf, reportlab" >/dev/null 2>&1; then
        exec "$py" programa/app.py
    fi
done

MSG="Faltam programas para rodar os Diários.

Peça para alguém rodar no terminal, dentro desta pasta:
  pip install -r requirements.txt
  sudo apt install python3-tk poppler-utils"
zenity --error --title="Diários de Classe" --text="$MSG" 2>/dev/null || echo "$MSG"
exit 1
