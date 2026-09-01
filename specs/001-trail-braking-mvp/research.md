# Pesquisa técnica — MVP do treinador de trail braking

**Status:** Concluída  
**Objetivo:** reduzir incertezas antes do planejamento e da implementação  

## 1. Resumo das decisões

| Tema | Decisão inicial | Motivo |
|---|---|---|
| Linguagem | Python 3.12 | Familiaridade, velocidade de desenvolvimento e ecossistema suficiente para desktop, aquisição e análise dos dados |
| Interface | PySide6 com Qt Widgets | Interface desktop nativa, responsiva e adequada para mapa vetorial, calibração, resultados e ultrawide |
| Leitura do G29 | `pygame.joystick` sobre SDL | API genérica para eixos, botões e múltiplos dispositivos, sem acoplar o domínio ao SDK da Logitech |
| Fallback de dispositivo | SDK de volante da Logitech, somente se necessário | O SDK oficial encapsula DirectInput, mas adiciona dependência específica do fabricante e não é necessário para o escopo sem force feedback |
| Mapa 2D | `QGraphicsScene`, `QGraphicsView` e `QPainterPath` | Permite representar reta, curva, zonas e indicador móvel com geometria vetorial |
| Cálculo numérico | NumPy | Reamostragem, interpolação, derivadas e métricas determinísticas |
| Cenários | JSON validado por modelos tipados | Permite adicionar e versionar exercícios sem alterar o motor da aplicação |
| Persistência | SQLite local | Banco embutido, transacional e suficiente para calibrações, tentativas e amostras |
| Testes | pytest, adaptador falso de dispositivo e validação manual no G29 | Mantém a maior parte do sistema testável sem hardware conectado |
| Empacotamento | PyInstaller em modo `onedir` no MVP | Facilita diagnóstico, reduz o custo de inicialização e evita a extração temporária do modo `onefile` |

## 2. Interface: Pygame completo versus PySide6

### Alternativa A — Pygame para entrada e interface

Vantagens:

- Menor número de tecnologias.
- Bom para um protótipo semelhante a um jogo.
- Controle direto do loop de renderização.

Desvantagens:

- Exige construir mais elementos de interface manualmente.
- Configurações, tabelas, histórico e acessibilidade ficam mais trabalhosos.
- Evolução para um aplicativo desktop completo tende a aumentar o código de infraestrutura visual.

### Alternativa B — PySide6 para interface e Pygame somente para dispositivo

Vantagens:

- Componentes nativos para formulários, navegação, diálogos e acessibilidade.
- Qt possui APIs vetoriais adequadas para o mapa 2D.
- A camada de dispositivo pode ser trocada sem alterar a interface ou o domínio.
- Melhor adequação às resoluções 1920 × 1080 e 2560 × 1080 previstas na spec.

Desvantagens:

- Integração entre o loop do Qt e o processamento de eventos do SDL precisa ser validada.
- Empacotamento possui mais componentes.

### Decisão

Adotar a alternativa B. O produto é um aplicativo de treino e análise, não um jogo completo. A interface deve favorecer configuração, leitura de resultados e evolução futura.

## 3. Leitura do G29

O módulo `pygame.joystick` permite enumerar dispositivos, consultar eixos, botões, hats, nome, GUID e identificador de instância. A documentação também informa que a fila de eventos precisa ser processada para manter o estado do dispositivo atualizado.

O G29 não deve ser tratado como um controle Xbox padronizado. A API genérica de joystick é mais adequada do que a API SDL Controller, pois permite inspecionar todos os eixos expostos pelo driver.

Ainda não é seguro fixar índices como “eixo 0 = volante” ou “eixo 2 = freio”. Eles podem variar conforme driver, modo do volante e configuração do G Hub. A calibração deverá descobrir e persistir esse mapeamento.

### Hardware spike obrigatório

O primeiro executável técnico deverá:

1. Enumerar dispositivos conectados.
2. Registrar nome, GUID, instance ID, quantidade de eixos, botões e hats.
3. Exibir o valor bruto de todos os eixos.
4. Verificar se freio e acelerador aparecem separados ou combinados.
5. Verificar inversão, mínimo, máximo, centro e ruído em repouso.
6. Testar conexão, desconexão e reconexão.
7. Medir estabilidade a 60 Hz e 120 Hz.
8. Confirmar em qual thread o processamento de eventos do SDL permanece estável junto ao Qt.

