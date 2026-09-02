# Especificação 002 — Fundamentos do freio e telemetria visual

**Status:** Em revisão
**Fase SDD:** Especificação
**Versão-alvo:** 0.2.0
**Spec base:** [Especificação 001](../001-trail-braking-mvp/spec.md)
**Plataforma inicial:** Windows 10 e Windows 11, 64 bits
**Dispositivo validado:** Logitech G29 com pedais

## 1. Visão

A versão 0.2.0 do Pilotagem Virtual deverá introduzir um módulo progressivo para
ensinar controle do pedal de freio antes de combinar frenagem, esterço e aceleração.
O usuário praticará intensidades fixas, mudanças de patamar, aplicação inicial,
liberação progressiva e frenagem no limite por meio de exercícios curtos e repetíveis.

O principal instrumento visual será um gráfico temporal que compara a entrada-alvo
com a entrada executada. O módulo deverá começar com assistência visual completa e
reduzi-la gradualmente para favorecer memória muscular, consistência e controle sem
dependência permanente do gráfico.

## 2. Problema

A primeira versão funcional mostra o valor atual do freio, mas uma barra instantânea
não permite compreender como a entrada mudou durante toda a tentativa. Também exige
que um iniciante combine frenagem e esterço antes de dominar posições intermediárias
do pedal e sua liberação.

O usuário precisa:

- reconhecer aproximadamente 30%, 50%, 70% e outras intensidades configuradas;
- atingir e sustentar um alvo sem oscilações excessivas;
- trocar entre patamares de maneira controlada;
- aplicar o freio rapidamente e depois reduzir a entrada;
- visualizar a forma completa da frenagem após cada tentativa;
- praticar a mesma ação com menos assistência para desenvolver memória muscular;
- compreender didaticamente a diferença entre frenagem com e sem ABS.

## 3. Relação com a Especificação 001

Esta especificação estende o MVP definido na Spec 001 e não o substitui. Ela entrega
uma progressão anterior aos exercícios de curva e reutiliza a aquisição a 120 Hz, a
normalização observada no G29, a máquina de estados e o formato de cenários já
implementados.

A versão 0.2.0 deverá também concluir a calibração personalizada necessária para que
os percentuais exibidos sejam consistentes para o dispositivo do usuário.

## 4. Objetivos da versão 0.2.0

- Exibir a entrada do freio em percentual durante e depois de uma tentativa.
- Oferecer oito níveis progressivos, começando apenas com o pedal de freio.
- Comparar visualmente curva-alvo, tolerância e curva executada.
- Fornecer pontuação determinística adequada ao tipo de exercício.
- Alternar entre assistência guiada, treino de memória e avaliação.
- Permitir 20 a 30 repetições rápidas sem retornar ao menu principal.
- Demonstrar, por um modelo didático, frenagem com e sem ABS.
- Preservar o exercício de trail braking em curva da versão 0.1.0.

## 5. Fora do escopo

- Medir força física em quilogramas ou newtons.
- Medir pressão hidráulica real do sistema de freio.
- Detectar travamento real de rodas sem telemetria de um simulador.
- Reproduzir com fidelidade a física de pneus, temperatura, carga aerodinâmica ou
  transferência de peso de um veículo específico.
- Apresentar distância de parada simulada como equivalente à de um carro real.
- Gerar force feedback ou pulsação física no pedal do G29.
- Integrar com Assetto Corsa, Gran Turismo ou outro simulador nesta versão.
- Prescrever uma única técnica ou intensidade como universal para todos os carros.
- Implementar editor visual de exercícios.

## 6. Terminologia e limites de medição

O G29 fornece ao aplicativo a posição de um eixo do pedal. Portanto, a interface deve
usar o termo **Entrada do freio (%)**. Termos como força, carga física ou pressão de
freio não devem ser usados para descrever esse valor.

- `0%` representa o pedal solto segundo o perfil calibrado.
- `100%` representa o máximo definido no perfil calibrado.
- Valores intermediários representam posições normalizadas do sinal do pedal.
- A equivalência com o percentual exibido por um jogo pode variar conforme deadzone,
  saturação e curva de sensibilidade configuradas nesse jogo.

