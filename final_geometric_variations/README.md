# Variacoes geometricas finais

Esta pasta mostra organizacoes visuais distintas dentro da mesma construcao
aritmetica finita usada na sequencia final.

## Invariantes preservados

- Campo CM: `K = Q(zeta_24)`
- Primos split: `73 97 193`
- Pares de ideais conjugados: `12`
- Maior fibra de classe: `4096`
- Translacoes construidas como `u = alpha / c(alpha)`, com `u*c(u)=1`
- Pontos construidos por somas centradas e corte por polidisco
- Arestas unitarias geradas por troca de um bit, isto e, por somar uma
  translacao `u_j`

## Variacoes

| Variacao | Selector | Translacoes | R | Pontos | Pares unitarios | Razao vs grade |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `01_angular_spread_balanced.png` | `angle_spread` | 10 | 4.0 | 1020 | 5080 | 2.571x |
| `02_angular_spread_tight_cut.png` | `angle_spread` | 10 | 3.0 | 930 | 4298 | 2.389x |
| `03_sector_cluster.png` | `sector_cluster` | 10 | 4.0 | 1022 | 5100 | 2.576x |
| `04_low_hidden_distortion.png` | `low_hidden_distortion` | 10 | 4.0 | 1020 | 5080 | 2.571x |
| `05_random_representative.png` | `random` | 10 | 4.0 | 1024 | 5120 | 2.581x |
| `06_dense_angular_spread.png` | `angle_spread` | 12 | 4.0 | 4054 | 24106 | 3.021x |

## Leitura visual

As cores das arestas indicam qual translacao `u_j` gerou o par unitario. Os
pontos mais escuros/claros refletem o tamanho maximo da soma centrada nas
imersoes complexas usadas no corte. Assim, a diferenca entre as figuras vem da
organizacao geometrica da mesma fonte aritmetica, nao de uma mudanca para uma
construcao aleatoria.

## Limite conceitual

Estas imagens sao amostras finitas fieis ao mecanismo da prova. Elas nao sao
uma reproducao completa do teorema assintotico, que afirma uma familia infinita
de conjuntos com `n` arbitrariamente grande e depende de controle de torres de
campos, discriminantes e classes.
