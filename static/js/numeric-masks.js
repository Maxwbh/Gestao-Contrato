/**
 * numeric-masks.js — Máscaras de entrada para campos numéricos
 *
 * Uso (widget Django):
 *   data-mask="moeda"      →  R$ 1.234,56
 *   data-mask="pct2"       →  1,23 %
 *   data-mask="pct4"       →  1,2345 %
 *   data-mask="decimal"    →  1.234,56  (sem símbolo)
 *   data-mask="decimal4"   →  1.234,5678 (4 casas, sem símbolo)
 *   data-mask="inteiro"    →  1.234
 *
 * Em campos ambíguos (R$ ou %), use também:
 *   data-mask-switch="<id-do-select-tipo>"
 *   data-mask-moeda="moeda"
 *   data-mask-pct="pct2"
 */
(function () {
    'use strict';

    // -----------------------------------------------------------------------
    // Funções de formatação
    // -----------------------------------------------------------------------

    function somenteDigitos(v) {
        return v.replace(/\D/g, '');
    }

    function formatMoeda(v) {
        var digits = somenteDigitos(v);
        if (!digits || digits === '0' || digits === '00') return '';
        var num = parseInt(digits, 10) / 100;
        return 'R$ ' + num.toLocaleString('pt-BR', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }

    function formatPct(v, casas) {
        var digits = somenteDigitos(v);
        if (!digits) return '';
        var divisor = Math.pow(10, casas);
        var num = parseInt(digits, 10) / divisor;
        return num.toLocaleString('pt-BR', {
            minimumFractionDigits: casas,
            maximumFractionDigits: casas
        }) + ' %';
    }

    function formatDecimal(v, casas) {
        var digits = somenteDigitos(v);
        if (!digits) return '';
        var divisor = Math.pow(10, casas);
        var num = parseInt(digits, 10) / divisor;
        return num.toLocaleString('pt-BR', {
            minimumFractionDigits: casas,
            maximumFractionDigits: casas
        });
    }

    function formatInteiro(v) {
        var digits = somenteDigitos(v);
        if (!digits) return '';
        var num = parseInt(digits, 10);
        return num.toLocaleString('pt-BR');
    }

    // Aplica a máscara correta pelo tipo
    function aplicarMascara(el, tipo) {
        var raw = el.value;
        var formatted;
        switch (tipo) {
            case 'moeda':    formatted = formatMoeda(raw); break;
            case 'pct2':     formatted = formatPct(raw, 2); break;
            case 'pct4':     formatted = formatPct(raw, 4); break;
            case 'decimal':  formatted = formatDecimal(raw, 2); break;
            case 'decimal4': formatted = formatDecimal(raw, 4); break;
            case 'inteiro':  formatted = formatInteiro(raw); break;
            default:         return;
        }
        el.value = formatted;
    }

    // -----------------------------------------------------------------------
    // Conversão raw → float (para limpeza antes de submit)
    // -----------------------------------------------------------------------

    function rawParaFloat(v, tipo) {
        // Remove R$, %, espaços e pontos de milhar; troca vírgula decimal por ponto
        v = v.replace(/R\$\s*/g, '').replace(/\s*%\s*/g, '').trim();
        v = v.replace(/\./g, '').replace(',', '.');
        return v === '' ? '' : v;
    }

    // -----------------------------------------------------------------------
    // Inicialização de um campo
    // -----------------------------------------------------------------------

    function initCampo(el) {
        if (el.dataset.maskInit) return;
        el.dataset.maskInit = '1';

        var tipo = el.dataset.mask;
        if (!tipo) return;

        // Troca type=number por text para aceitar formatação
        if (el.type === 'number') {
            el.type = 'text';
            el.removeAttribute('step');
            el.removeAttribute('min');
            el.removeAttribute('max');
        }

        // Se já tem valor numérico, formata na carga
        if (el.value && el.value !== '') {
            // Valor pode vir como "350000.00" do servidor — formata corretamente
            var numVal = parseFloat(el.value);
            if (!isNaN(numVal)) {
                // Simula dígitos brutos para os formatadores
                var casas = (tipo === 'pct4' || tipo === 'decimal4') ? 4 : 2;
                if (tipo === 'inteiro') {
                    el.value = Math.round(numVal).toLocaleString('pt-BR');
                } else if (tipo === 'moeda' || tipo === 'decimal' || tipo === 'decimal4') {
                    el.value = numVal.toLocaleString('pt-BR', {
                        minimumFractionDigits: casas,
                        maximumFractionDigits: casas
                    });
                    if (tipo === 'moeda') el.value = 'R$ ' + el.value;
                } else if (tipo === 'pct2' || tipo === 'pct4') {
                    el.value = numVal.toLocaleString('pt-BR', {
                        minimumFractionDigits: casas,
                        maximumFractionDigits: casas
                    }) + ' %';
                }
            }
        }

        // Handler de digitação
        el.addEventListener('input', function () {
            var pos = el.selectionStart;
            var oldLen = el.value.length;
            aplicarMascara(el, el.dataset.mask);
            // Reposiciona cursor proporcionalmente
            var newLen = el.value.length;
            var newPos = pos + (newLen - oldLen);
            try { el.setSelectionRange(newPos, newPos); } catch (e) {}
        });

        // Aceita apenas dígitos, vírgula e teclas de navegação
        el.addEventListener('keydown', function (e) {
            var allowed = [
                'Backspace', 'Delete', 'Tab', 'Escape', 'Enter',
                'ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown',
                'Home', 'End'
            ];
            if (allowed.indexOf(e.key) !== -1) return;
            if ((e.ctrlKey || e.metaKey) && ['a','c','v','x'].indexOf(e.key.toLowerCase()) !== -1) return;
            if (!/\d/.test(e.key)) e.preventDefault();
        });
    }

    // -----------------------------------------------------------------------
    // Switch dinâmico de máscara (ex: tipo_valor_multa → R$ ou %)
    // -----------------------------------------------------------------------

    function initSwitch(el) {
        var selectId = el.dataset.maskSwitch;
        if (!selectId) return;
        var sel = document.getElementById(selectId);
        if (!sel) return;

        function atualizarTipo() {
            var val = sel.value;
            // "PERCENTUAL" → pct, qualquer outro → moeda
            var isPct = (val === 'PERCENTUAL' || val === 'P' || val === 'pct');
            el.dataset.mask = isPct
                ? (el.dataset.maskPct || 'pct2')
                : (el.dataset.maskMoeda || 'moeda');
            // Reformata o valor atual
            aplicarMascara(el, el.dataset.mask);
        }

        sel.addEventListener('change', atualizarTipo);
        // Inicializa conforme valor atual do select
        atualizarTipo();
    }

    // -----------------------------------------------------------------------
    // Limpeza antes de submit (devolve float ao servidor)
    // -----------------------------------------------------------------------

    function limparForm(form) {
        var campos = form.querySelectorAll('[data-mask]');
        campos.forEach(function (el) {
            if (el.disabled) return;
            el.value = rawParaFloat(el.value, el.dataset.mask);
        });
    }

    // -----------------------------------------------------------------------
    // Inicialização global
    // -----------------------------------------------------------------------

    function initAll() {
        document.querySelectorAll('[data-mask]').forEach(function (el) {
            initCampo(el);
            if (el.dataset.maskSwitch) initSwitch(el);
        });

        // Limpa formatação em todos os forms antes de enviar
        document.querySelectorAll('form').forEach(function (form) {
            form.addEventListener('submit', function () {
                limparForm(form);
            });
        });
    }

    // Expõe API pública
    window.NumericMasks = {
        init: initAll,
        initCampo: initCampo,
        limparForm: limparForm,
        aplicarMascara: aplicarMascara
    };

    // Inicializa quando o DOM estiver pronto
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAll);
    } else {
        initAll();
    }

})();