Qualquer velocidade, aderência, rotação de roda ou distância mostrada no nível sem
ABS deve receber o rótulo **Simulação didática**.

## 7. Jornada principal

1. O usuário conecta o G29 e abre o aplicativo.
2. Se ainda não houver um perfil válido, executa a calibração do freio.
3. Seleciona a categoria **Fundamentos do freio**.
4. Escolhe um nível e visualiza objetivo, duração, alvo e tolerância.
5. Seleciona o modo Guiado, Memória ou Avaliação quando disponível.
6. Inicia a tentativa após a contagem regressiva.
7. Executa o movimento acompanhando somente a assistência permitida pelo modo.
8. Recebe imediatamente gráfico comparativo, pontuação e principal feedback.
9. Repete o exercício ou avança para o próximo nível.
10. Depois dos fundamentos, pratica o mesmo controle no exercício de curva.

## 8. Currículo inicial

Todos os valores exatos devem permanecer configuráveis por cenário. Os exemplos a
seguir definem a intenção pedagógica e não limites universais.

| Nível | Exercício | Objetivo inicial |
|---|---|---|
| 1 | Encontrar intensidade | Atingir aproximadamente 30% e sustentar por um período curto. |
| 2 | Sustentar intensidade | Manter aproximadamente 60% dentro de uma faixa de tolerância. |
| 3 | Trocar patamares | Alternar de 80% para 40% sem soltar completamente o pedal. |
| 4 | Ataque e sustentação | Aplicar 100% rapidamente e reduzir para aproximadamente 70%. |
| 5 | Liberação progressiva | Partir de 100% e aliviar continuamente até 0%. |
| 6 | Pré-trail braking | Reduzir rapidamente de 100% para 60% e depois liberar lentamente. |
| 7 | Trail braking em curva | Combinar o perfil de freio com esterço, ápice e aceleração. |
| 8 | Frenagem no limite sem ABS | Permanecer próximo ao limite didático e recuperar um travamento. |

### 8.1 Níveis de intensidade fixa

Os níveis 1 e 2 deverão ensinar aquisição e estabilidade. O alvo pode possuir uma
fase de entrada, uma fase avaliada de sustentação e uma fase de liberação. A
pontuação de estabilidade não deverá punir o usuário antes de ele entrar na janela
temporal avaliada.

### 8.2 Mudanças de patamar

Os níveis 3 e 4 deverão medir se o usuário alcançou cada patamar, quanto tempo levou
e se ultrapassou significativamente o alvo. A aplicação inicial e a redução posterior
devem ser avaliadas separadamente.

### 8.3 Liberação progressiva

Os níveis 5 e 6 deverão comparar a forma da curva executada com keyframes-alvo. Uma
pequena quantidade de ruído natural do sensor não deverá ser classificada como
reaplicação intencional do freio.

### 8.4 Aplicação em curva

O nível 7 reutilizará o mapa do exercício atual. O gráfico de freio deverá aparecer
junto ao mapa durante o resultado e, quando o layout permitir, em formato compacto
durante a tentativa.

### 8.5 Demonstração com e sem ABS

O nível 8 deverá possuir duas etapas comparáveis:

- **Com ABS:** o usuário mantém uma entrada intensa enquanto o modelo didático mostra
  a modulação virtual do sistema e evita travamento contínuo.
- **Sem ABS:** ultrapassar o limite virtual gera travamento; o usuário deve aliviar o
  pedal apenas o suficiente para recuperar a rotação e reaplicar próximo ao limite.

O exercício deverá ensinar frenagem no limiar. Não deverá recomendar bombear o pedal
continuamente como técnica principal.

O limite de aderência poderá variar segundo um perfil versionado de superfície seca,
molhada, escorregadia ou variável. Os percentuais serão parâmetros do exercício e
deverão ser apresentados como didáticos.

## 9. Modos de assistência

### Guiado

- Exibe curva-alvo, tolerância, curva executada e percentual ao vivo.
- Destinado ao primeiro contato e à correção consciente do movimento.

### Memória

- Exibe o objetivo antes da tentativa.
- Durante a execução, mostra apenas as informações mínimas configuradas, como o valor
  percentual atual.
