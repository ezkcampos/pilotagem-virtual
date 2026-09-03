# P0 — Contagem de preparação

**Data:** 2026-09-03 · **Solicitação:** o usuário relatou que a ausência de
contagem visível atrapalhou as medições físicas e pediu pelo menos 3 segundos.

## Comportamento

Após confirmar a prontidão dos eixos, o experimento mostra **3 → 2 → 1 → VALENDO**
em uma faixa grande acima do gráfico. Funciona na thread principal e no worker,
inclusive com desenho desligado, e recomeça em toda nova medição.

A GUI pinta o primeiro número antes de confirmar o início do relógio ao sampler.
Atraso na entrega do sinal de prontidão não consome os três segundos. A captura
começa na primeira leitura real a partir desse prazo e mantém seus 10 segundos
inteiros; não há preenchimento ou alteração dos timestamps.

O JSON `acquisition-probe-v3` separa `initialization.samples`, `countdown.samples`
e `samples` da medição. Registra o início da preparação e sua duração mínima,
além dos números exibidos com timestamps em `ui.countdown_displays`. Leituras
e quadros anteriores à captura não entram nas métricas da janela medida.
Cancelar, desconectar ou fechar durante a contagem preserva o relatório sem
inventar uma tentativa, taxa ou origem de captura.

Este incremento sucede o [build de prontidão](p0-readiness.md). O treino legado
já tinha preparação de três segundos. A validação física T016 permanece aberta;
o [roteiro de teste](p0-acquisition-test.md) agora informa quando iniciar o movimento.

## Verificação

- Suíte local: **77 testes passaram em 18,95 s**.
- Testes reais de Qt observam 3, 2, 1 e VALENDO, visibilidade com/sem desenho e
  prazo mínimo, além da janela de captura completa.
- Relógio controlado verifica fronteiras exatas e atraso de quatro segundos na
  confirmação da GUI, sem reduzir a preparação.
- Cancelamento, fechamento, repetição e desconexão durante a contagem cobertos
  nos dois contextos; regressões existentes incluem 30 ciclos do worker.
- Faixa conferida em capturas Qt offscreen de 1920×1080 com gráfico e 2560×1080
  sem gráfico, ambas com fonte falsa e sequência completa. Evidência local em
  `build/p0-countdown/`; interação física continua pendente.

## Build Windows

Build pelo GitHub Actions e conferência do executável pendentes neste registro.
