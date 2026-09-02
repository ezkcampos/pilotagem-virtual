# Changelog

Todas as mudanças relevantes do projeto serão registradas neste arquivo.

O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/), e o
projeto usa [Versionamento Semântico](https://semver.org/lang/pt-BR/) enquanto estiver
na série inicial `0.x`.

## [Unreleased]

### Adicionado

- Spec 002 de fundamentos do freio e telemetria visual, com alvo na versão 0.2.0.
- Registro da aprovação do quality gate da Spec 002 em 2026-09-02, com sete decisões
  adiadas explicitamente para experimentação no Plan.
- Plano técnico da Spec 002 em revisão, com arquitetura, hipóteses, incrementos,
  rastreabilidade e builds Windows pelo GitHub Actions.

### Alterado

- Revisão preparatória do Plan 002 contra o código: restrições de SDL/Qt,
  timestamps e fronteiras ainda por validar, integridade dos dados, métricas,
  compatibilidade legada e dependências dos incrementos. Gate do Plan pendente.
- Pontuação da família de sustentação prevista já em P2, com pesos e escalas
  sujeitos aos experimentos; persistência de snapshots para reprocessamento.

### Corrigido

- Título de CA2-004 alinhado ao modo Avaliação, preservando o enunciado aprovado.
- Descrição da aquisição na Spec 002 distingue o alvo de 120 Hz de uma medição.

### Planejado

- Oito níveis de fundamentos do freio, gráfico temporal e modos Guiado, Memória e Avaliação.
- Comparação didática com e sem ABS, mantendo o diagnóstico do G29 separado.
- Assistente de calibração e persistência do perfil do dispositivo.
- Pontuação determinística e feedback imediato da tentativa.
- Histórico local completo e comparação entre sessões permanecem no backlog da
  Spec 001, fora da 0.2.0; nesta Spec, preservar dados para resultado/reprocessamento.

## [0.1.0] - 2026-09-02

### Adicionado

- Aplicativo principal `PilotagemVirtual.exe`, separado da ferramenta de diagnóstico.
- Mapa 2D do exercício com reta, curva e marcadores de frenagem, turn-in, trail,
  ápice e aceleração.
- Primeiro cenário de oito segundos para curva média à direita.
- Fluxo Preview → Countdown → Running → Completed/Cancelled.
- Captura normalizada de volante, freio, acelerador e embreagem durante a tentativa.
- Contratos de dispositivo, adaptador SDL/Pygame e adaptador falso para testes.
- Ferramenta permanente `PilotagemVirtual-G29-Spike.exe` para diagnóstico do G29.
- Exportação JSONL bruta em um caminho escolhido pelo usuário.
- Workflows Windows para testar e empacotar os dois executáveis.
- Workflow de release para publicar os dois pacotes ao enviar uma tag `vX.Y.Z`.
- Documentação SDD da Spec 001, pesquisa, plano técnico e tarefas.

### Alterado

- Pedais do G29 passam a usar a normalização `(1 - valor_bruto) / 2`, corrigindo o
  sentido invertido observado no hardware real.
- A ferramenta de diagnóstico exibe nomes e valores normalizados sem alterar o
  conteúdo bruto da captura JSONL.

### Evidências

- Captura real do G29 com 6.908 amostras em 55,26 segundos.
- Aquisição observada de aproximadamente 125 Hz.
- 24 testes automatizados aprovados localmente antes da preparação da release.

### Limitações conhecidas

- O assistente de calibração, a pontuação e o histórico ainda não fazem parte desta
  versão.
- Botões, hats e desconexão/reconexão ainda precisam de validação manual no G29.

[Unreleased]: https://github.com/ezkcampos/pilotagem-virtual/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/ezkcampos/pilotagem-virtual/releases/tag/v0.1.0

