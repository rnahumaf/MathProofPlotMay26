# n=25 Proof Search

Busca de uma prova para o caso `n = 25`, com foco no candidato de `70` pares a
distancia 1 e em filtros para eliminar configuracoes com `71+` pares.

## Conteudo

- `n25_max70_investigation/`: certificado exato de limite inferior, bounds
  finitos UCCS e busca por contraexemplos.
- `n25_global_proof_search/`: busca combinatoria/geometrica global, pools de
  candidatos, filtros, certificados e subcores.

## Reproducao

```powershell
cd "C:\Users\rnahu\OneDrive\Docs pessoais\Documents\GitHub\MathProofPlotMay26\05_n25_proof_search"
python .\n25_max70_investigation\investigate_n25_max70.py --exact-lower-bound
```
