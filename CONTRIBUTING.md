# Contribuindo

O projeto combina Spec-Driven Development (SDD), branches curtas, Conventional
Commits e Versionamento Semântico.

## Fluxo de trabalho

1. Atualize a Spec, o plano ou as tarefas quando a mudança afetar comportamento,
   arquitetura ou critérios de aceitação.
2. Crie a branch a partir da `main` atualizada.
3. Implemente somente o incremento definido e mantenha os testes verdes.
4. Atualize a seção `[Unreleased]` do `CHANGELOG.md`.
5. Abra um pull request e faça o merge na `main` após a validação.
6. Quando o gate da versão for aprovado, finalize o changelog, atualize a versão,
   crie a tag e deixe o workflow publicar a release.

Depois da importação inicial da `0.1.0`, mudanças comuns não devem ser desenvolvidas
diretamente na `main`.

## Nomes de branches

| Tipo | Formato | Exemplo |
|---|---|---|
| Funcionalidade | `feature/<spec>-<resumo>` | `feature/001-scoring` |
| Correção | `fix/<spec>-<resumo>` | `fix/001-g29-deadzone` |
| Manutenção | `chore/<resumo>` | `chore/update-pyinstaller` |
| Documentação | `docs/<resumo>` | `docs/calibration-guide` |
| Release | `release/<versao>` | `release/0.2.0` |

## Commits

Use mensagens no formato Conventional Commits, por exemplo:

- `feat(scoring): calculate brake release score`
- `fix(input): normalize inverted G29 pedals`
- `docs(sdd): record calibration acceptance criteria`
- `chore(release): prepare version 0.2.0`

Os próximos commits do projeto devem usar `camposezek@gmail.com` como e-mail do autor.
O histórico anterior não será reescrito.

## Gate de release

Antes de criar uma tag:

- todos os critérios previstos para a versão estão registrados no SDD;
- os testes automatizados passam na `main`;
- a validação de hardware exigida pela versão foi concluída ou está explicitamente
  registrada como limitação;
- `pyproject.toml` e `pilotagem_virtual.__version__` possuem a mesma versão;
- o `CHANGELOG.md` contém a seção final da versão, sem itens ambíguos;
- os dois executáveis são gerados pelo workflow Windows.

Exemplo para a versão `0.1.0`:

```bash
git tag -a v0.1.0 -m "Pilotagem Virtual 0.1.0"
git push origin v0.1.0
```

O push da tag executa o workflow **Release Pilotagem Virtual**, que valida a versão,
executa os testes, gera os dois pacotes Windows e cria a GitHub Release.
Se a release tiver sido criada pela interface do GitHub junto com a tag, o workflow
detecta a release existente e adiciona ou substitui os dois pacotes automaticamente.
