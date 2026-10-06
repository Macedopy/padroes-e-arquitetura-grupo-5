

[Pós-objeções] - Revisão arquitetural

Após a análise das objeções recebidas, foram revisadas as decisões arquiteturais do
projeto.
As ADRs anteriormente aprovadas não foram editadas. Quando uma objeção contradiz uma
decisão existente, foi criada uma nova ADR para substituí-la.
ADR-007 — Revisão da Integração com Legado de Leitos
Substitui: ADR-003
Objeções relacionadas: 1 e 4.
## Alterações:
● SQL Direct no banco do legado foi removido.
● A integração passa a utilizar exclusivamente a API/contrato do sistema legado
através da ACL.
● Redis/Redlock deixa de ser a garantia final de consistência das reservas.
● PostgreSQL passa a garantir a consistência das reservas através de mecanismos
transacionais e constraints de unicidade.
Motivo: reduzir o acoplamento com o banco do legado e evitar que uma regra crítica de
consistência dependa exclusivamente de um serviço externo de locks.

ADR-008 — Persistência da Outbox para Notificações
Substitui: ADR-001
Objeção relacionada: 5.
## Alterações:
● A comunicação In-Memory deixa de ser utilizada como mecanismo responsável pela
persistência de notificações compulsórias.
● A intenção de envio passa a ser registrada na Transactional Outbox na mesma
transação do evento clínico.
● O envio ao sistema externo continua assíncrono, permitindo novas tentativas em
caso de falha.
Motivo: evitar que uma falha entre a publicação do evento In-Memory e a criação da
Outbox cause a perda silenciosa de uma notificação obrigatória.

Objeção 2 — RabbitMQ

## Decisão: Rebatida.
A objeção apontou o custo operacional adicional do RabbitMQ, porém a decisão foi mantida
porque o RabbitMQ possui responsabilidade complementar à Outbox: a Outbox garante a
persistência da mensagem, enquanto o RabbitMQ realiza a distribuição e o processamento
assíncrono.
Nenhuma ADR foi substituída.

## Objeção 3 — Monólito Modular
## Decisão: Rebatida.
A diferença de características entre os módulos não foi considerada suficiente para justificar
a adoção de microsserviços. As restrições do Envelope C, principalmente a equipe reduzida
de infraestrutura e o ambiente On-Premises, continuam favorecendo o Monólito Modular.
Nenhuma ADR foi substituída.

Objeção 6 — Redis como fonte de verdade das cotas
Decisão: Aceita como princípio arquitetural, porém não houve substituição de ADR.
Os ADRs 001–006 não registram uma decisão que estabeleça o Redis como fonte de
verdade das cotas. Portanto, não foi criada uma ADR com status de substituição para essa
objeção, pois não existe uma ADR anterior identificável a ser substituída.
Caso essa decisão esteja registrada em outro artefato arquitetural, deverá ser criada uma
nova ADR substituindo explicitamente o documento correspondente.
