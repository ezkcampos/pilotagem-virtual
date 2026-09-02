# Pilotagem Virtual

Treinador modular de técnicas de pilotagem para volante e pedais, começando por trail braking.

**Versão atual:** `0.1.0`

O projeto está sendo desenvolvido com uma abordagem de Spec-Driven Development (SDD). A especificação e o plano técnico foram aprovados, o hardware spike do G29 foi validado e o núcleo do MVP está em construção.

## Especificações

- [MVP — Treinador de trail braking](specs/001-trail-braking-mvp/spec.md)
- [Changelog](CHANGELOG.md)
- [Fluxo de contribuição e releases](CONTRIBUTING.md)

## Estado atual

`Build 1 — primeira fatia vertical do treinador`

O treinador principal e o diagnóstico são aplicativos separados:

- `PilotagemVirtual.exe`: treinador com mapa, cenário, contagem regressiva e captura normalizada.
- `PilotagemVirtual-G29-Spike.exe`: ferramenta permanente de diagnóstico e exportação JSONL bruto.

O Build 1 do treinador usa o perfil observado na captura real do G29. A calibração personalizada, a pontuação e o histórico serão adicionados nos próximos incrementos.

## Executável do treinador

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
