# Small Unit Graph Search

Use esta skill quando a tarefa envolver `search_best_leq32_unit_graph.py`,
`best_leq32_search/`, `best_leq32_search_wide/` ou o exercicio de achar muitas
distancias unitarias com no maximo 32 pontos.

## Objetivo

Explorar uma familia booleana-ciclotomica pequena:

```text
P(epsilon) = sum_j (epsilon_j - 1/2) u_j, epsilon_j in {0,1}
```

onde os `u_j` sao raizes da unidade/projecoes de norma 1. O foco aqui e
comparativo e visual; nao e uma prova de otimalidade global para `n <= 32`.

## Comando principal

```powershell
python .\search_best_leq32_unit_graph.py
```

Saidas principais:

- `best_leq32_search/best_leq32_cm_boolean.png`
- `best_leq32_search/best_points.csv`
- `best_leq32_search/best_unit_edges.csv`
- `best_leq32_search/search_summary.csv`

## Resultado de referencia

A busca padrao encontrou:

- `K = Q(zeta_18)`;
- expoentes `0 1 2 3 4`;
- 32 pontos;
- 96 pares a distancia 1.

## Gotchas

- O resultado `96` e o melhor encontrado nesta familia, nao um maximo absoluto
  conhecido para qualquer configuracao plana com 32 pontos.
- Fixar o expoente `0` remove simetria rotacional e reduz busca redundante.
- Ao ampliar a busca, escreva saidas em nova pasta para preservar comparacao
  com `best_leq32_search/`.

