// Variáveis globais para os gráficos
let graficoEvolucaoGeral = null;
let graficoDesempenhoEixos = null;
let graficoEvolucaoEixos = null;

// Configurações de cores e temas
const cores = {
    primaria: '#667eea',
    secundaria: '#764ba2',
    sucesso: '#10b981',
    erro: '#ef4444',
    aviso: '#f59e0b',
    info: '#3b82f6',
    gradiente: ['#667eea', '#764ba2', '#10b981', '#f59e0b', '#ef4444']
};

// Inicializar quando a página carregar
document.addEventListener('DOMContentLoaded', function() {
    carregarResultados();
});

// Função principal para carregar todos os resultados
async function carregarResultados() {
    try {
        showLoading();
        
        // Fazer requisição para API de resultados
        const response = await fetch('/api/resultados');
        
        // Verificar se o usuário foi redirecionado para login
        if (response.redirected && response.url.includes('/login')) {
            window.location.href = '/login';
            return;
        }
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const dados = await response.json();
        
        console.log('Dados recebidos da API:', dados);
        
        if (dados.total_perguntas === 0) {
            showNoData();
            return;
        }
        
        // Atualizar cards de resumo
        atualizarCardsResumo(dados);
        
        // Criar gráficos se houver dados
        if (dados.evolucao_geral && dados.evolucao_geral.length > 0) {
            criarGraficoEvolucaoGeral(dados.evolucao_geral);
        }
        
        if (dados.por_eixo && dados.por_eixo.length > 0) {
            criarGraficoDesempenhoEixos(dados.por_eixo);
            preencherTabelaEstatisticas(dados.por_eixo);
        }
        
        if (dados.evolucao_eixos && dados.evolucao_eixos.length > 0) {
            criarGraficoEvolucaoEixos(dados.evolucao_eixos);
        }
        
        showContent();
        
    } catch (error) {
        console.error('Erro ao carregar resultados:', error);
        showError('Erro ao carregar os resultados. Tente novamente mais tarde.');
    }
}

// Atualizar cards de resumo
function atualizarCardsResumo(dados) {
    const totalPerguntas = dados.total_perguntas || 0;
    const totalAcertos = dados.total_acertos || 0;
    const totalErros = dados.total_erros || 0;
    const percentualAcerto = totalPerguntas > 0 ? Math.round((totalAcertos / totalPerguntas) * 100) : 0;
    
    // Animar os números
    animarNumero('total-perguntas', totalPerguntas);
    animarNumero('total-acertos', totalAcertos);
    animarNumero('total-erros', totalErros);
    animarNumero('percentual-acerto', percentualAcerto, '%');
}

// Função para animar números
function animarNumero(elementId, valorFinal, sufixo = '') {
    const elemento = document.getElementById(elementId);
    if (!elemento) return;
    
    const duracao = 1500; // 1.5 segundos
    const incremento = valorFinal / (duracao / 16); // 60fps
    let valorAtual = 0;
    
    const timer = setInterval(() => {
        valorAtual += incremento;
        if (valorAtual >= valorFinal) {
            valorAtual = valorFinal;
            clearInterval(timer);
        }
        elemento.textContent = Math.round(valorAtual) + sufixo;
    }, 16);
}