- Revela a comparação completa somente no resultado.

### Avaliação

- Não exibe a curva executada nem o percentual durante a tentativa.
- Mostra alvo e execução somente depois do encerramento.
- Usa a mesma fórmula do exercício para permitir comparação justa entre tentativas do
  mesmo modo.

Os modos não devem alterar a aquisição nem a curva-alvo; somente a assistência visual.

## 10. Requisitos funcionais

### 10.1 Calibração

- **RF2-001:** O aplicativo deve guiar o usuário para registrar o valor do pedal solto.
- **RF2-002:** O aplicativo deve registrar o máximo físico observado e o máximo que o
  usuário definiu para o perfil de treino.
- **RF2-003:** O aplicativo deve calcular e aplicar deadzone do pedal solto.
- **RF2-004:** A calibração deve mostrar o percentual resultante em tempo real antes de
  ser confirmada.
- **RF2-005:** O perfil deve ser salvo localmente e carregado nas próximas execuções.
- **RF2-006:** O usuário deve poder refazer ou restaurar a calibração observada do G29.

### 10.2 Seleção e execução

- **RF2-007:** O aplicativo deve apresentar separadamente as categorias Fundamentos
  do freio e Trail braking em curva.
- **RF2-008:** Cada nível deve informar objetivo, duração, assistência e tolerância.
- **RF2-009:** Cada tentativa deve durar entre 5 e 10 segundos, salvo demonstração
  explicitamente justificada na configuração.
- **RF2-010:** O usuário deve poder repetir imediatamente o mesmo exercício.
- **RF2-011:** O usuário deve poder avançar ao próximo nível a partir do resultado.
- **RF2-012:** O aplicativo deve preservar as amostras normalizadas capturadas a cada
  tentativa para cálculo e exibição do resultado.

### 10.3 Gráfico temporal

- **RF2-013:** O gráfico deve usar tempo no eixo horizontal e entrada do freio de 0% a
  100% no eixo vertical.
- **RF2-014:** O gráfico deve distinguir curva-alvo, faixa de tolerância e curva
  executada por cor, estilo de linha e legenda textual.
- **RF2-015:** No modo Guiado, o gráfico deve atualizar a curva executada durante a
  tentativa.
- **RF2-016:** O gráfico ao vivo deve indicar a posição temporal atual.
- **RF2-017:** O resultado deve sobrepor alvo e execução usando a mesma escala.
- **RF2-018:** Trechos fora da tolerância devem ser identificáveis sem depender apenas
  da cor vermelha.
- **RF2-019:** O resultado deve permitir identificar valores e tempos relevantes sem
  exigir conhecimento prévio de telemetria.
- **RF2-020:** No exercício de curva, o gráfico não deve impedir a leitura dos
  marcadores do mapa.

### 10.4 Pontuação e feedback

- **RF2-021:** Cada tentativa concluída deve receber nota geral de 0 a 100.
- **RF2-022:** Exercícios de sustentação devem avaliar tempo na faixa, erro médio,
  estabilidade e tempo de aquisição do alvo.
- **RF2-023:** Exercícios de liberação devem avaliar erro da curva, suavidade,
  sincronização e reaplicações indevidas.
- **RF2-024:** A interface deve exibir subpontuações e pelo menos um feedback derivado
  da maior penalidade normalizada.
- **RF2-025:** A mesma série de amostras, cenário e versão da fórmula devem sempre
  produzir o mesmo resultado.
- **RF2-026:** A pontuação deve ignorar amostras anteriores à janela avaliada quando o
  exercício explicitamente permitir tempo para aquisição do alvo.

### 10.5 Simulação didática de ABS

- **RF2-027:** O nível 8 deve comparar uma etapa com ABS e outra sem ABS.
- **RF2-028:** O modelo deve possuir limite de aderência configurável e versionado ao
  longo do tempo ou da velocidade simulada.
- **RF2-029:** No modo sem ABS, ultrapassar o limite deve gerar um estado explícito de
  roda travada.
- **RF2-030:** O gráfico deve destacar início, duração e recuperação de cada
  travamento.
