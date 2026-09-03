# P0 — Evidências e pendências

**Atualizado:** 2026-09-03 · **Status:** implementação automática verificada; evidência física parcial, gate aberto
**Código:** 1cb48e8a8b3e6f561f2afc7b03118ddfc98fe7db
**Roteiro físico:** [p0-acquisition-test.md](p0-acquisition-test.md)

**Incremento posterior:** [prontidão inicial e encerramento](p0-readiness.md),
com JSON v2 e salvamento automático para os próximos testes físicos.

## Entregue e verificado

- T010/T011: fim de replay explícito, timestamp original, ID por tentativa,
  rejeição de valores inválidos, contexto antes/depois da execução e snapshot
  imutável. Trinta repetições verificam ausência de dados residuais.
- T012: coordenador controla dispositivo/perfil/sessão; o desenho não gera
  amostras. Troca de dispositivo bloqueada durante tentativa; cancelamento e
  desconexão restauram ações. O caminho normal permanece na thread principal.
- T013/T014: relatório de taxas por segundo, intervalos e lacunas, fonte
  sintética ou G29, experimento em principal/worker, FPS de paintEvent, atraso
  de entrega e registro de redimensionamentos. Ciclo do backend inteiro no
  contexto proprietário foi verificado com backend substituto, não G29.
- `python -m pytest`: **54 testes passaram** localmente em Python 3.12.4;
  PySide6 6.11.2, pygame 2.6.1 e pytest 9.1.1. Inclui 30 ciclos do worker
  experimental com fonte falsa e fechamento/cancelamento nos dois contextos.
- Inspeção visual de capturas locais em 1920×1080 e 2560×1080: mapa legado,
  marcadores e ações visíveis; experimento sem sobreposição. Qt `offscreen`,
  escala 1 e Segoe UI carregada explicitamente no harness de captura, pois
  o plugin offscreen não descobriu a fonte automaticamente. Isso não substitui
  o teste visual do executável com o plugin Windows e a escala do usuário.

## Medições exploratórias com fonte sintética

Ambiente local: Windows 11 build 26200, Ryzen 5 5600 (6 núcleos/12 threads),
25.688.522.752 bytes de RAM informados pelo Windows (aproximadamente 23,9 GiB).
Cada execução durou 10 s com Qt offscreen. Houve atividade de desenvolvimento
concorrente e as resoluções com desenho diferem; os números não permitem
comparação controlada de superioridade entre arquiteturas. Este computador não
foi declarado computador de referência. Não houve acesso ao G29 nessas medições.

| Contexto / desenho | Resolução | Leituras/s | Menor contagem em 1 s | Intervalo p95 / máximo | FPS desenhados |
|---|---|---:|---:|---|---:|
| Principal / sem gráfico | 1920×1080 | 119,7 | 118 | 9,024 / 9,403 ms | — |
| Principal / com gráfico | 1920×1080 | 117,5 | 116 | 9,698 / 15,576 ms | 58,8 |
| Worker / sem gráfico | 1920×1080 | 119,2 | 116 | 9,020 / 9,306 ms | — |
| Worker / com gráfico | 2560×1080 | 113,5 | 88 | 10,200 / 17,324 ms | 58,9 |

Os arquivos completos e as imagens ficaram em `build/p0-final/`, ignorado pelo
Git; o [resumo sem amostras](p0-synthetic-summary.json) acompanha este documento.
Os timestamps medem polls
reais de uma fonte falsa, não atualizações do sensor. Resultado ≤500 ms de uma
tentativa pontuada não foi medido: ainda não há pontuação implementada.

O agendamento inicial por próximo deadline de 120 Hz mostrou intervalos curtos
de compensação após atrasos. Foi substituído no experimento por QTimer preciso
single-shot de 8 ms após cada poll, sem catch-up. A tabela corresponde a essa
última implementação. O intervalo configurado não garante aquisição a 120 Hz.
O worker continua experimental; os resultados acima não autorizam sua promoção.

