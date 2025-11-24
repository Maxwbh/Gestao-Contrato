/*
==============================================================================
Sistema de Gestao de Contratos - Oracle APEX 24
Pagina 9000: Setup Wizard - Configuracao Inicial do Sistema
==============================================================================
Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
LinkedIn: https://www.linkedin.com/in/maxwbh/
GitHub: https://github.com/Maxwbh/
Empresa: M&S do Brasil LTDA
Site: msbrasil.inf.br
==============================================================================
*/

-- ============================================================================
-- PAGINA 9000: SETUP WIZARD
-- ============================================================================
-- Tipo: Wizard com steps
-- Template: Standard
-- Auth: Public (primeiro setup) / Admin (posteriores)

/*
================================================================================
REGIAO: Banner de Boas-Vindas
================================================================================
*/

-- Type: Static Content
/*
<div class="setup-banner">
    <div class="setup-banner-icon">
        <span class="fa fa-cogs fa-4x"></span>
    </div>
    <h1>Configuração Inicial do Sistema</h1>
    <p class="setup-subtitle">Sistema de Gestão de Contratos Imobiliários</p>
    <p>Configure seu ambiente, crie usuários e opcionalmente carregue dados de teste.</p>
</div>

<style>
.setup-banner {
    text-align: center;
    padding: 30px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 10px;
    margin-bottom: 20px;
}
.setup-banner-icon {
    margin-bottom: 15px;
}
.setup-subtitle {
    font-size: 1.2em;
    opacity: 0.9;
}
</style>
*/

/*
================================================================================
REGIAO: Status do Sistema (Cards)
================================================================================
*/

-- Type: Cards
-- Source SQL:
/*
SELECT
    'Banco de Dados' AS titulo,
    CASE WHEN COUNT(*) > 0 THEN 'Conectado' ELSE 'Erro' END AS valor,
    'fa-database' AS icone,
    CASE WHEN COUNT(*) > 0 THEN 'u-success' ELSE 'u-danger' END AS css,
    1 AS ordem
FROM dual
WHERE EXISTS (SELECT 1 FROM user_tables WHERE table_name = 'GC_CONTABILIDADE')
UNION ALL
SELECT
    'Tabelas' AS titulo,
    (SELECT COUNT(*) FROM user_tables WHERE table_name LIKE 'GC_%') || ' tabelas' AS valor,
    'fa-table' AS icone,
    CASE WHEN (SELECT COUNT(*) FROM user_tables WHERE table_name LIKE 'GC_%') >= 20 THEN 'u-success' ELSE 'u-warning' END AS css,
    2 AS ordem
FROM dual
UNION ALL
SELECT
    'Contabilidades' AS titulo,
    NVL((SELECT COUNT(*) FROM gc_contabilidade), 0) || ' registros' AS valor,
    'fa-building-o' AS icone,
    CASE WHEN NVL((SELECT COUNT(*) FROM gc_contabilidade), 0) > 0 THEN 'u-success' ELSE 'u-normal' END AS css,
    3 AS ordem
FROM dual
UNION ALL
SELECT
    'Imobiliárias' AS titulo,
    NVL((SELECT COUNT(*) FROM gc_imobiliaria), 0) || ' registros' AS valor,
    'fa-home' AS icone,
    CASE WHEN NVL((SELECT COUNT(*) FROM gc_imobiliaria), 0) > 0 THEN 'u-success' ELSE 'u-normal' END AS css,
    4 AS ordem
FROM dual
UNION ALL
SELECT
    'Contas Bancárias' AS titulo,
    NVL((SELECT COUNT(*) FROM gc_conta_bancaria), 0) || ' registros' AS valor,
    'fa-bank' AS icone,
    CASE WHEN NVL((SELECT COUNT(*) FROM gc_conta_bancaria), 0) > 0 THEN 'u-success' ELSE 'u-warning' END AS css,
    5 AS ordem
FROM dual
UNION ALL
SELECT
    'Imóveis' AS titulo,
    NVL((SELECT COUNT(*) FROM gc_imovel), 0) || ' registros' AS valor,
    'fa-map-marker' AS icone,
    CASE WHEN NVL((SELECT COUNT(*) FROM gc_imovel), 0) > 0 THEN 'u-success' ELSE 'u-normal' END AS css,
    6 AS ordem
FROM dual
UNION ALL
SELECT
    'Compradores' AS titulo,
    NVL((SELECT COUNT(*) FROM gc_comprador), 0) || ' registros' AS valor,
    'fa-users' AS icone,
    CASE WHEN NVL((SELECT COUNT(*) FROM gc_comprador), 0) > 0 THEN 'u-success' ELSE 'u-normal' END AS css,
    7 AS ordem
FROM dual
UNION ALL
SELECT
    'Contratos' AS titulo,
    NVL((SELECT COUNT(*) FROM gc_contrato), 0) || ' registros' AS valor,
    'fa-file-text' AS icone,
    CASE WHEN NVL((SELECT COUNT(*) FROM gc_contrato), 0) > 0 THEN 'u-success' ELSE 'u-normal' END AS css,
    8 AS ordem
FROM dual
ORDER BY ordem
*/

