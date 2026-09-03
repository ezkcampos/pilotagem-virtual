# Tarefas 002 — Fundamentos do freio e telemetria visual

**Status:** P0 em desenvolvimento
**Plan aprovado:** 2026-09-02 — “bora, pode seguir”, após revisão de 0bbf068
**Spec:** [spec.md](spec.md) · **Plano:** [plan.md](plan.md)
**Branch:** feature/002-brake-control · **Versão-alvo:** 0.2.0

## Convenções e gates

- Uma tarefa só recebe `[x]` com comportamento verificado e evidência indicada.
- `[HW]` depende de G29 real no Windows; testes falsos não a concluem.
- E01–E07 são hipóteses, com fechamento antes da entrega da família afetada.
- P0 libera P1 após decisão registrada de aquisição. Experimentos não promovem
  automaticamente worker ao treinador. P2 depende também da decisão de fronteiras.
- Merge, tag e release continuam dependendo de autorização própria.

## P0 — Contratos e aquisição

| Estado / ID | Entrega | Dependências | Requisitos / conclusão verificável |
|---|---|---|---|
| [x] T000 | Registrar aprovação e decomposição | Plan aprovado | Aprovação registrada; tarefas com dependências e gates neste documento. |
| [x] T010 | Contratos e dispositivo falso | T000 | RF2-012, RNF2-002: relógio injetável, encerramento explícito, exaustão sem duplicar a última leitura. |
| [x] T011 | Integridade e snapshot da sessão | T010 | RF2-012/025, CA2-008: timestamps crescentes, identidade nova, fronteira final real, cancelamento com motivo, snapshot imutável; repetir 30 vezes sem resíduo. |
| [x] T012 | Coordenador e proteção do legado | T011 | RF2-012, seção 4: quatro eixos, contagem e mapa preservados; UI recebe estado, timestamp vem do dispositivo; seleção bloqueada durante execução; desconexão visível. |
| [x] T013 | Instrumentação de aquisição | T010/T011 | RNF2-002/003/004: frequência por segundo, percentis, lacunas, atraso de entrega e quadros desenhados; séries irregulares e vazias testadas. |
| [x] T014 | Experimento SDL/Qt reproduzível | T010/T013 | RNF2-002/003: thread principal e worker isolados, backend inicializado/fechado no contexto proprietário, entrada falsa e real, carga visual, relatório e testes de encerramento. |
| [ ] T015 | Experimento de fronteiras de janela | T011 | RF2-026, CA2-002: comparar interpolação com/sem amostras externas, timestamps deslocados e lacunas; registrar decisão ou mudança de requisito ainda necessária antes de P2. |
| [ ] T016 [HW] | Validar aquisição e escolher arquitetura | T012/T014, builds Windows | G29: 10 s sem/com desenho, redimensionar, cancelar, desconectar/reconectar e fechar; registrar PC, driver, SHA, taxas/lacunas e decisão. Não presumir que 8 ms comprova 120 Hz. |
| [x] T017 | Distinguir prontidão inicial e preservar encerramentos | Evidências parciais de T016 | Flags nativas por eixo, início bloqueado até prontidão, espera preservada em JSON v2, timeout, autosave e fechamento; testes de backend virtual/fluxos em [p0-readiness.md](p0-readiness.md). Confirmação física permanece em T016. |

## P1 — Calibração e persistência

| Estado / ID | Entrega | Dependências | Requisitos / conclusão verificável |
|---|---|---|---|
| [ ] T020 | Perfil validado e normalização | P0 | RF2-001–006: repouso, máximo físico/treino e deadzone; inversão, não finitos, eixos ausentes e preservação de volante/acelerador/embreagem. |
| [ ] T021 | SQLite e migrações de perfil | T020 | RF2-005/006, RNF2-001: transações, falha/corrupção sem perder último perfil; identidade compatível; restauração explícita. |
| [ ] T022 | Assistente de calibração | T020/T021 | RF2-001–006, CA2-001: etapas completas, prévia e cancelar sem modificar perfil; teclado e reinício do aplicativo. |
| [ ] T023 [HW] | Validar perfil personalizado | T022, build Windows | CA2-001: 0/100%, deadzone, conforto, demais eixos e perfil restaurado após reinício do executável. |

