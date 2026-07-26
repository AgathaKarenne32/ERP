# Esquema de Dados NoSQL (Firebase Firestore)
**Sistema de Gestão de Bar e PDV**

Este documento mapeia as coleções utilizadas no Firestore. O Firebase atua estritamente como uma **camada de visualização e sincronização em tempo real** (Read-Model). A fonte da verdade financeira e transacional permanece no banco relacional (Oracle/PostgreSQL).

---

## 1. Coleção: `tickets_producao`
Alimenta a tela da cozinha/copa (KDS - Kitchen Display System). Os aplicativos "escutam" esta coleção filtrando pelo status.

*   **Document ID:** Auto-gerado pelo Firebase ou `ID_ITEM` do banco relacional.
*   **Permissões:** Leitura para o App Cozinha. Atualização de status para o App Cozinha.
*   **Estrutura:**

```json
{
  "id_comanda": 4092,
  "identificador_cliente": "Mesa 12",
  "origem": "IFOOD",
  "status_producao": "PENDENTE", 
  "timestamp_pedido": "2026-07-22T19:30:45Z",
  "itens": [
    {
      "nome_produto": "Caipirinha",
      "quantidade": 2,
      "observacoes": "Sem açúcar"
    }
  ]
}
