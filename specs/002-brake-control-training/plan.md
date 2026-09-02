# Plano técnico 002 — Fundamentos do freio e telemetria visual

**Status:** Em revisão
**Fase SDD:** Plan
**Versão-alvo:** 0.2.0
**Data:** 2026-09-02
**Spec relacionada:** [spec.md](spec.md)
**Plano anterior:** [Spec 001 — plano](../001-trail-braking-mvp/plan.md)
**Branch:** feature/002-brake-control
**Base analisada:** 3a4e7af03af39cafc58ed55ffe2db8369e4cbe3b, descendente de
742d64cfced100512b022d33f9508360dcc39a5e (main / v0.1.0 na abertura da fase).

## 1. Autorização e fronteira da fase

O responsável aprovou o quality gate da Spec 002 em 2026-09-02, autorizando que
as sete decisões abertas da seção 17 fossem explicitamente adiadas para
experimentação e definição no Plan. Aprovação nesta conversa: “aprovo, pode
continuar com o trabalho”. Ela autoriza planejamento; não representa validação
de hardware, aprovação das hipóteses abaixo ou gate de release.

Este plano define arquitetura, contratos, hipóteses, sequência e validação.
Seguindo o fluxo da Spec 001, a decomposição em tasks.md acontece depois do
quality gate deste plano. Não há implementação funcional ou build novo concluído
nesta fase. O merge na main continua pendente de autorização explícita.

## 2. Estado real do código

| Área | Base existente | Mudança necessária |
|---|---|---|
| Stack | Python 3.12 no CI, PySide6 6.11.2, pygame 2.6.1, PyInstaller 6.22.2 | Reutilizar o stack; evitar dependências novas no primeiro incremento. |
| trainer_app.py | Cenário fixo; QTimer de 8 ms lê G29 e atualiza widgets | Separar aquisição, sessão e renderização; configuração do timer não comprova frequência efetiva. |
| domain/calibration.py | Normaliza quatro comandos; perfil observado e máximo confortável | Adicionar deadzone do freio, assistente, validação e persistência; preservar os demais eixos. |
| domain/scenario.py | Exige direção, geometria e marcadores; duração de 5–10 s | Suportar exercícios sem mapa e manter compatibilidade legada. |
| domain/session.py | Preview, Countdown, Running, Completed, Cancelled; amostras em memória | Reutilizar estados; definir identidade, validade, fronteiras temporais e snapshot final. |
| Resultado | Exibe quantidade de amostras, sem nota | Implementar gráfico, métricas, pontuação e feedback. |
| Persistência | Não existe módulo na árvore atual | Implementar SQLite conforme direção do plano 001; não presumir histórico pronto. |
| Diagnóstico | Entrada spike_main.py e workflow próprios | Manter aplicativo e captura JSONL bruta independentes. |
| Testes | Calibração, eixos, cenários, sessão e captura do spike | Expandir com contratos, séries sintéticas, falhas e interface. |

O cenário medium_right_v1.json dura 8 s e possui marcadores em progresso 0,20
(frear), 0,42 (turn-in), 0,52 (trail), 0,70 (ápice) e 0,84 (acelerar).
Não contém curvas-alvo ou pesos. O nível 7 reutilizará geometria e marcadores;
alvos serão uma definição nova e versionada, sem alterar o arquivo legado.

NumPy e SQLite aparecem no plano 001. Nesta entrega, começar com Python e SQLite
da biblioteca padrão; adicionar biblioteca numérica somente se medições justificarem.
Histórico completo e comparação entre sessões continuam no backlog da Spec 001.
A 0.2.0 preservará dados para resultado/reprocessamento sem acrescentar uma tela
de histórico ao escopo desta Spec.

## 3. Arquitetura e propriedade dos dados

Manter dois produtos desktop: treinador e diagnóstico. No treinador:

- input/: detecção, conexão, leitura bruta e desconexão.
- domain/: calibração, exercício, keyframes, janelas, amostras e estados.
- app/ (novo): comandos, coordenação, snapshots e conclusão.
- scoring/ (novo): validação, métricas, subpontuações e feedback puros.
- simulation/ (novo): modelo didático e eventos de travamento.
- persistence/ (novo): perfis, tentativas e migrações SQLite.
- ui/: assistente, catálogo, gráfico, mapa, resultado e política de assistência.

