# Final Blueprint Symmetric Variations

Esta pasta e a galeria final em estilo Blueprint. Ela substitui a paleta
experimental colorida por uma linguagem unica: fundo claro azulado, linhas
azuis finas com acumulacao visual nas intersecoes e pontos escuros.

## Invariantes matematicos

Todas as figuras preservam o mesmo motor finito alinhado ao Stage 16:

- Campo CM: `K = Q(zeta_24)`
- Primos split: `73 97 193`
- Fibra de classe: `4096` escolhas
- Translacoes: `u = alpha / c(alpha)`, logo `u*c(u)=1`
- Pontos: somas centradas de translacoes, cortadas por um polidisco de Minkowski
- Arestas: troca de um bit, isto e, soma de uma das translacoes `u_j`
- Projecao final: uma coordenada complexa, identificada com o plano

## Parametros variados

A galeria varia somente parametros permitidos pela construcao finita:

- quantidade de translacoes de norma relativa 1;
- alvo angular regular modulo `pi`;
- raio do corte por polidisco;
- penalidade leve para controlar distorcao nas outras imersoes.

Isso muda a forma visual e o numero de pontos sem abandonar a familia
aritmetica usada na prova.

## Resultados

| Variacao | Forma | Translacoes | R | Pontos | Pares | RMS angular | Razao |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `01_regular6_open.png` | hexagonal skeleton | 6 | 4.0 | 64 | 192 | 0.007 deg | 1.714x |
| `02_regular8_open.png` | octagonal mesh | 8 | 4.0 | 256 | 1024 | 0.010 deg | 2.133x |
| `03_regular10_compact.png` | tight decagonal mesh | 10 | 3.0 | 936 | 4360 | 0.008 deg | 2.409x |
| `04_regular10_balanced.png` | balanced decagonal mesh | 10 | 4.0 | 1024 | 5120 | 0.008 deg | 2.581x |
| `05_regular10_axis_locked.png` | axis-aligned decagonal mesh | 10 | 4.0 | 1020 | 5080 | 0.038 deg | 2.571x |
| `06_regular10_low_hidden.png` | low-hidden decagonal mesh | 10 | 4.0 | 1022 | 5100 | 0.155 deg | 2.576x |
| `07_regular11_balanced.png` | eleven-direction mesh | 11 | 4.0 | 2044 | 11220 | 0.010 deg | 2.807x |
| `08_regular12_compact.png` | tight dodecagonal mesh | 12 | 3.0 | 3418 | 18264 | 0.012 deg | 2.718x |
| `09_regular12_balanced.png` | dense dodecagonal mesh | 12 | 4.0 | 4050 | 24082 | 0.012 deg | 3.021x |

## Leitura visual recomendada

- `01` e `02`: figuras pequenas para explicar a regra de construcao.
- `03` a `06`: zona principal para apresentacao, com cerca de mil pontos.
- `07`: transicao para densidade maior.
- `08` e `09`: variantes densas, mantendo simetria angular forte.

## Arquivos

Cada variacao contem `.png`, `_points.csv`, `_edges.csv`, `_selected_u.csv` e
`_summary.json`. `manifest.csv` resume a colecao e e consumido pelo app
`interactive_graph_styler/`.
