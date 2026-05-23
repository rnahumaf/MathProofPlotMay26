# Interactive Graph Styler

Aplicacao estatica para ajustar visualmente os graficos finais sem rerodar
Sage. Ela abre no preset Blueprint por padrao e embute um snapshot em
`graph_data.js`.

## Como usar

Abra no navegador:

```text
interactive_graph_styler/index.html
```

Controles disponiveis:

- filtro de fonte dos datasets embutidos;
- escolha do dataset/seletor;
- carregamento manual de um par `points.csv` + `edges.csv`;
- preset visual;
- cor de fundo por sliders HSL e intensidade de preto;
- largura e alpha das linhas;
- cor customizada de linhas por sliders HSL e intensidade de preto;
- reforco de densidade em interseccoes;
- tamanho, alpha e esquema de cor dos pontos;
- cor customizada de pontos por sliders HSL e intensidade de preto;
- escala de exportacao;
- download do PNG renderizado.

Ao mover os sliders `Hue`, `Saturation` ou `Lightness` de linhas ou pontos, o
modo correspondente muda automaticamente para `Custom HSL`. O slider
`Black intensity` tambem funciona sobre as paletas prontas.

## Regenerar os dados

Depois de atualizar `final_blueprint_symmetric_variations/`,
`final_geometric_variations/` ou `symmetric_variation_search/`, rode:

```powershell
python .\interactive_graph_styler\build_data.py
```

Isso recria `interactive_graph_styler/graph_data.js`.

## CSVs customizados

O carregamento manual espera:

- pontos com colunas `id`, `x`, `y` e opcionalmente `max_embedding_abs`;
- arestas com colunas `from_id`, `to_id` e opcionalmente `changed_generator`.

Tambem aceita aliases comuns como `fromId`, `toId`, `source`, `target`,
`generator`, `re`, `im`, `real` e `imag`.
