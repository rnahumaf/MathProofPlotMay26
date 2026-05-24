# Symmetric Variation Search

Esta pasta busca variacoes visualmente mais simetricas dentro da mesma familia
aritmetica Stage 16.

## Invariantes preservados

- Campo CM: `K = Q(zeta_24)`
- Primos split: `73 97 193`
- Fibra de classe: `4096` escolhas
- Translacoes de norma relativa 1: `u = alpha / c(alpha)`
- Pontos por somas centradas e corte por polidisco
- Arestas por troca de um bit, isto e, por somar uma translacao `u_j`

## Criterio de simetria

As direcoes das translacoes sao comparadas modulo `pi`, porque arestas
unitarias nao orientadas identificam `u` e `-u`. Para cada quantidade de
translacoes, testamos fases de um alvo angular regular e escolhemos o conjunto
com menor erro RMS contra esse alvo. Algumas variacoes incluem uma penalidade
leve por distorcao nas demais imersoes.

## Resultados

| Variacao | Translacoes | R | Pontos | Pares | RMS angular | Gap min/max | Razao |
| --- | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| `01_regular6_phase_opt.png` | 6 | 4.0 | 64 | 192 | 0.008° | 29.98°/30.01° | 1.714x |
| `02_regular8_phase_opt.png` | 8 | 4.0 | 256 | 1024 | 0.008° | 22.48°/22.52° | 2.133x |
| `03_regular10_phase_opt.png` | 10 | 4.0 | 1024 | 5120 | 0.008° | 17.98°/18.02° | 2.581x |
| `04_regular10_axis_locked.png` | 10 | 4.0 | 1020 | 5080 | 0.038° | 17.92°/18.09° | 2.571x |
| `05_regular10_tight_cut.png` | 10 | 3.0 | 936 | 4360 | 0.008° | 17.98°/18.02° | 2.409x |
| `06_regular10_low_hidden.png` | 10 | 4.0 | 1022 | 5100 | 0.157° | 17.50°/18.50° | 2.576x |
| `07_regular12_phase_opt.png` | 12 | 4.0 | 4068 | 24264 | 0.013° | 14.97°/15.03° | 3.030x |
| `08_regular12_low_hidden.png` | 12 | 4.0 | 4044 | 24010 | 0.172° | 14.53°/15.39° | 3.016x |

## Arquivos

Cada variacao contem `.png`, `.svg`, `_points.csv`, `_edges.csv`,
`_selected_u.csv` e `_summary.json`. `manifest.csv` resume a busca.
