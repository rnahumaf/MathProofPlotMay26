# MathProofPlotMay26

Visualizacoes finitas da construcao de distancias unitarias inspirada na prova
de 2026 para o problema de Erdos no plano.

O objetivo deste repositorio e transformar uma prova assintotica em uma serie de
figuras concretas. Cada imagem abaixo e uma amostra finita de uma familia
infinita de exemplos: os pontos sao construidos a partir de campos numericos CM,
translacoes de norma relativa 1, corte por polidisco de Minkowski e projecao
para o plano complexo.

Essas figuras nao sao uma busca aleatoria por pontos bonitos. Elas implementam,
em escala finita, os mesmos blocos matematicos usados no artigo: primos split,
fibras de classes de ideais, razoes principais, elementos `u = alpha/c(alpha)`,
rede de Minkowski, corte finito e contagem de pares a distancia 1. Dentro das
restricoes de uma plotagem finita, esta e a aproximacao visual mais fiel que o
projeto produziu ate agora para uma das familias infinitas geradas pela prova.

Referencia principal: Will Sawin, *An explicit lower bound for the unit distance
problem*, arXiv:2605.20579v1, 20 May 2026:
https://arxiv.org/html/2605.20579v1

## Galeria Final Blueprint

A galeria final usa apenas o experimento simetrico em estilo Blueprint. O fundo
azulado, as linhas azuis semi-transparentes e os pontos escuros seguem o preset
padrao do editor interativo em `interactive_graph_styler/`.

| 64 pontos | 256 pontos | 936 pontos |
| --- | --- | --- |
| ![Blueprint Regular 6](final_blueprint_symmetric_variations/01_regular6_open.png) | ![Blueprint Regular 8](final_blueprint_symmetric_variations/02_regular8_open.png) | ![Blueprint Regular 10 Compact](final_blueprint_symmetric_variations/03_regular10_compact.png) |
| `01_regular6_open`<br>192 pares unitarios<br>ratio `1.714x` | `02_regular8_open`<br>1.024 pares unitarios<br>ratio `2.133x` | `03_regular10_compact`<br>4.360 pares unitarios<br>ratio `2.409x` |

| 1.024 pontos | 1.020 pontos | 1.022 pontos |
| --- | --- | --- |
| ![Blueprint Regular 10 Balanced](final_blueprint_symmetric_variations/04_regular10_balanced.png) | ![Blueprint Regular 10 Axis Locked](final_blueprint_symmetric_variations/05_regular10_axis_locked.png) | ![Blueprint Regular 10 Low Hidden](final_blueprint_symmetric_variations/06_regular10_low_hidden.png) |
| `04_regular10_balanced`<br>5.120 pares unitarios<br>ratio `2.581x` | `05_regular10_axis_locked`<br>5.080 pares unitarios<br>ratio `2.571x` | `06_regular10_low_hidden`<br>5.100 pares unitarios<br>ratio `2.576x` |

| 2.044 pontos | 3.418 pontos | 4.050 pontos |
| --- | --- | --- |
| ![Blueprint Regular 11](final_blueprint_symmetric_variations/07_regular11_balanced.png) | ![Blueprint Regular 12 Compact](final_blueprint_symmetric_variations/08_regular12_compact.png) | ![Blueprint Regular 12 Balanced](final_blueprint_symmetric_variations/09_regular12_balanced.png) |
| `07_regular11_balanced`<br>11.220 pares unitarios<br>ratio `2.807x` | `08_regular12_compact`<br>18.264 pares unitarios<br>ratio `2.718x` | `09_regular12_balanced`<br>24.082 pares unitarios<br>ratio `3.021x` |

## Como Ler As Imagens

Cada ponto preto representa um ponto do conjunto finito projetado no plano. Cada
linha azul representa um par de pontos a distancia exatamente 1, produzido por
uma das translacoes de norma relativa 1. Onde muitas linhas se cruzam ou se
acumulam, o azul fica mais intenso.

A prova completa e assintotica: ela nao produz apenas uma imagem, mas uma
sequencia infinita de conjuntos finitos cada vez maiores. Como nao se plota uma
familia infinita inteira, o repositorio mostra cortes finitos dessa construcao.
As imagens acima sao exemplos progressivos: aumentamos o numero de translacoes,
mudamos o raio do corte e escolhemos direcoes mais simetricas para tornar a
estrutura visivel.

O que permanece fixo na galeria:

- `K = Q(zeta_24)`, um campo ciclotomico CM;
- primos racionais split `73`, `97` e `193`;
- uma fibra de classe com `4096` escolhas;
- translacoes `u = alpha/c(alpha)` com `u*c(u)=1`;
- corte por polidisco na rede de Minkowski;
- projecao para uma coordenada complexa, identificada com o plano.

O que varia:

