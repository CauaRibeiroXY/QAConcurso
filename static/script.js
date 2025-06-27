// Aguarda o carregamento completo do DOM
document.addEventListener('DOMContentLoaded', function() {
    // --- Seletores de Elementos ---
    // Garante que todos os seletores correspondem aos IDs do dashboard.html
    const welcomeSectionEl = document.getElementById('welcome-section');
    const selecaoEixoEl = document.getElementById('eixo-selecao');
    const quizAreaEl = document.getElementById('quiz-area');
    const resultadoAreaEl = document.getElementById('resultado-area');
    const contadorUiEl = document.getElementById('contador-ui');
    const loadingEl = document.getElementById('loading');
    const erroContainerEl = document.getElementById('erro-container');
    const perguntaTextoEl = document.getElementById('pergunta-texto');
    const alternativasContainerEl = document.getElementById('alternativas-container');
    const explicacaoContainerEl = document.getElementById('explicacao-container');
    const botaoProximaEl = document.getElementById('botao-proxima');
    const botaoFinalizarEl = document.getElementById('botao-finalizar');
    const voltarInicioEl = document.getElementById('voltar-inicio');
    const botoesEixo = document.querySelectorAll('.eixo-btn');

    // --- Estado do Quiz ---
    const TAMANHO_DO_QUIZ = 10;
    let contadorPerguntas = 0;
    let currentEixo = null;
    let currentPergunta = null;
    let respostasCorretas = 0;
    let respostasIncorretas = 0;
    let quizAtivo = false; // Controlar se o quiz está ativo
    let carregandoPergunta = false; // Controlar se está carregando pergunta 

    // --- Verificação Inicial ---
    if (!selecaoEixoEl || !quizAreaEl) {
        console.error("ERRO CRÍTICO: Não foi possível encontrar os contêineres 'eixo-selecao' ou 'quiz-area'. Verifique os IDs no arquivo HTML.");
        return; 
    }

    console.log('Elementos carregados:', {
        welcomeSectionEl: !!welcomeSectionEl,
        selecaoEixoEl: !!selecaoEixoEl,
        quizAreaEl: !!quizAreaEl,
        resultadoAreaEl: !!resultadoAreaEl,
        botaoProximaEl: !!botaoProximaEl,
        botaoFinalizarEl: !!botaoFinalizarEl
    });

    // --- Inicialização ---
    inicializarEventListeners();
    
    // Garantir que elementos iniciem ocultos
    if (loadingEl) {
        loadingEl.style.display = 'none';
        loadingEl.classList.add('hidden');
    }
    
    if (explicacaoContainerEl) {
        explicacaoContainerEl.style.display = 'none';
        explicacaoContainerEl.classList.add('hidden');
    }

    function inicializarEventListeners() {
        // Remover listeners anteriores se existirem
        botoesEixo.forEach(botao => {
            // Clone o botão para remover todos os event listeners
            const novoBotao = botao.cloneNode(true);
            botao.parentNode.replaceChild(novoBotao, botao);
        });
        
        // Re-selecionar os botões após cloning
        const novosBootoesEixo = document.querySelectorAll('.eixo-btn');
        
        novosBootoesEixo.forEach(botao => {
            botao.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                console.log('Botão de eixo clicado:', this.dataset.eixo);
                iniciarQuiz(this.dataset.eixo);
            });
        });

        if (botaoProximaEl) {
            botaoProximaEl.addEventListener('click', buscarProximaPergunta);
        }

        if (botaoFinalizarEl) {
            botaoFinalizarEl.addEventListener('click', finalizarQuiz);
        }

        if (voltarInicioEl) {
            voltarInicioEl.addEventListener('click', voltarParaInicio);
        }
    }

    function iniciarQuiz(eixo) {
        // Verificar se o quiz já está ativo
        if (quizAtivo) {
            console.log('Quiz já está ativo, ignorando nova tentativa');
            return;
        }
        
        console.log(`Iniciando quiz para o eixo: ${eixo}`);
        console.log('Elementos encontrados:', {
            selecaoEixoEl: !!selecaoEixoEl,
            quizAreaEl: !!quizAreaEl,
            loadingEl: !!loadingEl,
            perguntaTextoEl: !!perguntaTextoEl,
            alternativasContainerEl: !!alternativasContainerEl
        });
        
        // Marcar quiz como ativo
        quizAtivo = true;
        carregandoPergunta = false;
        
        // Reiniciar contadores
        contadorPerguntas = 0;
        respostasCorretas = 0;
        respostasIncorretas = 0;
        currentEixo = eixo;
        currentPergunta = null;

        // Ocultar seções iniciais
        welcomeSectionEl.classList.add('hidden');
        welcomeSectionEl.style.display = 'none';
        
        selecaoEixoEl.classList.add('hidden');
        selecaoEixoEl.style.display = 'none';
        
        resultadoAreaEl.classList.add('hidden');
        resultadoAreaEl.style.display = 'none';
        
        // Mostrar área do quiz
        quizAreaEl.classList.remove('hidden');
        quizAreaEl.style.display = '';

        buscarProximaPergunta();
    }

    async function buscarProximaPergunta() {
        console.log('=== INICIANDO buscarProximaPergunta ===');
        console.log('Contador atual:', contadorPerguntas, 'Limite:', TAMANHO_DO_QUIZ);
        
        // Verificar se já está carregando uma pergunta
        if (carregandoPergunta) {
            console.log('Já está carregando uma pergunta, aguardando...');
            return;
        }
        
        // Verificar se o quiz está ativo
        if (!quizAtivo) {
            console.log('Quiz não está ativo, cancelando busca de pergunta');
            return;
        }
        
        if (contadorPerguntas >= TAMANHO_DO_QUIZ) {
            finalizarQuiz();
            return;
        }

        contadorPerguntas++;
        atualizarContadorUI();
        limparParaProximaPergunta();
        
        // Marcar como carregando
        carregandoPergunta = true;
        mostrarLoading(true);

        try {
            console.log('Fazendo requisição para eixo:', currentEixo);
            const response = await fetch('/obter-pergunta-quiz', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ eixo: currentEixo })
            });

            console.log('Status da resposta:', response.status);

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `Erro HTTP: ${response.status}`);
            }

            currentPergunta = await response.json();
            console.log('Pergunta recebida:', currentPergunta);
            exibirPergunta(currentPergunta);
            
            if (contadorPerguntas < TAMANHO_DO_QUIZ) {
                Promise.all([preGerarProximaPergunta(), preGerarProximaPergunta()])
                       .catch(error => console.warn('Falha na pré-geração:', error));
            }

        } catch (error) {
            console.error('Erro ao buscar pergunta:', error);
            mostrarErro(error.message);
        } finally {
            // Marcar como não carregando
            carregandoPergunta = false;
            mostrarLoading(false);
        }
    }

    function exibirPergunta(pergunta) {
        console.log('=== EXIBINDO PERGUNTA ===');
        console.log('Pergunta recebida:', pergunta);
        
        // Garantir que o loading seja removido imediatamente
        mostrarLoading(false);
        
        currentPergunta = pergunta;
        
        // Adicionar indicador de tipo de pergunta
        let indicadorTipo = '';
        if (pergunta.tipo_pergunta === 'revisao_incorreta') {
            indicadorTipo = '<div class="alert alert-warning mb-3"><i class="fas fa-redo me-2"></i><strong>Revisão:</strong> Você errou esta pergunta antes</div>';
        } else if (pergunta.tipo_pergunta === 'revisao_antiga') {
            indicadorTipo = '<div class="alert alert-info mb-3"><i class="fas fa-history me-2"></i><strong>Revisão:</strong> Pergunta respondida há mais de 7 dias</div>';
        }
        
        // Adicionar indicador de tópico se disponível
        let indicadorTopico = '';
        if (pergunta.topico) {
            const numeroTopico = pergunta.topico.replace('topico_', '');
            indicadorTopico = `<div class="alert alert-secondary mb-3"><i class="fas fa-book me-2"></i><strong>Tópico ${numeroTopico}</strong></div>`;
        }
        
        perguntaTextoEl.innerHTML = indicadorTipo + indicadorTopico + pergunta.pergunta;

        alternativasContainerEl.innerHTML = '';
        pergunta.alternativas.forEach(alt => {
            console.log('Criando alternativa:', alt);
            const botao = document.createElement('button');
            botao.className = 'alternativa btn'; // Adicionando a classe 'btn' para consistência
            botao.dataset.id = alt.id;
            botao.innerHTML = `<strong>${alt.id})</strong> ${alt.texto}`;
            botao.addEventListener('click', () => handleAnswer(alt.id));
            alternativasContainerEl.appendChild(botao);
        });
        
        console.log('Pergunta exibida com sucesso!');
    }

    function handleAnswer(idAlternativaClicada) {
        const respostaCorretaId = currentPergunta.resposta_correta;
        const acertou = idAlternativaClicada === respostaCorretaId;

        // Contar respostas
        if (acertou) {
            respostasCorretas++;
        } else {
            respostasIncorretas++;
        }

        alternativasContainerEl.querySelectorAll('.alternativa').forEach(botao => {
            botao.disabled = true;
            if (botao.dataset.id === respostaCorretaId) {
                botao.classList.add('correta');
            } else if (botao.dataset.id === idAlternativaClicada) {
                botao.classList.add('incorreta');
            }
        });
        
        exibirExplicacoes(currentPergunta.explicacoes, respostaCorretaId, idAlternativaClicada);
        
        // Mostrar botões apropriados
        if (contadorPerguntas < TAMANHO_DO_QUIZ) {
            botaoProximaEl.classList.remove('hidden');
        }
        botaoFinalizarEl.classList.remove('hidden');
        
        salvarResposta(currentPergunta.id, acertou);
    }
    
    async function salvarResposta(perguntaId, acertou) {
        console.log('=== SALVANDO RESPOSTA ===');
        console.log('Pergunta ID:', perguntaId);
        console.log('Acertou:', acertou);
        
        try {
            const response = await fetch('/salvar-resposta', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ pergunta_id: perguntaId, acertou: acertou ? 1 : 0 })
            });
            
            const result = await response.json();
            console.log('Resposta do servidor:', result);
            
            if (!response.ok) {
                console.error('Erro ao salvar resposta:', result);
            } else {
                console.log('Resposta salva com sucesso!');
            }
        } catch (error) {
            console.error('Erro na requisição de salvar resposta:', error);
        }
    }

    function exibirExplicacoes(explicacoes, respostaCorreta, respostaSelecionada) {
        let htmlExplicacao = '<div class="alert alert-info">';
        if (explicacoes[respostaCorreta]) {
            htmlExplicacao += `<div class="explicacao-item correta"><h4>✅ Resposta Correta (${respostaCorreta}):</h4><p>${explicacoes[respostaCorreta]}</p></div>`;
        }
        if (respostaSelecionada !== respostaCorreta && explicacoes[respostaSelecionada]) {
            htmlExplicacao += `<div class="explicacao-item incorreta mt-3 pt-3 border-top"><h4>❌ Sua Resposta (${respostaSelecionada}):</h4><p>${explicacoes[respostaSelecionada]}</p></div>`;
        }
        htmlExplicacao += '</div>';
        
        explicacaoContainerEl.innerHTML = htmlExplicacao;
        // Mostrar o container explicitamente
        explicacaoContainerEl.style.display = 'block';
        explicacaoContainerEl.classList.remove('hidden');
    }

    function preGerarProximaPergunta() {
        return fetch('/pre-gerar-proxima', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ eixo: currentEixo })
        });
    }
    
    function limparParaProximaPergunta() {
        botaoProximaEl.classList.add('hidden');
        botaoFinalizarEl.classList.add('hidden');
        
        // Ocultar explicações completamente
        explicacaoContainerEl.style.display = 'none';
        explicacaoContainerEl.classList.add('hidden');
        explicacaoContainerEl.innerHTML = '';
        
        alternativasContainerEl.innerHTML = '';
        erroContainerEl.innerHTML = '';
    }

    function atualizarContadorUI() {
        contadorUiEl.textContent = `Pergunta ${contadorPerguntas}/${TAMANHO_DO_QUIZ}`;
    }

    function finalizarQuiz() {
        // Marcar quiz como inativo
        quizAtivo = false;
        carregandoPergunta = false;
        
        const totalPerguntas = respostasCorretas + respostasIncorretas;
        const percentualAcerto = totalPerguntas > 0 ? Math.round((respostasCorretas / totalPerguntas) * 100) : 0;

        // Ocultar área do quiz
        quizAreaEl.classList.add('hidden');
        quizAreaEl.style.display = 'none';

        // Atualizar elementos do resultado
        document.getElementById('pontos-display').textContent = `${respostasCorretas}/${totalPerguntas}`;
        document.getElementById('percentual-display').textContent = `${percentualAcerto}% de acerto`;
        document.getElementById('corretas-count').textContent = respostasCorretas;
        document.getElementById('incorretas-count').textContent = respostasIncorretas;
        document.getElementById('total-count').textContent = totalPerguntas;

        // Mostrar área de resultado
        resultadoAreaEl.classList.remove('hidden');
        resultadoAreaEl.style.display = '';

        console.log('Quiz finalizado:', {
            corretas: respostasCorretas,
            incorretas: respostasIncorretas,
            total: totalPerguntas,
            percentual: percentualAcerto
        });
    }

    function mostrarLoading(mostrar) {
        console.log(`=== MOSTRANDO LOADING: ${mostrar} ===`);
        if (loadingEl) {
            // Usar style.display diretamente para ter controle total
            if (mostrar) {
                loadingEl.style.display = 'block';
                loadingEl.classList.remove('hidden');
            } else {
                loadingEl.style.display = 'none';
                loadingEl.classList.add('hidden');
            }
            console.log('Loading element classes:', loadingEl.className);
            console.log('Loading element style.display:', loadingEl.style.display);
        } else {
            console.error('Loading element não encontrado!');
        }
    }

    function mostrarErro(mensagem) {
        erroContainerEl.innerHTML = `<div class="alert alert-danger">⚠️ ${mensagem}</div>`;
    }

    function voltarParaInicio() {
        // Restaurar estado inicial
        contadorPerguntas = 0;
        respostasCorretas = 0;
        respostasIncorretas = 0;
        currentEixo = null;
        currentPergunta = null;
        quizAtivo = false; // Resetar controle do quiz
        carregandoPergunta = false; // Resetar controle de carregamento

        // Mostrar seções iniciais
        welcomeSectionEl.classList.remove('hidden');
        welcomeSectionEl.style.display = '';
        
        selecaoEixoEl.classList.remove('hidden');
        selecaoEixoEl.style.display = '';

        // Ocultar outras seções
        quizAreaEl.classList.add('hidden');
        quizAreaEl.style.display = 'none';
        
        resultadoAreaEl.classList.add('hidden');
        resultadoAreaEl.style.display = 'none';

        // Limpar conteúdo que pode estar alterado
        if (perguntaTextoEl) {
            perguntaTextoEl.innerHTML = '';
        }
        if (alternativasContainerEl) {
            alternativasContainerEl.innerHTML = '';
        }
        if (explicacaoContainerEl) {
            explicacaoContainerEl.innerHTML = '';
            explicacaoContainerEl.style.display = 'none';
            explicacaoContainerEl.classList.add('hidden');
        }

        console.log('Voltando para o início - layout restaurado');
    }
});