# Documento de Requisitos e Regras de Negócio
**Projeto:** Sistema de Gestão de Bar, PDV e Omnichannel

Este documento consolida os Requisitos Funcionais (RF), Requisitos Não Funcionais (RNF) e as Regras de Negócio (RN) que guiarão a engenharia e o desenvolvimento da plataforma.

---

## 1. Requisitos Funcionais (RF)
*Descrevem o que o sistema deve fazer e as funcionalidades visíveis ao usuário.*

### Módulo de Atendimento e Omnichannel
* **[RF01]** O sistema deve permitir a realização de pedidos via WhatsApp de forma automatizada (integração via chatbot/webhook).
* **[RF02]** O sistema deve disponibilizar um cardápio digital acessível via QR Code (Web) e Totem/Tablet, com atualização de catálogo em tempo real.
* **[RF03]** O cliente deve ser capaz de adicionar observações personalizadas aos itens do pedido (ex: "sem gelo", "ao ponto").
* **[RF04]** O sistema deve notificar ativamente o cliente sobre as mudanças de status do pedido (Em preparo, Pronto).

### Módulo de Caixa e Salão (PDV)
* **[RF05]** O operador deve conseguir abrir, editar, transferir itens e fechar comandas vinculadas a identificadores físicos (mesas) ou lógicos (senhas).
* **[RF06]** O sistema deve consolidar automaticamente pedidos físicos (feitos no salão) e virtuais (ifood, whatsapp) na mesma comanda.
* **[RF07]** O sistema deve possuir uma tela de KDS (Kitchen Display System) para a equipe de cozinha gerenciar a fila de preparo.

### Módulo de Gestão e Retaguarda (ERP)
* **[RF08]** O sistema deve permitir o cadastro hierárquico de Produtos, Insumos e suas respectivas Fichas Técnicas.
* **[RF09]** O sistema deve manter um extrato de pontos de fidelidade atrelado à identificação do cliente (CPF).
* **[RF10]** O sistema deve emitir relatórios de fechamento de caixa e consolidação de métodos de pagamento.

---

## 2. Requisitos Não Funcionais (RNF)
*Descrevem como o sistema deve se comportar, englobando padrões de arquitetura, segurança e performance.*

### Arquitetura e Tecnologias
* **[RNF01]** As interfaces de salão, totem e KDS devem ser construídas em **Flutter**, garantindo uma base de código única e alta performance em dispositivos variados (tablets, mobile, web).
* **[RNF02]** A API Core (regras de negócio e finanças) deve ser implementada em **Java**, focando em tipagem forte e integridade transacional.
* **[RNF03]** O processamento de webhooks externos (WhatsApp, iFood) deve ser feito via microsserviços paralelos (Workers) em **TypeScript/Node.js**.
* **[RNF04]** A sincronização de status das telas (KDS e Salão) deve ocorrer em tempo real (latência < 2s) utilizando coleções NoSQL no **Firebase Firestore**.

### Segurança e Escalabilidade
* **[RNF05]** O banco de dados principal deve ser estritamente relacional (Oracle ou PostgreSQL), delegando rotinas internas (**PL/SQL**) para garantir a consistência das baixas de estoque.
* **[RNF06]** Pedidos virtuais devem ser obrigatoriamente enfileirados em um *Message Broker* (ex: AWS SQS ou RabbitMQ) para evitar sobrecarga no banco de dados durante picos de concorrência.
* **[RNF07]** Os serviços de back-end devem ser executados em containers isolados dentro de uma VPC privada, expostos à internet apenas através de um API Gateway.

---

## 3. Regras de Negócio (RN)
*Determinam as restrições e lógicas inegociáveis que regem o funcionamento financeiro e operacional do estabelecimento.*

* **[RN01] Baixa Automática de Estoque:** A venda de um Produto deve, obrigatoriamente, acionar o abatimento proporcional dos Insumos vinculados à sua Ficha Técnica no momento exato da inserção do item na comanda.
* **[RN02] Controle de Estoque Insuficiente:** Se a quantidade em estoque de um insumo não for suficiente, o sistema deve alertar o operador. A venda (estoque negativo) só será processada se a flag "Permitir Quebra" estiver ativa no perfil gerencial.
* **[RN03] Precedência de Pagamento:** O status financeiro de uma comanda só pode ser alterado para "Paga" pelo módulo isolado de Caixa (PDV). Após esse status, o sistema deve bloquear novas adições de itens à comanda.
* **[RN04] Imutabilidade de Preço Histórico:** O preço aplicado no item da comanda deve ser gravado de forma estática no momento da intenção de compra. Alterações posteriores no preço de catálogo do produto não devem retroagir em comandas ativas ou pagas.
* **[RN05] Motor de Fidelidade:** O cálculo de acúmulo de pontos de fidelidade só deve ser computado e creditado no extrato do cliente após a confirmação final da conciliação do pagamento da comanda.
* **[RN06] Isolamento Multi Lojas:** Todas as consultas (SELECT) e inserções (INSERT/UPDATE) no banco de dados relacional devem, obrigatoriamente, registrar e filtrar o identificador da loja, garantindo o isolamento total dos dados operacionais e financeiros entre franquias diferentes.
