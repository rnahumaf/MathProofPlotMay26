# MathProofPlotMay26

Este repositorio e um caderno visual para estudar a melhoria de 2026 no
problema de Erdos sobre distancias unitarias no plano. O objetivo aqui nao e
reproduzir a prova assintotica completa do zero. O objetivo e registrar uma
evolucao de analogos finitos que tornam o mecanismo visivel:

1. construir muitos elementos algebricos cuja projecao tem comprimento 1;
2. usa-los como translacoes entre pontos projetados;
3. cortar uma regiao finita;
4. comparar a quantidade de pares unitarios com uma grade de mesmo tamanho.

Referencia: Will Sawin, *An explicit lower bound for the unit distance problem*,
arXiv:2605.20579v1, 20 May 2026:
https://arxiv.org/html/2605.20579v1

## Orientacao para agentes e manutencao

- `GUIDELINES.html`: copia local das guidelines gerais usadas em outros
  repositorios para agentes, skills, documentacao e interfaces.
- `AGENTS.md`: contrato operacional especifico deste repositorio.
- `SKILLS/`: memoria curta e acionavel para gotchas e fluxos recorrentes,
  incluindo Sage/WSL, busca pequena `n <= 32` e Git/LFS.

## Evolucao das tentativas

A maior parte dos scripts de estagio foi escrita para SageMath e deve ser
executada no WSL com um ambiente Sage disponivel. O grafico final pequeno e a
excecao: ele precisa apenas de Python comum com `numpy` e `Pillow`.

| Estagio | Arquivos | Papel |
| --- | --- | --- |
| Inicio toy | `unit_distance_projection_vs_grid.py` | Projeta um cubo booleano por vetores unitarios escolhidos. Serve para enxergar a geometria antes da aritmetica pesada. |
| Stage 5 | `stage5_sage_exact_cyclotomic.py`, `stage5_out_m24/` | Usa dados ciclotomicos e deltas unitarios exatos em um pequeno campo CM. |
| Stages 6-10 | `stage6_*` ate `stage10_*` | Explora quocientes CM de norma 1, fibras de mesma norma relativa, deduplicacao e varreduras de escala. |
| Stages 11-14 | `stage11_*` ate `stage14_*` | Aproxima os ingredientes de primos split, fibras tipo ideal e cortes por polidisco centrado. |
| Stage 16 | `stage16_class_fiber_cm*.py`, saidas `stage16_*` | Motor finito mais alinhado com a prova: ideais primos split em `Q(zeta_m)`, agrupamento por fibra de classe, razoes principais, translacoes de norma 1 e projecao por polidisco centrado. |
| Grafico final pequeno | `build_final_small_cm_plot.py`, `final_small_cm/` | Figura explicativa compacta com 32 pontos usando raizes da unidade em `Q(zeta_24)` como translacoes exatas de norma 1. |
| Busca <= 32 | `search_best_leq32_unit_graph.py`, `best_leq32_search/` | Exercicio computacional: busca, dentro da familia booleana-ciclotomica, configuracoes com ate 32 pontos e muitas distancias unitarias. |
| Sequencia final | `build_final_proof_sequence.py`, `final_proof_sequence/` | Galeria final alinhada ao Stage 16: primos split, fibras de classe, razoes principais, translacoes de norma 1, corte por polidisco e projecao. |
| Variacoes geometricas | `build_final_geometric_variations.py`, `final_geometric_variations/` | Organizacoes visuais distintas dentro da mesma familia Stage 16: espalhamento angular, corte apertado, setor angular, baixa distorcao e amostra aleatoria controlada. |
| Busca simetrica | `build_symmetric_variation_search.py`, `symmetric_variation_search/` | Busca variacoes Stage 16 com direcoes quase regularmente espacadas modulo `pi`, favorecendo malhas radiais/dihedrais de alto impacto visual. |
| Galeria Blueprint simetrica | `build_blueprint_symmetric_gallery.py`, `final_blueprint_symmetric_variations/` | Colecao final em estilo Blueprint, com variacoes simetricas de forma, numero de pontos, raio do polidisco e quantidade de translacoes. |
| Styler interativo | `interactive_graph_styler/index.html` | Interface em canvas para filtrar/carregar datasets, ajustar background, largura/alpha/densidade de linhas, tamanho/cor/alpha de pontos e exportar PNG. |

## Grafico final pequeno

Execute:

```powershell
python .\build_final_small_cm_plot.py
```

Saidas:

- `final_small_cm/final_small_cm_unit_distance.png`
- `final_small_cm/points.csv`
- `final_small_cm/unit_edges.csv`
- `final_small_cm/summary.csv`

