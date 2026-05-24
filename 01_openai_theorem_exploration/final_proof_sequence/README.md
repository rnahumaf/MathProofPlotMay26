# Sequencia final: amostra finita alinhada a prova

Esta pasta contem a melhor reproducao visual finita, dentro dos limites
computacionais locais, da construcao de muitos pares a distancia 1 inspirada
pela prova de 2026.

## Parametros aritmeticos

- Campo CM: `K = Q(zeta_24)`
- Grau de `K`: `8`
- Primos racionais que splitam completamente em `K`: `73 97 193`
- Pares de ideais conjugados: `12`
- Escolhas de produto de ideais: `4096`
- Maior fibra de classe encontrada: `4096`
- Testes de razao principal bem-sucedidos: `4095`
- Falhas de razao principal: `0`

## Tecnica

1. Trabalhamos em `K = Q(zeta_24)`, um campo CM.
2. Escolhemos primos `p == 1 mod 24`; por isso eles splitam completamente em
   `K`.
3. Para cada primo, os ideais primos acima dele sao pareados pela conjugacao
   CM.
4. Enumeramos escolhas de um ideal em cada par conjugado.
5. Agrupamos os produtos de ideais por fibra de classe usando testes de
   principialidade de razoes `I/I0`.
6. Para cada razao principal `(alpha) = I/I0`, construimos
   `u = alpha / c(alpha)`.
7. Cada `u` satisfaz exatamente `u*c(u)=1`; suas imagens complexas funcionam
   como translacoes unitarias.
8. A nuvem finita vem das somas centradas
   `sum_j (epsilon_j - 1/2) u_j`, cortadas pelo polidisco
   `max_sigma |x_sigma| <= 4`.
9. Projetamos para uma coordenada complexa e desenhamos as arestas obtidas por
   trocar um bit, isto e, por somar uma das translacoes unitarias.

Esta e uma amostra finita fiel ao mecanismo. Ela nao demonstra sozinha o
expoente assintotico; o papel da prova e mostrar que esse mecanismo pode ser
feito em uma familia infinita de campos com controle aritmetico.

## Sequencia crescente

| Arquivo | Translacoes | Pontos | Pares unitarios | Razao vs grade |
| --- | ---: | ---: | ---: | ---: |
| `01_m24_spc3_tc4_polyR4.png` | 4 | 16 | 32 | 1.333x |
| `02_m24_spc3_tc6_polyR4.png` | 6 | 64 | 192 | 1.714x |
| `03_m24_spc3_tc8_polyR4.png` | 8 | 256 | 1024 | 2.133x |
| `04_m24_spc3_tc10_polyR4.png` | 10 | 1020 | 5080 | 2.571x |
| `05_m24_spc3_tc12_polyR4.png` | 12 | 4054 | 24106 | 3.021x |
| `06_m24_spc3_tc14_polyR4.png` | 14 | 15844 | 108216 | 3.442x |

## Arquivos

Para cada passo existem:

- `.png`: figura de apresentacao;
- `.svg`: SVG estruturado com metadados em nos e arestas;
- `_points.csv`: pontos projetados;
- `_edges.csv`: arestas unitarias geradas pelas translacoes;
- `_selected_u.csv`: translacoes selecionadas, com angulo e norma nas imersoes;
- `_summary.json`: resumo da configuracao.

`manifest.csv` resume todos os passos.

## Observacao visual

As figuras densas amostram as arestas no PNG/SVG para manter legibilidade e
tamanho de arquivo. Os CSVs de arestas guardam a lista completa de pares
unitarios gerados para cada passo.
