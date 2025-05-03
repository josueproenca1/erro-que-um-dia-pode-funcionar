from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os
import json

# Configuração do aplicativo Flask com caminho estático correto
app = Flask(__name__, static_folder='.')
CORS(app, resources={r"/api/*": {"origins": "*"}})

DATABASE = 'database/padaria.db'

# Ensure database directory exists
os.makedirs(os.path.dirname(DATABASE), exist_ok=True)

def inicializar_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Create products table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS produtos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        categoria TEXT NOT NULL,
        codigo TEXT NOT NULL UNIQUE,
        preco REAL NOT NULL
    )
    ''')
    
    # Create cart table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS carrinho (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        categoria TEXT NOT NULL,
        codigo TEXT NOT NULL,
        preco REAL NOT NULL,
        quantidade INTEGER NOT NULL
    )
    ''')
    
    # Create fiado (credit) table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS fiado (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente TEXT NOT NULL,
        telefone TEXT NOT NULL,
        data TEXT NOT NULL,
        total REAL NOT NULL,
        itens TEXT NOT NULL,
        pago INTEGER DEFAULT 0
    )
    ''')
    
    conn.commit()
    conn.close()

def conectar_db():
    return sqlite3.connect(DATABASE)

# Rota para servir arquivos HTML e outros arquivos estáticos
@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('.', path)

# Routes for static files - esta tem prioridade sobre a rota genérica
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# Rota para teste específico para a página teste_post.html
@app.route('/teste_post.html')
def teste_post_page():
    return send_from_directory('.', 'teste_post.html')

# Rota para teste específico para a página adicionar_produto.html
@app.route('/adicionar_produto.html')
def adicionar_produto_page():
    return send_from_directory('.', 'adicionar_produto.html')

# Rota para testar se a API está funcionando
@app.route('/api/teste', methods=['GET'])
def api_teste():
    return jsonify({"status": "ok", "message": "API funcionando corretamente!"})

# API endpoints for products
@app.route('/api/produtos', methods=['GET'])
def listar_produtos():
    conn = conectar_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM produtos")
    dados = cur.fetchall()
    conn.close()
    return jsonify([
        {"id": row[0], "nome": row[1], "categoria": row[2], "codigo": row[3], "preco": row[4]}
        for row in dados
    ])

@app.route('/api/produtos', methods=['POST'])
def adicionar_produto():
    # Log da solicitação para depuração
    print("Recebido POST para /api/produtos")
    print(f"Content-Type: {request.headers.get('Content-Type')}")
    
    # Verificar se o conteúdo é JSON
    if not request.is_json:
        print("O pedido não contém JSON válido")
        return jsonify({'status': 'erro', 'message': 'O pedido deve conter JSON válido'}), 400
        
    try:
        # Tentar ler o JSON
        data = request.json
        print(f"Dados recebidos: {data}")
        
        if not data:
            print("JSON vazio ou inválido")
            return jsonify({'status': 'erro', 'message': 'JSON inválido ou vazio'}), 400
            
        # Verificar campos obrigatórios
        required_fields = ['nome', 'categoria', 'codigo', 'preco']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            print(f"Campos ausentes: {missing_fields}")
            return jsonify({
                'status': 'erro', 
                'message': f'Campos obrigatórios ausentes: {", ".join(missing_fields)}'
            }), 400
                
        conn = conectar_db()
        cur = conn.cursor()
        
        try:
            cur.execute("INSERT INTO produtos (nome, categoria, codigo, preco) VALUES (?, ?, ?, ?)",
                        (data['nome'], data['categoria'], data['codigo'], data['preco']))
            produto_id = cur.lastrowid
            conn.commit()
            print(f"Produto adicionado com sucesso, ID: {produto_id}")
            return jsonify({
                'status': 'ok', 
                'message': 'Produto adicionado com sucesso',
                'id': produto_id
            })
        except sqlite3.IntegrityError as e:
            print(f"Erro de integridade: {e}")
            return jsonify({'status': 'erro', 'message': 'Código de produto já existe'}), 400
        except Exception as e:
            print(f"Erro ao inserir no banco: {e}")
            return jsonify({'status': 'erro', 'message': str(e)}), 500
        finally:
            conn.close()
    except Exception as e:
        print(f"Erro ao processar a requisição: {e}")
        return jsonify({'status': 'erro', 'message': f'Erro ao processar a requisição: {str(e)}'}), 500
        
@app.route('/api/produtos/<codigo>', methods=['DELETE'])
def remover_produto(codigo):
    conn = conectar_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM produtos WHERE codigo = ?", (codigo,))
    if cur.rowcount == 0:
        conn.close()
        return jsonify({'status': 'erro', 'message': 'Produto não encontrado'}), 404
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok', 'message': 'Produto removido com sucesso'})

# API endpoints for cart
@app.route('/api/carrinho', methods=['GET'])
def listar_carrinho():
    conn = conectar_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM carrinho")
    dados = cur.fetchall()
    conn.close()
    return jsonify([
        {"id": row[0], "nome": row[1], "categoria": row[2], "codigo": row[3], "preco": row[4], "quantidade": row[5]}
        for row in dados
    ])

@app.route('/api/carrinho', methods=['POST'])
def adicionar_ao_carrinho():
    if not request.is_json:
        return jsonify({'status': 'erro', 'message': 'O pedido deve conter JSON válido'}), 400
        
    try:
        data = request.json
        conn = conectar_db()
        cur = conn.cursor()
        
        # Check if the item already exists in the cart
        cur.execute("SELECT * FROM carrinho WHERE codigo = ?", (data['codigo'],))
        item_existente = cur.fetchone()
        
        if item_existente:
            # Update quantity if the item already exists
            nova_quantidade = item_existente[5] + data['quantidade']
            cur.execute("UPDATE carrinho SET quantidade = ? WHERE codigo = ?", 
                       (nova_quantidade, data['codigo']))
        else:
            # Add new item if it doesn't exist
            cur.execute("INSERT INTO carrinho (nome, categoria, codigo, preco, quantidade) VALUES (?, ?, ?, ?, ?)",
                       (data['nome'], data['categoria'], data['codigo'], data['preco'], data['quantidade']))
        
        conn.commit()
        conn.close()
        return jsonify({'status': 'ok', 'message': 'Item adicionado ao carrinho'})
    except Exception as e:
        return jsonify({'status': 'erro', 'message': str(e)}), 500

@app.route('/api/carrinho/<codigo>', methods=['PUT'])
def atualizar_quantidade_carrinho(codigo):
    if not request.is_json:
        return jsonify({'status': 'erro', 'message': 'O pedido deve conter JSON válido'}), 400
        
    try:
        data = request.json
        quantidade = data.get('quantidade', 0)
        
        conn = conectar_db()
        cur = conn.cursor()
        
        if quantidade <= 0:
            # Remove the item if quantity is 0 or less
            cur.execute("DELETE FROM carrinho WHERE codigo = ?", (codigo,))
        else:
            # Update the quantity
            cur.execute("UPDATE carrinho SET quantidade = ? WHERE codigo = ?", (quantidade, codigo))
        
        conn.commit()
        conn.close()
        return jsonify({'status': 'ok', 'message': 'Quantidade atualizada'})
    except Exception as e:
        return jsonify({'status': 'erro', 'message': str(e)}), 500

@app.route('/api/carrinho/<codigo>', methods=['DELETE'])
def remover_do_carrinho(codigo):
    conn = conectar_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM carrinho WHERE codigo = ?", (codigo,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok', 'message': 'Item removido do carrinho'})

@app.route('/api/carrinho/limpar', methods=['POST'])
def limpar_carrinho():
    conn = conectar_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM carrinho")
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok', 'message': 'Carrinho limpo'})

# API endpoint for fiado (credit purchases)
@app.route('/api/fiado', methods=['POST'])
def registrar_fiado():
    if not request.is_json:
        return jsonify({'status': 'erro', 'message': 'O pedido deve conter JSON válido'}), 400
        
    try:
        data = request.json
        conn = conectar_db()
        cur = conn.cursor()
        
        try:
            cur.execute("INSERT INTO fiado (cliente, telefone, data, total, itens) VALUES (?, ?, ?, ?, ?)",
                       (data['cliente'], data['telefone'], data['data'], data['total'], data['itens']))
            conn.commit()
            
            # Clear the cart after credit purchase is registered
            cur.execute("DELETE FROM carrinho")
            conn.commit()
            
            conn.close()
            return jsonify({'status': 'ok', 'message': 'Compra fiado registrada com sucesso'})
        except Exception as e:
            conn.close()
            return jsonify({'status': 'erro', 'message': str(e)}), 500
    except Exception as e:
        return jsonify({'status': 'erro', 'message': f'Erro ao processar a requisição: {str(e)}'}), 500

@app.route('/api/fiado', methods=['GET'])
def listar_fiado():
    conn = conectar_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM fiado")
    dados = cur.fetchall()
    conn.close()
    return jsonify([
        {
            "id": row[0], 
            "cliente": row[1], 
            "telefone": row[2], 
            "data": row[3], 
            "total": row[4], 
            "itens": row[5],
            "pago": bool(row[6])
        }
        for row in dados
    ])

@app.route('/api/fiado/<int:id>/pagar', methods=['POST'])
def pagar_fiado(id):
    conn = conectar_db()
    cur = conn.cursor()
    cur.execute("UPDATE fiado SET pago = 1 WHERE id = ?", (id,))
    if cur.rowcount == 0:
        conn.close()
        return jsonify({'status': 'erro', 'message': 'Registro não encontrado'}), 404
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok', 'message': 'Pagamento registrado com sucesso'})

if __name__ == '__main__':
    inicializar_db()
    app.run(debug=True, host='0.0.0.0')  # host='0.0.0.0' permite acessar de qualquer IP