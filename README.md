# QAConcurso — Quiz Inteligente para Concursos Públicos

> Plataforma web de estudo com geração automática de questões via Inteligência Artificial, voltada para candidatos do Concurso Nacional Unificado (CNU).

---

## Descrição

O **QAConcurso** é uma aplicação web full-stack que automatiza a criação de questões de múltipla escolha para estudo de concursos públicos. Utilizando a API do **Google Gemini**, o sistema gera questões contextualizadas com base em textos de referência organizados por eixo temático, armazena o histórico de respostas do usuário e aplica uma lógica inteligente de revisão espaçada para maximizar o aprendizado.

---

## Contexto do Projeto

Estudar para concursos públicos exige grande volume de exercícios, revisão constante e cobertura de múltiplos tópicos. O QAConcurso foi criado para resolver esse problema de forma automatizada: em vez de depender de bancos de questões fixos e limitados, a aplicação gera novas questões dinamicamente com IA, garantindo variedade infinita de exercícios baseados nos conteúdos programáticos reais dos eixos temáticos do CNU. O sistema também rastreia o desempenho do estudante e prioriza a revisão de tópicos com menor taxa de acerto.

---

## Tecnologias Utilizadas

### Linguagens
- **Python 3** — backend e lógica do servidor
- **JavaScript (ES6+)** — lógica do frontend (vanilla JS com async/await)
- **HTML5 / CSS3** — estrutura e estilização das páginas

### Frameworks e Bibliotecas Backend
| Tecnologia | Finalidade |
|---|---|
| **Flask** | Framework web principal (rotas, templates, servidor HTTP) |
| **Flask-Login** | Gerenciamento de sessões e autenticação de usuários |
| **Flask-Bcrypt** | Hash seguro de senhas (bcrypt) |
| **python-dotenv** | Carregamento de variáveis de ambiente via arquivo `.env` |
| **google-generativeai** | SDK oficial para integração com a API do Google Gemini |

### Banco de Dados
- **SQLite** — banco de dados relacional local, acessado via biblioteca padrão `sqlite3` do Python

### Frontend (CDN)
| Tecnologia | Finalidade |
|---|---|
| **Bootstrap 5.3** | Framework CSS para layout responsivo e componentes UI |
| **Font Awesome 6.5** | Biblioteca de ícones |
| **Chart.js** | Geração de gráficos de desempenho interativos |

### API Externa
- **Google Gemini API** (`gemini-2.0-flash`) — geração de questões de múltipla escolha com IA generativa

### Ferramentas e Infraestrutura
- **python-dotenv** — gerenciamento de variáveis de ambiente
- **Git** — controle de versão
- **Ambiente Virtual Python (venv)** — isolamento de dependências

---

## Arquitetura e Estrutura do Projeto

O projeto segue uma arquitetura **monolítica MVC** com Flask, onde toda a lógica de negócio, acesso a dados e servimento de templates está centralizada no arquivo `app.py`. O frontend utiliza o padrão de **SPA parcial** (Single Page Application), em que a navegação entre as seções do quiz é controlada por JavaScript sem recarregamento completo da página.

### Padrões Arquiteturais
- **MVC (Model-View-Controller)**: modelos definidos via SQL puro, views em Jinja2 (templates HTML), controllers nas rotas do Flask
- **Template Inheritance (Herança de Templates)**: `layout.html` serve como base, e as demais páginas estendem (`{% extends %}`) esse layout
- **REST API interna**: rotas que retornam JSON são consumidas pelo frontend via `fetch()` (ex.: `/obter-pergunta-quiz`, `/salvar-resposta`, `/api/resultados`)
- **Revisão Espaçada (Spaced Repetition)**: algoritmo de priorização de perguntas que considera:
  1. Perguntas nunca respondidas (prioridade máxima)
  2. Perguntas respondidas incorretamente (revisão imediata)
  3. Perguntas corretas respondidas há mais de 7 dias (revisão periódica)