/*
================================================================================
REGIAO: Acoes de Setup
================================================================================
*/

-- Type: Static Content with Buttons
/*
<div class="setup-actions-grid">

    <!-- Card: Verificar Estrutura -->
    <div class="setup-action-card">
        <div class="setup-action-icon u-color-1">
            <span class="fa fa-check-circle fa-3x"></span>
        </div>
        <h3>Verificar Estrutura</h3>
        <p>Verifica se todas as tabelas, triggers e packages estão instalados corretamente.</p>
        <button type="button" class="t-Button t-Button--primary" onclick="executarAcao('verificar')">
            <span class="fa fa-search"></span> Verificar
        </button>
    </div>

    <!-- Card: Instalar Estrutura -->
    <div class="setup-action-card">
        <div class="setup-action-icon u-color-2">
            <span class="fa fa-database fa-3x"></span>
        </div>
        <h3>Instalar Estrutura</h3>
        <p>Cria todas as tabelas, índices, triggers e packages necessários.</p>
        <button type="button" class="t-Button t-Button--warning" onclick="executarAcao('instalar')">
            <span class="fa fa-cog"></span> Instalar
        </button>
    </div>

    <!-- Card: Criar Admin -->
    <div class="setup-action-card">
        <div class="setup-action-icon u-color-3">
            <span class="fa fa-user-plus fa-3x"></span>
        </div>
        <h3>Criar Administrador</h3>
        <p>Cria o usuário administrador padrão do sistema.</p>
        <button type="button" class="t-Button t-Button--success" onclick="executarAcao('admin')">
            <span class="fa fa-user-secret"></span> Criar Admin
        </button>
    </div>

    <!-- Card: Dados de Teste -->
    <div class="setup-action-card">
        <div class="setup-action-icon u-color-4">
            <span class="fa fa-magic fa-3x"></span>
        </div>
        <h3>Gerar Dados de Teste</h3>
        <p>Gera dados fictícios para demonstração e testes do sistema.</p>
        <button type="button" class="t-Button t-Button--hot" onclick="abrirModalDadosTeste()">
            <span class="fa fa-bolt"></span> Gerar Dados
        </button>
    </div>

    <!-- Card: Setup Completo -->
    <div class="setup-action-card setup-action-card--featured">
        <div class="setup-action-icon u-success">
            <span class="fa fa-rocket fa-3x"></span>
        </div>
        <h3>Setup Completo</h3>
        <p>Executa todas as etapas: estrutura, admin e dados de teste.</p>
        <button type="button" class="t-Button t-Button--primary t-Button--stretch" onclick="executarSetupCompleto()">
            <span class="fa fa-play-circle"></span> Executar Setup Completo
        </button>
    </div>

    <!-- Card: Limpar Dados -->
    <div class="setup-action-card">
        <div class="setup-action-icon u-danger">
            <span class="fa fa-trash fa-3x"></span>
        </div>
        <h3>Limpar Dados</h3>
        <p>Remove todos os dados de teste do sistema. Use com cautela!</p>
        <button type="button" class="t-Button t-Button--danger" onclick="confirmarLimpeza()">
            <span class="fa fa-eraser"></span> Limpar Dados
        </button>
    </div>

</div>

<style>
.setup-actions-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 20px;
    margin-top: 20px;
}
.setup-action-card {
    background: var(--ut-component-background-color);
    border: 1px solid var(--ut-component-border-color);
    border-radius: 8px;
    padding: 25px;
    text-align: center;
    transition: transform 0.2s, box-shadow 0.2s;
}
.setup-action-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
.setup-action-card--featured {
    grid-column: span 2;
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
}
.setup-action-icon {
    margin-bottom: 15px;
}
.setup-action-card h3 {
    margin: 10px 0;
    font-size: 1.2em;
}
.setup-action-card p {
    color: var(--ut-body-text-color);
    font-size: 0.9em;
    margin-bottom: 15px;
}
</style>
*/