Reprodução sintética (ambiente de desenvolvimento ou executável Actions):

```powershell
.venv/Scripts/python.exe trainer_main.py --acquisition-probe --source fake --context main --auto --output build/main.json
.venv/Scripts/python.exe trainer_main.py --acquisition-probe --source fake --context worker --auto --output build/worker.json
```

Para repetir offscreen, definir `$env:QT_QPA_PLATFORM = 'offscreen'` nesse processo.
Usar `--no-drawing` para retirar carga gráfica e `--size 2560x1080` para ultrawide.
As medições físicas precisam usar o plugin Windows e a janela visível.

## Medições físicas recebidas em 2026-09-03 — primeiro lote

Três JSONs completos fornecidos pelo usuário, preservados em
`build/actions/trainer/package/`. O [resumo auditável](p0-g29-summary.json)
registra SHA-256 de cada original, configuração, métricas recalculadas e variação
dos eixos. São três repetições de **G29 / thread principal / com gráfico**, com
10 s cada; não representam três configurações diferentes.

Todos identificam o G29 de quatro eixos, Windows 11 build 26200, Python 3.12.10,
pygame 2.6.1 / SDL 2.28.4, plugin Qt `windows`, janela 1920×1061, escala 1 e
build Actions 1cb48e8. CPU/RAM e versão do G Hub não estão nos relatórios.
O usuário informou instalação física improvisada; isso permite avaliar captura,
mas não calibrar o máximo confortável nem julgar precisão de execução.

| Arquivo | Leituras | Média (Hz) | Menor contagem em 1 s | Intervalo p95 / máximo | FPS |
|---|---:|---:|---:|---|---:|
| `medicao-p0.json` | 853 | 85,3 | 60 | 18,989 / 36,192 ms | 58,9 |
| `medicao-p0.1json.json` | 939 | 93,9 | 65 | 17,440 / 23,960 ms | 58,9 |
| `medicao-p02.json` | 1.082 | 108,2 | 93 | 15,808 / 19,924 ms | 58,9 |

As três terminaram como `completed`, sem erro, com conexão presente em todas
as amostras. Foi conferido que timestamps são estritamente crescentes, todas as
amostras pertencem a `[0, 10 s)`, os quatro eixos são finitos e estão em faixa,
e a leitura de contexto final está após a janela. As estatísticas recalculadas
coincidem com as exportadas. São taxas de polling do host, não de atualização
independente do sensor.

O freio (eixo 2) teve 187, 183 e 178 valores distintos, respectivamente, com
centenas de mudanças durante cada captura. Pela normalização legada, o máximo
observado foi 87,1%, 89,5% e 85,2%; não é necessário alcançar 100% para este
experimento de aquisição. Volante, acelerador e embreagem ficaram constantes
depois da transição inicial, portanto estas capturas não revalidam seu movimento.

Pontos para investigação antes de concluir T016:

- As contagens por segundo caem de 114 para 60, de 116 para 65 e de 107 para 93.
  Todos os segundos completos atingiram o mínimo de 60, mas o primeiro ensaio
  chegou ao limite; nenhum atingiu média de 120 Hz. O p95 de desenho foi 12,145,
  8,987 e 7,622 ms. A curva de execução é reconstruída a cada desenho a partir
  de uma lista crescente no mesmo contexto da captura; isso é uma hipótese de
  contenção a comparar sem gráfico e no worker, não uma causa confirmada.
- Nas duas primeiras capturas, os quatro eixos começam exatamente em zero:
  111 e 38 amostras, até a primeira leitura não nula em 980,977 e 339,528 ms.
  Na terceira não há esse trecho inicial. Zero bruto de pedal vira 50% pela
  normalização legada. Investigar inicialização/atualização do estado antes de
  calibrar ou pontuar; não atribuir esse padrão ao improviso da montagem nem
  remover essas amostras silenciosamente. Todas foram mantidas nas estatísticas.
