# Diários de Classe

Programa que, para cada sala:

1. baixa o diário de classe do Gestão Escolar;
2. confere se os dias letivos lançados batem com o calendário oficial;
3. nas salas que estão certas, baixa o documento de **Habilidades** de cada professor;
4. junta tudo em um PDF só: diário, Polivalente, Inglês, Educação Física, Relações Étnico-Raciais e Educação Financeira.

## Como usar

1. Dê **dois cliques** em **`Abrir programa.sh`**.
   Se o arquivo abrir num editor de texto em vez de rodar, clique nele com o botão direito e escolha **"Executar como um programa"**.
2. Na janela:
   - escolha o **bimestre**;
   - confira os **números das salas**: é o número que aparece no endereço da sala no sistema, por exemplo `.../atividade/sala/780/diario`;
   - clique em **Escolher dias letivos…**, informe o primeiro e o último dia do bimestre, clique em **Marcar segunda a sexta** e depois clique nos feriados para desmarcar. Os dias ficam salvos para a próxima vez.
3. Clique em **Começar** e espere. Na primeira vez o Chrome vai abrir para você fazer o login no Gestão Escolar.
4. No fim, o programa mostra um resumo e pergunta se você quer abrir a pasta com os resultados.

## Onde ficam os arquivos

```
Resultados/
  3º Bimestre 2026/
    Diários prontos/                 ← PDFs finais, um por sala
    Relatório de dias letivos.pdf    ← quais salas têm dias faltando ou sobrando
    Arquivos baixados/               ← diários e habilidades soltos
```

Para não guardar os arquivos soltos, marque na janela a opção **"No final, apagar os diários e habilidades baixados"**. Aí ficam só os diários prontos e o relatório.

A pasta `programa/` tem o código e as configurações. Não precisa mexer nela.

## Instalação (só uma vez, em um computador novo)

Precisa do Google Chrome instalado. No terminal, dentro desta pasta:

```bash
sudo apt install python3-tk poppler-utils
pip install -r requirements.txt
```