/*
================================================================================
REGIAO: Modal - Gerar Dados de Teste
================================================================================
*/

-- Type: Inline Dialog
-- Static ID: modal-dados-teste

/*
<div id="modal-dados-teste" class="t-Dialog-region" style="display:none;">
    <div class="t-Dialog-header">
        <h2>Gerar Dados de Teste</h2>
    </div>
    <div class="t-Dialog-body">
        <!-- Opcoes -->
        <div class="setup-option-group">
            <label class="setup-checkbox">
                <input type="checkbox" id="chk_limpar_antes" />
                <span>Limpar dados existentes antes de gerar</span>
            </label>
        </div>

        <!-- Dados a serem gerados -->
        <div class="setup-data-preview">
            <h4>Dados que serão gerados:</h4>
            <ul class="setup-data-list">
                <li><span class="fa fa-building-o"></span> 1 Contabilidade (Sete Lagoas/MG)</li>
                <li><span class="fa fa-home"></span> 2 Imobiliárias</li>
                <li><span class="fa fa-bank"></span> 6 Contas Bancárias (BB, Sicoob, Bradesco)</li>
                <li><span class="fa fa-map-marker"></span> 65 Imóveis (2 Loteamentos + Terrenos)</li>
                <li><span class="fa fa-users"></span> 60 Compradores (80% PF, 20% PJ)</li>
                <li><span class="fa fa-file-text"></span> ~50 Contratos</li>
                <li><span class="fa fa-list-ol"></span> ~2.000 Parcelas</li>
                <li><span class="fa fa-line-chart"></span> 252 Índices de Reajuste (36 meses)</li>
            </ul>
        </div>

        <!-- Progress -->
        <div id="progress-container" style="display:none;">
            <h4>Progresso:</h4>
            <div class="setup-progress">
                <div class="setup-progress-step" id="step-contabilidade">
                    <span class="fa fa-circle-o"></span> Contabilidade
                </div>
                <div class="setup-progress-step" id="step-imobiliarias">
                    <span class="fa fa-circle-o"></span> Imobiliárias
                </div>
                <div class="setup-progress-step" id="step-contas">
                    <span class="fa fa-circle-o"></span> Contas Bancárias
                </div>
                <div class="setup-progress-step" id="step-imoveis">
                    <span class="fa fa-circle-o"></span> Imóveis
                </div>
                <div class="setup-progress-step" id="step-compradores">
                    <span class="fa fa-circle-o"></span> Compradores
                </div>
                <div class="setup-progress-step" id="step-contratos">
                    <span class="fa fa-circle-o"></span> Contratos
                </div>
                <div class="setup-progress-step" id="step-parcelas">
                    <span class="fa fa-circle-o"></span> Parcelas
                </div>
                <div class="setup-progress-step" id="step-indices">
                    <span class="fa fa-circle-o"></span> Índices
                </div>
            </div>
            <div class="setup-progress-bar">
                <div class="setup-progress-bar-fill" id="progress-bar-fill"></div>
            </div>
        </div>

        <!-- Resultado -->
        <div id="resultado-container" style="display:none;">
            <div class="t-Alert t-Alert--success">
                <div class="t-Alert-icon"><span class="fa fa-check-circle"></span></div>
                <div class="t-Alert-body" id="resultado-mensagem"></div>
            </div>
        </div>
    </div>
    <div class="t-Dialog-footer">
        <button type="button" class="t-Button t-Button--hot" id="btn-gerar" onclick="gerarDadosTeste()">
            <span class="fa fa-magic"></span> Gerar Dados
        </button>
        <button type="button" class="t-Button" onclick="fecharModal()">
            <span class="fa fa-times"></span> Fechar
        </button>
    </div>
</div>

<style>
.setup-option-group {
    margin-bottom: 20px;
}
.setup-checkbox {
    display: flex;
    align-items: center;
    gap: 10px;
    cursor: pointer;
}
.setup-data-preview {
    background: var(--ut-palette-generic1);
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 20px;
}
.setup-data-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
}
.setup-data-list li {
    padding: 5px 0;
}
.setup-data-list li .fa {
    width: 20px;
    color: var(--ut-palette-primary);
}
.setup-progress {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-bottom: 15px;
}
.setup-progress-step {
    padding: 8px 12px;
    background: var(--ut-palette-generic1);
    border-radius: 4px;
    font-size: 0.85em;
}
.setup-progress-step.active {
    background: var(--ut-palette-warning);
    color: white;
}
.setup-progress-step.completed {
    background: var(--ut-palette-success);
    color: white;
}
.setup-progress-step.completed .fa {
    content: "\f00c";
}
.setup-progress-bar {
    height: 8px;
    background: var(--ut-palette-generic1);
    border-radius: 4px;
    overflow: hidden;
}
.setup-progress-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--ut-palette-primary), var(--ut-palette-success));
    width: 0%;
    transition: width 0.3s ease;
}
</style>
*/