- **Distribuição Uniforme de Tópicos**: sistema que rastreia quantas perguntas foram geradas por tópico e prioriza os menos abordados

### Fluxo Principal da Aplicação
```
Usuário faz login → Seleciona eixo temático → 
  Sistema busca pergunta no banco (cache) →
    Se não existir: chama API Gemini com texto de contexto →
      Salva pergunta no SQLite →
  Exibe pergunta com 5 alternativas →
  Usuário responde → Sistema salva resultado →
  Exibe explicação detalhada de cada alternativa →
  Pré-gera próximas perguntas em background →
  Ao final do quiz (10 perguntas): exibe estatísticas da sessão
```

---

## Funcionalidades Principais

### 🔐 Autenticação e Segurança
- Cadastro de usuários com hash de senha via **bcrypt**
- Login/logout com gerenciamento de sessão por **Flask-Login**
- Proteção de rotas com o decorator `@login_required`
- Dados sigilosos (chave de API, secret key) carregados via variáveis de ambiente

### 🤖 Geração de Questões com IA
- Questões geradas dinamicamente pela **API Google Gemini** (`gemini-2.0-flash`)
- Prompts engenheirados para garantir saída em **JSON estruturado**
- Contexto baseado em **arquivos de texto por eixo temático** (`contextos/eixo_N.txt`)
- Foco em **tópicos específicos** extraídos via regex do conteúdo do eixo
- Cada questão gerada inclui: enunciado, 5 alternativas (A–E), resposta correta e explicação detalhada para cada alternativa

### 🧠 Sistema Inteligente de Estudo
- **Cache de perguntas**: questões geradas são armazenadas no banco para reuso eficiente
- **Revisão espaçada**: priorização automática de perguntas com base no histórico de respostas
- **Distribuição balanceada de tópicos**: garante cobertura uniforme de todos os tópicos do edital
- **Pré-geração assíncrona**: enquanto o usuário responde uma questão, o sistema solicita à IA as próximas em background (`Promise.all`)
- **Indicação visual do tipo de pergunta**: questões de revisão são sinalizadas ao usuário (revisão por erro ou revisão periódica)

### 📊 Dashboard de Resultados
- Estatísticas gerais: total de perguntas respondidas, acertos, erros e taxa de acerto
- **Gráfico de evolução geral** ao longo do tempo (Chart.js — linha)
- **Gráfico de desempenho por eixo** (Chart.js — rosca/doughnut)
- **Gráfico de evolução por eixo** ao longo do tempo (Chart.js — linha multi-série)
- Tabela detalhada com métricas por eixo temático e indicador de status

### 🎮 Interface do Quiz
- Quiz com **10 perguntas por sessão**
- Contador visual de progresso (ex.: "Pergunta 3/10")
- Feedback imediato após resposta: destaque em verde (correta) e vermelho (incorreta)
- Exibição da explicação da alternativa correta e da selecionada
- Resultado final da sessão com pontuação e percentual de acerto
- Rota administrativa para geração manual de perguntas (`/gerar-uma-pergunta/<eixo>`)

---

## Integrações e APIs

### Google Gemini API
- **SDK**: `google-generativeai`
- **Modelo utilizado**: `gemini-2.0-flash`
- **Autenticação**: chave de API carregada via variável de ambiente `GEMINI_API_KEY`
- **Uso**: geração de questões de múltipla escolha em formato JSON estruturado
- **Engenharia de Prompt**: o sistema monta prompts com contexto específico por eixo e tópico, instrui o modelo a responder somente com JSON válido e inclui tratamento de limpeza para casos onde o modelo retorna markdown (`\`\`\`json`)

---

## Como Executar o Projeto

