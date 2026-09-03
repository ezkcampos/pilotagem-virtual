# Pilotagem Virtual

Treinador modular de técnicas de pilotagem para volante e pedais, começando por trail braking.

**Versão estável:** `0.1.0` · **Build de desenvolvimento:** `0.2.0.dev0`

O projeto segue Spec-Driven Development (SDD). A versão 0.2.0 está integrada na
branch `feature/002-brake-control` e aguarda validação física e gate de release.

## Especificações

- [MVP — Treinador de trail braking](specs/001-trail-braking-mvp/spec.md)
- [Spec 002 — Fundamentos do freio](specs/002-brake-control-training/spec.md)
- [Tarefas da Spec 002](specs/002-brake-control-training/tasks.md)
- [Changelog](CHANGELOG.md)
- [Fluxo de contribuição e releases](CONTRIBUTING.md)

## Estado atual

`Candidata integrada da Spec 002 — validação Windows/G29 pendente`

O treinador principal e o diagnóstico são aplicativos separados:

- `PilotagemVirtual.exe`: oito fundamentos do freio, calibração, gráfico, pontuação,
  modos Guiado/Memória/Avaliação, ABS didático e exercício original preservado.
- `PilotagemVirtual-G29-Spike.exe`: ferramenta permanente de diagnóstico e exportação JSONL bruto.

O treinador oferece calibração personalizada persistente. Tentativas guardam localmente
os snapshots necessários para repetir os cálculos. Histórico navegável e comparação
entre sessões permanecem no backlog, fora da 0.2.0.

## Executável do treinador

Na branch `feature/002-brake-control`, o treinador integrado está em
`PilotagemVirtual.exe`. O pacote mantém o experimento P0 e o diagnóstico separado.
Consulte o [registro da candidata integrada](specs/002-brake-control-training/v020-integrated.md).

O executável principal é produzido pelo workflow **Build Pilotagem Virtual Trainer**.

1. Abra a aba **Actions** do repositório.
2. Entre na execução mais recente de **Build Pilotagem Virtual Trainer**.
3. Baixe o artefato `PilotagemVirtual-windows-x64`.
4. Extraia o `.zip` inteiro e execute `PilotagemVirtual.exe`.

## Executável de diagnóstico

O diagnóstico continuará sendo produzido pelo workflow **Build G29 Hardware Spike** no GitHub Actions.

1. Abra a aba **Actions** do repositório.
2. Entre na execução mais recente de **Build G29 Hardware Spike**.
3. Baixe o artefato `PilotagemVirtual-G29-Spike-windows-x64`.
4. Extraia o `.zip` e execute `PilotagemVirtual-G29-Spike.exe`.

Ao iniciar uma gravação, o aplicativo abre uma janela para escolher a pasta e o nome do arquivo JSONL.

## Releases

As versões estáveis são publicadas na aba **Releases**. Cada release contém dois
pacotes independentes para Windows x64: o treinador e o diagnóstico do G29.

O desenvolvimento segue SDD e Versionamento Semântico. Depois da importação inicial
da `0.1.0`, cada incremento é desenvolvido em branch própria, integrado à `main` e
documentado no `CHANGELOG.md` antes da próxima tag.