/*
================================================================================
REGIAO: Modal - Confirmacao de Limpeza
================================================================================
*/

-- Type: Inline Dialog
-- Static ID: modal-confirmar-limpeza

/*
<div id="modal-confirmar-limpeza" class="t-Dialog-region" style="display:none;">
    <div class="t-Dialog-header">
        <h2><span class="fa fa-exclamation-triangle u-danger"></span> Confirmar Limpeza</h2>
    </div>
    <div class="t-Dialog-body">
        <div class="t-Alert t-Alert--danger t-Alert--horizontal">
            <div class="t-Alert-icon"><span class="fa fa-warning"></span></div>
            <div class="t-Alert-body">
                <strong>ATENÇÃO!</strong> Esta ação irá remover TODOS os dados do sistema:
            </div>
        </div>

        <div id="dados-a-remover" class="setup-data-preview">
            <ul class="setup-data-list">
                <li><span class="fa fa-times u-danger"></span> <span id="count-parcelas">0</span> Parcelas</li>
                <li><span class="fa fa-times u-danger"></span> <span id="count-contratos">0</span> Contratos</li>
                <li><span class="fa fa-times u-danger"></span> <span id="count-boletos">0</span> Boletos</li>
                <li><span class="fa fa-times u-danger"></span> <span id="count-imoveis">0</span> Imóveis</li>
                <li><span class="fa fa-times u-danger"></span> <span id="count-compradores">0</span> Compradores</li>
                <li><span class="fa fa-times u-danger"></span> <span id="count-imobiliarias">0</span> Imobiliárias</li>
                <li><span class="fa fa-times u-danger"></span> <span id="count-contabilidades">0</span> Contabilidades</li>
                <li><span class="fa fa-times u-danger"></span> <span id="count-indices">0</span> Índices</li>
            </ul>
        </div>

        <div class="setup-confirm-input">
            <label>Digite <strong>CONFIRMAR</strong> para prosseguir:</label>
            <input type="text" id="input-confirmar" class="text_field apex-item-text" placeholder="CONFIRMAR" />
        </div>
    </div>
    <div class="t-Dialog-footer">
        <button type="button" class="t-Button t-Button--danger" id="btn-confirmar-limpeza" onclick="executarLimpeza()" disabled>
            <span class="fa fa-trash"></span> Confirmar Limpeza
        </button>
        <button type="button" class="t-Button" onclick="fecharModalLimpeza()">
            <span class="fa fa-times"></span> Cancelar
        </button>
    </div>
</div>

<style>
.setup-confirm-input {
    margin-top: 20px;
}
.setup-confirm-input input {
    margin-top: 10px;
    width: 100%;
}
</style>
*/

