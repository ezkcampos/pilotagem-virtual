# Candidata integrada 0.2.0

**Data:** 2026-09-03 · **Versão de desenvolvimento:** `0.2.0.dev0`

Esta candidata reúne o escopo funcional da Spec 002 em `PilotagemVirtual.exe`.
O exercício original e o diagnóstico G29 continuam disponíveis. A implementação
está na branch de desenvolvimento; validação física, merge, tag e release permanecem
como gates separados.

## Entrega integrada

- Catálogo em JSON com oito níveis, de intensidade fixa ao limite didático.
- Calibração guiada: 2 s de repouso, duas aplicações em 4 s, deadzone calculada,
  máximo de treino ajustável, prévia, salvamento local e restauração do perfil G29.
- Gráfico QPainter reutilizável com tempo, entrada do freio, alvo tracejado,
  tolerância hachurada, execução contínua, cursor temporal, cruzes fora da faixa,
  lacunas visíveis e consulta textual da leitura real mais próxima.
- Modos Guiado, Memória e Avaliação. Memória mostra o percentual atual e oculta
  a comparação durante a execução. Avaliação oculta percentual, execução, alvo,
  tolerância e consultas; o resultado revela a comparação completa. A aquisição,
  cenário e fórmula são iguais entre modos.
- Pontuação `brake-v1`, pura e determinística. Sustentação, patamares, liberação,
  curva e limite possuem quatro subnotas, pesos explícitos e feedback pela maior
  penalidade normalizada. Séries originais alimentam erro e tempo; grade derivada
  de 120 Hz serve somente para eventos e suavidade.
- Nível 7 combina mapa e gráfico. O nível 8 executa uma etapa pontuada com ABS e
  outra sem ABS, vinculadas por uma identidade de comparação. Inclui superfícies
  seca, molhada, escorregadia e variável, histerese, recuperação e fim travado.
  Toda saída recebe o rótulo “Simulação didática”. Não há sinal sonoro nesta versão.
- SQLite local versionado guarda perfis e snapshots completos das tentativas.
  IDs tornam novas tentativas de escrita idempotentes; se a escrita falhar, o
  resultado permanece em memória e bloqueia outra tentativa até o retry.

## Decisões experimentais fechadas

Os oito níveis ficam livres. Percentuais, durações, tolerâncias e pesos iniciais
estão no catálogo/fórmula e serão ajustados com uso real. O gráfico do nível 7
fica abaixo do mapa. As duas etapas do nível 8 recebem nota e usam condições
equivalentes. O modo Memória mantém o percentual ao vivo; Avaliação o remove.

A política de fronteiras `inside-endpoint-hold-max-25ms-v1` usa apenas amostras
dentro da fase avaliada. Ela admite a estimativa constante da borda pelo ponto
interno mais próximo por até 25 ms e registra a duração estimada. Uma borda sem
cobertura ou lacuna maior invalida a nota. Assim, valores anteriores à janela não
alteram CA2-002 e uma captura normal não depende de coincidência exata do poll.

## Verificação antes do build

- Suíte local: **98 testes aprovados**.
- Séries perfeitas, fora da faixa, abruptas, ruidosas e com reaplicação.
- Limite igual, superior e variável; múltiplos travamentos, recuperação e fim
  travado; replay determinístico.
- Catálogo, perfis, snapshots idempotentes, repetição, modos e legado.
- Trinta repetições integradas criam IDs, buffers e registros distintos.
- Capturas Qt em 1920×1080 e 2560×1080 conferem a legibilidade dos níveis 1, 7 e
  8. Os tempos finais do Windows serão acrescentados com o executável Actions.

Os testes falsos não validam a sensibilidade, calibração física, frequência ou
compreensão do feedback com o G29. Esses pontos serão testados juntos no build
integrado, evitando novos ciclos manuais por incremento.

