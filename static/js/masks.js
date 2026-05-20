/**
 * masks.js — Máscaras de entrada para CPF, CNPJ, telefone e CEP.
 *
 * Ativas automaticamente via classes CSS no elemento:
 *   .mask-cpf    → 000.000.000-00
 *   .mask-cnpj   → 00.000.000/0000-00
 *   .mask-phone  → (00) 0000-0000  /  (00) 00000-0000  (dinâmico)
 *   .mask-cep    → 00000-000
 */
(function () {
    'use strict';

    function onlyDigits(v) { return v.replace(/\D/g, ''); }

    function maskCpf(v) {
        var d = onlyDigits(v).slice(0, 11);
        if (d.length <= 3) return d;
        if (d.length <= 6) return d.slice(0,3) + '.' + d.slice(3);
        if (d.length <= 9) return d.slice(0,3) + '.' + d.slice(3,6) + '.' + d.slice(6);
        return d.slice(0,3) + '.' + d.slice(3,6) + '.' + d.slice(6,9) + '-' + d.slice(9);
    }

    function maskCnpj(v) {
        var d = onlyDigits(v).slice(0, 14);
        if (d.length <= 2) return d;
        if (d.length <= 5) return d.slice(0,2) + '.' + d.slice(2);
        if (d.length <= 8) return d.slice(0,2) + '.' + d.slice(2,5) + '.' + d.slice(5);
        if (d.length <= 12) return d.slice(0,2) + '.' + d.slice(2,5) + '.' + d.slice(5,8) + '/' + d.slice(8);
        return d.slice(0,2) + '.' + d.slice(2,5) + '.' + d.slice(5,8) + '/' + d.slice(8,12) + '-' + d.slice(12);
    }

    function maskPhone(v) {
        var d = onlyDigits(v).slice(0, 11);
        if (d.length <= 0) return '';
        if (d.length <= 2) return '(' + d;
        if (d.length <= 6) return '(' + d.slice(0,2) + ') ' + d.slice(2);
        if (d.length <= 10) return '(' + d.slice(0,2) + ') ' + d.slice(2,6) + '-' + d.slice(6);
        return '(' + d.slice(0,2) + ') ' + d.slice(2,7) + '-' + d.slice(7);
    }

    function maskCep(v) {
        var d = onlyDigits(v).slice(0, 8);
        if (d.length <= 5) return d;
        return d.slice(0,5) + '-' + d.slice(5);
    }

    function applyMask(el, fn) {
        el.addEventListener('input', function () {
            var pos = this.selectionStart;
            var old = this.value;
            this.value = fn(this.value);
            var diff = this.value.length - old.length;
            try { this.setSelectionRange(pos + diff, pos + diff); } catch(e) {}
        });
        // Format existing value on init
        if (el.value) el.value = fn(el.value);
    }

    document.addEventListener('DOMContentLoaded', function () {
        document.querySelectorAll('.mask-cpf').forEach(function (el) { applyMask(el, maskCpf); });
        document.querySelectorAll('.mask-cnpj').forEach(function (el) { applyMask(el, maskCnpj); });
        document.querySelectorAll('.mask-phone').forEach(function (el) { applyMask(el, maskPhone); });
        document.querySelectorAll('.mask-cep:not(.cep-input)').forEach(function (el) { applyMask(el, maskCep); });
    });

    // Expose for testing / external use
    window.InputMasks = { maskCpf: maskCpf, maskCnpj: maskCnpj, maskPhone: maskPhone, maskCep: maskCep };
})();
