# Sage Proof Pipeline

Use esta skill quando a tarefa envolver `stage*_*.py`,
`build_final_proof_sequence.py`, `final_proof_sequence/` ou a reproducao
finita da construcao CM/Stage 16.

## Objetivo

Manter uma sequencia visual fiel aos ingredientes da prova:

1. campo ciclotomico/CM, atualmente `Q(zeta_24)`;
2. primos split;
3. pares de ideais conjugados;
4. fibra de classe;
5. razoes principais;
6. translacoes `u = alpha / c(alpha)` com `u*c(u)=1`;
7. corte por polidisco centrado;
8. projecao para uma coordenada complexa.

## Comando principal

No WSL Ubuntu:

```bash
cd "/mnt/c/Users/rnahu/OneDrive/Docs pessoais/Documents/GitHub/MathProofPlotMay26"
source ~/miniforge3/etc/profile.d/conda.sh
conda activate sage
python build_final_proof_sequence.py
```

No PowerShell:

```powershell
wsl -e bash -lc "cd '/mnt/c/Users/rnahu/OneDrive/Docs pessoais/Documents/GitHub/MathProofPlotMay26'; source ~/miniforge3/etc/profile.d/conda.sh; conda activate sage; python build_final_proof_sequence.py"
```

## Saidas esperadas

`final_proof_sequence/manifest.csv` deve conter a sequencia crescente. No
ultimo resultado conhecido:

- passo `04`: melhor equilibrio visual;
- passo `06`: melhor quantitativo, com 15.844 pontos e 108.216 pares unitarios.

`final_geometric_variations/manifest.csv` deve conter variacoes visuais com o
mesmo nucleo aritmetico. Gere com:

```bash
python build_final_geometric_variations.py
```

## Gotchas

- Nao rode scripts Sage diretamente no PowerShell.
- Nao use apenas `conda activate sage` em WSL nao interativo; carregue antes
  `~/miniforge3/etc/profile.d/conda.sh`.
- Evite mudar parametros globais sem registrar a nova justificativa no
  `README.md` ou em `final_proof_sequence/README.md`.
- A contagem de pares depende de tolerancias numericas na projecao; preserve a
  diferenca entre verificacao algebraica no Sage e visualizacao plana.
