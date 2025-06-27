from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
import sqlite3
import json
from datetime import datetime
import os
from dotenv import load_dotenv
import google.generativeai as genai
import traceback

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# --- CONFIGURAÇÃO INICIAL ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua-chave-secreta-aqui-mude-em-producao'

# Inicialização das extensões
bcrypt = Bcrypt(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor, faça login para acessar esta página.'

# --- CONFIGURAÇÃO DO GOOGLE GEMINI ---
api_key = os.getenv("GEMINI_API_KEY")
model = None

if not api_key:
    print("ERRO: A variável de ambiente GEMINI_API_KEY não foi encontrada.")
    print("Por favor, crie um arquivo .env e adicione a linha: GEMINI_API_KEY='sua_chave'")
else:
    try:
        genai.configure(api_key=api_key)
        # CORREÇÃO: O nome do modelo foi ajustado para um existente.
        model = genai.GenerativeModel('gemini-2.0-flash') 
        print("API do Gemini configurada com sucesso a partir do .env.")
    except Exception as e:
        print(f"ERRO: Não foi possível configurar a API do Gemini. Verifique sua chave. Detalhes: {e}")

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
DATABASE = 'cnu_quiz.db'

def get_db():
    """Conecta ao banco de dados SQLite"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializa o banco de dados com as tabelas necessárias"""
    with get_db() as conn:
        # (código do init_db sem alterações)
        conn.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS perguntas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                eixo TEXT NOT NULL,
                topico TEXT,
                pergunta TEXT NOT NULL,
                alternativas TEXT NOT NULL,
                resposta_correta TEXT NOT NULL,
                explicacoes TEXT NOT NULL,
                data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS respostas_usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                pergunta_id INTEGER NOT NULL,
                acertou BOOLEAN NOT NULL,
                data_resposta TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES usuarios (id),
                FOREIGN KEY (pergunta_id) REFERENCES perguntas (id)
            )
        ''')
        
        # Nova tabela para controle de distribuição de tópicos
        conn.execute('''
            CREATE TABLE IF NOT EXISTS topicos_usuario (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                eixo TEXT NOT NULL,
                topico TEXT NOT NULL,
                perguntas_geradas INTEGER DEFAULT 0,
                ultima_pergunta TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES usuarios (id),
                UNIQUE(user_id, eixo, topico)
            )
        ''')
        
        # Adicionar coluna topico se não existir (para compatibilidade)
        try:
            conn.execute('ALTER TABLE perguntas ADD COLUMN topico TEXT')
        except:
            pass  # Coluna já existe
        
        conn.commit()

# --- MODELO DE USUÁRIO E LÓGICA DE GERAÇÃO ---
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    with get_db() as conn:
        user = conn.execute('SELECT * FROM usuarios WHERE id = ?', (user_id,)).fetchone()
        if user:
            return User(user['id'], user['username'])
    return None

def gerar_pergunta_com_ia(eixo, topico_especifico=None):
    """ (VERSÃO ATUALIZADA)
    Lê o arquivo de contexto do eixo, gera perguntas via API do Gemini
    baseado nesse texto e retorna um objeto JSON.
    Se topico_especifico for fornecido, foca a pergunta nesse tópico.
    """
    if not model:
        raise Exception("O modelo de IA Gemini não foi inicializado. Verifique a chave de API.")

    caminho_arquivo = f"contextos/eixo_{eixo}.txt"
    print(f">>> [DEBUG] Tentando ler o arquivo de contexto: {caminho_arquivo}")

    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as f:
            texto_base = f.read()
        print(">>> [DEBUG] Arquivo de contexto lido com sucesso.")
    except FileNotFoundError:
        print(f"!!!!!!!!!!!!!!!!! ERRO CRÍTICO !!!!!!!!!!!!!!!!!!")
        print(f"O arquivo de contexto '{caminho_arquivo}' não foi encontrado.")
        print("Certifique-se de que o arquivo existe na pasta 'contextos'.")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        raise FileNotFoundError(f"Arquivo de contexto para o eixo {eixo} não encontrado.")

    # Se um tópico específico foi solicitado, extrair o conteúdo dele
    contexto_focado = texto_base
    if topico_especifico:
        print(f">>> [DEBUG] Focando no tópico: {topico_especifico}")
        # Extrair o número do tópico (ex: topico_3 -> 3)
        numero_topico = topico_especifico.replace('topico_', '')
        
        # Buscar o conteúdo específico do tópico
        import re
        padrao = rf'^{numero_topico}\.\s*(.+?)(?=^\d+\.|\Z)'
        match = re.search(padrao, texto_base, re.MULTILINE | re.DOTALL)
        
        if match:
            contexto_focado = f"{numero_topico}. {match.group(1).strip()}"
            print(f">>> [DEBUG] Conteúdo do tópico extraído: {len(contexto_focado)} caracteres")
        else:
            print(f">>> [DEBUG] Tópico {numero_topico} não encontrado, usando contexto completo")

    instrucao_topico = ""
    if topico_especifico:
        numero_topico = topico_especifico.replace('topico_', '')
        instrucao_topico = f"\n\nIMPORTANTE: Crie a pergunta focada especificamente no tópico {numero_topico} do conteúdo fornecido."

    prompt_template = f"""
    Você é um especialista em criar questões para concursos públicos, agindo como uma banca examinadora.

    Baseado EXCLUSIVAMENTE no "TEXTO DE REFERÊNCIA" fornecido abaixo, crie UMA pergunta de múltipla escolha sobre o Eixo Temático {eixo} do CNU, com 5 alternativas (A, B, C, D, E).

    As perguntas não devem está escrito de acordo com o texto de referência, conforme texto de referência, e não precisam falar de acordo com o texto de referência ou algo do tipo.{instrucao_topico}

    Sua resposta DEVE ser um objeto JSON válido e nada mais. Não inclua ```json ou qualquer outro texto fora do objeto JSON.

    O objeto JSON deve seguir ESTRITAMENTE a seguinte estrutura:
    {{
      "pergunta": "O texto completo da pergunta aqui.",
      "alternativas": [
        {{ "id": "A", "texto": "Texto da alternativa A." }},
        {{ "id": "B", "texto": "Texto da alternativa B." }},
        {{ "id": "C", "texto": "Texto da alternativa C." }},
        {{ "id": "D", "texto": "Texto da alternativa D." }},
        {{ "id": "E", "texto": "Texto da alternativa E." }}
      ],
      "resposta_correta": "A letra da alternativa correta (ex: 'C').",
      "explicacoes": {{
        "A": "A explicação detalhada do porquê a alternativa A está correta ou incorreta, baseada no texto de referência.",
        "B": "A explicação detalhada do porquê a alternativa B está correta ou incorreta, baseada no texto de referência.",
        "C": "A explicação detalhada do porquê a alternativa C está correta ou incorreta, baseada no texto de referência.",
        "D": "A explicação detalhada do porquê a alternativa D está correta ou incorreta, baseada no texto de referência.",
        "E": "A explicação detalhada do porquê a alternativa E está correta ou incorreta, baseada no texto de referência."
      }}
    }}
    
    --- TEXTO DE REFERÊNCIA ---
    {contexto_focado}
    --- FIM DO TEXTO DE REFERÊNCIA ---
    """
    
    print(">>> [DEBUG] Enviando prompt para a API do Gemini com texto de referência...")
    response = model.generate_content(prompt_template)
    
    # print(f">>> [DEBUG] Texto bruto recebido da API: {response.text}")
    
    json_text = response.text.strip()
    if json_text.startswith("```json"):
        json_text = json_text[7:]
    if json_text.endswith("```"):
        json_text = json_text[:-3]

    print(">>> [DEBUG] Tentando converter texto em JSON...")
    parsed_json = json.loads(json_text)
    print(">>> [DEBUG] JSON convertido com sucesso!")
    return parsed_json


# --- ROTAS DE AUTENTICAÇÃO (sem alterações) ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    # ... (código sem alterações)
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if not username or not password:
            flash('Username e senha são obrigatórios!')
            return render_template('register.html')
        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
        try:
            with get_db() as conn:
                conn.execute('INSERT INTO usuarios (username, password_hash) VALUES (?, ?)', (username, password_hash))
                conn.commit()
                flash('Registro realizado com sucesso! Faça login.')
                return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username já existe!')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    # ... (código sem alterações)
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with get_db() as conn:
            user = conn.execute('SELECT * FROM usuarios WHERE username = ?', (username,)).fetchone()
        if user and bcrypt.check_password_hash(user['password_hash'], password):
            user_obj = User(user['id'], user['username'])
            login_user(user_obj)
            return redirect(url_for('dashboard'))
        else:
            flash('Username ou senha incorretos!')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    # ... (código sem alterações)
    logout_user()
    flash('Logout realizado com sucesso!')
    return redirect(url_for('login'))

# --- ROTAS DO QUIZ (com logs de depuração) ---
@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', username=current_user.username)

@app.route('/obter-pergunta-quiz', methods=['POST'])
@login_required
def obter_pergunta_quiz():
    # ... (código sem alterações)
    try:
        data = request.get_json()
        eixo = data.get('eixo')
        print(f"\n--- [LOG] Recebida requisição para o eixo: {eixo} ---")
        
        if not eixo:
            print("--- [ERRO] Eixo não fornecido na requisição.")
            return jsonify({'error': 'Eixo é obrigatório'}), 400
        
        with get_db() as conn:
            print("--- [LOG] Buscando pergunta existente no banco de dados...")
            
            # Prioridade 1: Perguntas nunca respondidas
            pergunta = conn.execute('''
                SELECT p.* FROM perguntas p
                LEFT JOIN respostas_usuarios ru ON p.id = ru.pergunta_id AND ru.user_id = ?
                WHERE p.eixo = ? AND ru.id IS NULL
                ORDER BY RANDOM() LIMIT 1
            ''', (current_user.id, eixo)).fetchone()
            
            # Prioridade 2: Se não há perguntas não respondidas, buscar perguntas respondidas incorretamente
            # Dar prioridade às perguntas erradas mais recentemente
            if not pergunta:
                print("--- [LOG] Nenhuma pergunta não respondida encontrada. Buscando perguntas respondidas incorretamente...")
                pergunta = conn.execute('''
                    SELECT p.*, ru.data_resposta FROM perguntas p
                    INNER JOIN respostas_usuarios ru ON p.id = ru.pergunta_id 
                    WHERE p.eixo = ? AND ru.user_id = ? AND ru.acertou = 0
                    ORDER BY ru.data_resposta DESC, RANDOM() LIMIT 1
                ''', (eixo, current_user.id)).fetchone()
                
                if pergunta:
                    print(f"--- [LOG] Pergunta incorreta encontrada para revisão: ID {pergunta['id']} (respondida em {pergunta['data_resposta']})")
                    
            # Prioridade 3: Se não há perguntas incorretas, permitir revisão de perguntas corretas antigas
            if not pergunta:
                print("--- [LOG] Nenhuma pergunta incorreta encontrada. Buscando perguntas corretas antigas para revisão...")
                pergunta = conn.execute('''
                    SELECT p.*, ru.data_resposta FROM perguntas p
                    INNER JOIN respostas_usuarios ru ON p.id = ru.pergunta_id 
                    WHERE p.eixo = ? AND ru.user_id = ? AND ru.acertou = 1
                    AND datetime(ru.data_resposta) < datetime('now', '-7 days')
                    ORDER BY ru.data_resposta ASC, RANDOM() LIMIT 1
                ''', (eixo, current_user.id)).fetchone()
                
                if pergunta:
                    print(f"--- [LOG] Pergunta correta antiga encontrada para revisão: ID {pergunta['id']} (respondida em {pergunta['data_resposta']})")
            
            if pergunta:
                print(f"--- [LOG] Pergunta encontrada no banco! ID: {pergunta['id']}")
                
                # Determinar o tipo de pergunta para feedback ao usuário
                tipo_pergunta = "nova"
                if 'data_resposta' in pergunta.keys():
                    # Se há data_resposta, significa que veio de uma das queries de revisão
                    resposta_anterior = conn.execute('''
                        SELECT acertou FROM respostas_usuarios 
                        WHERE user_id = ? AND pergunta_id = ? 
                        ORDER BY data_resposta DESC LIMIT 1
                    ''', (current_user.id, pergunta['id'])).fetchone()
                    
                    if resposta_anterior:
                        tipo_pergunta = "revisao_incorreta" if resposta_anterior['acertou'] == 0 else "revisao_antiga"
                
                return jsonify({
                    'id': pergunta['id'],
                    'pergunta': pergunta['pergunta'],
                    'alternativas': json.loads(pergunta['alternativas']),
                    'resposta_correta': pergunta['resposta_correta'],
                    'explicacoes': json.loads(pergunta['explicacoes']) if pergunta['explicacoes'] else {},
                    'eixo': pergunta['eixo'],
                    'tipo_pergunta': tipo_pergunta
                })
            else:
                print("--- [LOG] Nenhuma pergunta encontrada. Iniciando geração via IA...")
                
                # Determinar tópico menos usado para distribuição uniforme
                topico_escolhido = obter_topico_menos_usado(eixo, current_user.id)
                print(f"--- [LOG] Tópico escolhido para nova pergunta: {topico_escolhido}")
                
                nova_pergunta_data = gerar_pergunta_com_ia(eixo, topico_escolhido)
                
                print("--- [LOG] Salvando nova pergunta no banco de dados...")
                cursor = conn.execute('''
                    INSERT INTO perguntas (eixo, topico, pergunta, alternativas, resposta_correta, explicacoes)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    eixo,
                    topico_escolhido,
                    nova_pergunta_data['pergunta'],
                    json.dumps(nova_pergunta_data['alternativas']),
                    nova_pergunta_data['resposta_correta'],
                    json.dumps(nova_pergunta_data['explicacoes'])
                ))
                
                pergunta_id = cursor.lastrowid
                conn.commit()
                print(f"--- [LOG] Pergunta salva com o ID: {pergunta_id}")
                
                # Atualizar contador de uso do tópico
                if topico_escolhido:
                    atualizar_uso_topico(current_user.id, eixo, topico_escolhido)
                    print(f"--- [LOG] Contador do tópico {topico_escolhido} atualizado")
                
                return jsonify({
                    'id': pergunta_id,
                    'pergunta': nova_pergunta_data['pergunta'],
                    'alternativas': nova_pergunta_data['alternativas'],
                    'resposta_correta': nova_pergunta_data['resposta_correta'],
                    'explicacoes': nova_pergunta_data['explicacoes'],
                    'eixo': eixo,
                    'topico': topico_escolhido,
                    'tipo_pergunta': 'nova'
                })
                
    except Exception as e:
        print("\n!!!!!!!!!!!!!!!!! ERRO INESPERADO EM /obter-pergunta-quiz !!!!!!!!!!!!!!!!!!")
        traceback.print_exc()
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
        return jsonify({'error': f'Erro interno do servidor: {str(e)}'}), 500