/*
================================================================================
REGIAO: Log de Execucao
================================================================================
*/

-- Type: Static Content
-- Collapsible: Yes
-- Default State: Collapsed

/*
<div class="setup-log-container">
    <h4><span class="fa fa-terminal"></span> Log de Execução</h4>
    <pre id="setup-log" class="setup-log"></pre>
</div>

<style>
.setup-log-container {
    margin-top: 20px;
}
.setup-log {
    background: #1e1e1e;
    color: #d4d4d4;
    padding: 15px;
    border-radius: 8px;
    max-height: 300px;
    overflow-y: auto;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 0.85em;
    white-space: pre-wrap;
}
.setup-log .log-success { color: #4ec9b0; }
.setup-log .log-error { color: #f14c4c; }
.setup-log .log-warning { color: #cca700; }
.setup-log .log-info { color: #3794ff; }
</style>
*/

/*
================================================================================
REGIAO: Proximos Passos
================================================================================
*/

-- Type: Static Content
-- Condition: Dados existem no sistema

/*
<div class="setup-next-steps">
    <h3><span class="fa fa-arrow-circle-right"></span> Próximos Passos</h3>
    <div class="setup-next-steps-grid">
        <a href="f?p=&APP_ID.:1:&SESSION." class="setup-next-step-card">
            <span class="fa fa-tachometer fa-2x"></span>
            <span>Ir para Dashboard</span>
        </a>
        <a href="f?p=&APP_ID.:20:&SESSION." class="setup-next-step-card">
            <span class="fa fa-building fa-2x"></span>
            <span>Cadastrar Imobiliária</span>
        </a>
        <a href="f?p=&APP_ID.:100:&SESSION." class="setup-next-step-card">
            <span class="fa fa-file-text fa-2x"></span>
            <span>Ver Contratos</span>
        </a>
        <a href="f?p=&APP_ID.:900:&SESSION." class="setup-next-step-card">
            <span class="fa fa-cogs fa-2x"></span>
            <span>Configurações</span>
        </a>
    </div>
</div>

<style>
.setup-next-steps {
    margin-top: 30px;
    padding: 20px;
    background: var(--ut-palette-generic1);
    border-radius: 8px;
}
.setup-next-steps h3 {
    margin-bottom: 20px;
}
.setup-next-steps-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 15px;
}
.setup-next-step-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    padding: 20px;
    background: var(--ut-component-background-color);
    border: 1px solid var(--ut-component-border-color);
    border-radius: 8px;
    text-decoration: none;
    color: var(--ut-body-text-color);
    transition: all 0.2s;
}
.setup-next-step-card:hover {
    background: var(--ut-palette-primary);
    color: white;
    transform: translateY(-2px);
}
</style>
*/

