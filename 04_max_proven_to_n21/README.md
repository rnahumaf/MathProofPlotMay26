# Max Proven To n=21

Comparacao com os maximos exatos publicamente conhecidos ate `n = 21` e buscas
pequenas auxiliares.

## Conteudo

- `square_method_comparison/`: grafico e tabela comparando grade simples,
  OpenAI/Stage 16, Erdos classico, UCCS e maximo provado conhecido.
- `build_square_method_comparison.py`: recria a tabela e o grafico.
- `search_best_leq32_unit_graph.py`: busca booleana-ciclotomica pequena.
- `best_leq32_search/` e `best_leq32_search_wide/`: artefatos da busca pequena.

## Reproducao

```powershell
cd "C:\Users\rnahu\OneDrive\Docs pessoais\Documents\GitHub\unit-distance-problem\04_max_proven_to_n21"
python .\build_square_method_comparison.py
python .\search_best_leq32_unit_graph.py
```