### Pré-requisitos
- Python 3.9+
- Conta no [Google AI Studio](https://aistudio.google.com/) com uma chave de API do Gemini

### 1. Clone o repositório
```bash
git clone <url-do-repositorio>
cd QAConcurso
```

### 2. Crie e ative um ambiente virtual
```bash
# Criar
python -m venv venv

# Ativar no Windows
venv\Scripts\activate

# Ativar no Linux/macOS
source venv/bin/activate
```

### 3. Instale as dependências
```bash
pip install -r requirementes.txt
```

> **Nota:** O arquivo está com o nome `requirementes.txt` (typo no nome). Certifique-se de usar o nome correto ao instalar.

### 4. Configure as variáveis de ambiente
Crie um arquivo `.env` na raiz do projeto com o seguinte conteúdo:
```env
GEMINI_API_KEY=sua_chave_aqui
```

### 5. Inicialize o banco de dados e execute a aplicação
```bash
python app.py
```

O banco de dados SQLite (`cnu_quiz.db`) será criado automaticamente na primeira execução.

### 6. Acesse a aplicação
Abra o navegador e acesse:
```
http://localhost:5000
```

Crie uma conta pelo link de cadastro e comece a estudar.

---

## Estrutura de Pastas

```
QAConcurso/
│
├── app.py                  # Aplicação principal: rotas, lógica de negócio, config do Flask
│
├── requirementes.txt       # Dependências Python do projeto
├── .gitignore              # Arquivos ignorados pelo Git (venv, .env, banco de dados)
│
├── contextos/              # Textos de referência usados como base para geração de questões
│   ├── eixo_1.txt          # Conteúdo programático do Eixo 1 (Gestão Governamental e Governo Digital)
│   └── eixo_2.txt          # Conteúdo programático do Eixo 2 (Políticas Públicas)
│
├── templates/              # Templates HTML (Jinja2)
│   ├── layout.html         # Template base com navbar, CDN imports e estrutura global
│   ├── login.html          # Página de login
│   ├── register.html       # Página de cadastro
│   ├── dashboard.html      # Dashboard do quiz (seleção de eixo + interface do quiz)
│   ├── resultados.html     # Página de resultados com gráficos e estatísticas
│   └── resultados_clean.html # Versão alternativa da página de resultados
│
├── static/                 # Arquivos estáticos servidos ao frontend
│   ├── style.css           # Estilos personalizados da aplicação
│   ├── script.js           # Lógica principal do quiz (SPA, fetch, state management)
│   ├── resultados.js       # Lógica da página de resultados e renderização dos gráficos
│   ├── resultados_fixed.js # Versão alternativa/corrigida do script de resultados
│   └── resultados_new.js   # Versão iterada do script de resultados
│
└── cnu_quiz.db             # Banco de dados SQLite (gerado em runtime, ignorado pelo Git)
```

### Tabelas do Banco de Dados

| Tabela | Descrição |
|---|---|
| `usuarios` | Armazena usuários cadastrados (id, username, password_hash) |
| `perguntas` | Cache de questões geradas pela IA (eixo, tópico, pergunta, alternativas, resposta, explicações) |
| `respostas_usuarios` | Histórico de respostas de cada usuário por pergunta (acertou, data) |
| `topicos_usuario` | Controle de distribuição — quantas perguntas foram geradas por tópico para cada usuário |

---

## Possíveis Melhorias

- **Adicionar mais eixos temáticos**: os arquivos `eixo_3.txt`, `eixo_4.txt` e `eixo_5.txt` ainda não foram criados; o backend já suporta até o eixo 5
- **Implementar algoritmo de revisão espaçada formal** (ex.: SM-2 do Anki) em substituição à lógica atual baseada em 7 dias
- **Separar a aplicação em módulos** (Blueprints do Flask) para melhor manutenibilidade à medida que o projeto cresce
- **Adicionar suporte a múltiplos concursos**, não apenas o CNU
- **Migrar o banco de dados para PostgreSQL** para suportar múltiplos usuários em ambiente produtivo
- **Adicionar testes automatizados** (pytest) para as rotas e lógica de geração de perguntas
- **Criar sistema de filtragem de perguntas duplicadas** antes de salvar no banco
- **Implementar rate limiting** nas chamadas à API do Gemini para evitar custos excessivos
- **Adicionar autenticação OAuth** (Google/GitHub) via Flask-OAuthlib
- **Dockerizar a aplicação** para facilitar deploy em serviços cloud
- **Adicionar modo de estudo por tópico específico**, permitindo ao usuário focar em um único tópico do edital
- **Exportar relatório de desempenho** em PDF ou CSV

---

## Aprendizados Técnicos

Este projeto demonstra e pratica os seguintes conhecimentos técnicos:

### Desenvolvimento Backend
- Criação de aplicações web com **Flask** (rotas, blueprints, templates Jinja2)
- **Autenticação segura**: hash de senhas com bcrypt, gerenciamento de sessão com Flask-Login
- **Integração com banco de dados relacional** (SQLite) sem ORM, utilizando SQL puro com queries complexas (JOINs, window functions, COALESCE, subqueries)
- **Carregamento de variáveis de ambiente** com python-dotenv para separar configuração do código

### Inteligência Artificial e APIs
- **Consumo de API de IA generativa**: integração com Google Gemini via SDK oficial
- **Engenharia de Prompt** (Prompt Engineering): estruturação de prompts para obter saídas em formato JSON confiável
- **Tratamento de respostas de LLMs**: limpeza e parsing de JSON retornado por modelos de linguagem

### Frontend e UX
- **Vanilla JavaScript com async/await** para comunicação assíncrona com o backend (Fetch API)
- **Manipulação de DOM** para criar uma experiência de SPA (Single Page Application) sem frameworks
- **Gerenciamento de estado** no frontend com variáveis de controle (quizAtivo, carregandoPergunta)
- **Pré-carregamento assíncrono** de dados para melhorar a experiência do usuário
- **Renderização de gráficos** interativos com Chart.js (linha, doughnut, multi-série)
- **Design responsivo** com Bootstrap 5

### Arquitetura e Boas Práticas
- **Padrão MVC** aplicado em contexto de aplicação Flask monolítica
- **Sistema de cache** de dados gerados por IA para reduzir chamadas à API e latência
- **Algoritmo de priorização** de conteúdo para estudo inteligente (revisão espaçada simplificada)
- **Tratamento de erros** robusto com `try/except` e respostas de erro padronizadas em JSON
- **Separação de responsabilidades** entre backend (API REST) e frontend (consumidor)

---

## Palavras-chave Técnicas (Importante para ATS)

`Python` · `Flask` · `Flask-Login` · `Flask-Bcrypt` · `SQLite` · `SQL` · `REST API` · `API Google Gemini` · `IA Generativa` · `Prompt Engineering` · `Autenticação` · `Sessão de Usuário` · `Bcrypt` · `Hash de Senha` · `Segurança Web` · `JavaScript` · `Vanilla JS` · `Fetch API` · `Async/Await` · `DOM Manipulation` · `Chart.js` · `Bootstrap 5` · `HTML5` · `CSS3` · `Jinja2` · `Template Engine` · `MVC` · `SPA` · `Revisão Espaçada` · `Machine Learning` · `LLM` · `Google Generative AI` · `python-dotenv` · `Variáveis de Ambiente` · `Git` · `Ambiente Virtual Python` · `JSON` · `Full-Stack` · `Desenvolvimento Web` · `Backend` · `Frontend` · `Banco de Dados Relacional` · `Engenharia de Software` · `CNU` · `Concurso Público` · `EdTech`

---

## Autor

Desenvolvido como projeto pessoal de estudo para o **Concurso Nacional Unificado (CNU)**, com foco em praticar desenvolvimento full-stack com Python, Flask e integração com APIs de Inteligência Artificial.