## P2 — Catálogo e níveis 1–2

| Estado / ID | Entrega | Dependências | Requisitos / conclusão verificável |
|---|---|---|---|
| [ ] T030 | Contrato versionado e adaptador legado | P0/P1, T015 resolvida | RF2-007–009, seção 11: JSONs válidos, keyframes/janelas, mensagens de erro e arquivo legado intacto. |
| [ ] T031 | Fechar E01/E04/E05 para sustentação | T030 | RF2-022/026, CA2-002: níveis livres; parâmetros, escalas, fases e pesos registrados; séries perfeitas, ruído, atraso, overshoot e fora da faixa. |
| [ ] T032 | Pontuar sustentação e gerar feedback | T031 | RF2-021/022/024/025/026: nota, quatro métricas, feedback por maior penalidade ativa; replay idêntico e invariância pré-janela. |
| [ ] T033 | Salvar tentativas e snapshots | T021/T032 | RF2-012/025: originais, perfil/cenário/fórmula imutáveis, falha de cálculo/escrita, retry idempotente e fila limitada. |
| [ ] T034 | Catálogo, execução e resultado básico | T030–T033 | RF2-007–011, CA2-008: níveis 1–2 funcionais, nota/subnotas/feedback, repetir e avançar sem dados anteriores; legado acessível. |

## P3 — Gráfico e resultado

| Estado / ID | Entrega | Dependências | Requisitos / conclusão verificável |
|---|---|---|---|
| [ ] T040 | Widget reutilizável de gráfico | P2 | RF2-013–018, RNF2-006/007: eixos, legenda, estilos/padrões, tolerância e cursor; lacunas visíveis e redução só visual. |
| [ ] T041 | Comparação e inspeção de valores/eventos | T040 | RF2-017–019, CA2-003: alvo/execução completos, tempos legíveis e alternativa textual; consulta usa série original. |
| [ ] T042 | Validar gráfico integrado | T041 | RNF2-002–005: dispositivo falso, capturas 1920×1080/2560×1080, taxas e latência; repetir medição com G29. |

## P4 — Métricas e níveis 3–6

| Estado / ID | Entrega | Dependências | Requisitos / conclusão verificável |
|---|---|---|---|
| [ ] T050 | Fechar E04/E05 de patamares/liberação | P2/P3 | RF2-023–026, CA2-005: alvos, filtros, escalas/pesos e feedback com sintéticos; transições e sustentação separadas. |
| [ ] T051 | Métricas e níveis 3–6 funcionais | T050 | RF2-021–026: perfeito, ruidoso, abrupto, atrasado, reaplicações e eventos ausentes; suave não premia pedal imóvel. |
| [ ] T052 [HW] | Validar tolerâncias e repetição | T051 | E04/E05: G29, ruído sem falsa reaplicação, movimentos reais preservados e feedback compreensível. |

## P5 — Assistência e nível 7

| Estado / ID | Entrega | Dependências | Requisitos / conclusão verificável |
|---|---|---|---|
| [ ] T060 | Fechar E02/E03 e política visual | P3/P4 | Seção 9, CA2-004: duas variantes Memória; Avaliação sem execução/percentual/tooltip/texto acessível residual; aquisição/alvo/fórmula iguais. |
| [ ] T061 | Nível 7 e mapa junto ao gráfico | T060, E04/E05 da curva | RF2-020, CA2-006: alvos novos de freio/esterço/acelerador; marcadores legíveis nas duas resoluções; cenário legado intacto. |

## P6 — Modelo didático com e sem ABS

