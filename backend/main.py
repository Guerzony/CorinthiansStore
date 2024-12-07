from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
import time
import asyncpg
import os

# Função para obter a conexão com o banco de dados PostgreSQL
async def get_database():
    DATABASE_URL = os.environ.get("PGURL", "postgres://postgres:postgres@db:5432/produtos") 
    return await asyncpg.connect(DATABASE_URL)

# Inicializar a aplicação FastAPI
app = FastAPI()

# Modelo para adicionar novos produtos
class produto(BaseModel):
    id: Optional[int] = None
    nome: str
    marca: str
    cor: str
    quantidade: int
    preco: float

class produtoBase(BaseModel):
    nome: str
    marca: str
    cor: str
    quantidade: int
    preco: float

# Modelo para venda de produtos
class Vendaproduto(BaseModel):
    quantidade: int

# Modelo para atualizar atributos de um produto (exceto o ID)
class Atualizarproduto(BaseModel):
    nome: Optional[str] = None
    marca: Optional[str] = None
    cor: Optional[str] = None
    quantidade: Optional[int] = None
    preco: Optional[float] = None

# Middleware para logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    print(f"Path: {request.url.path}, Method: {request.method}, Process Time: {process_time:.4f}s")
    return response

# Função para verificar se o produto existe usado marca e nome do produto
async def produto_existe(nome: str, marca: int, conn: asyncpg.Connection):
    try:
        query = "SELECT * FROM produtos WHERE LOWER(nome) = LOWER($1) AND marca = $2"
        result = await conn.fetchval(query, nome, marca)
        return result is not None
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao verificar se o produto existe: {str(e)}")

# 1. Adicionar um novo produto
@app.post("/api/v1/produto/", status_code=201)
async def adicionar_produto(produto: produtoBase):
    conn = await get_database()
    if await produto_existe(produto.nome, produto.marca, conn):
        raise HTTPException(status_code=400, detail="produto já existe.")
    try:
        query = "INSERT INTO produtos (nome, marca, cor, quantidade, preco) VALUES ($1, $2, $3, $4, $5)"
        async with conn.transaction():
            result = await conn.execute(query, produto.nome, produto.marca, produto.cor, produto.quantidade, produto.preco)
            return {"message": "produto adicionado com sucesso!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao adicionar o produto: {str(e)}")
    finally:
        await conn.close()

# 2. Listar todos os produtos
@app.get("/api/v1/produtos/", response_model=List[produto])
async def listar_produtos():
    conn = await get_database()
    try:
        # Buscar todos os produtos no banco de dados
        query = "SELECT * FROM produtos"
        rows = await conn.fetch(query)
        produtos = [dict(row) for row in rows]
        return produtos
    finally:
        await conn.close()

# 3. Buscar produto por ID
@app.get("/api/v1/produtos/{produto_id}")
async def listar_produto_por_id(produto_id: int):
    conn = await get_database()
    try:
        # Buscar o produto por ID
        query = "SELECT * FROM produtos WHERE id = $1"
        produto = await conn.fetchrow(query, produto_id)
        if produto is None:
            raise HTTPException(status_code=404, detail="produto não encontrado.")
        return dict(produto)
    finally:
        await conn.close()

# 4. Vender um produto (reduzir quantidade no estoque)
@app.put("/api/v1/produtos/{produto_id}/vender/")
async def vender_produto(produto_id: int, venda: Vendaproduto):
    conn = await get_database()
    try:
        # Verificar se o produto existe
        query = "SELECT * FROM produtos WHERE id = $1"
        produto = await conn.fetchrow(query, produto_id)
        if produto is None:
            raise HTTPException(status_code=404, detail="produto não encontrado.")

        # Verificar se a quantidade no estoque é suficiente
        if produto['quantidade'] < venda.quantidade:
            raise HTTPException(status_code=400, detail="Quantidade insuficiente no estoque.")

        # Atualizar a quantidade no banco de dados
        nova_quantidade = produto['quantidade'] - venda.quantidade
        update_query = "UPDATE produtos SET quantidade = $1 WHERE id = $2"
        await conn.execute(update_query, nova_quantidade, produto_id)


        # Calcular o valor total da venda
        valor_venda = produto['preco'] * venda.quantidade
        # Registrar a venda na tabela de vendas
        insert_venda_query = """
            INSERT INTO vendas (produto_id, quantidade_vendida, valor_venda) 
            VALUES ($1, $2, $3)
        """
        await conn.execute(insert_venda_query, produto_id, venda.quantidade, valor_venda)

        # Criar um novo dicionário com os dados atualizados
        produto_atualizado = dict(produto)
        produto_atualizado['quantidade'] = nova_quantidade

        return {"message": "Venda realizada com sucesso!", "produto": produto_atualizado}
    finally:
        await conn.close()

# 5. Atualizar atributos de um produto pelo ID (exceto o ID)
@app.patch("/api/v1/produtos/{produto_id}")
async def atualizar_produto(produto_id: int, produto_atualizacao: Atualizarproduto):
    conn = await get_database()
    try:
        # Verificar se o produto existe
        query = "SELECT * FROM produtos WHERE id = $1"
        produto = await conn.fetchrow(query, produto_id)
        if produto is None:
            raise HTTPException(status_code=404, detail="produto não encontrado.")

        # Atualizar apenas os campos fornecidos
        update_query = """
            UPDATE produtos
            SET nome = COALESCE($1, nome),
                marca = COALESCE($2, marca),
                cor = COALESCE($3, cor),
                quantidade = COALESCE($4, quantidade),
                preco = COALESCE($5, preco)
            WHERE id = $6
        """
        await conn.execute(
            update_query,
            produto_atualizacao.nome,
            produto_atualizacao.marca,
            produto_atualizacao.cor,
            produto_atualizacao.quantidade,
            produto_atualizacao.preco,
            produto_id
        )
        return {"message": "produto atualizado com sucesso!"}
    finally:
        await conn.close()

# 6. Remover um produto pelo ID
@app.delete("/api/v1/produto/{produto_id}")
async def remover_produto(produto_id: int):
    conn = await get_database()
    try:
        # Verificar se o produto existe
        query = "SELECT * FROM produtos WHERE id = $1"
        produto = await conn.fetchrow(query, produto_id)
        if produto is None:
            raise HTTPException(status_code=404, detail="produto não encontrado.")

        # Remover o produto do banco de dados
        delete_query = "DELETE FROM produtos WHERE id = $1"
        await conn.execute(delete_query, produto_id)
        return {"message": "produto removido com sucesso!"}
    finally:
        await conn.close()

# 7. Resetar repositorio de produtos
@app.delete("/api/v1/produtos/")
async def resetar_produtos():
    init_sql = os.getenv("INIT_SQL", "db/init.sql")
    conn = await get_database()
    try:
        # Read SQL file contents
        with open(init_sql, 'r') as file:
            sql_commands = file.read()
        # Execute SQL commands
        await conn.execute(sql_commands)
        return {"message": "Banco de dados limpo com sucesso!!"}
    finally:
        await conn.close()


# 8 . Listar vendas
@app.get("/api/v1/vendas/")
async def listar_vendas():
    conn = await get_database()
    try:
        # Buscar todas as vendas no banco de dados
        query = "SELECT * FROM vendas"
        rows = await conn.fetch(query)
        vendas = [dict(row) for row in rows]
        return vendas
    finally:
        await conn.close()