CREATE OR REPLACE TRIGGER TRG_BAIXA_ESTOQUE
AFTER INSERT ON ITEM_COMANDA
FOR EACH ROW
BEGIN
    -- Inicia um loop buscando todos os insumos da ficha técnica do produto vendido
    FOR r_ficha IN (
        SELECT ID_INSUMO, QTD_UTILIZADA
        FROM FICHA_TECNICA
        WHERE ID_PRODUTO = :NEW.ID_PRODUTO
    ) LOOP
        -- Atualiza a tabela de insumo, subtraindo a quantidade utilizada multiplicada 
        -- pela quantidade de produtos que o cliente pediu (ex: pediu 2 caipirinhas)
        UPDATE INSUMO
        SET QTD_ESTOQUE = QTD_ESTOQUE - (r_ficha.QTD_UTILIZADA * :NEW.QTD)
        WHERE ID_INSUMO = r_ficha.ID_INSUMO;
    END LOOP;
END;
/