- **RF2-031:** O resultado deve informar tempo total travado, tempo de recuperação e
  tempo útil próximo ao limite.
- **RF2-032:** Dados de velocidade, roda e distância gerados pelo modelo devem sempre
  receber o rótulo Simulação didática.
- **RF2-033:** O feedback deve ensinar a aliviar e reaplicar próximo ao limite, sem
  apresentar o exercício como instrução universal para veículos reais.

## 11. Modelo conceitual de exercício

Além dos campos definidos na Spec 001, um exercício desta versão deverá poder conter:

- tipo de exercício: sustentação, patamares, liberação, curva ou limite sem ABS;
- categoria e ordem pedagógica;
- modo de assistência padrão e modos permitidos;
- curva-alvo de freio por keyframes;
- faixa de tolerância fixa ou variável no tempo;
- janelas avaliadas por fase;
- textos de instrução antes e durante a tentativa;
- métricas e pesos aplicáveis ao tipo;
- modelo didático de aderência, quando aplicável;
- versão da fórmula de pontuação;
- pré-requisitos recomendados, sem bloqueio obrigatório na versão 0.2.0.

Os níveis deverão ser definidos por dados, sem duplicação de regras específicas na
interface.

## 12. Métricas candidatas

### Sustentação

- Percentual do tempo dentro da tolerância.
- Erro absoluto médio em relação ao alvo.
- Desvio durante a janela de sustentação.
- Tempo para entrar e permanecer na faixa.
- Overshoot máximo.

### Liberação e pré-trail

- Erro médio entre curva-alvo e curva executada.
- Momento de início da liberação.
- Momento de liberação total.
- Quantidade e amplitude de reaplicações significativas.
- Variação da taxa de liberação após tratamento do ruído aprovado.

### Limite sem ABS

- Tempo próximo ao limite sem travar.
- Quantidade e duração dos travamentos.
- Tempo entre travamento e recuperação.
- Distância percentual abaixo do limite durante a frenagem útil.
- Suavidade ao aliviar e reaplicar.

Os pesos finais serão definidos na fase de planejamento e validados por séries
sintéticas antes de testes no G29.

## 13. Requisitos não funcionais

- **RNF2-001:** O aplicativo deve continuar funcionando completamente offline.
- **RNF2-002:** A captura deve preservar o alvo de 120 Hz e nunca ficar abaixo de 60 Hz
  em condições normais do computador de referência.
- **RNF2-003:** O gráfico deve atualizar visualmente com alvo de 60 quadros por segundo
  sem bloquear a aquisição.
- **RNF2-004:** O resultado de uma tentativa de 10 segundos deve aparecer em até 500 ms
  no computador de referência.
- **RNF2-005:** O gráfico deve permanecer legível em 1920 × 1080 e 2560 × 1080.
- **RNF2-006:** Cores devem ser acompanhadas por estilos de linha, padrões, símbolos ou
  texto.
- **RNF2-007:** A implementação do gráfico deve ser reutilizável nos módulos futuros.
- **RNF2-008:** O modelo didático sem ABS deve ser determinístico e possuir versão.
- **RNF2-009:** Nenhum texto deve descrever entrada do pedal como força ou pressão real.

## 14. Critérios de aceitação

### CA2-001 — Calibração persistente

**Dado** um G29 conectado e sem perfil personalizado,
**quando** o usuário concluir a calibração do pedal,
**então** o pedal solto deve indicar 0%, o máximo configurado deve indicar 100% e o
perfil deve continuar disponível depois de reiniciar o aplicativo.

### CA2-002 — Intensidade fixa

**Dado** um exercício com alvo de 60% e tolerância de ±5%,
**quando** o usuário sustentar uma entrada entre 55% e 65% durante toda a janela,
**então** o tempo na faixa deve ser integral e a subpontuação correspondente deve ser
máxima, independentemente das amostras anteriores à janela de sustentação.

### CA2-003 — Gráfico guiado

**Dado** o modo Guiado,
**quando** a tentativa estiver em andamento,
**então** o usuário deve visualizar alvo, tolerância, execução e cursor temporal sem
interromper a aquisição das amostras.