/*
================================================================================
PAGE ITEMS (Hidden)
================================================================================
*/

-- P9000_ACAO
-- Type: Hidden
-- Used to track current action

-- P9000_RESULTADO
-- Type: Hidden
-- Used to store action result

/*
================================================================================
JAVASCRIPT - Funcoes do Setup
================================================================================
*/

/*
<script>
// Funcao para adicionar log
function addLog(message, type) {
    var log = document.getElementById('setup-log');
    var timestamp = new Date().toLocaleTimeString();
    var className = 'log-' + (type || 'info');
    log.innerHTML += '<span class="' + className + '">[' + timestamp + '] ' + message + '</span>\n';
    log.scrollTop = log.scrollHeight;
}

// Executar acao generica
function executarAcao(acao) {
    addLog('Iniciando ação: ' + acao, 'info');

    apex.server.process('EXECUTAR_ACAO_SETUP', {
        x01: acao
    }, {
        dataType: 'json',
        success: function(data) {
            if (data.status === 'success') {
                addLog(data.message, 'success');
                apex.message.showPageSuccess(data.message);
                // Atualizar cards de status
                apex.region('status-cards').refresh();
            } else {
                addLog('ERRO: ' + data.message, 'error');
                apex.message.showErrors([{
                    type: 'error',
                    location: 'page',
                    message: data.message
                }]);
            }
        },
        error: function(xhr, status, error) {
            addLog('ERRO: ' + error, 'error');
        }
    });
}

// Abrir modal de dados de teste
function abrirModalDadosTeste() {
    document.getElementById('modal-dados-teste').style.display = 'block';
    document.getElementById('progress-container').style.display = 'none';
    document.getElementById('resultado-container').style.display = 'none';
    document.getElementById('btn-gerar').disabled = false;
}

// Fechar modal
function fecharModal() {
    document.getElementById('modal-dados-teste').style.display = 'none';
}

// Gerar dados de teste
function gerarDadosTeste() {
    var limparAntes = document.getElementById('chk_limpar_antes').checked;
    var btnGerar = document.getElementById('btn-gerar');
    var progressContainer = document.getElementById('progress-container');

    btnGerar.disabled = true;
    progressContainer.style.display = 'block';

    addLog('Iniciando geração de dados de teste...', 'info');
    if (limparAntes) {
        addLog('Opção "Limpar antes" selecionada', 'warning');
    }

    var steps = ['contabilidade', 'imobiliarias', 'contas', 'imoveis', 'compradores', 'contratos', 'parcelas', 'indices'];
    var currentStep = 0;

    function updateProgress(step, status) {
        var stepEl = document.getElementById('step-' + step);
        if (status === 'active') {
            stepEl.classList.add('active');
            stepEl.classList.remove('completed');
            stepEl.querySelector('.fa').className = 'fa fa-spinner fa-spin';
        } else if (status === 'completed') {
            stepEl.classList.remove('active');
            stepEl.classList.add('completed');
            stepEl.querySelector('.fa').className = 'fa fa-check';
        }
        var progress = ((currentStep + 1) / steps.length) * 100;
        document.getElementById('progress-bar-fill').style.width = progress + '%';
    }

    apex.server.process('GERAR_DADOS_TESTE', {
        x01: limparAntes ? '1' : '0'
    }, {
        dataType: 'json',
        success: function(data) {
            // Simular progresso visual
            var interval = setInterval(function() {
                if (currentStep < steps.length) {
                    if (currentStep > 0) {
                        updateProgress(steps[currentStep - 1], 'completed');
                    }
                    updateProgress(steps[currentStep], 'active');
                    addLog('Processando: ' + steps[currentStep], 'info');
                    currentStep++;
                } else {
                    clearInterval(interval);
                    updateProgress(steps[steps.length - 1], 'completed');

                    if (data.status === 'success') {
                        addLog('Dados gerados com sucesso!', 'success');
                        document.getElementById('resultado-container').style.display = 'block';
                        document.getElementById('resultado-mensagem').innerHTML = data.message;
                        apex.message.showPageSuccess(data.message);
                        apex.region('status-cards').refresh();
                    } else {
                        addLog('ERRO: ' + data.message, 'error');
                        apex.message.showErrors([{type: 'error', location: 'page', message: data.message}]);
                    }
                }
            }, 300);
        },
        error: function(xhr, status, error) {
            addLog('ERRO: ' + error, 'error');
            btnGerar.disabled = false;
        }
    });
}

// Confirmar limpeza
function confirmarLimpeza() {
    document.getElementById('modal-confirmar-limpeza').style.display = 'block';
    document.getElementById('input-confirmar').value = '';
    document.getElementById('btn-confirmar-limpeza').disabled = true;

    // Buscar contagens
    apex.server.process('OBTER_CONTAGENS', {}, {
        dataType: 'json',
        success: function(data) {
            document.getElementById('count-parcelas').textContent = data.parcelas || 0;
            document.getElementById('count-contratos').textContent = data.contratos || 0;
            document.getElementById('count-boletos').textContent = data.boletos || 0;
            document.getElementById('count-imoveis').textContent = data.imoveis || 0;
            document.getElementById('count-compradores').textContent = data.compradores || 0;
            document.getElementById('count-imobiliarias').textContent = data.imobiliarias || 0;
            document.getElementById('count-contabilidades').textContent = data.contabilidades || 0;
            document.getElementById('count-indices').textContent = data.indices || 0;
        }
    });
}

// Habilitar botao de limpeza ao digitar CONFIRMAR
document.addEventListener('DOMContentLoaded', function() {
    var inputConfirmar = document.getElementById('input-confirmar');
    if (inputConfirmar) {
        inputConfirmar.addEventListener('input', function() {
            document.getElementById('btn-confirmar-limpeza').disabled =
                this.value.toUpperCase() !== 'CONFIRMAR';
        });
    }
});

// Fechar modal de limpeza
function fecharModalLimpeza() {
    document.getElementById('modal-confirmar-limpeza').style.display = 'none';
}

// Executar limpeza
function executarLimpeza() {
    addLog('Iniciando limpeza de dados...', 'warning');
    fecharModalLimpeza();

    apex.server.process('LIMPAR_DADOS', {}, {
        dataType: 'json',
        success: function(data) {
            if (data.status === 'success') {
                addLog('Dados removidos com sucesso!', 'success');
                apex.message.showPageSuccess(data.message);
                apex.region('status-cards').refresh();
            } else {
                addLog('ERRO: ' + data.message, 'error');
                apex.message.showErrors([{type: 'error', location: 'page', message: data.message}]);
            }
        },
        error: function(xhr, status, error) {
            addLog('ERRO: ' + error, 'error');
        }
    });
}

// Setup completo
function executarSetupCompleto() {
    if (!confirm('Executar setup completo? Isso irá:\n1. Verificar estrutura\n2. Criar administrador\n3. Gerar dados de teste')) {
        return;
    }

    addLog('=== INICIANDO SETUP COMPLETO ===', 'info');

    apex.server.process('SETUP_COMPLETO', {}, {
        dataType: 'json',
        success: function(data) {
            if (data.status === 'success') {
                addLog('Setup completo finalizado!', 'success');
                apex.message.showPageSuccess(data.message);
                apex.region('status-cards').refresh();
            } else {
                addLog('ERRO: ' + data.message, 'error');
                apex.message.showErrors([{type: 'error', location: 'page', message: data.message}]);
            }
        },
        error: function(xhr, status, error) {
            addLog('ERRO: ' + error, 'error');
        }
    });
}
</script>
*/

