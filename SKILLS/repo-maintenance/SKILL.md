# Repo Maintenance

Use esta skill quando a tarefa envolver Git, GitHub, Git LFS, organizacao de
artefatos, documentacao de fluxo ou preparacao de commits.

## Estado remoto

Repositorio GitHub:

```text
https://github.com/rnahumaf/MathProofPlotMay26
```

Remote local:

```text
origin https://github.com/rnahumaf/MathProofPlotMay26.git
```

## Checks uteis

```powershell
git status --short --branch
git lfs status
git diff --check
git log --oneline -3
```

## LFS

`.gitattributes` rastreia:

```text
*.csv
*.png
*.pdf
*.svg
*.zip
```

Antes de adicionar muitos arquivos gerados, confira se eles sao parte da
historia que o projeto deve preservar. Artefatos grandes demais podem exigir
uma decisao explicita antes de entrar no historico.

## Gotchas

- Ja existe `origin`; se `gh repo create --source . --push` falhar ao adicionar
  remoto, use `git remote -v` e depois `git push -u origin main`.
- Reescrever historico para remover LFS pesado exige decisao explicita do
  usuario e geralmente `git push --force-with-lease`.
- `_external_review/` e material local de comparacao e esta ignorado pelo Git.
- Nao use `git reset --hard` nem `git checkout --` para limpar mudancas sem
  pedido explicito.

