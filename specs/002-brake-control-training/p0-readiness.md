# P0 — Prontidão inicial e encerramento

**Data:** 2026-09-03 · **Status:** implementação para nova validação física

## Problema observado

Cinco das seis capturas físicas começaram com todos os eixos em zero, durante
até 2,306 s. Os JSONs antigos não contêm confirmação de inicialização; portanto
não permitem determinar se eram valores físicos ou estado ainda não recebido.
Normalizar esses zeros diretamente exibe cerca de 50% nos pedais.

A SDL distingue valor do eixo de disponibilidade do estado inicial com
[SDL_JoystickGetAxisInitialState](https://wiki.libsdl.org/SDL2/SDL_JoystickGetAxisInitialState).
O [código de SDL 2.28.4](https://github.com/libsdl-org/SDL/blob/release-2.28.4/src/joystick/SDL_joystick.c)
mantém essa confirmação por eixo. Eventos de movimento, por sua vez, podem
aguardar atividade antes de serem publicados; exigir movimento de cada eixo
não é equivalente a consultar sua inicialização.

## Alteração

- `SdlJoystickState` consulta as APIs públicas na DLL SDL2 já carregada pelo
  pygame, pelo handle do módulo no Windows. Não carrega outra cópia, não guarda
  ponteiros de joystick entre polls e falha explicitamente se a DLL for ambígua
  ou indisponível. Usa somente ctypes da biblioteca padrão.
- Cada leitura SDL traz `initialized_axes`, independente dos valores numéricos;
  zero com estado confirmado continua válido. Fontes sintéticas/replays mantêm
  seu contrato existente. A conexão também é consultada pela API SDL, além do
  evento de remoção.
- O treinador mostra “AGUARDANDO” e percentuais indisponíveis enquanto não recebe
  uma leitura com todos os eixos inicializados. Só então libera iniciar a
  tentativa. Perda de prontidão durante uma tentativa a cancela com motivo.
- No experimento, os 10 s começam no timestamp da primeira leitura pronta.
  Polls anteriores ficam integralmente em `initialization.samples`; não são
  apagados nem convertidos em amostras da tentativa. Após 10 s sem prontidão,
  retorna `initialization_timeout`, sem inventar uma tentativa ou taxa.
- O JSON passa a `acquisition-probe-v2`: inclui identidade da execução, espera,
  flags dos eixos, leitura terminal e eventos de abertura/encerramento com
  timestamp/thread. Relatórios antigos não são reescritos. Métricas de aquisição
  e de desenho cobrem somente a janela medida, excluindo a espera identificada.
- `--output-dir` salva cada execução em um arquivo único, inclusive cancelamento,
  desconexão, timeout e fechamento. O launcher seleciona G29/worker e salva em
  `medicoes-p0` ao lado do executável. Falha de salvamento ao fechar mantém a
  janela manual aberta, com relatório em memória para recuperação.
- O fechamento síncrono na thread principal agora aceita o evento externo de
  fechamento, evitando que um `close()` recursivo deixe a janela aberta.

## Limites e próximo gate

Isso trata a ausência de confirmação e permite investigar a causa do atraso;
não prova que o driver deixará de produzir o trecho inicial observado. Os logs
v2 revelarão quais flags acompanham os valores. Não há heurística que invalide
todo zero, espera fixa para esconder dados ou preenchimento de lacunas.

O worker continua no experimento. A integração no treinador depende de T016;
P1 e T015 permanecem pendentes. A comparação básica das quatro configurações
já foi feita e não precisa ser repetida integralmente. O
[roteiro atualizado](p0-acquisition-test.md) concentra a nova verificação em
prontidão, redimensionamento, cancelamento, desconexão/reconexão e fechamento.

## Verificação automática

Suíte final local: **70 testes passaram em 10,91 s**, Python 3.12.4, pygame 2.6.1,
PySide6 6.11.2 e pytest 9.1.1.

Testes cobrem zero inicial não confirmado versus zero legítimo, início bloqueado,
preservação da espera, timeout, desconexão durante espera/captura, nova execução,
cancelamento/fechamento nos dois contextos, autosave distinto e falha de escrita.
O teste nativo usa um joystick virtual da própria SDL para verificar a ABI do
Windows, correspondência com o dispositivo aberto pelo pygame, leitura de eixo
e remoção; não exige nem simula uma validação física do G29.

A suíte inclui regressão do treino legado e 30 ciclos do worker. Capturas locais
da UI com fonte falsa verificam os percentuais indisponíveis e o resultado salvo
em `build/p0-readiness/`, usando Qt offscreen e Segoe UI no harness. Isso não
substitui interação com o plugin Windows e o G29 no executável.

Uma execução da suíte parou dentro de `QTest.qWait` no teste de 30 ciclos. O
faulthandler registrou a espera na GUI, mas não identifica sozinho a causa
nativa. O encerramento agora conserva os objetos Qt/Python até `QThread.wait(0)`
confirmar o término da thread, sem bloquear a GUI durante a limpeza. Após essa
mudança, a suíte acima concluiu; cinco processos independentes também concluíram
o teste de 30 ciclos (150 execuções adicionais), com timeout externo de 30 s por
processo. A confirmação de estabilidade física continua em T016.