O domínio não importa Qt, Pygame ou SQLite. Adaptador falso e relógio injetável
permitem testes sem G29. O gravador é dono da série completa. A interface recebe
snapshots/lotes e não consulta o joystick nem altera gravações. Ao concluir,
congelar amostras e metadados antes de pontuar. Reduzir pontos para desenhar nunca
reduz a série usada no cálculo.

### 3.1 Aquisição e renderização

Proposta: worker dedicado, com inicialização, enumeração, abertura, bombeamento
de eventos SDL, leitura e encerramento no mesmo contexto. Candidato: QObject em
QThread, agendado por relógio monotônico com alvo de 120 Hz. Validar a combinação
SDL/Qt/G29 no Windows antes de consolidar. Não mover apenas pygame.event.pump()
e deixar o restante do backend em outra thread.

A UI atualiza a até 60 FPS em temporizador próprio; Qt Widgets fica na thread
da UI. Publicar último estado para medidores e lotes incrementais para o gráfico,
evitar redesenho por amostra. Serializar iniciar/cancelar/trocar dispositivo;
identificar a tentativa para descartar eventos atrasados. Congelar perfil durante
execução. Fechamento cancela coleta e encerra worker e banco.

Experimento inicial: medir leitura sem gráfico, com gráfico e durante
redimensionamento. Se worker SDL não for estável, registrar evidências e revisar
a arquitetura antes de prosseguir. Manter polling na UI só pode ser alternativa
se cumprir as mesmas metas mensuradas; não basta funcionar visualmente. Não
alterar o diagnóstico para forçar a arquitetura do treinador.

### 3.2 Tempo e integridade

Usar timestamp de RawInputState e origem monotônica da tentativa. Countdown fica
fora da execução. Não criar amostras para compensar frames perdidos nem repetir o
último valor como se fosse nova aquisição. Reinício cria novo ID, esvazia buffers
e remove eventos/resultado anteriores.

Validade candidata: timestamps estritamente crescentes, valores finitos, conexão
contínua, cobertura das janelas, pelo menos 60 amostras/s em cada segundo completo
e nenhum intervalo acima de 50 ms. Limites sujeitos ao experimento de aquisição;
registrar também média, percentis e maior intervalo. Não aprovar só pela média total.

Cancelada, desconectada ou inválida não recebe nota comparável; guardar motivo e
oferecer repetir. Nota 0–100 se aplica à tentativa concluída válida. Parar coleta
pela duração; interpolar limites apenas quando houver amostras reais delimitando
a janela. Não extrapolar trechos ausentes.

## 4. Calibração e persistência

Assistente registra repouso, máximo físico observado e máximo de treino escolhido.
Semente experimental: 2 s em repouso, duas aplicações completas e prévia interativa
antes da confirmação. Não orientar força excessiva nem chamar posição de força
ou pressão.

Perfil: versão de esquema, ID/revisão, GUID, nome, quantidade de eixos, mapeamentos,
valores brutos, deadzone, origem e data. Índice de enumeração não é identidade
persistente. GUID/eixos incompatíveis exigem escolha/calibração; GUID indisponível
não autoriza reutilização silenciosa. Calibrar freio preserva os outros comandos.

Sejam r repouso, p máximo físico, x sinal bruto, d deadzone na escala física e m
máximo de treino nessa escala:

- u = clamp((x - r) / (p - r), 0, 1)
- freio = clamp((u - d) / (m - d), 0, 1)

Validar finitude, amplitude mínima e 0 <= d < m <= 1. O sinal de p-r cobre inversão.
Deadzone vem do ruído de repouso com margem configurável. Migração do perfil atual:
d=0 e m=comfortable_max preservam comportamento. Restaurar o perfil observado é
uma ação explícita e reversível; perfil inválido/ausente abre o assistente.

SQLite fica no diretório local de dados do aplicativo, fora do executável. Usar
migrações incrementais e transações, mantendo último perfil válido se salvar falhar.
Por tentativa, preservar ID, versão do app, snapshot/hash do cenário, versão da
fórmula/modelo, modo/variante, perfil/revisão, amostras normalizadas originais,
eventos e resultado. Não substituir dado capturado por série filtrada. Captura
bruta dos eixos continua no diagnóstico separado. Falha de escrita fica visível;
manter resultado em memória para nova tentativa de salvamento.

