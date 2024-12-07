DROP TABLE IF EXISTS "vendas";
DROP TABLE IF EXISTS "produtos"; 

CREATE TABLE "produtos" (
    "id" SERIAL PRIMARY KEY,
    "nome" VARCHAR(255) NOT NULL,
    "marca" VARCHAR(255) NOT NULL,
    "cor" VARCHAR(255) NOT NULL,
    "quantidade" INTEGER NOT NULL,
    "preco" FLOAT NOT NULL
);

CREATE TABLE "vendas" (
    "id" SERIAL PRIMARY KEY,
    "produto_id" INTEGER REFERENCES "produtos"(id) ON DELETE CASCADE, 
    "quantidade_vendida" INTEGER NOT NULL,
    "valor_venda" FLOAT NOT NULL,
    "data_venda" TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO "produtos" ("nome", "marca", "cor", "quantidade", "preco") VALUES ('Camisa', 'Adidas', 'marron', 5, 500.00);
INSERT INTO "produtos" ("nome", "marca", "cor", "quantidade", "preco") VALUES ('Tenis', 'nike', 'branco e preto',10, 300.00);
INSERT INTO "produtos" ("nome", "marca", "cor", "quantidade", "preco") VALUES ('Relogio', 'nike', 'Azul' ,15, 10000.00);
