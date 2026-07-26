# Contratos de Comunicação (Payloads)
**Sistema de Gestão de Bar e PDV**

Este documento define os contratos de dados (DTOs) para a comunicação entre os microsserviços (Worker Node.js, App Flutter e API Core Java).

---

## 1. Novo Pedido Externo (Assíncrono)
Este é o evento de mensageria. O worker (TypeScript) recebe o webhook do iFood ou WhatsApp, normaliza os dados e publica este payload na fila (SQS/RabbitMQ). A API Core (Java) consome esta fila para processar a venda e dar baixa no estoque.

*   **Origem:** Worker de Integração (Node.js)
*   **Destino:** Fila de Mensageria -> API Core (Java)
*   **Ação:** `INSERT` na tabela `ITEM_COMANDA` e gatilho de baixa de insumos.

### Payload (JSON)
```json
{
  "evento": "NOVO_PEDIDO",
  "detalhes_pedido": {
    "origem_pedido": "IFOOD", 
    "id_referencia_externa": "ifood-order-98765-xyz",
    "identificador_cliente": "Mesa 12", 
    "timestamp_criacao": "2026-07-22T19:30:45Z"
  },
  "itens": [
    {
      "id_produto": 105,
      "quantidade": 2,
      "preco_aplicado": 25.00,
      "observacoes": "Sem açúcar"
    },
    {
      "id_produto": 42,
      "quantidade": 1,
      "preco_aplicado": 15.50,
      "observacoes": null
    }
  ]
}
