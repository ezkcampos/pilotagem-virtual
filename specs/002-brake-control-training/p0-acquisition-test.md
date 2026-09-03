# Validação manual P0 — aquisição SDL/Qt

Este roteiro compara arquiteturas candidatas. Um resultado isolado não valida o
G29 nem promove o worker ao treinador. Use o pacote do workflow **Build Pilotagem
Virtual Trainer**, confirme o SHA mostrado no relatório e feche o treinador e o
diagnóstico antes de iniciar cada medição.

## Próxima verificação — build com prontidão e salvamento automático

A comparação básica das quatro configurações já foi recebida em seis relatórios.
Agora use o novo build descrito em [p0-readiness.md](p0-readiness.md).

1. Feche o experimento antigo, o treinador e o diagnóstico. Extraia o novo pacote
   inteiro e abra `run-p0-acquisition-probe.bat`. G29/worker já estarão selecionados.
2. Inicie uma medição com gráfico. Enquanto aparecer “Aguardando primeira leitura”,
   mova e solte os pedais; os 10 s começam quando a leitura estiver pronta. Durante
   a captura, altere o tamanho da janela arrastando uma borda. Se estiver maximizada,
   restaure-a primeiro; mover a janela de lugar não é redimensionar.
3. Inicie outra medição e clique em **Cancelar**.
4. Inicie outra e desconecte o cabo USB do G29 durante a captura.
5. Reconecte o G29, inicie novamente e deixe completar os 10 s.
6. Inicie mais uma e feche a janela antes de terminar.
7. Os relatórios são salvos automaticamente em **`medicoes-p0`**, dentro da pasta
   do pacote, inclusive o de fechamento. Se houver timeout ou erro, esse resultado
   também será salvo: envie a pasta completa sem apagar os casos de falha.
8. Abra `PilotagemVirtual.exe` normalmente e confirme que espera a primeira leitura,
   libera iniciar e ainda completa/cancela/repete o treino legado. Observe também
   volante, acelerador e embreagem; relate qualquer comportamento estranho.

Não é necessário executar movimentos precisos ou pressionar o freio até 100%.
Informe também versão do G Hub e se houve travamento. Os JSONs registram a versão
do Windows, o build e a escala da janela; a designação do PC de referência e os
dados completos de hardware ainda precisam constar da validação final.

## Sequência original de comparação — já executada sem redimensionamento

1. Extraia o ZIP completo e execute `run-p0-acquisition-probe.bat`.
2. Selecione **Logitech G29 real**, **Thread principal** e gráfico desativado.
3. Inicie 10 s, mova volante e pedais durante todo o intervalo e salve o JSON.
4. Repita com o gráfico ativado; durante esses 10 s redimensione a janela.
5. Repita os passos 2–4 com **Worker experimental**.
6. Inicie e cancele uma medição. Depois desconecte o G29 durante outra medição,
   reconecte-o, inicie uma medição nova e feche a janela antes dos 10 s.
7. Execute `PilotagemVirtual.exe` normalmente e confirme que o treino legado
   ainda completa, cancela e repete com volante, acelerador, freio e embreagem.

Envie os quatro JSONs completos e relate Windows, CPU/RAM, versão do Logitech G
Hub, escala da tela e qualquer travamento.

## Critério para decidir a arquitetura

- Cada segundo completo tem pelo menos 60 leituras reais; analisar também
  p50/p95/p99, maior intervalo e lacunas das bordas.
- O gráfico desenha próximo de 60 FPS sem reduzir aquisição ou criar rajadas.
- Cancelar, desconectar e fechar terminam a captura e o contexto proprietário.
- Nenhuma amostra é gerada para preencher atraso; `owner_thread` diferencia
  worker e thread principal, e o SHA do build coincide com a execução.

Se o worker falhar ou não superar a thread principal com carga visual, manter o
polling principal e separar somente renderização/consumo. Se ambos ficarem abaixo
do mínimo, revisar processo separado ou backend antes de avançar P1.