# --- ROTAS restantes (sem alterações) ---
@app.route('/salvar-resposta', methods=['POST'])
@login_required
def salvar_resposta():
    try:
        data = request.get_json()
        print(f"\n--- [LOG] Dados recebidos para salvar resposta: {data}")
        
        pergunta_id = data.get('pergunta_id')
        acertou = data.get('acertou')
        
        print(f"--- [LOG] pergunta_id: {pergunta_id}, acertou: {acertou}, user_id: {current_user.id}")
        
        if pergunta_id is None or acertou is None:
            print("--- [ERRO] Pergunta ID ou acertou está faltando")
            return jsonify({'error': 'Pergunta ID e acertou são obrigatórios'}), 400
            
        with get_db() as conn:
            # Verificar se a pergunta existe
            pergunta = conn.execute('SELECT * FROM perguntas WHERE id = ?', (pergunta_id,)).fetchone()
            if not pergunta:
                print(f"--- [ERRO] Pergunta com ID {pergunta_id} não encontrada")
                return jsonify({'error': 'Pergunta não encontrada'}), 404
            
            # Verificar se já existe uma resposta para esta pergunta e usuário
            resposta_existente = conn.execute(
                'SELECT id FROM respostas_usuarios WHERE user_id = ? AND pergunta_id = ?', 
                (current_user.id, pergunta_id)
            ).fetchone()
            
            if resposta_existente:
                print(f"--- [LOG] Resposta já existe para pergunta {pergunta_id}, atualizando...")
                conn.execute(
                    'UPDATE respostas_usuarios SET acertou = ?, data_resposta = CURRENT_TIMESTAMP WHERE user_id = ? AND pergunta_id = ?',
                    (acertou, current_user.id, pergunta_id)
                )
            else:
                print(f"--- [LOG] Inserindo nova resposta para pergunta {pergunta_id}")
                conn.execute(
                    'INSERT INTO respostas_usuarios (user_id, pergunta_id, acertou, data_resposta) VALUES (?, ?, ?, CURRENT_TIMESTAMP)', 
                    (current_user.id, pergunta_id, acertou)
                )
            
            conn.commit()
            print(f"--- [LOG] Resposta salva com sucesso!")
            
            return jsonify({'success': True, 'message': 'Resposta salva com sucesso'})
            
    except Exception as e:
        print(f"\n!!!!!!!!!!!!!!!!! ERRO EM /salvar-resposta !!!!!!!!!!!!!!!!!")
        traceback.print_exc()
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