/*
================================================================================
AJAX CALLBACKS
================================================================================
*/

-- AJAX Callback: EXECUTAR_ACAO_SETUP
/*
DECLARE
    v_acao VARCHAR2(50) := APEX_APPLICATION.g_x01;
    v_resultado VARCHAR2(4000);
BEGIN
    CASE v_acao
        WHEN 'verificar' THEN
            v_resultado := pkg_setup.verificar_estrutura();
        WHEN 'instalar' THEN
            v_resultado := pkg_setup.instalar_estrutura();
        WHEN 'admin' THEN
            v_resultado := pkg_setup.criar_admin();
        ELSE
            v_resultado := 'Ação desconhecida: ' || v_acao;
    END CASE;

    APEX_JSON.open_object;
    APEX_JSON.write('status', 'success');
    APEX_JSON.write('message', v_resultado);
    APEX_JSON.close_object;
EXCEPTION
    WHEN OTHERS THEN
        APEX_JSON.open_object;
        APEX_JSON.write('status', 'error');
        APEX_JSON.write('message', SQLERRM);
        APEX_JSON.close_object;
END;
*/

-- AJAX Callback: GERAR_DADOS_TESTE
/*
DECLARE
    v_limpar_antes BOOLEAN := APEX_APPLICATION.g_x01 = '1';
    v_resultado CLOB;
BEGIN
    v_resultado := pkg_setup.gerar_dados_teste(p_limpar_antes => v_limpar_antes);

    APEX_JSON.open_object;
    APEX_JSON.write('status', 'success');
    APEX_JSON.write('message', v_resultado);
    APEX_JSON.close_object;
EXCEPTION
    WHEN OTHERS THEN
        APEX_JSON.open_object;
        APEX_JSON.write('status', 'error');
        APEX_JSON.write('message', SQLERRM);
        APEX_JSON.close_object;
END;
*/

