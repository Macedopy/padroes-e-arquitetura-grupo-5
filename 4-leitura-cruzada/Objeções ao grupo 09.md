Objeções ao grupo 09

1 -

Reserva de leitos vs legado

O TRECHO

Pergunta Obrigatória 2 / C4 de Componentes: "Toda reserva nova passa por um único ponto: o Módulo Regulação de Leitos e Transporte [...] dentro do mesmo processo, sobre o mesmo banco transacional — assim a exclusividade é garantida."

O ARGUMENTO

A ADR 0002 estabelece que a migração é gradual e leva até 2 anos, com unidades antigas operando diretamente no sistema legado. Assumir que o novo módulo de escrita é o ponto único autorizador ignora que os postos não migrados continuam a escrever no banco antigo por fora. Como a transação local do banco novo não enxerga nem bloqueia as gravações diretas do legado em tempo real, haverá dois autorizadores concorrentes, gerando overbooking de leitos de UTI.

A SAÍDA

Centralizar a reserva diretamente no banco do legado (como fonte única da verdade durante a transição) através de chamadas síncronas com trava na ACL, ou implementar uma Saga com reserva temporária pendente e confirmação prévia no sistema antigo antes de efetivar o leito no novo banco.

2 –

Load shedding em Urgência (HTTP 429)

O TRECHO

ADR 0001 e Spike (⁠exemplo.py⁠): "Em sobrecarga, a célula rejeita requisições excedentes [...] simulando descarte ativo para manter a célula operacional e responsiva aos clientes já conectados."

O ARGUMENTO

Tratou-se o sistema de saúde pública como um e-commerce comercial, onde rejeitar requisições com ⁠HTTP 429⁠ é aceitável. Em uma UPA durante um surto epidemiológico, um médico ou enfermeiro não pode ter o cadastro de triagem rejeitado na tela enquanto atende


uma emergência. O descarte ativo na borda gera perda de operação e risco ao paciente, violando a premissa de resiliência e alta disponibilidade do domínio clínico.

· A SAÍDA

Substituir o descarte ativo (⁠HTTP 429⁠) por absorção assíncrona na borda utilizando filas/buffers locais com resposta ⁠HTTP 202 Accepted⁠. A aplicação confirma a recepção da ficha médica para o profissional de saúde e processa a ingestão no banco de dados conforme a capacidade dos workers, sem perda de dados nem interrupção do atendimento.

3 -

N pessoas da equipe vs. celulas

1 - O Trecho

ADR 0001, secao Consequencias ("N instalacoes completas para operar, observar e atualizar em vez de uma") e README, Envelope D.

2 - O Argumento

O envelope D diz explicitamente que a equipe e de 25 desenvolvedores em 3 times. Cada municipio novo contratado soma mais uma celula completa (app, fila, cache, banco) pros mesmos 25 devs operarem, e a propria ADR 0005 admite que o ciclo de implantacao "passa de minutos... para horas ou dias, conforme o numero de celulas". A arquitetura escala em numero de clientes, mas a capacidade operacional do time nao escala junto, em algum ponto os 25 devs nao dao conta de manter N celulas saudaveis ao mesmo tempo, e nenhuma ADR registra esse custo.

3 - A Saida

Infraestrutura como codigo com template unico de celula, provisionamento automatizado por onda e um teto explicito de celulas novas por sprint, coordenado por um time de plataforma dedicado, assumindo o custo de tirar gente do produto pra sustentar a operacao.

4-

Na correcao de dados do prontuario (LGPD)

1 - O Trecho

ADR 0004, Contexto ("este caso nao exige exclusao fisica antecipada do prontuario: o direito do paciente aqui e de acesso").


- 2 - O Argumento

A LGPD (Art. 18, III) garante tambem o direito de correcao de dado incompleto, inexato ou desatualizado, e esse direito nao depende do prazo de retencao. Num fluxo de eventos imutavel, corrigir um erro de cadastro, CPF ou nome digitado errado por exemplo, que e dado de identificacao e nao fato clinico, obriga a equipe a reescrever o passado ou conviver com o

dado errado por 20 anos. Eles so pensaram no "quem pode ver", nao no "quem pode corrigir".

3 - A Saida

Separar dado de identificacao (mutavel, corrigivel em tabela de estado normal) do fluxo de eventos clinicos (imutavel). O event sourcing fica so pra fato clinico, assumindo o custo de manter dois modelos de dado dentro do mesmo modulo de prontuario.

