# Proposta — Curvas de frenagem personalizadas

**Origem:** ideia do usuário em 2026-09-03, acompanhada de imagem do gráfico.
**Estado:** incorporado à candidata 0.3.0 em 2026-09-04.

O usuário cria sua própria curva-alvo de frenagem, alterando a inclinação de
trechos a cada 10% da linha temporal. Interpretação adotada na prévia: esses
10% se referem à duração, enquanto o eixo vertical representa entrada do freio.

## Interação proposta

- Onze pontos: 0%, 10%, …, 100% do tempo; dez segmentos entre eles.
- Cada ponto tem tempo fixo e intensidade ajustável de 0 a 100%, arrastando na
  vertical ou usando seleção do ponto e controle acessível por teclado.
- A linha une os pontos com trechos retos. Sua inclinação resulta da diferença
  de intensidade entre pontos e do tempo disponível; não é preciso editar graus.
- Subidas, patamares e descidas são permitidos para criar ataque, sustentação,
  liberação e reaplicação. Curvas arbitrárias são exercícios personalizados,
  sem classificação automática de toda forma como técnica correta de trail braking.
- A duração total transforma a malha percentual em segundos: em 10 s, há um
  ponto a cada 1 s; em 8 s, a cada 0,8 s.

## Comportamento implementado

Cada curva guarda localmente nome, duração de 5 a 10 segundos, tolerância e os
onze pontos. A edição aceita arraste vertical e teclado; esquerda/direita muda o
ponto, cima/baixo altera 1 ponto percentual e Shift altera 5.

A categoria `Curvas personalizadas` permite criar, editar e treinar a curva nos
modos Guiado, Memória e Avaliação. Durante o modo Guiado, o gráfico apresenta ao
vivo o alvo, sua faixa de tolerância e a entrada real do pedal. O resultado mede
forma, tempo na faixa, sincronização e controle sem tratar uma subida intencional
como erro de reaplicação. Tentativas continuam sendo armazenadas como snapshots
imutáveis; as curvas usam uma tabela própria no mesmo banco SQLite.

A Spec 002 aprovada excluía o editor visual. Esta extensão inaugura o escopo da
0.3.0 sem modificar os oito exercícios fixos da série 0.2.