O grafico final usa `K = Q(zeta_24)` e as translacoes selecionadas
`zeta_24^1`, `zeta_24^6`, `zeta_24^10`, `zeta_24^15` e `zeta_24^20`.
Cada elemento satisfaz `u*c(u)=1`, entao sua projecao complexa escolhida tem
comprimento exatamente 1.

Os 32 pontos sao:

```text
P(epsilon) = sum_j (epsilon_j - 1/2) u_j,  epsilon_j in {0,1}.
```

Trocar um bit move um ponto por `+/-u_j`, gerando pares a distancia 1. Esta
figura pequena e propositalmente didatica: ela deixa claro o mecanismo das
translacoes de norma 1. O comportamento assintotico mais forte esta no pipeline
do Stage 16, onde as translacoes vem de fibras de classes de ideais, nao apenas
de raizes da unidade.

## Melhor saida grande ja existente

A melhor saida local mais alinhada com a prova e:

```text
stage16_small_final_v3_1/best_m24_spc3_bucket0_tc14_polyR4p0_prinRnone_comparison.png
```

O resumo dessa saida registra:

- familia de campos: `Q(zeta_24)`;
- primos split: `73 97 193`;
- translacoes de norma 1 selecionadas: `14`;
- pontos projetados distintos: cerca de `15.900`;
- pares a distancia 1: cerca de `109.000`;
- razao contra uma grade de mesmo tamanho: cerca de `3.46x`.

Use essa imagem quando o objetivo for mostrar o motor finito mais proximo da
prova. Use a nova imagem em `final_small_cm` quando o objetivo for uma
explicacao legivel com poucos pontos.

## Sequencia final alinhada a prova

A pasta principal para apresentacao final e:

```text
final_proof_sequence/
```

Ela foi gerada com Sage no WSL:

```bash
source ~/miniforge3/etc/profile.d/conda.sh
conda activate sage
python build_final_proof_sequence.py
```

Essa pasta contem uma sequencia crescente:

- `01`: 16 pontos, 32 pares unitarios;
- `02`: 64 pontos, 192 pares unitarios;
- `03`: 256 pontos, 1.024 pares unitarios;
- `04`: 1.020 pontos, 5.080 pares unitarios;
- `05`: 4.054 pontos, 24.106 pares unitarios;
- `06`: 15.844 pontos, 108.216 pares unitarios.

O passo `04` e o mais equilibrado visualmente. O passo `06` e o melhor
quantitativamente e representa a melhor amostra finita Stage 16 nesta pasta.

## Variacoes geometricas finais

Para mostrar que a mesma construcao aritmetica pode produzir organizacoes
visuais distintas, use:

```bash
source ~/miniforge3/etc/profile.d/conda.sh
conda activate sage
python build_final_geometric_variations.py
```

Saidas:

- `final_geometric_variations/01_angular_spread_balanced.png`
- `final_geometric_variations/02_angular_spread_tight_cut.png`
- `final_geometric_variations/03_sector_cluster.png`
- `final_geometric_variations/04_low_hidden_distortion.png`
- `final_geometric_variations/05_random_representative.png`
- `final_geometric_variations/06_dense_angular_spread.png`

Todas preservam o mesmo nucleo: `Q(zeta_24)`, primos split `73 97 193`, fibra
de classe, razoes principais, translacoes `u = alpha/c(alpha)` de norma
relativa 1, corte por polidisco e projecao complexa.

## Busca por simetria visual

Para procurar malhas com maior impacto visual por simetria angular:

```bash
source ~/miniforge3/etc/profile.d/conda.sh
conda activate sage
python build_symmetric_variation_search.py
```

Saidas:

- `symmetric_variation_search/manifest.csv`
- `symmetric_variation_search/01_regular6_phase_opt.png`
- `symmetric_variation_search/02_regular8_phase_opt.png`
- `symmetric_variation_search/03_regular10_phase_opt.png`
- `symmetric_variation_search/04_regular10_axis_locked.png`
- `symmetric_variation_search/05_regular10_tight_cut.png`
- `symmetric_variation_search/06_regular10_low_hidden.png`
- `symmetric_variation_search/07_regular12_phase_opt.png`
- `symmetric_variation_search/08_regular12_low_hidden.png`

Essa busca compara as direcoes das translacoes modulo `pi` contra alvos
angulares regulares. A variante `03_regular10_phase_opt` e uma boa candidata
equilibrada; `07_regular12_phase_opt` e mais densa e quantitativamente mais
forte.

