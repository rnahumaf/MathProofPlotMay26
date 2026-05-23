# AGENTS.md

Contrato operacional para agentes trabalhando neste repositorio.

## Prioridade

1. Leia este arquivo antes de alterar scripts, figuras ou documentacao.
2. Use `GUIDELINES.html` como referencia geral de manejo de repositorios,
   agentes e skills.
3. Use as skills locais em `SKILLS/` quando a tarefa tocar o fluxo descrito
   por elas.
4. Preserve alteracoes do usuario. Nunca reverta arquivos sem pedido explicito.

## Contexto do projeto

Este repositorio registra visualizacoes finitas ligadas ao problema de Erdos
sobre distancias unitarias e a construcao CM/ciclotomica inspirada na prova de
2026. A pasta principal de apresentacao e `final_proof_sequence/`; a figura
pequena didatica fica em `final_small_cm/`.

## Ambiente

Scripts Sage devem rodar no WSL Ubuntu com o ambiente Conda `sage`:

```bash
source ~/miniforge3/etc/profile.d/conda.sh
conda activate sage
python build_final_proof_sequence.py
```

Chamando a partir do PowerShell, use este padrao:

```powershell
wsl -e bash -lc "cd '/mnt/c/Users/rnahu/OneDrive/Docs pessoais/Documents/GitHub/MathProofPlotMay26'; source ~/miniforge3/etc/profile.d/conda.sh; conda activate sage; python build_final_proof_sequence.py"
```

`build_final_small_cm_plot.py` e `search_best_leq32_unit_graph.py` rodam em
Python comum, sem Sage.

## Arquivos gerados

- `final_proof_sequence/`: sequencia final alinhada ao Stage 16.
- `final_blueprint_symmetric_variations/`: galeria final padrao em estilo
  Blueprint, com variacoes simetricas da construcao Stage 16.
- `final_geometric_variations/`: variacoes visuais da mesma familia Stage 16.
- `final_small_cm/`: exemplo pequeno didatico.
- `best_leq32_search/` e `best_leq32_search_wide/`: busca booleana-ciclotomica
  para ate 32 pontos.
- `stage*_out*` e `stage16_*`: historico de tentativas e artefatos grandes.

CSV, PNG, PDF, SVG e ZIP estao sob Git LFS via `.gitattributes`.

## Gotchas criticos

- `conda activate sage` falha em WSL nao interativo se o script nao fizer antes
  `source ~/miniforge3/etc/profile.d/conda.sh`.
- O diretorio do repo contem espacos e acentos no caminho Windows; sempre use
  aspas no PowerShell e aspas simples no caminho `/mnt/c/...` dentro do WSL.
- Algumas saidas sao grandes. Antes de commitar novos artefatos, confira
  `git status --short` e avalie se o arquivo deve mesmo entrar no historico.
- O remoto GitHub ja existe como `origin`:
  `https://github.com/rnahumaf/MathProofPlotMay26.git`.
- O repo usa Git LFS. Antes de empurrar muitos artefatos, confirme que
  `git lfs status` nao mostra arquivos inesperados.

## Verificacao minima

- Para mudancas em scripts Python comuns, rode o script afetado quando o custo
  for razoavel.
- Para mudancas no pipeline Stage 16, rode pelo WSL/Sage ou documente que o
  check ficou pendente.
- Para mudancas so de documentacao, rode ao menos:

```powershell
git diff --check
git status --short
```