## 5. Contrato dos exercícios

Adicionar schema_version separado da versão do conteúdo. Arquivos legados sem o
campo passam por adaptador explícito de curva. Não inventar alvo ou pontuação para
o arquivo legado durante migração.

Campos novos: tipo, categoria, ordem pedagógica, instruções, duração, modos,
política de assistência, curvas-alvo, tolerâncias, fases/janelas, métricas, pesos
e versões. Direção/geometria/marcadores de mapa são obrigatórios só para curva;
exercícios de freio têm fases temporais independentes de mapa.

Keyframes: progresso [0,1], valores [0,1], tempos estritamente crescentes, cobertura
dos extremos e interpolação linear. Patamares usam rampas curtas, sem dois pontos
no mesmo instante. Permitir alvos de esterço/aceleração no nível 7. Tolerância pode
variar por fase; faixa desenhada é limitada a 0–100%.

Validar IDs únicos, finitude, enumerações, modos, keyframes, janelas não ambíguas,
pesos não negativos com soma positiva e modelo ABS quando exigido. Duração normal
5–10 s; exceção didática precisa justificativa e limite validado. Recursos oficiais
são somente leitura. Cenário inválido não aparece como executável; informar o erro.

## 6. Hipóteses das sete decisões adiadas

São propostas para avaliação, não decisões já aprovadas ou experimentos realizados.
Registrar resultados antes de implementar o incremento afetado.

| ID | Decisão | Hipótese | Validação e ponto de decisão |
|---|---|---|---|
| E01 | Acesso aos níveis | Oito níveis livres, ordem recomendada, coerente com seção 11 da Spec | Percorrer catálogo/repetição/avanço. Bloqueio obrigatório exige revisão da Spec e persistência de progresso antes de implementação. |
| E02 | Modo Memória | Só percentual atual e instruções; comparar variante somente instruções | Treino nas duas variantes seguido de Avaliação; registrar variante, erro e consistência; não misturar resultados de assistências diferentes. |
| E03 | Gráfico da curva | Abaixo do mapa em 16:9; comparar lateral em 21:9 | Capturas em 1920×1080 e 2560×1080; marcadores e ações legíveis, sem sobreposição. |
| E04 | Alvos/tempos/tolerâncias | Sementes abaixo | Séries perfeitas/ruidosas e G29; tolerância não pune ruído nem esconde erro relevante. Fechar por família antes de pontuar. |
| E05 | Pesos | Distribuições da seção 8, iguais entre modos | Ordenação por qualidade em séries sintéticas e revisão do feedback antes do treino real. |
| E06 | Som de travamento | Alerta visual; som opcional desligado inicialmente | Avaliar compreensão/distração; se aprovado, tocar em transições com limitação de repetição, sem afetar captura. |
| E07 | Comparação ABS | Introdução com ABS seguida de tentativa sem ABS pontuada | Métricas separadas, mesmas condições; validar entendimento/repetição. Se ambas forem pontuadas, definir fórmula/identidade distintas. |

### 6.1 Sementes de cenários

Tempos são segundos desde execução, sem a contagem de 3 s. Tolerâncias em pontos
percentuais de entrada; valores não são recomendações universais para carros.

| Nível | Duração | Perfil candidato | Janela/ênfase | Tolerância |
|---|---:|---|---|---:|
| 1 | 6 s | 0→30% em 1 s; manter até 5 s; liberar até 6 s | Sustentação 1–5 s; aquisição separada | ±8 pp |
| 2 | 8 s | 0→60% em 1 s; manter até 7 s; liberar até 8 s | Sustentação 1–7 s | ±5 pp |
| 3 | 8 s | 0→80% em 1 s; manter até 3 s; 80→40% entre 3–4 s; manter até 7 s; liberar | Patamares e transição separados | ±7 pp |
| 4 | 6 s | 0→100% em 0,4 s; manter até 1 s; 100→70% até 1,5 s; manter até 5 s; liberar | Ataque e sustentação separados | ±8 pp |
| 5 | 8 s | 0→100% em 1 s; manter até 2 s; aliviar linearmente até 0% em 7 s | Liberação 2–7 s | ±8 pp |
| 6 | 8 s | 0→100% em 1 s; manter até 2 s; 100→60% até 2,5 s; 60→0% até 7 s | Transição e liberação separados | ±8 pp |
| 7 | 8 s | Frear em 1,6 s; pico até 2 s; alívio no turn-in em 3,36 s; zero no ápice em 5,6 s | Marcadores atuais; acelerar após 6,72 s | ±10 pp no freio |
| 8 | 8 s por etapa | Entrada intensa com ABS; aproximação ao limite didático de 80% sem ABS | Após 1 s, proximidade/travamento/recuperação | Faixa útil inicial 75–80% |