@app.route('/pre-gerar-proxima', methods=['POST'])
@login_required
def pre_gerar_proxima():
    # ... (código sem alterações)
    try:
        data = request.get_json()
        eixo = data.get('eixo')
        if not eixo:
            return jsonify({'error': 'Eixo é obrigatório'}), 400
        nova_pergunta_data = gerar_pergunta_com_ia(eixo)
        with get_db() as conn:
            conn.execute('''
                INSERT INTO perguntas (eixo, pergunta, alternativas, resposta_correta, explicacoes)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                eixo,
                nova_pergunta_data['pergunta'],
                json.dumps(nova_pergunta_data['alternativas']),
                nova_pergunta_data['resposta_correta'],
                json.dumps(nova_pergunta_data['explicacoes'])
            ))
            conn.commit()
        return jsonify({'success': True, 'message': 'Pergunta pré-gerada com sucesso'})
    except Exception as e:
        return jsonify({'error': f'Erro interno: {str(e)}'}), 500

# ADIÇÃO DA ROTA DE GERAÇÃO MANUAL
@app.route('/gerar-uma-pergunta/<int:eixo>')
@login_required
def gerar_pergunta_manual(eixo):
    """
    Uma rota manual para gerar e salvar uma única pergunta,
    facilitando a depuração e o povoamento do banco de dados.
    """
    if eixo not in [1, 2, 3, 4, 5]:
        return "Eixo inválido. Use um número de 1 a 5.", 400
    
    try:
        print(f"--- [GERAÇÃO MANUAL] Iniciando para o eixo {eixo}...")
        # A função já converte o eixo para string ao criar o caminho do arquivo
        nova_pergunta_data = gerar_pergunta_com_ia(str(eixo))
        
        with get_db() as conn:
            conn.execute('''
                INSERT INTO perguntas (eixo, pergunta, alternativas, resposta_correta, explicacoes)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                str(eixo),
                nova_pergunta_data['pergunta'],
                json.dumps(nova_pergunta_data['alternativas']),
                nova_pergunta_data['resposta_correta'],
                json.dumps(nova_pergunta_data['explicacoes'])
            ))
            conn.commit()
        
        mensagem = f"Sucesso! Uma nova pergunta para o Eixo {eixo} foi gerada e salva no banco de dados."
        print(f"--- [GERAÇÃO MANUAL] {mensagem}")
        return mensagem

    except Exception as e:
        mensagem_erro = f"Falha na geração manual para o Eixo {eixo}."
        print(f"--- [GERAÇÃO MANUAL] {mensagem_erro}")
        traceback.print_exc()
        return f"{mensagem_erro} Verifique o terminal para mais detalhes.", 500

