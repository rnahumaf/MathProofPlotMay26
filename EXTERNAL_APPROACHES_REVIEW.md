# Avaliacao de abordagens externas

Repositorios avaliados em 2026-05-23:

- https://github.com/alozanoroble/Erdos90
- https://github.com/Tenobrus/graphglyph

## 1. alozanoroble/Erdos90

Resumo: conjunto estatico de imagens/PDF/SVG sobre o grafo de distancia
unitaria associado aos pontos

```text
z = a + b i + c rho + d i rho,
a,b,c,d in {-2,-1,0,1,2},
rho = exp(2 pi i / 3).
```

O repositorio nao traz scripts, README ou pipeline de reproducao; traz apenas
artefatos finais. A pagina do GitHub descreve o projeto como "Some graphs
related to the unit-distance problem".

Arquivos principais observados:

- `OK_minus2_to_2_unit_distance_high_resolution.png`
- `OK_minus2_to_2_unit_distance_high_resolution.pdf`
- `OK_minus2_to_2_complex_abs_lt_4_unit_graph.png`
- `OK_minus2_to_2_complex_abs_lt_4_unit_graph.pdf`
- `OK_minus2_to_2_complex_abs_lt_4_unit_graph.svg`

Contagens inferidas localmente a partir da formula do titulo:

| Variante | Pontos distintos | Pares unitarios | Grau medio |
| --- | ---: | ---: | ---: |
| Caixa completa `{-2,...,2}^4` | 625 | 2800 | 8.96 |
| Corte `|z| < 4` | 545 | 2396 | 8.79 |

Pontos fortes:

- E uma representacao direta, limpa e matematicamente legivel da construcao
  finita baseada em `Z[i,rho]`.
- O titulo da figura explicita a formula dos pontos, o que ajuda bastante na
  leitura matematica.
- A imagem comunica bem a ideia de "muitos pares unitarios" em uma projecao
  plana.

Limitacoes:

- Sem codigo, nao ha como variar parametros, reproduzir a contagem, gerar CSVs
  ou testar outras janelas.
- A visualizacao fica densa rapidamente; ela demonstra riqueza combinatoria,
  mas nao e boa para explicar passo a passo a construcao.
- A abordagem fica no modelo finito `a + bi + c rho + di rho`; ela nao tenta
  representar a etapa mais forte de fibras de classes de ideais da prova de
  2026.

Uso recomendado no nosso projeto:

- Usar como referencia visual para a camada "toy/algebrica" com `rho`.
- Incorporar a ideia de sempre colocar a formula do conjunto no proprio
  grafico.
- Nao usar como base principal da narrativa final, porque falta pipeline
  reprodutivel.

## 2. Tenobrus/graphglyph

Resumo: gerador Python que transforma texto em imagens SVG/JSON decodificaveis
com estilo de grafo de distancia unitaria. O README declara que o estilo e
baseado na ilustracao finita do artigo da OpenAI, com pontos da forma

```text
z = a + b i + c rho + d i rho.
```

O projeto vai alem de visualizacao matematica: ele usa o grafo como suporte
para uma codificacao reversivel de mensagens.

Arquivos principais observados:

- `graph_cipher.py`
- `analyze_reference.py`
- exemplos em `examples/`

Comportamento verificado:

- `graph_cipher.py decode` recupera corretamente os textos dos SVGs de exemplo.
- Um teste local com `--variant-strength 0` gerou `625` nos e `3760` arestas
  totais no SVG, com `120` celulas de dados.
- Exemplos existentes observados:
  - `you_are_loved_immensely.svg`: `857` nos, `4592` linhas SVG, `120` celulas
    de dados.
  - outro exemplo curto: `589` nos, `3281` linhas SVG, `120` celulas de dados.

Pontos fortes:

- Muito mais reprodutivel que `Erdos90`: ha CLI, encoder, decoder, SVG e JSON.
- A separacao entre geometria e payload e interessante: as cores sao
  apresentacionais, enquanto os dados ficam em pesos e atributos SVG.
- O modo `--variant-strength 0` preserva uma caixa algebrica exata baseada em
  `rho`, util para comparacao matematica.
- O arquivo SVG contem atributos estruturados (`data-cell`, `data-slot`,
  `data-bit`, `data-weight`), entao a imagem tambem funciona como artefato de
  dados.

Limitacoes:

- A prioridade do projeto e esteganografia/codificacao visual, nao otimizacao
  de distancias unitarias.
- O modo padrao `--variant-strength 0.75` introduz variacao por semente,
  janelas deformadas e familias de base diferentes; isso melhora a aparencia,
  mas enfraquece a leitura como objeto matematico canonico.
- Para fins de prova, muitas arestas sao tambem portadoras de dados com pesos;
  isso mistura "aresta de distancia unitaria" com "aresta visual/semantica".
- Nao ha conexao com a etapa CM mais forte da prova de 2026 baseada em fibras
  de classes de ideais.

Uso recomendado no nosso projeto:

- Aproveitar a ideia de SVG estruturado/decodificavel para nossas saidas:
  `data-u`, `data-v`, `data-distance`, `data-translation`, etc.
- Separar explicitamente arestas matematicas de arestas de anotacao visual, se
  adotarmos pesos, cores ou destaque.
- Manter um modo `exact` sem variacao estetica para preservar a verificabilidade.

## Comparacao com a nossa abordagem atual

| Criterio | Erdos90 | graphglyph | Nosso repositorio |
| --- | --- | --- | --- |
| Finalidade | Figura estatica de grafo unitario | Codificacao reversivel em grafo visual | Narrativa matematica + experimentos CM |
| Reprodutibilidade | Baixa | Alta | Media/alta; Sage para estagios, Python comum para figuras pequenas |
| Fidelidade a prova 2026 | Baixa/media; modelo `rho` finito | Baixa/media; estilo baseado no modelo `rho` | Mais alta no Stage 16, com fibras de classes de ideais |
| Valor visual | Bom para imagem unica densa | Muito bom para artefato visual | Bom para explicacao; ainda pode melhorar como design final |
| Dados exportaveis | Nao | Sim, SVG/JSON | Sim, CSV/PNG; pode melhorar com SVG estruturado |

Conclusao pratica:

- `Erdos90` e a melhor referencia externa para uma figura matematica simples e
  direta.
- `graphglyph` e a melhor referencia externa para engenharia de artefato:
  CLI, SVG estruturado, decoder e variacao controlada.
- Nosso projeto deve combinar as duas licoes: manter a clareza matematica de
  `Erdos90`, mas adotar a rastreabilidade estrutural de `graphglyph`.

Proximos ajustes recomendados:

1. Gerar tambem SVG estruturado nas nossas figuras finais pequenas.
2. Incluir nos CSVs e SVGs a translacao exata responsavel por cada aresta.
3. Criar dois modos de saida:
   - `didactic`: poucos pontos, anotado, adequado para explicacao.
   - `dense`: muitos pontos, comparacao quantitativa, adequado para relatorio.
4. Para o Stage 16, produzir um resumo visual em camadas: campo, primos split,
   fibra de classe, translacoes de norma 1, corte e projecao.