Keyframes completos e alvos de esterço/aceleração do nível 7 serão fechados em E04
antes de pontuá-lo; preservar cenário legado funcional. Não apresentar duas etapas
de 8 s como uma tentativa total de 8 s.

## 7. Gráfico, assistência e fluxo

Candidato: BrakeChartWidget com QPainter, sem nova biblioteca de gráficos.
Curva-alvo tracejada, tolerância preenchida/com padrão, execução contínua, legenda
textual. Eixos em segundos e 0–100%; cursor temporal ao vivo. Cache de elementos
estáticos; se necessário, reduzir desenho por mínimos/máximos por coluna de pixels,
preservando a série de cálculo.

Resultado mostra alvo/execução na mesma escala, saídas da tolerância, eventos de
liberação e travamentos. Seleção/cursor mostra valores e tempos; lista textual de
eventos dá alternativa à leitura do gráfico. Fundamentos priorizam gráfico;
curva preserva mapa e marcadores.

Guiado revela todos os elementos. Memória segue E02 e revela comparação no
resultado. Avaliação esconde execução em curvas, medidores, números, tooltips e
atalhos; pode mostrar instruções, contagem e tempo restante. Alvo e execução
aparecem no resultado. Modos não alteram aquisição, alvo, filtro ou fórmula.

Seleção mostra objetivo, duração, alvo, tolerância e modo. Resultado mostra nota,
subpontuações, feedback, repetir e próximo nível. Verificar 30 repetições sem
retornar ao catálogo, buffers residuais ou acúmulo de sinais. Troca de dispositivo
ou calibração durante execução deve ficar bloqueada ou cancelar explicitamente.

## 8. Pontuação determinística

Contrato: score(snapshot_tentativa, snapshot_cenario, versao_formula) devolve
métricas, subpontuações, nota, feedback e eventos, sem UI, relógio ou aleatoriedade.

1. Validar integridade e recortar janelas. Amostras externas não influenciam suas
   métricas; aquisição é avaliada separadamente.
2. Reamostrar a 120 Hz com interpolação linear entre amostras reais. Grade,
   fronteiras e arredondamento fazem parte da versão da fórmula.
3. Usar série original para erro e tempo na faixa. Para eventos/suavidade, testar
   filtro curto e limiares derivados do ruído, com parâmetros registrados.
4. Converter métricas em penalidades [0,1] por escalas explícitas do cenário.
   Subnota = 100 × (1 − penalidade); nota geral = média ponderada. Pesos zero
   desativam componentes; proibir soma zero.
5. Feedback vem da maior penalidade normalizada; empate por ordem fixa de IDs.
   Exibir métricas intermediárias; arredondar apenas na apresentação.

Tempo na faixa é fração de duração, ponderada no tempo; janela integralmente na
faixa recebe subnota máxima. Erro usa MAE; estabilidade usa dispersão na sustentação.
Aquisição exige permanência mínima candidata de 200 ms para não premiar uma
passagem isolada. Liberação mede MAE, início/fim, variação da taxa e reaplicações
significativas, com limiar de amplitude/duração. Ruído pequeno não vira evento;
filtragem não pode apagar reaplicação real. Parâmetros são fechados em E04/E05.

| Família | Pesos candidatos, soma 100 |
|---|---|
| Sustentação | Tempo na faixa 40; erro 25; estabilidade 20; aquisição 15 |
| Patamares/ataque | Erro por fase 30; aquisição/transição 30; overshoot 20; estabilidade 20 |
| Liberação/pré-trail | Erro 40; sincronização 25; suavidade 20; reaplicações 15 |
| Curva | Perfil de freio 40; sincronização com esterço 25; suavidade 20; aceleração 15 |
| Sem ABS | Tempo útil próximo ao limite 45; tempo travado 25; recuperação 20; suavidade 10 |

