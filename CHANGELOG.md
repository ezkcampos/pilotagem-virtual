# Changelog

Todas as mudanças relevantes do projeto serão registradas neste arquivo.

O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/), e o
projeto usa [Versionamento Semântico](https://semver.org/lang/pt-BR/) enquanto estiver
na série inicial `0.x`.

## [Unreleased]

### Corrigido

- O gráfico do modo Guiado agora redesenha continuamente a linha azul da entrada
  do freio e o cursor temporal durante a tentativa, em vez de mostrá-los somente
  depois da conclusão.

## [0.2.0] - 2026-09-03

### Adicionado

- Candidata integrada 0.2.0.dev0 com oito níveis de fundamentos do freio, catálogo
  por dados e acesso separado ao trail braking original.
- Assistente de calibração do freio com repouso, duas aplicações, deadzone, máximo
  de treino, prévia, restauração e perfil local transacional em SQLite.
- Gráfico temporal reutilizável com alvo, tolerância, execução, cursor, lacunas,
  marcas fora da faixa e inspeção textual de leituras reais.
- Pontuação determinística por sustentação, patamares, liberação, curva e limite,
  com subnotas, feedback e snapshots de tentativas idempotentes em SQLite.
- Modos Guiado, Memória e Avaliação e nível 7 com mapa e gráfico combinados.
- Nível 8 em duas etapas, com e sem ABS, superfícies didáticas fixa e variável,
  travamento, recuperação, atuação virtual e comparação de resultados.
- Contagem visível de 3 segundos no experimento P0, após prontidão dos eixos,
  com sinal “VALENDO” antes dos 10 s de captura, inclusive sem gráfico. JSON v3
  preserva as leituras de preparação separadas da medição.
- Confirmação nativa de inicialização dos eixos SDL, com zero legítimo preservado;
  treinador aguarda a primeira leitura antes de permitir uma tentativa.
- Relatório P0 v2 com espera inicial completa, identidade por execução e ciclo
  de vida. Launcher G29/worker salva automaticamente em `medicoes-p0`, inclusive
  cancelamento, timeout, desconexão e fechamento.

- Aprovação do Plan 002 e decomposição em Tasks em 2026-09-02; P0 autorizado,
  mantendo hipóteses experimentais e gates de hardware/merge/release separados.
- Sessões com identidade própria, snapshots imutáveis e contexto real de fronteira;
  diagnósticos de frequência por segundo, intervalos e lacunas da captura.
- Testes de integração/interface com dispositivo falso, 30 repetições e regressão
  do cenário legado nas duas resoluções previstas.
- Modo experimental de aquisição P0 no treinador, com fonte falsa/G29, thread
  principal/worker, carga visual e exportação JSON; worker permanece fora do
  caminho normal do treinador até validação física.
- CI Windows para testes na branch de desenvolvimento e identidade do commit
  nos relatórios dos builds manuais do treinador.
- Builds Windows de desenvolvimento P0 para treinador e diagnóstico (commit
  1cb48e8), com [evidências e roteiro de teste](specs/002-brake-control-training/p0-evidence.md).
- Análise de três capturas físicas do G29 em 2026-09-03: métricas recalculadas,
  integridade temporal e hashes dos originais registrados; evidência parcial da
  thread principal com gráfico, com queda de taxa e estado inicial a investigar.
- Segundo lote físico de P0 completa a comparação das quatro configurações:
  worker com gráfico observou 116,1 Hz e 58,9 FPS, tornando-se candidato preferido.
  Integração permanece pendente da investigação do estado inicial e da validação
  operacional; o treinador continua usando a thread principal.

- Spec 002 de fundamentos do freio e telemetria visual, com alvo na versão 0.2.0.
- Registro da aprovação do quality gate da Spec 002 em 2026-09-02, com sete decisões
  adiadas explicitamente para experimentação no Plan.
- Plano técnico da Spec 002, aprovado após revisão, com arquitetura, hipóteses, incrementos,
  rastreabilidade e builds Windows pelo GitHub Actions.

### Alterado

- Revisão preparatória do Plan 002 contra o código: restrições de SDL/Qt,
  timestamps e fronteiras ainda por validar, integridade dos dados, métricas,
  compatibilidade legada e dependências dos incrementos. Gate do Plan aprovado;
  validações experimentais permanecem pendentes conforme Tasks.
- Pontuação da família de sustentação prevista já em P2, com pesos e escalas
  sujeitos aos experimentos; persistência de snapshots para reprocessamento.

### Corrigido

- Estados ainda não inicializados deixam de aparecer como pedais a 50% no
  treinador; a captura do experimento começa somente após confirmação dos eixos.
- Fechamento síncrono do experimento na thread principal e recuperação manual
  quando o relatório não pode ser salvo ao fechar.

- Captura do treinador usa timestamps da leitura e rejeita eixos inválidos,
  duplicação temporal e fim de replay, sem fabricar amostras.
- Desconexão via eventos SDL, proteção contra troca de dispositivo durante a
  tentativa e separação dos temporizadores de leitura e desenho no treinador.

- Título de CA2-004 alinhado ao modo Avaliação, preservando o enunciado aprovado.
- Descrição da aquisição na Spec 002 distingue o alvo de 120 Hz de uma medição.

### Planejado

- Proposta de [curvas de frenagem personalizadas](specs/backlog/custom-brake-curves.md),
  editáveis em onze pontos a cada 10% do tempo; versão de entrega ainda não definida.

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