O resultado do spike decidirá se o adaptador SDL é suficiente. O SDK oficial da Logitech permanece como fallback e não como dependência inicial.

## 4. Frequência e tempo

- Aquisição alvo: 120 amostras por segundo.
- Mínimo aceito pela spec: 60 amostras por segundo.
- Renderização alvo: 60 quadros por segundo.
- Relógio de tentativa: `time.perf_counter_ns()`, monotônico e de alta resolução.
- A interface pode consumir o estado mais recente a 60 Hz enquanto o gravador mantém as amostras de 120 Hz.

A separação entre aquisição e renderização impede que uma queda de quadros altere a série temporal usada na pontuação.

## 5. Representação do mapa

O Qt permite criar caminhos vetoriais uma vez e reutilizá-los no desenho. Cada cenário fornecerá a geometria normalizada do trajeto, e a interface a adaptará ao espaço disponível.

O mapa será composto por:

- Caminho central da pista.
- Segmentos semânticos: aproximação, frenagem, turn-in, trail braking, ápice e saída.
- Marcadores com texto ou símbolo.
- Indicador móvel com posição derivada do progresso temporal do cenário.
- Camada de resultado para mostrar regiões corretas, aceitáveis e incorretas.

No modo guiado do MVP, o indicador segue a linha temporal e não uma física de veículo.

## 6. Empacotamento

PyInstaller analisa as dependências e produz uma pasta ou executável distribuível contendo o interpretador Python e os módulos necessários.

O MVP utilizará `onedir` porque:

- inicia sem extrair todo o aplicativo em um diretório temporário;
- facilita inspecionar arquivos e dependências durante os primeiros testes;
- torna falhas de plugins Qt ou SDL mais fáceis de diagnosticar.

O modo `onefile` poderá ser avaliado após estabilização. O `pyside6-deploy`, baseado em Nuitka, permanece como alternativa futura.

## 7. Persistência

SQLite foi escolhido por ser embutido, transacional e acessível pela biblioteca padrão do Python. Os cenários fornecidos com o aplicativo continuarão em arquivos JSON versionados; dados gerados pelo usuário ficarão no banco local.

O diretório de dados será obtido pelo Qt por meio da localização padrão de dados locais do aplicativo, evitando caminhos fixos.

## 8. Testabilidade

A entrada física será escondida atrás de uma interface de dispositivo. Um adaptador falso poderá reproduzir séries temporais sintéticas e permitir:

- testar calibração sem G29;
- reproduzir uma tentativa perfeita;
- produzir frenagem precoce ou tardia;
- simular liberação brusca;
- simular ruído e desconexão;
- validar a pontuação de forma determinística.

O hardware real será exigido somente nos testes marcados como manuais.

## 9. Fontes oficiais consultadas

- [Qt for Python](https://doc.qt.io/qtforpython-6/)
- [QThread — Qt for Python](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QThread.html)
- [QGraphicsPathItem — Qt for Python](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QGraphicsPathItem.html)
- [QPainterPath — Qt for Python](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QPainterPath.html)
- [Deployment do Qt for Python](https://doc.qt.io/qtforpython-6/deployment/index.html)
- [Pygame Joystick](https://www.pygame.org/docs/ref/joystick.html)
- [Pygame Event Queue](https://www.pygame.org/docs/ref/event.html)
- [Logitech Partner Developer Lab](https://www-gaming.logitech.com/en-us/programs/partner-developer-lab)
- [PyInstaller — funcionamento](https://pyinstaller.org/en/stable/operating-mode.html)
- [PyInstaller — uso](https://pyinstaller.org/en/stable/usage.html)
- [Python `sqlite3`](https://docs.python.org/3/library/sqlite3.html)
- [Python `time`](https://docs.python.org/3/library/time.html)
- [NumPy `interp`](https://numpy.org/doc/stable/reference/generated/numpy.interp.html)
- [pytest — parametrização](https://docs.pytest.org/en/stable/how-to/parametrize.html)