@app.route('/progresso-topicos/<eixo>')
@login_required
def progresso_topicos(eixo):
    """Retorna o progresso do usuário nos tópicos de um eixo"""
    try:
        # Obter todos os tópicos disponíveis
        topicos_disponiveis = obter_topicos_eixo(eixo)
        
        with get_db() as conn:
            # Obter progresso do usuário
            progresso = conn.execute('''
                SELECT topico, perguntas_geradas, ultima_pergunta
                FROM topicos_usuario
                WHERE user_id = ? AND eixo = ?
                ORDER BY topico
            ''', (current_user.id, eixo)).fetchall()
            
            # Converter para dict para facilitar acesso
            progresso_dict = {p['topico']: p for p in progresso}
            
            resultado = []
            for topico in topicos_disponiveis:
                progresso_topico = progresso_dict.get(topico['id'], {
                    'perguntas_geradas': 0,
                    'ultima_pergunta': None
                })
                
                resultado.append({
                    'topico_id': topico['id'],
                    'numero': topico['numero'],
                    'titulo': topico['titulo'],
                    'perguntas_geradas': progresso_topico['perguntas_geradas'],
                    'ultima_pergunta': progresso_topico['ultima_pergunta']
                })
            
            return jsonify({
                'eixo': eixo,
                'topicos': resultado,
                'total_topicos': len(topicos_disponiveis)
            })
            
    except Exception as e:
        print(f"Erro ao obter progresso dos tópicos: {e}")
        return jsonify({'error': str(e)}), 500

