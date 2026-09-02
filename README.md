# Pilotagem Virtual

Treinador modular de técnicas de pilotagem para volante e pedais, começando por trail braking.

**Versão atual:** `0.1.0`

O projeto segue Spec-Driven Development (SDD). A versão estável é a 0.1.0;
a Spec 002 e seu plano foram aprovados e P0 está em desenvolvimento na branch
`feature/002-brake-control`. A aquisição nova ainda depende de validação física.

## Especificações

- [MVP — Treinador de trail braking](specs/001-trail-braking-mvp/spec.md)
- [Spec 002 — Fundamentos do freio](specs/002-brake-control-training/spec.md)
- [Tarefas da Spec 002](specs/002-brake-control-training/tasks.md)
- [Changelog](CHANGELOG.md)
- [Fluxo de contribuição e releases](CONTRIBUTING.md)

## Estado atual

`P0 da Spec 002 — base de aquisição e medição; treino legado preservado`

O treinador principal e o diagnóstico são aplicativos separados:

- `PilotagemVirtual.exe`: treinador com mapa, cenário, contagem regressiva e captura normalizada.
- `PilotagemVirtual-G29-Spike.exe`: ferramenta permanente de diagnóstico e exportação JSONL bruto.

O treinador usa o perfil observado na captura real do G29. Calibração personalizada,
pontuação, gráfico de treino e novos níveis serão adicionados após P0. Histórico
completo e comparação entre sessões permanecem no backlog, fora da 0.2.0.

## Executável do treinador

Na branch `feature/002-brake-control`, P0 já possui proteção de timestamps,
snapshots por tentativa e um modo experimental de medição. O pacote de
desenvolvimento inclui `run-p0-acquisition-probe.bat`; o treino normal continua
em `PilotagemVirtual.exe`. A escolha da arquitetura de aquisição ainda depende
de teste físico. Consulte as [evidências P0](specs/002-brake-control-training/p0-evidence.md)
e o [roteiro G29](specs/002-brake-control-training/p0-acquisition-test.md).

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
