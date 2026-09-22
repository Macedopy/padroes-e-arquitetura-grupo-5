# Entrega 2 — Documento de Arquitetura de Software

**Grupo 05** · PUC-Campinas · Padrões e Arquitetura de Software
**Caso:** Saúde — Rede Municipal de Atenção à Saúde
**Envelope C:** Prefeitura, equipe interna (10 devs + 2 infra), servidores próprios (*On-Premises*, sem nuvem pública por exigência legal), orçamento anual fixo, sistema legado de regulação de leitos não pode ser desligado.

---

## 1. Visão Geral da Arquitetura

A arquitetura da Rede Municipal de Saúde foi desenhada sob o modelo de **Arquitetura Híbrida Primária**, adotando o estilo **Monólito Modular** como espinha dorsal (*Backbone*), complementado por padrões táticos de **Arquitetura Hexagonal (Ports and Adapters)**, **Arquitetura Orientada a Eventos (EDA)**, **CQRS** e **Pipes and Filters**.

Esta composição equilibra a riqueza funcional e a interdependência das regras clínicas com o rigoroso limite operacional do **Envelope C** (10 desenvolvedores, 2 profissionais de infraestrutura, orçamento fixo e ambiente estritamente *On-Premises*).

## Respostas às 5 Perguntas Obrigatórias do Caso

### Pergunta 1: Como a UPA continua triando e atendendo com a internet fora do ar, e o que acontece quando ela volta?
**Resposta:** A resiliência das UPAs é sustentada pelo estilo **Orientado a Eventos (EDA)** e operação descentralizada de contingência. A aplicação Web da UPA funciona em modo PWA com armazenamento temporário em banco local de borda (*Edge Database*). Durante a perda de link, os eventos de triagem e atendimento são enfileirados localmente. Na reativação da rede, os eventos são consumidos em lote pelo **RabbitMQ** central utilizando idempotência baseada no Hash do atendimento para reconciliar as informações sem duplicidade no Prontuário Eletrônico.
* **Sustentação:** `ADR-001`, `ADR-004` e Diagrama de Contêineres (`C4-Contêineres`).

### Pergunta 2: Como duas unidades disputando o mesmo leito nunca conseguem reservá-lo ao mesmo tempo, com o sistema legado ainda no circuito?
**Resposta:** A consistência forte na reserva é garantida por um **Lock Distribuído (Redis/Redlock)** adquirido pelo `BedRegulationService` antes de qualquer confirmação. Duas unidades que tentam reservar o mesmo leito simultaneamente disputam o mesmo lock: apenas uma consegue adquiri-lo, a outra recebe rejeição imediata (< 15ms) sem nunca chegar a confirmar a reserva no legado. A confirmação no sistema legado é feita de forma assíncrona e resiliente via **Transactional Outbox** (`TransactionalOutboxHandler`), garantindo que a reserva local e o registro de sincronização com o legado aconteçam na mesma transação — não há janela em que o leito esteja reservado localmente mas não enfileirado para o legado.
* **Sustentação:** `ADR-003` e Diagrama de Componentes (`C4-Componentes`).

### Pergunta 3: Como o prontuário garante que se saiba quem acessou cada registro, e como convive a guarda de 20 anos com os direitos do paciente sob a LGPD?
**Resposta:** Através do padrão **CQRS (Command Query Responsibility Segregation)** e registro de auditoria *Append-Only* inspirada em **Event Sourcing**. As operações de escrita (comandos clínicos) gravam a alteração e registram um evento imutável na tabela de auditoria (`prontuario_audit_log`). A camada de leitura utiliza views materializadas e uma réplica de leitura no PostgreSQL para relatórios e consultas de histórico. Dados históricos com mais de 5 anos são movidos por Jobs automatizados para tabelas particionadas por ano (*cold storage* no próprio PostgreSQL), preservando a performance da base quente.
* **Sustentação:** `ADR-002` e Diagrama de Contêineres (`C4-Contêineres`).

### Pergunta 4: Como a notificação compulsória chega à vigilância em até 24 horas mesmo se o sistema federal estiver indisponível?
**Resposta:** O módulo de Vigilância Epidemiológica processa os eventos clínicos relevantes através de um pipeline **Pipes and Filters** (ingestão → triagem de doenças de notificação compulsória → enriquecimento → saída), consumindo do mesmo **RabbitMQ** usado pelas UPAs. O envio ao e-SUS/CADSUS passa por um **Transactional Outbox** dedicado — a notificação é persistida na mesma transação do evento clínico — e um **Circuit Breaker** evita que uma indisponibilidade do sistema federal se propague para o restante da aplicação. Reenvios seguem *backoff* exponencial até confirmação; um job de monitoração alerta a equipe caso uma notificação ultrapasse o SLA de 24h sem sucesso.
* **Sustentação:** `ADR-006` e Diagrama de Contêineres (`C4-Contêineres`).

### Pergunta 5: Como o sistema legado de regulação é substituído aos poucos sem interromper o serviço?
**Resposta:** A substituição gradual é viabilizada pela aplicação da **Arquitetura Hexagonal (Ports & Adapters)** combinada com uma **Camada Anti-Corrupção (ACL)** no módulo de leitos. O novo sistema não acessa a base legada diretamente; toda interação passa por adaptadores que traduzem o modelo do novo domínio para os contratos do legado. Isso permite substituir o legado no futuro trocando apenas o adaptador (`LegacyBedSystemAdapter`), sem tocar na regra de negócio nova nem exigir uma migração *big bang*.
* **Sustentação:** `ADR-003`, `ADR-005` e Diagrama de Componentes (`C4-Componentes`).
