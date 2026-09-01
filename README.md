# Pilotagem Virtual

Treinador modular de técnicas de pilotagem para volante e pedais, começando por trail braking.

O projeto está sendo desenvolvido com uma abordagem de Spec-Driven Development (SDD). Nesta etapa, o foco está na definição do produto e dos critérios de aceitação antes de decisões de arquitetura e implementação.

## Especificações

- [MVP — Treinador de trail braking](specs/001-trail-braking-mvp/spec.md)

## Estado atual

`Build 0 — coletor de diagnóstico do G29`

O primeiro build é um coletor de dados brutos do volante e dos pedais. Ele permite escolher onde salvar uma captura `.jsonl`, que será usada para validar o mapeamento e o comportamento real do G29 antes do desenvolvimento da calibração definitiva.

## Executável de diagnóstico

O executável para Windows é produzido pelo workflow **Build G29 Hardware Spike** no GitHub Actions.

1. Abra a aba **Actions** do repositório.
2. Entre na execução mais recente de **Build G29 Hardware Spike**.
3. Baixe o artefato `PilotagemVirtual-G29-Spike-windows-x64`.
4. Extraia o `.zip` e execute `PilotagemVirtual-G29-Spike.exe`.

Ao iniciar uma gravação, o aplicativo abre uma janela para escolher a pasta e o nome do arquivo JSONL.
