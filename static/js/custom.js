/**
 * Custom JavaScript for Gestão de Contratos
 * Desenvolvedor: Maxwell da Silva Oliveira
 * Email: maxwbh@gmail.com
 */

(function() {
    'use strict';

    // ========================================================================
    // UTILITY FUNCTIONS
    // ========================================================================

    /**
     * Debounce function to limit function calls
     */
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    /**
     * Show toast notification
     */
    function showToast(message, type = 'info') {
        let toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toastContainer';
            toastContainer.style.cssText = 'position:fixed;top:20px;right:20px;z-index:9999;';
            document.body.appendChild(toastContainer);
        }

        const toast = document.createElement('div');
        toast.className = `alert alert-${type} alert-dismissible fade show`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        toastContainer.appendChild(toast);

        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }

    // ========================================================================
    // INPUT MASKS
    // ========================================================================

    /**
     * Apply CPF mask (999.999.999-99)
     */
    function mascaraCPF(value) {
        return value
            .replace(/\D/g, '')
            .replace(/(\d{3})(\d)/, '$1.$2')
            .replace(/(\d{3})(\d)/, '$1.$2')
            .replace(/(\d{3})(\d{1,2})$/, '$1-$2')
            .slice(0, 14);
    }

    /**
     * Apply CNPJ mask - Suporta formato numérico e alfanumérico (preparado para 2026)
     */
    function mascaraCNPJ(value) {
        // Remove caracteres especiais mas mantém letras e números
        value = value.toUpperCase().replace(/[^A-Z0-9]/g, '');
        value = value.slice(0, 14);

        // Aplica máscara: XX.XXX.XXX/XXXX-XX
        if (value.length > 2) {
            value = value.substring(0, 2) + '.' + value.substring(2);
        }
        if (value.length > 6) {
            value = value.substring(0, 6) + '.' + value.substring(6);
        }
        if (value.length > 10) {
            value = value.substring(0, 10) + '/' + value.substring(10);
        }
        if (value.length > 15) {
            value = value.substring(0, 15) + '-' + value.substring(15);
        }

        return value.slice(0, 20);
    }

    /**
     * Apply phone mask
     */
    function mascaraTelefone(value) {
        value = value.replace(/\D/g, '');
        if (value.length <= 10) {
            return value
                .replace(/(\d{2})(\d)/, '($1) $2')
                .replace(/(\d{4})(\d)/, '$1-$2');
        } else {
            return value
                .replace(/(\d{2})(\d)/, '($1) $2')
                .replace(/(\d{5})(\d)/, '$1-$2')
                .slice(0, 15);
        }
    }

    /**
     * Apply CEP mask (99999-999)
     */
    function mascaraCEP(value) {
        return value
            .replace(/\D/g, '')
            .replace(/(\d{5})(\d)/, '$1-$2')
            .slice(0, 9);
    }

    /**
     * Buscar endereço via ViaCEP
     */
    async function buscarCEP(cep) {
        const cepLimpo = cep.replace(/\D/g, '');

        if (cepLimpo.length !== 8) {
            return { erro: true, mensagem: 'CEP deve ter 8 dígitos' };
        }

        try {
            const response = await fetch(`https://viacep.com.br/ws/${cepLimpo}/json/`);
            const data = await response.json();

            if (data.erro) {
                return { erro: true, mensagem: 'CEP não encontrado' };
            }

            return {
                erro: false,
                cep: data.cep,
                logradouro: data.logradouro,
                complemento: data.complemento,
                bairro: data.bairro,
                localidade: data.localidade,
                uf: data.uf
            };
        } catch (error) {
            console.error('Erro ao buscar CEP:', error);
            return { erro: true, mensagem: 'Erro ao buscar CEP. Tente novamente.' };
        }
    }

    /**
     * Preencher campos de endereço com dados do ViaCEP
     */
    function preencherEndereco(dados) {
        const campos = {
            logradouro: ['logradouro', 'id_logradouro'],
            bairro: ['bairro', 'id_bairro'],
            cidade: ['cidade', 'id_cidade', 'localidade'],
            estado: ['estado', 'id_estado', 'uf']
        };

        Object.keys(campos).forEach(campo => {
            campos[campo].forEach(possibilidade => {
                const elemento = document.querySelector(`[name="${possibilidade}"]`) ||
                                document.getElementById(possibilidade);

                if (elemento) {
                    if (campo === 'cidade') {
                        elemento.value = dados.localidade || '';
                    } else if (campo === 'estado') {
                        elemento.value = dados.uf || '';
                    } else {
                        elemento.value = dados[campo] || '';
                    }
                    elemento.removeAttribute('readonly');
                    elemento.dispatchEvent(new Event('change'));
                }
            });
        });

        // Foca no campo número
        const campoNumero = document.querySelector('[name="numero"]');
        if (campoNumero) {
            setTimeout(() => campoNumero.focus(), 100);
        }
    }

    /**
     * Buscar dados da empresa via BrasilAPI (CNPJ)
     */
    async function buscarCNPJ(cnpj) {
        const cnpjLimpo = cnpj.replace(/\D/g, '');

        if (cnpjLimpo.length !== 14) {
            return { erro: true, mensagem: 'CNPJ deve ter 14 digitos' };
        }

        try {
            // Usar o endpoint local que faz proxy para BrasilAPI
            const response = await fetch(`/api/cnpj/${cnpjLimpo}/`);
            const data = await response.json();

            if (!data.sucesso) {
                return { erro: true, mensagem: data.erro || 'CNPJ nao encontrado' };
            }

            return {
                erro: false,
                cnpj: data.cnpj,
                razao_social: data.razao_social,
                nome_fantasia: data.nome_fantasia,
                situacao_cadastral: data.situacao_cadastral,
                email: data.email,
                telefone: data.telefone,
                cep: data.cep,
                logradouro: data.logradouro,
                numero: data.numero,
                complemento: data.complemento,
                bairro: data.bairro,
                cidade: data.cidade,
                estado: data.estado
            };
        } catch (error) {
            console.error('Erro ao buscar CNPJ:', error);
            return { erro: true, mensagem: 'Erro ao buscar CNPJ. Tente novamente.' };
        }
    }

    /**
     * Preencher campos com dados da empresa (CNPJ)
     */
    function preencherDadosEmpresa(dados) {
        const mapeamento = {
            // Dados da empresa
            'nome': dados.razao_social,
            'id_nome': dados.razao_social,
            'razao_social': dados.razao_social,
            'nome_fantasia': dados.nome_fantasia,
            'id_nome_fantasia': dados.nome_fantasia,

            // Contato
            'email': dados.email,
            'id_email': dados.email,
            'telefone': dados.telefone,
            'id_telefone': dados.telefone,

            // Endereco
            'cep': dados.cep,
            'id_cep': dados.cep,
            'logradouro': dados.logradouro,
            'id_logradouro': dados.logradouro,
            'numero': dados.numero,
            'id_numero': dados.numero,
            'complemento': dados.complemento,
            'id_complemento': dados.complemento,
            'bairro': dados.bairro,
            'id_bairro': dados.bairro,
            'cidade': dados.cidade,
            'id_cidade': dados.cidade,
            'estado': dados.estado,
            'id_estado': dados.estado
        };

        Object.keys(mapeamento).forEach(campo => {
            const valor = mapeamento[campo];
            if (valor) {
                const elemento = document.querySelector(`[name="${campo}"]`) ||
                                document.getElementById(campo);
                if (elemento && !elemento.value) {
                    elemento.value = valor;
                    elemento.dispatchEvent(new Event('change'));
                }
            }
        });

        // Mostrar situacao cadastral
        if (dados.situacao_cadastral) {
            const situacaoDiv = document.getElementById('situacao-cnpj');
            if (situacaoDiv) {
                situacaoDiv.innerHTML = `<span class="badge ${dados.situacao_cadastral === 'ATIVA' ? 'bg-success' : 'bg-danger'}">${dados.situacao_cadastral}</span>`;
            }
        }
    }

    /**
     * Apply currency mask
     */
    function mascaraMoeda(value) {
        value = value.replace(/\D/g, '');
        value = (parseInt(value) / 100).toFixed(2);
        value = value.replace('.', ',');
        value = value.replace(/(\d)(?=(\d{3})+(?!\d))/g, '$1.');
        return 'R$ ' + value;
    }

    // ========================================================================
    // FORM VALIDATION
    // ========================================================================

    /**
     * Validate CPF
     */
    function validarCPF(cpf) {
        cpf = cpf.replace(/\D/g, '');

        if (cpf.length !== 11 || /^(\d)\1{10}$/.test(cpf)) {
            return false;
        }

        let soma = 0;
        let resto;

        for (let i = 1; i <= 9; i++) {
            soma += parseInt(cpf.substring(i - 1, i)) * (11 - i);
        }

        resto = (soma * 10) % 11;
        if (resto === 10 || resto === 11) resto = 0;
        if (resto !== parseInt(cpf.substring(9, 10))) return false;

        soma = 0;
        for (let i = 1; i <= 10; i++) {
            soma += parseInt(cpf.substring(i - 1, i)) * (12 - i);
        }

        resto = (soma * 10) % 11;
        if (resto === 10 || resto === 11) resto = 0;
        if (resto !== parseInt(cpf.substring(10, 11))) return false;

        return true;
    }

    /**
     * Validate CNPJ - Suporta formato numérico e alfanumérico (2026+)
     */
    function validarCNPJ(cnpj) {
        const cnpjLimpo = cnpj.replace(/[.\-\/]/g, '');

        if (cnpjLimpo.length !== 14) {
            return false;
        }

        const isNumerico = /^\d{14}$/.test(cnpjLimpo);

        if (isNumerico) {
            const numeros = cnpjLimpo.replace(/\D/g, '');

            if (/^(\d)\1{13}$/.test(numeros)) {
                return false;
            }

            let tamanho = numeros.length - 2;
            let digitosOriginais = numeros.substring(tamanho);
            let soma = 0;
            let pos = tamanho - 7;

            for (let i = tamanho; i >= 1; i--) {
                soma += numeros.charAt(tamanho - i) * pos--;
                if (pos < 2) pos = 9;
            }

            let resultado = soma % 11 < 2 ? 0 : 11 - soma % 11;
            if (resultado != digitosOriginais.charAt(0)) return false;

            tamanho = tamanho + 1;
            soma = 0;
            pos = tamanho - 7;

            for (let i = tamanho; i >= 1; i--) {
                soma += numeros.charAt(tamanho - i) * pos--;
                if (pos < 2) pos = 9;
            }

            resultado = soma % 11 < 2 ? 0 : 11 - soma % 11;
            if (resultado != digitosOriginais.charAt(1)) return false;

            return true;
        } else {
            // CNPJ alfanumérico (formato 2026+)
            const formatoAlfanumerico = /^[A-Z0-9]{14}$/;
            if (!formatoAlfanumerico.test(cnpjLimpo)) {
                return false;
            }
            console.info('CNPJ alfanumérico detectado. Validação completa disponível após 2026.');
            return true;
        }
    }

    /**
     * Validate email
     */
    function validarEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    }

    // ========================================================================
    // TIPO PESSOA (PF/PJ) TOGGLE
    // ========================================================================

    function initTipoPessoaToggle() {
        // Buscar tanto select quanto radio buttons
        const tipoPessoaSelect = document.querySelector('select[name="tipo_pessoa"]');
        const tipoPessoaRadios = document.querySelectorAll('input[name="tipo_pessoa"]');

        // Elementos do formulário
        const camposPF = document.getElementById('campos-pf');
        const camposPJ = document.getElementById('campos-pj');
        const cardConjuge = document.getElementById('card-conjuge');
        const labelNome = document.querySelector('label[for="id_nome"]');
        const tituloIdentificacao = document.getElementById('titulo-identificacao');

        function getTipoPessoa() {
            // Se for select
            if (tipoPessoaSelect) {
                return tipoPessoaSelect.value;
            }
            // Se for radio buttons
            const checkedRadio = document.querySelector('input[name="tipo_pessoa"]:checked');
            return checkedRadio ? checkedRadio.value : 'PF';
        }

        function toggleCampos() {
            const tipo = getTipoPessoa();
            const isPF = tipo === 'PF';
            const isPJ = tipo === 'PJ';

            console.log('Toggle tipo pessoa:', tipo);

            // Toggle seções PF/PJ
            if (camposPF) {
                camposPF.style.display = isPF ? 'block' : 'none';
            }
            if (camposPJ) {
                camposPJ.style.display = isPJ ? 'block' : 'none';
            }
            if (cardConjuge) {
                cardConjuge.style.display = isPF ? 'block' : 'none';
            }

            // Atualizar labels
            if (labelNome) {
                labelNome.innerHTML = isPF
                    ? 'Nome Completo <span class="text-danger">*</span>'
                    : 'Razão Social <span class="text-danger">*</span>';
            }
            if (tituloIdentificacao) {
                tituloIdentificacao.innerHTML = isPF
                    ? '<i class="fas fa-user me-2"></i>Dados Pessoais'
                    : '<i class="fas fa-building me-2"></i>Dados da Empresa';
            }

            // Atualizar placeholder do campo nome
            const campoNome = document.querySelector('input[name="nome"]');
            if (campoNome) {
                campoNome.placeholder = isPF ? 'Nome completo do comprador' : 'Razão social da empresa';
            }

            // Limpar campos não utilizados ao trocar tipo
            if (isPF) {
                // Limpar campos PJ
                const camposClear = ['cnpj', 'nome_fantasia', 'inscricao_estadual',
                                     'inscricao_municipal', 'responsavel_legal', 'responsavel_cpf'];
                camposClear.forEach(nome => {
                    const campo = document.querySelector(`[name="${nome}"]`);
                    if (campo) campo.value = '';
                });
            } else if (isPJ) {
                // Limpar campos PF
                const camposClear = ['cpf', 'rg', 'data_nascimento', 'profissao',
                                     'conjuge_nome', 'conjuge_cpf', 'conjuge_rg'];
                camposClear.forEach(nome => {
                    const campo = document.querySelector(`[name="${nome}"]`);
                    if (campo) campo.value = '';
                });
                // Resetar estado civil
                const estadoCivil = document.querySelector('select[name="estado_civil"]');
                if (estadoCivil) estadoCivil.value = '';
            }
        }

        // Adicionar event listeners
        if (tipoPessoaSelect) {
            tipoPessoaSelect.addEventListener('change', toggleCampos);
        }

        if (tipoPessoaRadios.length > 0) {
            tipoPessoaRadios.forEach(radio => {
                radio.addEventListener('change', toggleCampos);
            });
        }

        // Executar na carga da página
        toggleCampos();
    }

    // ========================================================================
    // AUTO-APPLY MASKS
    // ========================================================================

    document.addEventListener('DOMContentLoaded', function() {

        // ====================================================================
        // INICIALIZAR TOGGLE PF/PJ
        // ====================================================================
        initTipoPessoaToggle();

        // ====================================================================
        // CPF inputs
        // ====================================================================
        const cpfInputs = document.querySelectorAll('input[name="cpf"], input[name="conjuge_cpf"], input[name="responsavel_cpf"]');
        cpfInputs.forEach(input => {
            // Aplicar máscara em valores já existentes (edição)
            if (input.value) {
                input.value = mascaraCPF(input.value);
            }

            input.addEventListener('input', function(e) {
                e.target.value = mascaraCPF(e.target.value);
            });

            input.addEventListener('blur', function(e) {
                const cpf = e.target.value;
                if (cpf && cpf.length >= 14 && !validarCPF(cpf)) {
                    e.target.classList.add('is-invalid');
                    e.target.classList.remove('is-valid');
                    let feedback = e.target.parentElement.querySelector('.invalid-feedback');
                    if (!feedback) {
                        feedback = document.createElement('div');
                        feedback.className = 'invalid-feedback';
                        feedback.textContent = 'CPF inválido';
                        e.target.parentElement.appendChild(feedback);
                    }
                } else if (cpf && validarCPF(cpf)) {
                    e.target.classList.remove('is-invalid');
                    e.target.classList.add('is-valid');
                } else {
                    e.target.classList.remove('is-invalid', 'is-valid');
                }
            });
        });

        // ====================================================================
        // CNPJ inputs
        // ====================================================================
        const cnpjInputs = document.querySelectorAll('input[name="cnpj"]');
        cnpjInputs.forEach(input => {
            // Aplicar máscara em valores já existentes (edição)
            if (input.value) {
                input.value = mascaraCNPJ(input.value);
            }

            input.addEventListener('input', function(e) {
                e.target.value = mascaraCNPJ(e.target.value);
            });

            input.addEventListener('blur', function(e) {
                const cnpj = e.target.value;
                if (cnpj && cnpj.length >= 18 && !validarCNPJ(cnpj)) {
                    e.target.classList.add('is-invalid');
                    e.target.classList.remove('is-valid');
                    let feedback = e.target.parentElement.querySelector('.invalid-feedback');
                    if (!feedback) {
                        feedback = document.createElement('div');
                        feedback.className = 'invalid-feedback';
                        feedback.textContent = 'CNPJ inválido';
                        e.target.parentElement.appendChild(feedback);
                    }
                } else if (cnpj && validarCNPJ(cnpj)) {
                    e.target.classList.remove('is-invalid');
                    e.target.classList.add('is-valid');
                } else {
                    e.target.classList.remove('is-invalid', 'is-valid');
                }
            });
        });

        // ====================================================================
        // Phone inputs
        // ====================================================================
        const phoneInputs = document.querySelectorAll('input[name="telefone"], input[name="celular"]');
        phoneInputs.forEach(input => {
            input.addEventListener('input', function(e) {
                e.target.value = mascaraTelefone(e.target.value);
            });
        });

        // ====================================================================
        // CEP inputs with ViaCEP integration
        // ====================================================================
        const cepInputs = document.querySelectorAll('input[name="cep"], .cep-input');
        cepInputs.forEach(input => {
            input.addEventListener('input', function(e) {
                e.target.value = mascaraCEP(e.target.value);
            });

            input.addEventListener('blur', async function(e) {
                const cep = e.target.value.replace(/\D/g, '');

                if (cep.length === 8) {
                    const originalValue = e.target.value;
                    e.target.value = 'Buscando...';
                    e.target.disabled = true;

                    const resultado = await buscarCEP(cep);

                    e.target.value = originalValue;
                    e.target.disabled = false;

                    if (resultado.erro) {
                        showToast(resultado.mensagem, 'warning');
                        e.target.classList.add('is-invalid');
                        e.target.classList.remove('is-valid');
                    } else {
                        e.target.classList.remove('is-invalid');
                        e.target.classList.add('is-valid');
                        preencherEndereco(resultado);
                        showToast('Endereco encontrado!', 'success');
                    }
                }
            });
        });

        // ====================================================================
        // CNPJ inputs with BrasilAPI integration
        // ====================================================================
        const cnpjInputs = document.querySelectorAll('input[name="cnpj"], .cnpj-input');
        cnpjInputs.forEach(input => {
            input.addEventListener('input', function(e) {
                e.target.value = mascaraCNPJ(e.target.value);
            });

            input.addEventListener('blur', async function(e) {
                const cnpj = e.target.value.replace(/\D/g, '');

                if (cnpj.length === 14) {
                    // Validar CNPJ primeiro
                    if (!validarCNPJ(e.target.value)) {
                        showToast('CNPJ invalido', 'warning');
                        e.target.classList.add('is-invalid');
                        e.target.classList.remove('is-valid');
                        return;
                    }

                    const originalValue = e.target.value;
                    e.target.value = 'Buscando...';
                    e.target.disabled = true;

                    const resultado = await buscarCNPJ(cnpj);

                    e.target.value = originalValue;
                    e.target.disabled = false;

                    if (resultado.erro) {
                        showToast(resultado.mensagem, 'warning');
                        e.target.classList.add('is-invalid');
                        e.target.classList.remove('is-valid');
                    } else {
                        e.target.classList.remove('is-invalid');
                        e.target.classList.add('is-valid');
                        preencherDadosEmpresa(resultado);

                        // Mensagem com nome da empresa
                        const nomeEmpresa = resultado.nome_fantasia || resultado.razao_social;
                        showToast(`Empresa encontrada: ${nomeEmpresa}`, 'success');
                    }
                }
            });
        });

        // ====================================================================
        // Email inputs
        // ====================================================================
        const emailInputs = document.querySelectorAll('input[type="email"]');
        emailInputs.forEach(input => {
            input.addEventListener('blur', function(e) {
                const email = e.target.value;
                if (email && !validarEmail(email)) {
                    e.target.classList.add('is-invalid');
                    let feedback = e.target.parentElement.querySelector('.invalid-feedback');
                    if (!feedback) {
                        feedback = document.createElement('div');
                        feedback.className = 'invalid-feedback';
                        feedback.textContent = 'Email inválido';
                        e.target.parentElement.appendChild(feedback);
                    }
                } else {
                    e.target.classList.remove('is-invalid');
                    if (email) e.target.classList.add('is-valid');
                }
            });
        });

        // ====================================================================
        // FORM SUBMIT ANIMATION
        // ====================================================================
        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            form.addEventListener('submit', function(e) {
                const submitBtn = form.querySelector('button[type="submit"]');
                if (submitBtn && !form.classList.contains('no-loading')) {
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Processando...';
                }
            });
        });

        // ====================================================================
        // SEARCH WITH DEBOUNCE
        // ====================================================================
        const searchInputs = document.querySelectorAll('input[name="search"]');
        searchInputs.forEach(input => {
            input.addEventListener('input', debounce(function(e) {
                console.log('Searching for:', e.target.value);
            }, 500));
        });

        // ====================================================================
        // ANIMATE ELEMENTS ON SCROLL
        // ====================================================================
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver(function(entries) {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('fade-in');
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);

        const animatedElements = document.querySelectorAll('.card, .table, .alert');
        animatedElements.forEach(el => observer.observe(el));

        // ====================================================================
        // AUTO-DISMISS ALERTS
        // ====================================================================
        const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(alert => {
            setTimeout(() => {
                if (typeof bootstrap !== 'undefined') {
                    const bsAlert = new bootstrap.Alert(alert);
                    bsAlert.close();
                }
            }, 5000);
        });

        // ====================================================================
        // CONFIRM DELETIONS
        // ====================================================================
        const deleteButtons = document.querySelectorAll('.btn-danger[type="submit"]');
        deleteButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                if (!confirm('Tem certeza que deseja executar esta ação?')) {
                    e.preventDefault();
                }
            });
        });

        // ====================================================================
        // TABLE ROW CLICK
        // ====================================================================
        const tableRows = document.querySelectorAll('tr[data-href]');
        tableRows.forEach(row => {
            row.style.cursor = 'pointer';
            row.addEventListener('click', function(e) {
                if (e.target.tagName !== 'BUTTON' && e.target.tagName !== 'A') {
                    window.location.href = this.dataset.href;
                }
            });
        });

        // ====================================================================
        // PRINT FUNCTIONALITY
        // ====================================================================
        window.printPage = function() {
            window.print();
        };

        // ====================================================================
        // COPY TO CLIPBOARD
        // ====================================================================
        window.copyToClipboard = function(text) {
            navigator.clipboard.writeText(text).then(() => {
                showToast('Copiado para a área de transferência!', 'success');
            }).catch(() => {
                showToast('Erro ao copiar', 'danger');
            });
        };
    });

    // ========================================================================
    // EXPOSE UTILITY FUNCTIONS GLOBALLY
    // ========================================================================
    window.GestaoContratos = {
        mascaraCPF,
        mascaraCNPJ,
        mascaraTelefone,
        mascaraCEP,
        mascaraMoeda,
        validarCPF,
        validarCNPJ,
        validarEmail,
        buscarCEP,
        preencherEndereco,
        showToast,
        debounce
    };

})();