## Galeria Blueprint simetrica

A referencia visual principal do projeto passa a ser:

```bash
source ~/miniforge3/etc/profile.d/conda.sh
conda activate sage
python build_blueprint_symmetric_gallery.py
```

Saidas:

- `final_blueprint_symmetric_variations/01_regular6_open.png`
- `final_blueprint_symmetric_variations/02_regular8_open.png`
- `final_blueprint_symmetric_variations/03_regular10_compact.png`
- `final_blueprint_symmetric_variations/04_regular10_balanced.png`
- `final_blueprint_symmetric_variations/05_regular10_axis_locked.png`
- `final_blueprint_symmetric_variations/06_regular10_low_hidden.png`
- `final_blueprint_symmetric_variations/07_regular11_balanced.png`
- `final_blueprint_symmetric_variations/08_regular12_compact.png`
- `final_blueprint_symmetric_variations/09_regular12_balanced.png`

Todas usam o mesmo nucleo matematico Stage 16: `K = Q(zeta_24)`, primos split
`73 97 193`, fibra de classe com `4096` escolhas, translacoes
`u = alpha/c(alpha)` de norma relativa 1, corte por polidisco de Minkowski e
projecao para uma coordenada complexa. O que muda entre elas e permitido pela
propria construcao finita: quantidade de translacoes, simetria angular alvo,
raio do corte e penalidade leve nas outras imersoes.

Resumo da galeria atual:

| Variacao | Pontos | Pares unitarios | Uso visual |
| --- | ---: | ---: | --- |
| `01_regular6_open` | 64 | 192 | explicacao pequena |
| `02_regular8_open` | 256 | 1.024 | transicao compacta |
| `03_regular10_compact` | 936 | 4.360 | malha decagonal apertada |
| `04_regular10_balanced` | 1.024 | 5.120 | padrao recomendado |
| `05_regular10_axis_locked` | 1.020 | 5.080 | composicao alinhada ao eixo |
| `06_regular10_low_hidden` | 1.022 | 5.100 | baixa distorcao oculta |
| `07_regular11_balanced` | 2.044 | 11.220 | densidade intermediaria |
| `08_regular12_compact` | 3.418 | 18.264 | dodecagonal compacta |
| `09_regular12_balanced` | 4.050 | 24.082 | dodecagonal densa |

O preset Blueprint tambem e o padrao no app interativo. Use
`04_regular10_balanced` como primeira candidata para apresentacao, e depois
compare com `05`, `06` e `09` para escolher a organizacao visual.

## Styler interativo

Para ajustar visualmente as figuras sem rerodar Sage, abra:

```text
interactive_graph_styler/index.html
```

Se o navegador bloquear arquivos locais, sirva a raiz do repositorio:

```powershell
python -m http.server 8765 --bind 127.0.0.1
```

Depois acesse:

```text
http://127.0.0.1:8765/interactive_graph_styler/index.html
```

O snapshot de dados fica em `interactive_graph_styler/graph_data.js` e inclui
datasets de `final_blueprint_symmetric_variations/`,
`final_geometric_variations/` e `symmetric_variation_search/`. A interface
tambem aceita carga manual de `points.csv` e `edges.csv`.

Para regenera-lo depois de atualizar as pastas de datasets:

```powershell
python .\interactive_graph_styler\build_data.py
```

## Exercicio: melhor grafico pequeno encontrado

Para buscar configuracoes pequenas dentro da familia booleana-ciclotomica:

```powershell
python .\search_best_leq32_unit_graph.py
```

Saidas:

- `best_leq32_search/best_leq32_cm_boolean.png`
- `best_leq32_search/best_points.csv`
- `best_leq32_search/best_unit_edges.csv`
- `best_leq32_search/search_summary.csv`

Na busca padrao, o melhor exemplo encontrado tem:

- `K = Q(zeta_18)`;
- expoentes escolhidos: `0 1 2 3 4`;
- pontos: `32`;
- pares a distancia 1: `96`.

Tambem foi feita uma varredura mais ampla em `m = 12, 16, 18, 20, 24, 30, 36,
42, 48, 54, 60` para `k = 5`, registrada em `best_leq32_search_wide/`. Ela
nao encontrou exemplo acima de `96` nessa familia.

Importante: isso nao prova que `96` seja o maximo absoluto para qualquer
conjunto plano com ate 32 pontos. A literatura de pequenos conjuntos e dificil:
resultados recentes enumeram exatamente os casos ate `n <= 21` e melhoram
limites superiores para `16 <= n <= 30`, mas nao fornecem uma resposta global
simples para `n = 32`.
