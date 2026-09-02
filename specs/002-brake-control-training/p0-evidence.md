# P0 — Evidências e pendências

**Data:** 2026-09-02 · **Status:** implementação automática verificada; gate físico pendente
**Código:** 1cb48e8a8b3e6f561f2afc7b03118ddfc98fe7db
**Roteiro físico:** [p0-acquisition-test.md](p0-acquisition-test.md)

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

T016 depende dos quatro relatórios com G29 e das operações de
cancelar/desconectar/reconectar/fechar; P1 não foi iniciado. Não houve merge,
mudança de versão, tag ou release. E01–E07 continuam experimentais.