- 5 –

Objeções trabalho Douglas

Objeção 1:

- 1. O Trecho

ADR 0002, contexto: “Não há registro público das regras internas do legado além do

que a operação observa em produção.”

- 2. O Argumento

A própria ADR reconhece que as regras internas do sistema legado não estão

documentadas. Isso cria um risco durante a migração, pois podem existir comportamentos ou regras de negócio que não foram identificados pela equipe e que só aparecem durante a operação. Como o Envelope D possui vários municípios, esse problema pode se repetir em diferentes clientes, aumentando o esforço necessário para descobrir e validar essas regras durante a migração.

- 3. A Saída

Antes de migrar cada capacidade da regulação de leitos, realizar uma etapa de

levantamento e validação das regras observadas no legado, transformando os comportamentos identificados em testes de aptidão. Isso acrescenta esforço de análise e testes por município, mas reduz o risco de descobrir regras não documentadas somente depois da migração.


- 6 -

- 1. O Trecho

ADR 0003, contexto: “O caso exige integração por API com sistemas federais de saúde,

usados por todos os municípios clientes da mesma forma.”

- 2. O Argumento

Se a integração com os sistemas federais é utilizada da mesma forma por todos os

municípios, manter toda a implementação dentro de cada célula pode gerar duplicação de código e de manutenção. Embora o isolamento por célula atenda ao requisito de impedir que uma falha afete outros municípios, a solução aumenta o esforço de manutenção à medida que

novos clientes são adicionados.

- 3. A Saída

Manter a integração sendo executada de forma isolada em cada célula, mas

disponibilizar a lógica comum de integração como uma biblioteca ou componente versionado compartilhado em código, sem transformá-lo em um serviço compartilhado durante a execução. Assim, mantém-se o isolamento de falhas entre municípios, enquanto atualizações na integração federal podem ser reaproveitadas entre as células. O custo é a necessidade de versionar, distribuir e atualizar esse componente de forma coordenada.

- 7 -

- 1. O Trecho

ADR 0004, consequências: “A equipe precisa versionar o formato dos eventos clínicos

por até 20 anos, porque o código de hoje continua tendo de ler o formato de registros gravados há vinte anos.”

- 2. O Argumento

A consequência apresentada cria uma responsabilidade técnica de longo prazo: os

eventos registrados hoje precisarão continuar sendo interpretados pelo sistema por até 20 anos. Com mudanças futuras no sistema, no modelo de dados e na equipe responsável pelo desenvolvimento, manter compatibilidade com versões antigas dos eventos pode aumentar significativamente a complexidade de manutenção.


- 3. A Saída

Definir desde o início um mecanismo explícito de versionamento dos eventos,

acompanhado de testes de compatibilidade entre versões e uma política de migração ou arquivamento para eventos antigos. Isso adiciona custo de desenvolvimento, armazenamento e manutenção dos testes, mas reduz o risco de que uma alteração futura torne registros históricos ilegíveis.

- 8 -

- 1. O Trecho

ADR 0005, decisão: “Nas chamadas das UBS para os serviços da própria célula, aplicar

tempo limite curto derivado da latência observada, no máximo duas tentativas com recuo

exponencial, e um disjuntor que abre após falhas seguidas.”

- 2. O Argumento

Limitar as chamadas a duas tentativas e abrir o disjuntor após falhas seguidas pode

fazer com que uma instabilidade temporária da internet seja rapidamente convertida em chamadas interrompidas para o sistema central. Como as UBS realizam atendimentos continuamente, o comportamento definido para detectar uma falha precisa evitar que uma sequência curta de falhas de rede provoque interrupções desnecessárias na sincronização dos atendimentos.

Além disso, o próprio Envelope D estabelece que existe **pico sazonal**, tornando

relevante o impacto de atendimentos pendentes acumulados durante períodos de instabilidade.

- 3. A Saída

Definir o limite de abertura do disjuntor com base em métricas reais de falhas e

latência das UBS, diferenciando falhas transitórias de indisponibilidades prolongadas. Também deve existir monitoramento da quantidade e do tempo dos atendimentos pendentes antes e durante a abertura do disjuntor. Isso adiciona complexidade ao monitoramento e à configuração por célula, mas permite ajustar o mecanismo de proteção ao comportamento real das UBS.
