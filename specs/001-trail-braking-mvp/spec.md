# Especificação 001 — MVP do treinador de trail braking

**Status:** Aprovada  
**Fase SDD:** Especificação  
**Plataforma inicial:** Windows  
**Dispositivo inicial:** Logitech G29 com pedais  

## 1. Visão do produto

O Pilotagem Virtual será um aplicativo de desktop para treinar técnicas específicas de pilotagem por meio de exercícios curtos, repetíveis e mensuráveis usando volante e pedais.

O primeiro módulo será dedicado ao trail braking. O aplicativo deverá ensinar a coordenação entre frenagem, esterço e aceleração usando um mapa 2D de uma curva, perfis de comando esperados e feedback imediato após cada tentativa.

O produto não pretende substituir um simulador de veículos. No modo guiado do MVP, o objetivo é treinar coordenação, suavidade, sincronização e consistência dos comandos.

## 2. Problema

Treinar trail braking diretamente em um simulador exige abrir o jogo, escolher carro e pista, completar setores ou voltas e interpretar telemetria. Isso torna lenta a repetição isolada da técnica e dificulta identificar exatamente qual parte do movimento foi executada incorretamente.

O usuário precisa de uma maneira rápida de repetir uma entrada de curva, visualizar onde deve frear e esterçar, comparar seus comandos com um perfil-alvo e receber feedback objetivo.

## 3. Objetivos do MVP

- Detectar e calibrar os eixos do Logitech G29.
- Ensinar a sequência básica de uma entrada de curva com trail braking.
- Permitir tentativas de aproximadamente 5 a 10 segundos.
- Representar cada exercício em um mapa 2D com reta e curva.
- Comparar freio, volante e acelerador com perfis-alvo.
- Apresentar pontuação geral, subpontuações e feedback específico.
- Permitir repetir o exercício imediatamente.
- Registrar o histórico local básico das tentativas.

## 4. Fora do escopo do MVP

- Simulação física completa do veículo, pneus ou transferência de peso.
- Controle físico da trajetória do veículo pelos comandos do usuário.
- Force feedback gerado pelo aplicativo.
- Integração com Assetto Corsa ou outros jogos.
- Contas, sincronização em nuvem ou ranking online.
- Multiplayer.
- Editor visual de cenários.
- Suporte oficialmente validado para outros volantes.
- Uso de inteligência artificial para gerar pontuações.

## 5. Princípios do produto

1. **Repetição rápida:** o usuário deve conseguir iniciar uma nova tentativa em poucos segundos.
2. **Feedback explicável:** toda nota deve ser acompanhada de uma causa compreensível.
3. **Treino antes de simulação:** o MVP avalia comandos em relação ao exercício, sem alegar reproduzir toda a dinâmica de um carro real.
4. **Progressão gradual:** exercícios iniciais isolam movimentos antes de combiná-los.
5. **Dados locais:** o aplicativo deve funcionar offline e manter os dados do usuário no computador.

## 6. Usuário principal

Pessoa que utiliza volante e pedais em simuladores e deseja aprender ou melhorar técnicas de pilotagem por meio de exercícios isolados, rápidos e objetivos.

Não deve ser necessário compreender telemetria avançada para utilizar o aplicativo.

## 7. Jornada principal

1. O usuário conecta o G29 e abre o aplicativo.
2. Na primeira execução, calibra volante, freio e acelerador.
3. Escolhe um exercício de trail braking.
4. Visualiza o mapa da reta e da curva, incluindo os marcadores do exercício.
5. Inicia a tentativa após uma contagem regressiva.
6. Um indicador de veículo percorre automaticamente o mapa.
7. O usuário freia, esterça, alivia o freio e acelera de acordo com o cenário.
8. O aplicativo registra os comandos durante toda a tentativa.
9. Ao final, apresenta mapa analisado, gráficos, pontuação e principal feedback.
10. O usuário inicia outra tentativa por um botão do G29 ou pela interface.

## 8. Requisitos funcionais

### 8.1 Dispositivo e calibração

- **RF-001:** O aplicativo deve listar os dispositivos de controle compatíveis detectados pelo Windows.
- **RF-002:** O usuário deve poder selecionar o Logitech G29 quando houver mais de um dispositivo.
- **RF-003:** O aplicativo deve identificar e exibir em tempo real os eixos de volante, freio e acelerador.
- **RF-004:** A calibração deve registrar os valores mínimo, máximo e neutro aplicáveis a cada eixo.
- **RF-005:** O usuário deve poder definir uma zona morta do volante.
- **RF-006:** O usuário deve poder definir o máximo confortável do pedal de freio.
- **RF-007:** A calibração deve ser salva localmente e reutilizada em execuções futuras.
- **RF-008:** O aplicativo deve informar claramente quando o dispositivo for desconectado durante o uso.

