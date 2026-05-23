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
