# Validação manual P0 — aquisição SDL/Qt

Este roteiro compara arquiteturas candidatas. Um resultado isolado não valida o
G29 nem promove o worker ao treinador. Use o pacote do workflow **Build Pilotagem
Virtual Trainer**, confirme o SHA mostrado no relatório e feche o treinador e o
diagnóstico antes de iniciar cada medição.

## Sequência

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