### 8.2 Cenários e mapa 2D

- **RF-009:** Cada exercício deve apresentar um mapa 2D ampliado contendo uma reta e uma curva.
- **RF-010:** O mapa deve indicar início, zona de frenagem, turn-in, zona de trail braking, ápice e zona de aceleração.
- **RF-011:** Um indicador de veículo deve percorrer automaticamente o trajeto segundo a linha temporal do cenário.
- **RF-012:** No MVP, os comandos do usuário não devem alterar fisicamente a trajetória nem a velocidade do indicador.
- **RF-013:** O mapa deve suportar curvas para a esquerda e para a direita.
- **RF-014:** Antes da tentativa, o usuário deve poder visualizar os marcadores e o objetivo do exercício.
- **RF-015:** Durante a tentativa, o mapa deve mostrar a posição atual e a fase ativa do exercício.

### 8.3 Execução da tentativa

- **RF-016:** A tentativa deve começar com uma contagem regressiva clara.
- **RF-017:** O aplicativo deve registrar volante, freio e acelerador durante toda a tentativa.
- **RF-018:** O usuário deve visualizar os valores atuais dos três comandos durante o exercício.
- **RF-019:** O exercício deve possuir perfis-alvo e margens de tolerância versionados.
- **RF-020:** A tentativa deve terminar automaticamente ao final do cenário.
- **RF-021:** O usuário deve poder cancelar uma tentativa em andamento.
- **RF-022:** O usuário deve poder iniciar uma nova tentativa por um botão configurável do G29 ou pela interface.

### 8.4 Avaliação e feedback

- **RF-023:** O aplicativo deve gerar uma nota geral entre 0 e 100.
- **RF-024:** A avaliação deve apresentar subpontuações para, no mínimo, pressão inicial, liberação do freio, sincronização freio-volante, suavidade e acelerador na saída.
- **RF-025:** A fórmula de pontuação deve ser determinística e explicável.
- **RF-026:** O aplicativo deve destacar o principal erro ou acerto da tentativa.
- **RF-027:** O resultado deve comparar visualmente os perfis-alvo e executado.
- **RF-028:** O mapa de resultado deve indicar os trechos corretos, aceitáveis e incorretos sem depender exclusivamente de cores.
- **RF-029:** O resultado deve mostrar os pontos ideais e reais de início da frenagem, turn-in, liberação total do freio e início da aceleração.
- **RF-030:** O aplicativo não deve descrever a tentativa como fisicamente perfeita para um carro real; a nota é relativa ao perfil do exercício.

### 8.5 Histórico

- **RF-031:** Cada tentativa concluída deve ser salva localmente.
- **RF-032:** O histórico deve registrar cenário, data, nota geral, subpontuações e séries temporais dos comandos.
- **RF-033:** O usuário deve visualizar as tentativas recentes de cada exercício.
- **RF-034:** O usuário deve poder comparar a tentativa atual com a melhor tentativa anterior.
- **RF-035:** O usuário deve visualizar uma medida de consistência baseada em tentativas recentes do mesmo cenário.

## 9. Cenários iniciais do MVP

### Cenário 1 — Liberação do freio

Objetivo: atingir uma pressão-alvo e liberar o freio de maneira progressiva, sem esterço obrigatório.

### Cenário 2 — Curva longa

Objetivo: iniciar um esterço suave enquanto mantém uma pequena pressão residual de freio por um período mais longo.

### Cenário 3 — Curva média

Objetivo: coordenar uma frenagem inicial mais intensa, turn-in definido e redução progressiva do freio até o ápice.

## 10. Modelo conceitual de cenário

Cada cenário deve ser configurável por dados e conter, no mínimo:

- Identificador e versão.
- Nome e descrição.
- Nível de dificuldade.
- Direção da curva.
- Duração total.
- Geometria visual do trecho.
- Posição temporal dos marcadores.
- Perfis-alvo de volante, freio e acelerador.
- Margens de tolerância.
- Pesos das métricas.
- Textos de feedback associados a erros mensuráveis.

O formato de armazenamento será definido na fase de planejamento técnico.

## 11. Métricas de avaliação candidatas

- Erro da pressão máxima inicial.
- Diferença temporal no início da frenagem.
- Diferença temporal no turn-in.
- Erro entre as curvas-alvo e executada.
- Pressão residual do freio ao longo do esterço.
- Oscilações na liberação do freio.
- Suavidade do esterço.
- Momento de liberação total do freio.
- Momento de início da aceleração.
- Sobreposição inadequada entre freio e acelerador.
- Variação entre tentativas consecutivas.

