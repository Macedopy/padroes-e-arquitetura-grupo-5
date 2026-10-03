Resposta a Objeção 1 — Acoplamento direto ao banco do legado via SQL Direct
Posição: Aceitamos a objeção.
A crítica é válida porque o uso de SQL Direct cria um acoplamento entre o sistema novo e a estrutura interna do banco do legado. Isso enfraquece o propósito da Anti-Corruption Layer, que deveria justamente isolar o modelo interno do sistema novo das particularidades do sistema legado.
Como o objetivo do Envelope C é permitir a substituição gradual do legado, depender diretamente de tabelas e colunas do sistema antigo aumenta o risco de uma alteração no schema quebrar a aplicação nova.
Mudança: a integração com o legado será feita exclusivamente através da API/contrato formal disponibilizado pelo sistema antigo. O LegacyBedSystemAdapter continuará existindo como ACL, mas terá a responsabilidade de traduzir os contratos do legado para o modelo interno.
Assim, conseguimos manter o isolamento e evoluir a substituição do legado sem depender diretamente de seu banco.

Resposta a Objeção 2 — RabbitMQ como peça adicional de infraestrutura
Posição: Aceitamos parcialmente da objeção.
Concordamos que o RabbitMQ adiciona uma responsabilidade operacional, especialmente considerando que temos apenas dois profissionais de infraestrutura. Porém, discordamos de que ele seja simplesmente redundante em relação à Outbox.
A Transactional Outbox e o RabbitMQ possuem responsabilidades diferentes. A Outbox garante que o evento não seja perdido antes de ser publicado, pois mantém a mensagem de forma persistente no PostgreSQL. O RabbitMQ, por sua vez, fornece a infraestrutura para distribuir e processar esses eventos de maneira assíncrona entre diferentes consumidores.
Portanto, remover o RabbitMQ e utilizar somente workers sobre o PostgreSQL seria uma alternativa possível, mas não necessariamente equivalente em termos de distribuição e desacoplamento dos consumidores.
Decisão: manteremos o RabbitMQ para os fluxos que realmente necessitam de mensageria assíncrona e múltiplos consumidores. Não consideramos necessário eliminá-lo apenas pelo fato de já utilizarmos Outbox, pois os dois componentes possuem responsabilidades complementares.

Resposta Objeção 3 — Monólito único concentrando módulos de naturezas diferentes
Posição: Discordamos da objeção.
Discordamos da conclusão de que a existência de módulos com características diferentes obrigatoriamente exige sua separação em serviços independentes.
A escolha pelo Monólito Modular considera principalmente as restrições do projeto: temos uma equipe de 10 desenvolvedores e apenas 2 profissionais de infraestrutura, além da exigência de operação on-premises. Transformar cada módulo em um serviço independente aumentaria a quantidade de deploys, configurações, monitoramento, comunicação entre serviços e problemas operacionais que a equipe teria de administrar.
O fato de Regulação de Leitos possuir requisitos diferentes não significa que ele precise ser um microsserviço. O isolamento pode ser feito internamente através dos módulos, mantendo limites claros entre as responsabilidades.
Além disso, a substituição gradual do legado pode ocorrer através da ACL, sem exigir que todo o módulo seja transformado em uma unidade de implantação independente.
Decisão: manteremos o Monólito Modular. A diferença de características entre os módulos será tratada através da separação modular interna, evitando a complexidade operacional de uma arquitetura distribuída que não é necessária para o contexto do projeto.

Resposta Objeção 4 — Vulnerabilidade do Redlock para prevenção de overbooking
Posição: Aceitamos a objeção.
Essa é uma crítica válida porque a prevenção de overbooking é uma regra de consistência crítica. Não é adequado que a garantia final de que um leito não será reservado duas vezes dependa exclusivamente de um mecanismo externo de lock.
O Redis pode sofrer indisponibilidade, reinicialização ou problemas de comunicação. Portanto, mesmo utilizando Redlock, a garantia definitiva da reserva deve estar em uma fonte transacional confiável.
Mudança: o PostgreSQL passará a ser a fonte de verdade da reserva dos leitos. A concorrência será controlada utilizando mecanismos transacionais do próprio banco, como SELECT ... FOR UPDATE ou uma constraint de unicidade na tabela de alocações.
O Redis poderá continuar sendo utilizado como mecanismo auxiliar de coordenação ou desempenho, mas não será responsável pela garantia final de consistência.
Dessa forma, mesmo que o Redis fique indisponível, não será possível confirmar duas reservas válidas para o mesmo leito.

Resposta Objeção 5 — Perda silenciosa de notificações pelo uso de eventos In-Memory
Posição: Aceitamos a objeção.
A objeção identifica uma falha real na combinação entre o evento In-Memory da ADR-001 e a Outbox da ADR-006.
Se o atendimento for confirmado no banco e a aplicação cair antes de o evento In-Memory ser processado, o atendimento continuará persistido, mas o registro correspondente na Outbox poderá nunca ser criado. Nesse caso, não existe nem sequer um registro pendente para o mecanismo de retry encontrar.
Isso pode resultar na perda silenciosa de uma notificação compulsória.
Mudança: a intenção de gerar a notificação será registrada na Transactional Outbox dentro da mesma transação do atendimento.
Assim, temos atomicidade:
Atendimento + Outbox
       |
       –> mesma transação
        	   |
        	    –> commit ou rollback
Se o atendimento for confirmado, a mensagem para processamento também estará persistida. Se houver uma falha posterior na comunicação com o e-SUS, a Outbox poderá realizar novas tentativas.

Resposta Objeção 6 — Redis como fonte de verdade para contadores críticos
Posição: Aceitamos a objeção.
A crítica é válida porque os contadores de cotas representam estado crítico do sistema e precisam ser persistentes, auditáveis e recuperáveis.
Utilizar o Redis como fonte de verdade significa que uma falha ou divergência nesse componente pode produzir um estado incorreto das cotas, dificultando a recuperação e a auditoria.
Mudança: o PostgreSQL será a fonte de verdade das cotas e alocações. As operações serão realizadas de maneira transacional, utilizando constraints e operações atômicas para impedir inconsistências.
O Redis poderá ser utilizado como cache ou fast-path para melhorar desempenho, mas a perda do Redis não poderá alterar o estado oficial das cotas.
Assim, temos:
PostgreSQL –> verdade do sistema
Redis –> otimização
Isso mantém a consistência mesmo diante da indisponibilidade do Redis.