def obter_topicos_eixo(eixo):
    """Extrai os tópicos disponíveis do arquivo de contexto do eixo"""
    topicos = []
    try:
        caminho_arquivo = f'contextos/eixo_{eixo}.txt'
        if os.path.exists(caminho_arquivo):
            with open(caminho_arquivo, 'r', encoding='utf-8') as f:
                conteudo = f.read()
                
            # Extrair tópicos numerados (padrão: número seguido de ponto)
            import re
            padrao_topicos = r'^(\d+)\.\s*(.+?)(?=\n◦|\n\d+\.|\Z)'
            matches = re.findall(padrao_topicos, conteudo, re.MULTILINE | re.DOTALL)
            
            for numero, titulo in matches:
                topico_limpo = titulo.strip().split('\n')[0]  # Pegar só a primeira linha
                topicos.append({
                    'numero': int(numero),
                    'titulo': topico_limpo,
                    'id': f"topico_{numero}"
                })
                
    except Exception as e:
        print(f"Erro ao extrair tópicos do eixo {eixo}: {e}")
        
    return topicos

def obter_topico_menos_usado(eixo, user_id):
    """Retorna o tópico que foi menos usado pelo usuário"""
    with get_db() as conn:
        # Buscar tópicos com menos perguntas geradas
        resultado = conn.execute('''
            SELECT topico, perguntas_geradas, ultima_pergunta
            FROM topicos_usuario
            WHERE user_id = ? AND eixo = ?
            ORDER BY perguntas_geradas ASC, ultima_pergunta ASC
            LIMIT 1
        ''', (user_id, eixo)).fetchone()
        
        if resultado:
            return resultado['topico']
        
        # Se não há registros, obter tópicos disponíveis e escolher o primeiro
        topicos_disponiveis = obter_topicos_eixo(eixo)
        if topicos_disponiveis:
            return topicos_disponiveis[0]['id']
            
        return None