- Não há redimensionamentos registrados, cancelamentos ou desconexões nessas
  capturas. IDs SDL sucessivos não comprovam desconexão/reconexão física.

Decisão após o primeiro lote: evidência real útil de captura do freio e repetição na thread principal;
manter a arquitetura atual enquanto a comparação não está completa. Ainda faltam
principal sem gráfico, worker sem/com gráfico, carga de redimensionamento e as
operações de cancelar/desconectar/reconectar/fechar, além da confirmação do treino
legado. T016 permanece aberta e não libera P1 por estes três arquivos isoladamente.

## Segundo lote — comparação das quatro configurações

Recebidos `principal-sem-grafico.json`, `worker-sem-grafico.json` e
`worker-com-grafico.json` na mesma pasta. O [resumo](p0-g29-summary.json) agora
inclui os seis relatórios com hashes dos originais. Os três novos usam o mesmo
build 1cb48e8, G29, versões de runtime, janela 1920×1061 e escala 1 do primeiro
lote. Todos completaram 10 s sem erro; timestamps, faixa/finidade dos eixos,
conexão e contexto final foram conferidos. Métricas recalculadas coincidem
com as exportadas, e os IDs de thread confirmam os contextos escolhidos.

| Configuração | Leituras | Média (Hz) | Menor contagem em 1 s | Intervalo p95 / máximo | FPS |
|---|---:|---:|---:|---|---:|
| Principal / sem gráfico | 1.185 | 118,5 | 118 | 8,974 / 9,522 ms | — |
| Worker / sem gráfico | 1.182 | 118,2 | 118 | 8,993 / 9,183 ms | — |
| Worker / com gráfico | 1.161 | 116,1 | 113 | 9,712 / 22,251 ms | 58,9 |

Sem gráfico, ambas as threads mantiveram 118–119 leituras em cada segundo.
Com gráfico, o worker ficou entre 113 e 118; no primeiro lote a thread
principal variou de 60 a 116. O atraso de entrega à interface no worker com
gráfico teve p95 de 8,348 ms. Isso é distinto do intervalo entre leituras;
não significa latência de resultado nem latência ponta a ponta do sensor.

Interpretação: os resultados favorecem o worker para isolar a aquisição da
carga visual. A redução de frequência com desenho foi pequena no worker, e a
thread principal recuperou a regularidade sem desenho. Isso reforça a hipótese
de contenção pela renderização, sem isolar seu custo exato ou provar estabilidade
sob toda carga. Houve apenas uma captura por nova configuração, em momentos
diferentes. As médias ficaram próximas, mas abaixo do alvo de 120 Hz; todas as
contagens por segundo superaram o mínimo de 60 nas três novas capturas.

O estado inicial zerado persistiu nas duas threads:

| Arquivo | Amostras iniciais com quatro eixos zero | Primeira leitura com algum eixo não nulo |
|---|---:|---:|
| `principal-sem-grafico.json` | 273 | 2.306,163 ms |
| `worker-sem-grafico.json` | 209 | 1.779,482 ms |
| `worker-com-grafico.json` | 75 | 644,250 ms |

Depois, o freio apresentou 201, 183 e 172 valores distintos, respectivamente.
O padrão inicial não é exclusivo do gráfico ou da thread principal e exige
investigar quando o backend disponibiliza o primeiro estado físico. O código
atual aceita esses zeros finitos como leitura normal e não registra um estado
de prontidão separado. Não há evidência suficiente para definir a causa ou
tratar todo zero como inválido: zero também pode ser uma posição legítima.
Os trechos foram preservados e continuam incluídos nas métricas de polling.