// Criar gráfico de evolução geral
function criarGraficoEvolucaoGeral(dadosEvolucao) {
    const ctx = document.getElementById('grafico-evolucao-geral');
    if (!ctx) return;
    
    // Preparar dados
    const labels = dadosEvolucao.map(item => formatarData(item.data));
    const acertos = dadosEvolucao.map(item => item.acertos_acumulados);
    const total = dadosEvolucao.map(item => item.total_acumulado);
    const percentual = dadosEvolucao.map(item => 
        item.total_acumulado > 0 ? Math.round((item.acertos_acumulados / item.total_acumulado) * 100) : 0
    );
    
    // Destruir gráfico anterior se existir
    if (graficoEvolucaoGeral) {
        graficoEvolucaoGeral.destroy();
    }
    
    graficoEvolucaoGeral = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Taxa de Acerto (%)',
                    data: percentual,
                    borderColor: cores.primaria,
                    backgroundColor: cores.primaria + '20',
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: cores.primaria,
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 5,
                    pointHoverRadius: 8
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                tooltip: {
                    callbacks: {
                        afterLabel: function(context) {
                            const index = context.dataIndex;
                            return `Acertos: ${acertos[index]}/${total[index]}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                },
                x: {
                    ticks: {
                        maxTicksLimit: 10
                    }
                }
            },
            animation: {
                duration: 2000,
                easing: 'easeInOutQuart'
            }
        }
    });
}

// Criar gráfico de desempenho por eixo
function criarGraficoDesempenhoEixos(dadosPorEixo) {
    const ctx = document.getElementById('grafico-desempenho-eixos');
    if (!ctx) return;
    
    // Preparar dados
    const labels = dadosPorEixo.map(item => `Eixo ${item.eixo}`);
    const percentuais = dadosPorEixo.map(item => 
        item.total > 0 ? Math.round((item.acertos / item.total) * 100) : 0
    );
    
    // Destruir gráfico anterior se existir
    if (graficoDesempenhoEixos) {
        graficoDesempenhoEixos.destroy();
    }
    
    graficoDesempenhoEixos = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: percentuais,
                backgroundColor: cores.gradiente,
                borderColor: '#fff',
                borderWidth: 3,
                hoverBorderWidth: 5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const eixo = dadosPorEixo[context.dataIndex];
                            return `${context.label}: ${context.parsed}% (${eixo.acertos}/${eixo.total})`;
                        }
                    }
                }
            },
            animation: {
                animateRotate: true,
                duration: 2000
            }
        }
    });
}

// Criar gráfico de evolução por eixo
function criarGraficoEvolucaoEixos(dadosEvolucaoEixos) {
    const ctx = document.getElementById('grafico-evolucao-eixos');
    if (!ctx) return;
    
    // Preparar dados - organizar por eixo
    const eixos = {};
    dadosEvolucaoEixos.forEach(item => {
        if (!eixos[item.eixo]) {
            eixos[item.eixo] = [];
        }
        eixos[item.eixo].push(item);
    });
    
    // Obter todas as datas únicas e ordenar
    const todasDatas = [...new Set(dadosEvolucaoEixos.map(item => item.data))].sort();
    const labels = todasDatas.map(data => formatarData(data));
    
    // Criar datasets para cada eixo
    const datasets = Object.keys(eixos).map((eixo, index) => {
        const dadosEixo = eixos[eixo];
        
        // Criar array de percentuais para todas as datas
        const percentuais = todasDatas.map(data => {
            const dadoDia = dadosEixo.find(item => item.data === data);
            if (dadoDia && dadoDia.total_acumulado > 0) {
                return Math.round((dadoDia.acertos_acumulados / dadoDia.total_acumulado) * 100);
            }
            return null; // null para datas sem dados
        });
        
        return {
            label: `Eixo ${eixo}`,
            data: percentuais,
            borderColor: cores.gradiente[index % cores.gradiente.length],
            backgroundColor: cores.gradiente[index % cores.gradiente.length] + '20',
            borderWidth: 2,
            fill: false,
            tension: 0.4,
            pointBackgroundColor: cores.gradiente[index % cores.gradiente.length],
            pointBorderColor: '#fff',
            pointBorderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 6,
            spanGaps: true // Conectar pontos mesmo com dados ausentes
        };
    });
    
    // Destruir gráfico anterior se existir
    if (graficoEvolucaoEixos) {
        graficoEvolucaoEixos.destroy();
    }
    
    graficoEvolucaoEixos = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                },
                x: {
                    ticks: {
                        maxTicksLimit: 15
                    }
                }
            },
            animation: {
                duration: 2000,
                easing: 'easeInOutQuart'
            }
        }
    });
}

// Preencher tabela de estatísticas
function preencherTabelaEstatisticas(dadosPorEixo) {
    const tbody = document.getElementById('tabela-estatisticas');
    if (!tbody) return;
    
    tbody.innerHTML = '';
    
    dadosPorEixo.forEach(eixo => {
        const percentual = eixo.total > 0 ? Math.round((eixo.acertos / eixo.total) * 100) : 0;
        let statusClass = 'badge-success-custom';
        let statusText = 'Excelente';
        
        if (percentual < 50) {
            statusClass = 'badge-danger-custom';
            statusText = 'Precisa Melhorar';
        } else if (percentual < 70) {
            statusClass = 'badge-warning-custom';
            statusText = 'Bom';
        } else if (percentual < 85) {
            statusClass = 'badge-success-custom';
            statusText = 'Muito Bom';
        }
        
        const linha = `
            <tr>
                <td><strong>Eixo ${eixo.eixo}</strong></td>
                <td>${eixo.total}</td>
                <td class="text-success">${eixo.acertos}</td>
                <td class="text-danger">${eixo.erros}</td>
                <td>
                    <div class="progress-custom">
                        <div class="progress-bar-custom" style="width: ${percentual}%"></div>
                        <div class="progress-text">${percentual}%</div>
                    </div>
                </td>
                <td>
                    <span class="badge badge-custom ${statusClass}">${statusText}</span>
                </td>
            </tr>
        `;
        tbody.innerHTML += linha;
    });
}

// Função para formatar data
function formatarData(dataString) {
    const data = new Date(dataString);
    return data.toLocaleDateString('pt-BR', { 
        day: '2-digit', 
        month: '2-digit'
    });
}

// Funções de controle de exibição
function showLoading() {
    const loading = document.getElementById('loading-section');
    const content = document.getElementById('content-section');
    const noData = document.getElementById('no-data-section');
    
    if (loading) loading.style.display = 'block';
    if (content) content.style.display = 'none';
    if (noData) noData.style.display = 'none';
}

function showContent() {
    const loading = document.getElementById('loading-section');
    const content = document.getElementById('content-section');
    const noData = document.getElementById('no-data-section');
    
    if (loading) loading.style.display = 'none';
    if (content) content.style.display = 'block';
    if (noData) noData.style.display = 'none';
}

function showNoData() {
    const loading = document.getElementById('loading-section');
    const content = document.getElementById('content-section');
    const noData = document.getElementById('no-data-section');
    
    if (loading) loading.style.display = 'none';
    if (content) content.style.display = 'none';
    if (noData) noData.style.display = 'block';
}

function showError(mensagem) {
    const loading = document.getElementById('loading-section');
    const content = document.getElementById('content-section');
    const noData = document.getElementById('no-data-section');
    
    if (loading) loading.style.display = 'none';
    if (content) content.style.display = 'none';
    if (noData) noData.style.display = 'none';
    
    // Mostrar alert por enquanto
    alert(mensagem);
}

// Função para redimensionar gráficos quando a janela muda de tamanho
window.addEventListener('resize', function() {
    if (graficoEvolucaoGeral) graficoEvolucaoGeral.resize();
    if (graficoDesempenhoEixos) graficoDesempenhoEixos.resize();
    if (graficoEvolucaoEixos) graficoEvolucaoEixos.resize();
});