def atualizar_uso_topico(user_id, eixo, topico):
    """Atualiza o contador de uso do tópico"""
    with get_db() as conn:
        # Tentar atualizar registro existente
        conn.execute('''
            INSERT OR REPLACE INTO topicos_usuario 
            (user_id, eixo, topico, perguntas_geradas, ultima_pergunta)
            VALUES (?, ?, ?, 
                COALESCE((SELECT perguntas_geradas FROM topicos_usuario 
                         WHERE user_id = ? AND eixo = ? AND topico = ?), 0) + 1,
                CURRENT_TIMESTAMP)
        ''', (user_id, eixo, topico, user_id, eixo, topico))
        conn.commit()

@app.route('/resultados')
@login_required
def resultados():
    """Página de resultados do usuário"""
    return render_template('resultados.html', username=current_user.username)

@app.route('/api/resultados')
@login_required
def api_resultados():
    """API que retorna dados dos resultados para gráficos"""
    try:
        print(f"[DEBUG] API Resultados - User ID: {current_user.id}")
        
        with get_db() as conn:
            # Estatísticas gerais
            stats_gerais = conn.execute('''
                SELECT 
                    COUNT(*) as total_perguntas,
                    SUM(CASE WHEN acertou = 1 THEN 1 ELSE 0 END) as total_acertos,
                    SUM(CASE WHEN acertou = 0 THEN 1 ELSE 0 END) as total_erros
                FROM respostas_usuarios 
                WHERE user_id = ?
            ''', (current_user.id,)).fetchone()
            
            print(f"[DEBUG] Stats gerais: {dict(stats_gerais)}")
            
            # Estatísticas por eixo
            stats_por_eixo = conn.execute('''
                SELECT 
                    p.eixo,
                    COUNT(*) as total,
                    SUM(CASE WHEN ru.acertou = 1 THEN 1 ELSE 0 END) as acertos,
                    SUM(CASE WHEN ru.acertou = 0 THEN 1 ELSE 0 END) as erros
                FROM perguntas p
                INNER JOIN respostas_usuarios ru ON p.id = ru.pergunta_id
                WHERE ru.user_id = ?
                GROUP BY p.eixo
                ORDER BY p.eixo
            ''', (current_user.id,)).fetchall()
            
            print(f"[DEBUG] Stats por eixo: {len(stats_por_eixo)} registros")
            
            # Evolução geral por dia
            evolucao_geral = conn.execute('''
                SELECT 
                    DATE(ru.data_resposta) as data,
                    COUNT(*) as perguntas_dia,
                    SUM(CASE WHEN ru.acertou = 1 THEN 1 ELSE 0 END) as acertos_dia,
                    SUM(COUNT(*)) OVER (ORDER BY DATE(ru.data_resposta)) as total_acumulado,
                    SUM(SUM(CASE WHEN ru.acertou = 1 THEN 1 ELSE 0 END)) OVER (ORDER BY DATE(ru.data_resposta)) as acertos_acumulados
                FROM respostas_usuarios ru
                WHERE ru.user_id = ?
                GROUP BY DATE(ru.data_resposta)
                ORDER BY DATE(ru.data_resposta)
            ''', (current_user.id,)).fetchall()
            
            print(f"[DEBUG] Evolução geral: {len(evolucao_geral)} registros")
            
            # Evolução por eixo
            evolucao_eixos = conn.execute('''
                SELECT 
                    p.eixo,
                    DATE(ru.data_resposta) as data,
                    COUNT(*) as perguntas_dia,
                    SUM(CASE WHEN ru.acertou = 1 THEN 1 ELSE 0 END) as acertos_dia,
                    SUM(COUNT(*)) OVER (PARTITION BY p.eixo ORDER BY DATE(ru.data_resposta)) as total_acumulado,
                    SUM(SUM(CASE WHEN ru.acertou = 1 THEN 1 ELSE 0 END)) OVER (PARTITION BY p.eixo ORDER BY DATE(ru.data_resposta)) as acertos_acumulados
                FROM respostas_usuarios ru
                INNER JOIN perguntas p ON ru.pergunta_id = p.id
                WHERE ru.user_id = ?
                GROUP BY p.eixo, DATE(ru.data_resposta)
                ORDER BY p.eixo, DATE(ru.data_resposta)
            ''', (current_user.id,)).fetchall()
            
            print(f"[DEBUG] Evolução por eixo: {len(evolucao_eixos)} registros")
            
            # Converter para dicionários
            resultado = {
                'total_perguntas': stats_gerais['total_perguntas'] or 0,
                'total_acertos': stats_gerais['total_acertos'] or 0,
                'total_erros': stats_gerais['total_erros'] or 0,
                'por_eixo': [dict(row) for row in stats_por_eixo],
                'evolucao_geral': [dict(row) for row in evolucao_geral],
                'evolucao_eixos': [dict(row) for row in evolucao_eixos]
            }
            
            print(f"[DEBUG] Retornando resultado com {resultado['total_perguntas']} perguntas")
            
            return jsonify(resultado)
            
    except Exception as e:
        print(f"[ERROR] Erro ao obter resultados: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# --- Inicialização ---
if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)