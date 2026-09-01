# Tarefas — MVP do treinador de trail braking

**Status:** Build iniciado  
**Spec:** [spec.md](spec.md)  
**Plano:** [plan.md](plan.md)  

## Convenções

- `[P]`: pode ser executada em paralelo com outras tarefas da mesma fase.
- `[HW]`: exige validação manual com o G29 em um computador Windows.
- Cada tarefa só é concluída quando seus testes e evidências descritos estiverem disponíveis.

## Fase 0 — SDD e decisões

- [x] **T001** Registrar visão, requisitos e critérios de aceitação do MVP.
- [x] **T002** Aprovar a Spec 001.
- [x] **T003** Pesquisar stack, entrada, persistência e empacotamento.
- [x] **T004** Aprovar o plano técnico.
- [x] **T005** Definir o hardware spike e o contrato de exportação JSONL.

## Fase 1 — Fundação do projeto

- [x] **T010** Criar `pyproject.toml` com Python 3.12, PySide6, Pygame, pytest e PyInstaller.
- [x] **T011** Criar layout `src` e entrypoint do hardware spike.
- [x] **T012** Criar testes unitários do gravador JSONL.
- [x] **T013** Configurar workflow Windows para testes e build `onedir`.

## Fase 2 — Hardware spike do G29

- [x] **T020** Enumerar dispositivos e metadados expostos pelo Pygame/SDL.
- [x] **T021** Exibir valores brutos de eixos, botões e hats em tempo real.
- [x] **T022** Implementar aquisição com temporizador preciso e alvo de 120 Hz.
- [x] **T023** Implementar seletor de pasta e arquivo `.jsonl` antes da gravação.
- [x] **T024** Salvar linhas `metadata`, `event`, `sample` e `summary` com schema versionado.
- [x] **T025** Fazer flush periódico e fechamento seguro da captura.
- [x] **T026** Mostrar frequência observada, quantidade de amostras e caminho escolhido.
- [x] **T027** Tratar ausência e desconexão de dispositivo sem perder linhas já gravadas.
- [ ] **T028 [HW]** Executar o `.exe` com o G29 e gravar movimentos completos do volante.
- [ ] **T029 [HW]** Gravar acelerador e freio individualmente e simultaneamente.
- [ ] **T030 [HW]** Pressionar todos os botões e testar desconexão/reconexão.
- [ ] **T031 [HW]** Adicionar a captura JSONL ao repositório para análise.
- [ ] **T032** Analisar a captura e registrar o mapeamento, ruído e frequência real.

### Critérios de conclusão do spike

- O executável inicia no Windows sem um ambiente Python instalado.
- O G29 aparece na lista de dispositivos.
- Todos os eixos relevantes mudam na interface.
- O usuário escolhe livremente onde salvar a captura.
- Cada linha do arquivo é JSON válido e contém o tipo de registro.
- O resumo informa duração, quantidade de amostras e frequência observada.
- Uma captura interrompida mantém as linhas que já foram descarregadas.

## Fase 3 — Núcleo do MVP

- [ ] **T040** Criar contratos de dispositivo e adaptador falso.
- [ ] **T041** Consolidar o adaptador SDL conforme o resultado do spike.
- [ ] **T042** Implementar domínio de calibração e normalização.
- [ ] **T043** Implementar assistente de calibração.
- [ ] **T044** Persistir e recuperar o perfil do dispositivo.
- [ ] **T045** Definir e validar o schema JSON dos cenários.
- [ ] **T046** Implementar máquina de estados do exercício.
- [ ] **T047** Implementar mapa 2D e indicador temporal.
- [ ] **T048** Implementar gravação de tentativas normalizadas.

## Fase 4 — Pontuação e resultado

- [ ] **T050** Implementar reamostragem de alvo e execução.
- [ ] **T051** Detectar frenagem, turn-in, liberação e aceleração.
- [ ] **T052** Implementar subpontuações determinísticas.
- [ ] **T053** Implementar feedback por maior penalidade normalizada.
- [ ] **T054** Criar tela de resultado com mapa e gráfico.
- [ ] **T055** Validar casos sintéticos perfeitos e erros controlados.

## Fase 5 — Histórico e distribuição

- [ ] **T060** Criar schema e migrações SQLite.
- [ ] **T061** Persistir tentativa, amostras e relatório na mesma transação.
- [ ] **T062** Implementar histórico e comparação com melhor tentativa.
- [ ] **T063** Implementar consistência das últimas cinco tentativas.
- [ ] **T064** Gerar pacote Windows do MVP.
- [ ] **T065 [HW]** Executar 30 tentativas consecutivas com o G29.
- [ ] **T066** Validar todos os critérios de aceitação da Spec 001.

## Próximo gate

O projeto não avançará da Fase 2 para a calibração definitiva enquanto as tarefas T028 a T032 não forem concluídas. A captura real é a evidência necessária para decidir o mapeamento de eixos, filtro de ruído e frequência final de aquisição.