Os pesos finais permanecem em aberto até testes com dados reais do G29.

## 12. Requisitos não funcionais

- **RNF-001:** O aplicativo deve funcionar sem conexão com a internet.
- **RNF-002:** A leitura dos eixos deve ocorrer a uma frequência mínima de 60 amostras por segundo durante uma tentativa.
- **RNF-003:** A interface deve atualizar os indicadores com fluidez suficiente para não prejudicar o exercício, tendo 60 quadros por segundo como alvo.
- **RNF-004:** Nenhuma amostra registrada pode possuir valor fora do intervalo normalizado definido para seu eixo.
- **RNF-005:** Uma falha de persistência não deve apagar calibrações ou sessões anteriormente salvas.
- **RNF-006:** A interface deve ser utilizável em 1920 × 1080 e 2560 × 1080.
- **RNF-007:** Textos, símbolos e padrões visuais devem acompanhar as cores usadas para indicar acerto ou erro.
- **RNF-008:** A arquitetura deve permitir adicionar outros dispositivos e módulos de treino sem reescrever o domínio de cenários e pontuação.

## 13. Critérios de aceitação do MVP

### CA-001 — Calibração

**Dado** um G29 conectado,  
**quando** o usuário concluir as etapas de calibração,  
**então** os três eixos devem responder de 0% a 100% ou de -100% a 100%, conforme aplicável, e a configuração deve continuar disponível após reiniciar o aplicativo.

### CA-002 — Exercício guiado

**Dado** um cenário selecionado,  
**quando** a contagem regressiva terminar,  
**então** o indicador deve percorrer o mapa completo e o aplicativo deve registrar os três comandos até o fim da tentativa.

### CA-003 — Mapa da curva

**Dado** um exercício de trail braking,  
**quando** o mapa for apresentado,  
**então** deve ser possível distinguir a zona de frenagem, turn-in, trail braking, ápice e aceleração por texto ou símbolo, além das cores.

### CA-004 — Resultado explicável

**Dada** uma tentativa concluída,  
**quando** o resultado for calculado,  
**então** o usuário deve receber nota geral, subpontuações, comparação gráfica e pelo menos um feedback derivado de uma métrica registrada.

### CA-005 — Repetição rápida

**Dada** a tela de resultado,  
**quando** o usuário acionar o botão configurado ou a ação de repetir,  
**então** uma nova contagem regressiva deve começar sem retornar ao menu de cenários.

### CA-006 — Desconexão

**Dada** uma tentativa em andamento,  
**quando** o G29 for desconectado,  
**então** a tentativa deve ser interrompida e o aplicativo deve explicar que o dispositivo precisa ser reconectado.

### CA-007 — Histórico

**Dada** uma tentativa concluída,  
**quando** o usuário reabrir o aplicativo e acessar o mesmo cenário,  
**então** a tentativa deve aparecer no histórico com suas notas e dados de comando.

## 14. Riscos e hipóteses a validar

- A identificação dos eixos pode variar conforme driver e configuração do Logitech G Hub.
- O pedal de freio do G29 mede posição, não força; a calibração precisa considerar conforto e curso útil.
- Uma linha temporal fixa pode parecer artificial se o ritmo do cenário não estiver bem comunicado.
- As tolerâncias precisam ensinar sem punir pequenas variações naturais.
- O cálculo de suavidade não pode confundir ruído do sensor com movimentos bruscos do usuário.
- Os primeiros perfis-alvo precisam ser validados por experimentação e não apresentados como universais.

## 15. Decisões em aberto para o quality gate

1. Nome público inicial do aplicativo.
2. Aparência principal: mapa ocupando a maior parte da tela ou mapa e gráfico lado a lado.
3. Botão padrão do G29 para repetir uma tentativa.
4. Duração exata de cada um dos três cenários iniciais.
5. Perfil-alvo e tolerâncias iniciais de cada cenário.
6. Pesos iniciais das métricas de pontuação.
7. Versões mínimas do Windows suportadas.
8. Necessidade de modo janela, tela cheia ou ambos no MVP.

## 16. Quality gate da especificação

A especificação estará aprovada para seguir ao planejamento técnico quando:

- Objetivos e itens fora do escopo forem aceitos.
- Jornada principal e mapa guiado forem aceitos.
- Três cenários iniciais forem confirmados.
- Requisitos funcionais prioritários não apresentarem ambiguidades bloqueantes.
- Decisões em aberto necessárias para arquitetura forem resolvidas ou explicitamente adiadas.
- Critérios de aceitação forem considerados verificáveis.