**Decisão atual:** selecionar o worker como candidato preferido para a próxima
etapa de validação. A comparação básica das quatro configurações está registrada;
não é necessário repetir as mesmas capturas para esse objetivo. A integração
no treinador permanece pendente de prontidão inicial e ciclo de vida. Nenhum dos
seis relatórios registra redimensionamento, cancelamento ou desconexão; também
faltam confirmação de reconexão/fechamento e regressão manual do treino legado.
T016 permanece aberta, com evidência comparativa de desempenho concluída neste
conjunto e validação operacional ainda pendente. P1 não foi iniciado.

## Fronteiras de janela — T015 ainda aberta

Executado `python experiments/window_boundaries.py`, usando aritmética racional.
Janela nominal 1–7 s; todas as leituras internas são 60%; última leitura externa
em 0,997 s e primeira interna em 1,005 s. Interpolar a borda usando a amostra
externa altera o tempo na faixa de 55–65%:

| Entrada anterior | Valor interpolado em 1 s | Tempo na faixa calculado |
|---|---:|---:|
| 0% | 22,5% | 99,92778% |
| 60% | 60% | 100% |
| 100% | 85% | 99,93333% |

Isso viola a invariância de CA2-002/RF2-026, mesmo sendo uma diferença pequena.
Não foi adotada essa interpolação para a pontuação. A janela da tentativa usa
`[0, duração)` com leituras externas separadas; isso resolve propriedade dos
dados, mas não define sozinho integração nas bordas das janelas de métricas.
Antes de P2, fechar a convenção sem extrapolar lacunas ou pedir revisão explícita
do requisito caso seja necessário aceitar suporte temporal parcial. T015 não
foi marcada como concluída apenas pelo contraexemplo.

## Builds e próximo gate

- Treinador: [execução 33696545677](https://github.com/ezkcampos/pilotagem-virtual/actions/runs/33696545677), **sucesso**;
  [artefato PilotagemVirtual-windows-x64](https://github.com/ezkcampos/pilotagem-virtual/actions/runs/33696545677/artifacts/9872022282).
- Diagnóstico: [execução 33696548282](https://github.com/ezkcampos/pilotagem-virtual/actions/runs/33696548282), **sucesso**;
  [artefato PilotagemVirtual-G29-Spike-windows-x64](https://github.com/ezkcampos/pilotagem-virtual/actions/runs/33696548282/artifacts/9872022424).
- CI exclusivo: a [execução inicial](https://github.com/ezkcampos/pilotagem-virtual/actions/runs/33696530385)
  ficou sem concluir e foi cancelada, sem causa confirmada. Foram adicionados
  timeout e diagnóstico de stack em c6bc07d. A [nova execução 33696905726](https://github.com/ezkcampos/pilotagem-virtual/actions/runs/33696905726)
  concluiu com sucesso: **54 testes passaram em 5,03 s**. Esse commit altera somente o workflow;
  o código de aplicativo/testes continua idêntico ao dos builds.

Ambos os builds usam 1cb48e8, foram baixados e extraídos em `build/actions/`.
O log do treinador confirma 54 testes aprovados no Windows. O executável do
treinador foi executado com `--acquisition-probe --source fake --context worker
--auto`: concluiu 10 s, exportou JSON com SHA/run URL corretos, 1.174 leituras
(117,4 Hz), intervalo máximo 16,238 ms e 58,9 FPS offscreen. Isso verifica carga
do pacote, execução do worker e fechamento, não o G29 nem o fluxo completo de
treino real. O binário de diagnóstico foi conferido no pacote, mas não teve
interação física validada nesta etapa. Retenção dos artefatos: 14 dias.

T016 recebeu seis capturas físicas cobrindo as quatro configurações em 2026-09-03;
worker é o candidato preferido pelos resultados. Prontidão inicial,
redimensionamento e operações de cancelar/desconectar/reconectar/fechar
permanecem pendentes; P1 não foi iniciado. Não houve merge,
mudança de versão, tag ou release. E01–E07 continuam experimentais.
