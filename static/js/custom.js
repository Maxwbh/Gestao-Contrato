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
        const toastContainer = document.getElementById('toastContainer');
        if (!toastContainer) {
            const container = document.createElement('div');
            container.id = 'toastContainer';
            container.style.position = 'fixed';
            container.style.top = '20px';
            container.style.right = '20px';
            container.style.zIndex = '9999';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = `alert alert-${type} alert-dismissible fade show`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.getElementById('toastContainer').appendChild(toast);

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
     * Apply CNPJ mask (99.999.999/9999-99)
     */
    function mascaraCNPJ(value) {
        return value
            .replace(/\D/g, '')
            .replace(/^(\d{2})(\d)/, '$1.$2')
            .replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3')
            .replace(/\.(\d{3})(\d)/, '.$1/$2')
            .replace(/(\d{4})(\d)/, '$1-$2')
            .slice(0, 18);
    }

    /**
     * Apply phone mask
     */
    function mascaraTelefone(value) {
        value = value.replace(/\D/g, '');
        if (value.length <= 10) {
            // Telefone fixo: (99) 9999-9999
            return value
                .replace(/(\d{2})(\d)/, '($1) $2')
                .replace(/(\d{4})(\d)/, '$1-$2');
        } else {
            // Celular: (99) 99999-9999
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
        // Remove caracteres não numéricos
        const cepLimpo = cep.replace(/\D/g, '');

        // Valida CEP
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
        // Mapeia os campos do formulário
        const campos = {
            logradouro: ['logradouro', 'id_logradouro'],
            bairro: ['bairro', 'id_bairro'],
            cidade: ['cidade', 'id_cidade', 'localidade'],
            estado: ['estado', 'id_estado', 'uf']
        };

        // Preenche cada campo
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

                    // Remove readonly temporariamente para permitir edição
                    elemento.removeAttribute('readonly');

                    // Trigger change event
                    elemento.dispatchEvent(new Event('change'));
                }
            });
        });

        // Foca no campo número (geralmente o próximo a ser preenchido)
        const campoNumero = document.querySelector('[name="numero"]');
        if (campoNumero) {
            setTimeout(() => campoNumero.focus(), 100);
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
     * Validate CNPJ
     */
    function validarCNPJ(cnpj) {
        cnpj = cnpj.replace(/\D/g, '');

        if (cnpj.length !== 14 || /^(\d)\1{13}$/.test(cnpj)) {
            return false;
        }

        let tamanho = cnpj.length - 2;
        let numeros = cnpj.substring(0, tamanho);
        let digitos = cnpj.substring(tamanho);
        let soma = 0;
        let pos = tamanho - 7;

        for (let i = tamanho; i >= 1; i--) {
            soma += numeros.charAt(tamanho - i) * pos--;
            if (pos < 2) pos = 9;
        }

        let resultado = soma % 11 < 2 ? 0 : 11 - soma % 11;
        if (resultado != digitos.charAt(0)) return false;

        tamanho = tamanho + 1;
        numeros = cnpj.substring(0, tamanho);
        soma = 0;
        pos = tamanho - 7;

        for (let i = tamanho; i >= 1; i--) {
            soma += numeros.charAt(tamanho - i) * pos--;
            if (pos < 2) pos = 9;
        }

        resultado = soma % 11 < 2 ? 0 : 11 - soma % 11;
        if (resultado != digitos.charAt(1)) return false;

        return true;
    }

    /**
     * Validate email
     */
    function validarEmail(email) {
        const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return re.test(email);
    }

    // ========================================================================
    // AUTO-APPLY MASKS
    // ========================================================================

    document.addEventListener('DOMContentLoaded', function() {

        // CPF inputs
        const cpfInputs = document.querySelectorAll('input[name="cpf"], input[name="conjuge_cpf"]');
        cpfInputs.forEach(input => {
            input.addEventListener('input', function(e) {
                e.target.value = mascaraCPF(e.target.value);
            });

            input.addEventListener('blur', function(e) {
                const cpf = e.target.value;
                if (cpf && !validarCPF(cpf)) {
                    e.target.classList.add('is-invalid');
                    let feedback = e.target.parentElement.querySelector('.invalid-feedback');
                    if (!feedback) {
                        feedback = document.createElement('div');
                        feedback.className = 'invalid-feedback';
                        feedback.textContent = 'CPF inválido';
                        e.target.parentElement.appendChild(feedback);
                    }
                } else {
                    e.target.classList.remove('is-invalid');
                }
            });
        });

        // CNPJ inputs
        const cnpjInputs = document.querySelectorAll('input[name="cnpj"]');
        cnpjInputs.forEach(input => {
            input.addEventListener('input', function(e) {
                e.target.value = mascaraCNPJ(e.target.value);
            });

            input.addEventListener('blur', function(e) {
                const cnpj = e.target.value;
                if (cnpj && !validarCNPJ(cnpj)) {
                    e.target.classList.add('is-invalid');
                    let feedback = e.target.parentElement.querySelector('.invalid-feedback');
                    if (!feedback) {
                        feedback = document.createElement('div');
                        feedback.className = 'invalid-feedback';
                        feedback.textContent = 'CNPJ inválido';
                        e.target.parentElement.appendChild(feedback);
                    }
                } else {
                    e.target.classList.remove('is-invalid');
                }
            });
        });

        // Phone inputs
        const phoneInputs = document.querySelectorAll('input[name="telefone"], input[name="celular"]');
        phoneInputs.forEach(input => {
            input.addEventListener('input', function(e) {
                e.target.value = mascaraTelefone(e.target.value);
            });
        });

        // CEP inputs
        const cepInputs = document.querySelectorAll('input[name="cep"], .cep-input');
        cepInputs.forEach(input => {
            // Aplica máscara
            input.addEventListener('input', function(e) {
                e.target.value = mascaraCEP(e.target.value);
            });

            // Busca endereço via ViaCEP quando CEP está completo
            input.addEventListener('blur', async function(e) {
                const cep = e.target.value.replace(/\D/g, '');

                if (cep.length === 8) {
                    // Mostra loading
                    const originalValue = e.target.value;
                    e.target.value = 'Buscando...';
                    e.target.disabled = true;

                    const resultado = await buscarCEP(cep);

                    // Restaura campo
                    e.target.value = originalValue;
                    e.target.disabled = false;

                    if (resultado.erro) {
                        showToast(resultado.mensagem, 'warning');
                        e.target.classList.add('is-invalid');
                    } else {
                        e.target.classList.remove('is-invalid');
                        e.target.classList.add('is-valid');
                        preencherEndereco(resultado);
                        showToast('Endereço encontrado! Verifique e complete os dados.', 'success');
                    }
                }
            });
        });

        // Email inputs
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
                // Auto-submit could be implemented here
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
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }, 5000);
        });

        // ====================================================================
        // CONFIRM FORM SUBMISSION FOR DELETIONS
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
        // TABLE ROW CLICK TO VIEW DETAILS (if data-href exists)
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