-- AJAX Callback: OBTER_CONTAGENS
/*
BEGIN
    APEX_JSON.open_object;
    APEX_JSON.write('parcelas', (SELECT COUNT(*) FROM gc_parcela));
    APEX_JSON.write('contratos', (SELECT COUNT(*) FROM gc_contrato));
    APEX_JSON.write('boletos', (SELECT COUNT(*) FROM gc_boleto));
    APEX_JSON.write('imoveis', (SELECT COUNT(*) FROM gc_imovel));
    APEX_JSON.write('compradores', (SELECT COUNT(*) FROM gc_comprador));
    APEX_JSON.write('imobiliarias', (SELECT COUNT(*) FROM gc_imobiliaria));
    APEX_JSON.write('contabilidades', (SELECT COUNT(*) FROM gc_contabilidade));
    APEX_JSON.write('indices', (SELECT COUNT(*) FROM gc_valor_indice));
    APEX_JSON.close_object;
END;
*/

-- AJAX Callback: LIMPAR_DADOS
/*
DECLARE
    v_resultado VARCHAR2(4000);
BEGIN
    v_resultado := pkg_setup.limpar_dados();

    APEX_JSON.open_object;
    APEX_JSON.write('status', 'success');
    APEX_JSON.write('message', v_resultado);
    APEX_JSON.close_object;
EXCEPTION
    WHEN OTHERS THEN
        APEX_JSON.open_object;
        APEX_JSON.write('status', 'error');
        APEX_JSON.write('message', SQLERRM);
        APEX_JSON.close_object;
END;
*/

-- AJAX Callback: SETUP_COMPLETO
/*
DECLARE
    v_resultado CLOB;
BEGIN
    v_resultado := pkg_setup.setup_completo();

    APEX_JSON.open_object;
    APEX_JSON.write('status', 'success');
    APEX_JSON.write('message', v_resultado);
    APEX_JSON.close_object;
EXCEPTION
    WHEN OTHERS THEN
        APEX_JSON.open_object;
        APEX_JSON.write('status', 'error');
        APEX_JSON.write('message', SQLERRM);
        APEX_JSON.close_object;
END;
*/