Cada fase tem peso explícito. Não travar produz penalidade zero nos componentes
travamento/recuperação, mas pedal solto perde tempo útil. Não tratar notas de
famílias, cenários/versões ou modos/variantes diferentes como equivalentes.

## 9. Modelo didático de ABS

Motor puro, passo fixo 1/120 s, parâmetros versionados e estado inicial explícito.
Começar por limite fixo 80%; depois perfis seco/molhado/escorregadio/variável por
dados. São exemplos didáticos, não medidas de veículos reais.

Sem ABS: ultrapassar limite entra em travamento; recuperar exige reduzir até
limite menos margem. Sementes: margem 3 pp e permanência de 100 ms. Medir tempo
da entrada em travamento até recuperação. Se terminar travado, fechar intervalo
no fim e marcar sem recuperação. Registrar contagem, intervalos, total e tempo
útil próximo ao limite; tempo travado não conta como útil.

Com ABS: entrada do usuário e atuação virtual são séries distintas. Controlador
limita/modula virtualmente sem alterar a curva capturada ou gerar force feedback.
Mesma duração, superfície e estado inicial permitem comparação didática. Não
introduzir aleatoriedade sem seed/versão registrados. Evitar velocidade/distância
quando dispensáveis; quando presentes, rotular Simulação didática no gráfico,
resultado e legenda.

Feedback ensina aliviar o suficiente e reaplicar próximo ao limite. Não recomendar
bombear continuamente nem apresentar técnica universal. Som e formato das etapas
continuam sujeitos a E06/E07.

## 10. Incrementos e dependências

| Incremento | Entrega verificável | Dependências / saída |
|---|---|---|
| P0 — Contratos e aquisição | Exercício/tentativa, frequência, experimento SDL/Qt | Resolver propriedade/estabilidade da leitura e proteger regressões. |
| P1 — Calibração | Assistente, deadzone, máximo de treino, SQLite, restauração | CA2-001; preservar quatro comandos e carregar perfil após reinício. |
| P2 — Exercícios básicos | Catálogo, contrato evoluído, legado, níveis 1–2 e repetição | CA2-002/008; E01/E04; janelas validadas. |
| P3 — Gráfico e resultado | Widget, cursor, tolerância e comparação | CA2-003; aquisição independente do desenho. |
| P4 — Métricas e níveis 3–6 | Pontuação, feedback, patamares e liberação | CA2-005; E04/E05 por família; sintéticos antes do G29. |
| P5 — Assistência e curva | Três modos, mapa + gráfico, nível 7 | CA2-004/006; E02/E03 e alvos da curva fechados. |
| P6 — ABS didático | Duas etapas, modelo, eventos e métricas | CA2-007; E06/E07 e recuperação definidos. |
| P7 — Validação 0.2.0 | Builds Windows, regressão, 30 repetições, desempenho | Todos os critérios; autorização de merge separada. |

Commits pequenos por incremento; changelog/evidências atualizados ao entregar
comportamento. Tasks detalhará dependências e critérios individuais após o gate
deste plano. P2 pode usar métricas mínimas para CA2-002; a consolidação de todas
as famílias de pontuação ocorre em P4.

## 11. Rastreabilidade e validação