- quantidade de translacoes usadas;
- simetria angular alvo modulo `pi`;
- raio do polidisco;
- penalidade leve para controlar distorcao nas outras imersoes.

## O Que Significa O Ratio

O `ratio` compara a quantidade de pares a distancia 1 da figura com uma grade
quadrada comum usando aproximadamente o mesmo numero de pontos.

```text
ratio = pares unitarios da construcao / pares unitarios de uma grade comparavel
```

Por exemplo, `ratio 3.021x` significa que aquela amostra tem cerca de tres vezes
mais pares a distancia 1 do que uma grade de tamanho parecido. Esse numero e um
indicador simples de eficiencia: ele mede o quanto a construcao consegue
compactar muitos pares unitarios no mesmo numero de pontos.

Nas figuras finitas deste repositorio, o ratio cresce de `1.714x` para
`3.021x` dentro da galeria Blueprint. Na prova assintotica, a familia continua
crescendo: para tamanhos cada vez maiores, a quantidade de pares unitarios cresce
mais rapido do que no modelo de grade. Em termos visuais, isso quer dizer que a
vantagem nao deveria se estabilizar em um teto fixo de "tantas vezes a grade";
ela cresce ao longo da familia infinita. Se o modelo anterior for entendido como
a grade plana comum, a prova aponta exatamente para a superacao desse padrao de
eficiencia em escalas cada vez maiores. O limite infinito, porem, nao pode ser
plotado diretamente. O que vemos aqui sao janelas finitas desse mecanismo.

## Reproduzir A Galeria

Os scripts Sage devem rodar no WSL Ubuntu com o ambiente Conda `sage`:

```bash
cd "/mnt/c/Users/rnahu/OneDrive/Docs pessoais/Documents/GitHub/MathProofPlotMay26"
source ~/miniforge3/etc/profile.d/conda.sh
conda activate sage
python build_blueprint_symmetric_gallery.py
```

Isso recria:

- `final_blueprint_symmetric_variations/manifest.csv`
- `final_blueprint_symmetric_variations/*_points.csv`
- `final_blueprint_symmetric_variations/*_edges.csv`
- `final_blueprint_symmetric_variations/*_selected_u.csv`
- `final_blueprint_symmetric_variations/*_summary.json`
- `final_blueprint_symmetric_variations/*.png`

Depois de regenerar a galeria, atualize o snapshot do app:

```powershell
python .\interactive_graph_styler\build_data.py
```

## Editor Interativo

Abra:

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

O app permite escolher o dataset, alterar fundo, linha, alpha, densidade, pontos
e exportar PNG. O preset Blueprint e o padrao.

## Comparacao Em Quadrados

A comparacao entre grade simples, OpenAI/Stage 16, Erdos classico, UCCS e
maximo provado fica em:

[square_method_comparison/README.md](square_method_comparison/README.md)

Ela usa quadrados `n = m^2`, de `m=4` ate `m=20`, porque isso facilita comparar
visualmente as abordagens em tamanhos intuitivos. A coluna OpenAI combina
amostras Stage 16 completas quando elas ja existem naquele tamanho e subgrafos
induzidos exact-n extraidos do dataset Blueprint `09_regular12_balanced` nos
demais casos.

## Mapa Do Repositorio

| Area | Arquivos | Papel |
| --- | --- | --- |
| Galeria final | `build_blueprint_symmetric_gallery.py`, `final_blueprint_symmetric_variations/` | Experimento simetrico final em Blueprint. |
| Editor | `interactive_graph_styler/` | Ajuste visual e exportacao de PNG sem rerodar Sage. |
| Comparacao quadrada | `build_openai_square_exact_runs.py`, `build_square_method_comparison.py`, `square_method_comparison/` | Comparacao `n=m^2` entre grade, OpenAI, Erdos, UCCS e maximos provados conhecidos. |
| Motor Stage 16 | `stage16_class_fiber_cm*.py` | Implementacao finita mais alinhada com a prova. |
| Variacoes anteriores | `final_geometric_variations/`, `symmetric_variation_search/` | Experimentos usados para chegar a galeria final. |
| Busca pequena | `search_best_leq32_unit_graph.py`, `best_leq32_search/` | Exercicio com ate 32 pontos. |
| Agentes | `GUIDELINES.html`, `AGENTS.md`, `SKILLS/` | Regras de manutencao do repositorio. |

## Observacao Matematica

Este repositorio nao prova novamente o teorema assintotico. Ele documenta uma
implementacao finita, visual e inspecionavel dos ingredientes do metodo. A
prova completa exige uma torre infinita de campos e controle assintotico de
discriminantes, classes de ideais e contagens. Uma imagem so pode mostrar uma
amostra finita; a importancia da prova esta justamente em garantir que amostras
desse tipo existem para tamanhos arbitrariamente grandes.
