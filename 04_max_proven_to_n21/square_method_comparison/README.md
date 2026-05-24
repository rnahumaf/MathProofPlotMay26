# Square Method Comparison

Comparacao para `n = m^2`, usando os resultados UCCS e OpenAI/Stage 16
disponiveis localmente.

![Comparacao Blueprint](comparison_blueprint.png)

No grafico, as linhas OpenAI e UCCS mostram a media das tentativas, e a sombra
mostra `±1` desvio padrao. A tabela tambem preserva o melhor valor conhecido.

## Colunas

- **Grade simples**: malha quadrada `m x m`, contando vizinhos horizontais e
  verticais.
- **OpenAI exact-n**: melhor subgrafo induzido de tamanho exatamente `n`,
  extraido do dataset Stage 16 Blueprint `09_regular12_balanced`. A sombra usa
  o desvio padrao entre seeds independentes da busca exact-n.
- **Erdos classico**: melhor distancia repetida em uma grade retangular com
  `n` pontos, depois reescalada para distancia 1.
- **UCCS**: Unit-Circle Closure Search, a sua busca por fecho de intersecoes de
  circulos unitarios. Quando
  `../03_uccs_exploration/uccs_square_stat_runs/restart_summary_results.csv`
  existe, a sombra usa o desvio padrao dos melhores resultados por restart
  interno. Isso e diferente da trilha monotona de mensagens `novo melhor`.
- **Maximo provado**: valor exato conhecido. Entre os quadrados desta tabela,
  apenas `n=16` esta preenchido; `n=25` e os demais ficam em branco ate haver
  uma fonte de maximo exato.

## Tabela

| n | Grade simples | OpenAI best | OpenAI media ± σ | Erdos classico | UCCS best | UCCS media ± σ | Maximo provado |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 16 | 24 | 32 | 32 | 24 | 40 | 39.194 ± 1.0 | 41 |
| 25 | 40 | 54 | 54 | 48 | 70 | 69.228 ± 1.0 |  |
| 36 | 60 | 88 | 88 | 80 | 111 | 109.264 ± 1.8 |  |
| 49 | 84 | 130 | 129.800 ± 0.6 | 120 | 161 | 157.296 ± 2.1 |  |
| 64 | 112 | 192 | 185.300 ± 2.6 | 168 | 217 | 214.074 ± 2.5 |  |
| 81 | 144 | 239 | 237 ± 1.3 | 224 | 285 | 278.576 ± 2.7 |  |
| 100 | 180 | 310 | 308.100 ± 0.9 | 288 | 359 | 341.822 ± 2.3 |  |
| 121 | 220 | 400 | 389.600 ± 4.8 | 360 | 441 | 418.272 ± 2.1 |  |
| 144 | 264 | 473 | 466.700 ± 3.3 | 456 | 530 | 500.910 ± 2.0 |  |
| 169 | 312 | 574 | 568.600 ± 2.2 | 568 | 617 | 566.036 ± 1.6 |  |
| 196 | 364 | 688 | 681.800 ± 2.6 | 692 | 702 | 682.006 ± 2.2 |  |
| 225 | 420 | 821 | 821 | 828 | 810 | 804 ± 3.4 |  |
| 256 | 480 | 947 | 947 | 976 | 954 | 942.592 ± 4.8 |  |
| 289 | 544 | 1081 | 1081 | 1136 | 1089 | 1072.868 ± 5.0 |  |
| 324 | 612 | 1234 | 1234 | 1308 | 1232 | 1213.494 ± 5.6 |  |
| 361 | 684 | 1425 | 1425 | 1512 | 1363 | 1338.394 ± 6.8 |  |
| 400 | 760 | 1596 | 1596 | 1744 | 1527 | 1496.568 ± 8.2 |  |

## Leitura

UCCS melhora bastante a grade simples em todos os casos desta rodada. Em
valores baixos, ele tambem fica acima da coluna Erdos classico; a partir de
`n=225`, a grade de Erdos classica desta implementacao passa a superar a rodada
UCCS atual. A coluna OpenAI exact-n mostra uma comparacao concreta da familia
CM/Stage 16 em todos os mesmos quadrados, sem misturar os tamanhos naturais
completos da construcao com os subgrafos exact-n. Isso remove o pico artificial
que aparecia em `n=256`.

O valor `41` em `n=16` mostra que o resultado UCCS `40` esta a uma aresta do
maximo provado. Para `n=25`, nao foi preenchido maximo provado nesta tabela:
a fonte de referencia usada aqui lista maximos exatos ate `n=21`, entao `25`
nao deve ser tratado como resolvido sem outra citacao.
