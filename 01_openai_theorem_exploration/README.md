# OpenAI Theorem Exploration

Exploracao finita da construcao CM/ciclotomica inspirada na prova de 2026 para
o problema de Erdos. Esta pasta concentra os scripts Stage 5-16, as galerias
finais e o editor visual.

## Figuras Principais

- `final_blueprint_symmetric_variations/`: galeria final em estilo Blueprint.
- `final_proof_sequence/`: sequencia final alinhada ao Stage 16.
- `final_geometric_variations/`: variacoes visuais da mesma familia.
- `final_small_cm/`: exemplo didatico pequeno.
- `interactive_graph_styler/`: editor local para ajustar e exportar imagens.

## Reproducao

Os scripts Sage devem rodar a partir desta pasta no WSL Ubuntu com o ambiente
Conda `sage`:

```bash
cd "/mnt/c/Users/rnahu/OneDrive/Docs pessoais/Documents/GitHub/unit-distance-problem/01_openai_theorem_exploration"
source ~/miniforge3/etc/profile.d/conda.sh
conda activate sage
python build_blueprint_symmetric_gallery.py
python build_final_proof_sequence.py
```

Depois de regenerar a galeria Blueprint:

```powershell
cd "C:\Users\rnahu\OneDrive\Docs pessoais\Documents\GitHub\unit-distance-problem\01_openai_theorem_exploration"
python .\interactive_graph_styler\build_data.py
```