### CA2-004 — Treino de memória

**Dado** o modo Avaliação,
**quando** a tentativa estiver em andamento,
**então** a curva executada e o percentual atual não devem ser revelados, mas o
resultado deve apresentar a comparação completa após o encerramento.

### CA2-005 — Liberação progressiva

**Dadas** uma execução sintética igual ao alvo e outra com liberação abrupta,
**quando** ambas forem pontuadas,
**então** a execução igual ao alvo deve obter pontuação maior e a execução abrupta
deve receber feedback relacionado à taxa ou ao momento de liberação.

### CA2-006 — Aplicação em curva

**Dado** o nível 7,
**quando** a tentativa for concluída,
**então** o resultado deve apresentar o mapa da curva e a comparação temporal do freio
sem ocultar turn-in, trail, ápice ou aceleração.

### CA2-007 — Travamento sem ABS

**Dado** um limite didático de 80%,
**quando** a entrada permanecer acima desse limite na etapa sem ABS,
**então** o modelo deve registrar travamento, destacar o intervalo no gráfico e medir
o tempo até a entrada voltar à região de recuperação.

### CA2-008 — Repetição rápida

**Dada** a tela de resultado de qualquer nível,
**quando** o usuário selecionar repetir,
**então** uma nova contagem regressiva deve começar sem retornar à seleção e sem manter
amostras da tentativa anterior.

## 15. Riscos e hipóteses

- O percentual calibrado pode não coincidir com o percentual de um jogo que aplique
  curva, deadzone ou saturação própria.
- Assistência visual permanente pode gerar dependência; por isso ela deverá diminuir
  nos modos Memória e Avaliação.
- Tolerâncias muito estreitas podem punir ruído ou limitações do pedal em vez da
  técnica do usuário.
- Filtragem excessiva pode esconder reaplicações reais e não deve alterar o dado bruto
  armazenado da tentativa.
- Uma simulação simplificada de ABS pode criar falsas expectativas se o caráter
  didático não estiver evidente.
- O gráfico ao vivo não pode competir visualmente com os marcadores da curva.
- Percentuais e durações iniciais precisam ser ajustados após testes práticos.

## 16. Decisões já aprovadas

1. O gráfico será o elemento principal nos exercícios somente de freio.
2. O eixo vertical exibirá Entrada do freio (%) e o horizontal exibirá tempo.
3. A curva-alvo, a tolerância e a execução deverão aparecer juntas no resultado.
4. A progressão possuirá oito níveis, incluindo trail braking em curva e limite sem
   ABS.
5. Haverá redução progressiva de assistência para estimular memória muscular.
6. O nível sem ABS será explicitamente uma simulação didática.
7. A ferramenta independente de diagnóstico do G29 continuará no projeto.
8. A versão-alvo será 0.2.0 e seguirá o fluxo branch, main, tag e release.

## 17. Decisões para o quality gate

1. Confirmar se os oito níveis ficarão todos disponíveis ou serão desbloqueados em
   sequência.
2. Confirmar se o modo Memória exibirá o percentual atual ou somente instruções.
3. Definir se o gráfico compacto da curva ficará abaixo do mapa ou no painel lateral.
4. Definir os primeiros percentuais, durações e tolerâncias por nível.
5. Definir os pesos iniciais das métricas por tipo de exercício.
6. Decidir se o estado de travamento terá sinal sonoro além do alerta visual.
7. Confirmar se a comparação com ABS será uma introdução do nível 8 ou uma tentativa
   pontuada separadamente.

## 18. Quality gate da especificação

A Spec 002 estará aprovada para planejamento técnico quando:

- objetivos, limites de medição e itens fora do escopo forem aceitos;
- os oito níveis e sua ordem pedagógica forem confirmados;
- os três modos de assistência forem aceitos;
- os requisitos do gráfico e do resultado forem considerados verificáveis;
- o caráter didático do nível sem ABS estiver claro;
- as decisões abertas que alteram arquitetura forem resolvidas ou explicitamente
  adiadas para experimentação no plano técnico;
- os critérios de aceitação forem considerados suficientes para validar a versão
  0.2.0.
