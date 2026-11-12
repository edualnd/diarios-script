#!/bin/bash
# Instala as dependências Python SEM internet, a partir da pasta "dependencias/".
# Rode uma vez no computador novo: ./"Instalar dependencias.sh"
cd "$(dirname "$0")" || exit 1
DEP="$PWD/dependencias"

PY=python3
[ -x "$HOME/.pyenv/shims/python3" ] && PY="$HOME/.pyenv/shims/python3"

# Se o computador não tiver o pip, usa o pip que está na pasta.
if "$PY" -m pip --version >/dev/null 2>&1; then
    PIP=("$PY" -m pip)
else
    PIP=("$PY" "$(ls "$DEP"/pip-*.whl | head -1)/pip")
fi

OPCOES=(install --no-index --find-links="$DEP" -r requirements.txt)
"${PIP[@]}" "${OPCOES[@]}" --user ||
"${PIP[@]}" "${OPCOES[@]}" --user --break-system-packages ||
    { echo "ERRO ao instalar pacotes Python."; exit 1; }

echo
"$PY" -c "import playwright, pypdf, reportlab" && echo "Pacotes Python instalados!"
