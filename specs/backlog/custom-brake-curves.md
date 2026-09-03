# Proposta — Curvas de frenagem personalizadas

**Origem:** ideia do usuário em 2026-09-03, acompanhada de imagem do gráfico.
**Estado:** exploração de interação; versão de entrega ainda não definida.

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

## Caminho para implementação

Salvar nome, duração e pontos como um cenário próprio; escolher esse cenário
para treinar e comparar a execução do G29 com o alvo salvo. Manter controles
acessíveis e preservar os dados originais de aquisição. Compatibilidade do
cenário, tolerâncias, janelas avaliadas e pontuação precisam ser especificadas;
a prévia explora somente a edição da curva, sem captura ou pontuação.

A Spec 002 aprovada exclui editor visual de exercícios. Esta proposta registra
a nova ideia separadamente; sua incorporação a uma versão deve atualizar o
escopo correspondente. A validação P0 em andamento continua necessária.