| Requisitos | Componentes | Evidência esperada |
|---|---|---|
| RF2-001–006; CA2-001 | Calibração e SQLite | Inversão, ruído, limites inválidos, corrupção/falha de escrita, restauração e reinício real. |
| RF2-007–012; CA2-008 | Catálogo, sessão e gravador | Todos os JSONs, legado, duração, cancelar/desconectar, repetir/avançar e 30 repetições sem resíduo. |
| RF2-013–020; CA2-003/006 | Gráfico e mapa | Guiado ao vivo, resultado completo, valores/tempos legíveis, padrões além de cor, marcadores sem sobreposição. |
| RF2-021–026; CA2-002/005 | Pontuação e feedback | Perfeito, dentro/fora da faixa, overshoot, atraso, liberação abrupta, ruído, reaplicação, timestamps irregulares, empate e determinismo. |
| Modos da seção 9; CA2-004 | Política visual e Qt | Avaliação sem medidores/números/curvas; Memória na variante escolhida; dados e fórmula iguais entre modos. |
| RF2-027–033; CA2-007 | ABS, eventos e gráfico | Acima/igual/abaixo de 80%, recuperação, travamento até o fim, múltiplos eventos, ABS, superfície variável e rótulos. |
| RNF2-001/007/008/009 | App e empacotamento | Offline, widget reutilizável, replay idêntico, termos adequados e executáveis separados. |
| RNF2-002–004 | Aquisição, UI e conclusão | Frequência/intervalos/FPS no Windows de referência; resultado de 10 s em até 500 ms. |
| RNF2-005/006 | Layout | 1920×1080, 2560×1080, escala registrada, teclado e informação independente de cor. |

Usar pytest para domínio/integração e Qt com dispositivo falso para fluxos.
Fixtures representam comportamentos e erros esperados, não cópias das fórmulas.
Benchmark falso isola custo visual; G29 real valida aquisição/sensibilidade.
CI não comprova funcionamento do hardware.

Registrar commit, execução do Actions, artefato, Windows, CPU/RAM, resolução,
escala, driver, perfil, cenário/fórmula, modo e medidas. Computador de referência
ainda será registrado na validação; não foi presumido a partir desta máquina.
Persistência pode ser assíncrona, com estado de salvamento/falha visível.

Nota editorial: CA2-004 se chama “Treino de memória”, mas verifica Avaliação.
Usar seu enunciado e validar Memória separadamente após E02; corrigir título em
revisão documental sem mudar comportamento. Testes adicionais cobrem desempenho
e falhas além dos oito exemplos de aceitação.

## 12. Builds, branch e release

Executáveis serão construídos no **GitHub Actions, em Windows**, a partir do
commit da branch. Não é necessário empacotar .exe nesta máquina. O responsável
baixa os pacotes e testa o G29 no seu Windows.

- build-trainer.yml: Python 3.12, testes, PyInstaller onedir, resources incluído,
  artefato PilotagemVirtual-windows-x64.
- build-g29-spike.yml: testes, entrada própria e pacote independente,
  artefato PilotagemVirtual-G29-Spike-windows-x64.
- Ambos oferecem workflow_dispatch; pushes automáticos hoje só na main.
  Executar manualmente escolhendo feature/002-brake-control e registrar SHA.
  Na implementação, propor CI de testes em push da branch/pull request; não
  presumir que commit documental já gerou build.
- Retenção atual de artefatos: 14 dias. Identificar intermediários por SHA e
  incremento; não apresentá-los como release estável 0.2.0.
- release.yml responde a tags v*.*.*, confere versões, testa, gera dois pacotes
  e publica release. Não criar v0.2.0 nesta fase.

Novos commits usam camposezek@gmail.com. Não reescrever histórico ou tags.
Manter Unreleased distinguindo documentação adicionada de funções planejadas
ou entregues. Na preparação da release, atualizar conjuntamente pyproject.toml,
pilotagem_virtual.__version__ e changelog. Após validar critérios, obter autorização
de merge, verificar a main integrada e então aprovar gate/tag/release. Verificar
ambos os executáveis sempre que mudança compartilhada puder afetar diagnóstico.

## 13. Quality gate do Plan

Pronto para revisão quando:

- código atual e arquitetura proposta estiverem distinguidos;
- aquisição, normalização, gráfico e pontuação tiverem fronteiras claras;
- cenário evoluído preservar a curva existente;
- sete hipóteses tiverem experimento, ponto de decisão e impacto rastreáveis;
- calibração, dados originais e fórmula versionada permitirem reprocessamento;
- requisitos estiverem ligados a componentes e validações;
- builds na branch e separação dos executáveis estiverem definidos;
- riscos pendentes não forem apresentados como resolvidos;
- responsável aceitar o plano para decomposição em Tasks.

**Situação:** inspeção documental concluída; hipóteses/validações definidas;
nenhum experimento, teste novo, benchmark ou build novo executado.
**Próxima transição:** aprovação do Plan → tasks.md → implementação incremental
e validação, mantendo merge pendente de autorização explícita.