| Estado / ID | Entrega | Dependências | Requisitos / conclusão verificável |
|---|---|---|---|
| [ ] T070 | Modelo determinístico versionado | P0–P5 | RF2-028–031, RNF2-008: limite fixo e variável, igualdade ao limite, histerese, recuperação, múltiplos eventos/fim travado, replay igual ao vivo. |
| [ ] T071 | Fechar E04/E05/E06/E07 do nível 8 | T070 | RF2-027/033: demonstração versus tentativa pontuada, condições equivalentes, pesos e som definidos por evidências. |
| [ ] T072 | Duas etapas e resultado didático | T071 | RF2-027–033, CA2-007: séries distintas, travamentos no gráfico, tempo útil/recuperação, rótulos Simulação didática; repetir sem misturar etapas. |

## P7 — Validação integrada e builds

| Estado / ID | Entrega | Dependências | Requisitos / conclusão verificável |
|---|---|---|---|
| [x] T080 | CI de testes e builds independentes | T000; executada também nos incrementos | Dois workflows Windows; branch/SHA explícitos, testes e artefatos; nenhum build local substitui Actions. |
| [ ] T081 | Regressão integrada e desempenho | P0–P6 | RF2-001–033, RNF2-001–009, CA2-001–008: testes de domínio/UI/falha, offline, resoluções, 30 repetições, latência ≤500 ms e aquisição ≥60 Hz. |
| [ ] T082 [HW] | Executáveis e G29 no PC de referência | T080/T081 | Executar pacotes Actions, reinício/perfil, cancelamento/desconexão/reconexão, 30 repetições e diagnóstico; registrar evidência e limitações. |
| [ ] T083 | Gate da 0.2.0 e preparação da release | T082 e autorização explícita | Conferir critérios, autorizar merge, testar main, sincronizar versões/changelog; tag/release somente com autorização correspondente. |

## Evidências

- Base antes da implementação: 24 testes aprovados, registro no Plan, seção 14.
- Resultados incrementais serão registrados aqui e em relatórios vinculados,
  distinguindo testes automáticos, experimentos falsos e hardware real.

- P0 / T010–T012: 48 testes passaram localmente (Python 3.12.4), incluindo
  regressão Qt com fonte falsa em 1920×1080 e 2560×1080; aquisição real e
  confirmação visual/manual permanecem no gate T016.

- P0 / T013–T014: 54 testes aprovados, incluindo 30 ciclos do worker.
  Medições exploratórias, limites e contraexemplo de fronteiras em [p0-evidence.md](p0-evidence.md).
  T015 e T016 continuam abertas; não há aprovação final de aquisição real.

- P0 / T016 (2026-09-03): três capturas físicas de 10 s, todas em principal/com
  gráfico, conferidas contra as amostras originais: 85,3–108,2 Hz, mínimo por
  segundo 60–93 e 58,9 FPS. Evidência parcial em [p0-evidence.md](p0-evidence.md)
  e [p0-g29-summary.json](p0-g29-summary.json). Queda de taxa ao longo da captura
  e estado inicial com quatro eixos zerados exigem investigação; comparação
  entre configurações e ciclo de desconexão/fechamento continuam pendentes.

- P0 / T016, segundo lote (2026-09-03): completada a comparação básica das quatro
  configurações, com seis capturas no total. Principal sem gráfico: 118,5 Hz;
  worker sem/com gráfico: 118,2/116,1 Hz, mínimo por segundo 118/113. Worker é o
  candidato preferido, ainda sem integração no treinador. Estado inicial zerado
  também ocorreu no worker; prontidão, redimensionamento e ciclo de vida mantêm
  o gate aberto. Análise e hashes no mesmo relatório/resumo de P0.

- T080: dois builds Windows de 1cb48e8 concluídos; pacote do treinador executado
  com fonte falsa, SHA conferido no relatório. Artefatos e limitações em [p0-evidence.md](p0-evidence.md).

- T017/T080: build Trainer 33761741323 de 21a5489 concluído, 70 testes aprovados
  localmente e em ambos os jobs Windows; executável baixado conferido com fonte
  falsa e JSON v2. Novo pacote/roteiro em [p0-readiness.md](p0-readiness.md).
  O diagnóstico continua independente. T016 aguarda a confirmação física do incremento.
