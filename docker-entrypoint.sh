#!/bin/bash
# Entrypoint para BRCobranca API no Render
# Desenvolvedor: Maxwell da Silva Oliveira
# Empresa: M&S do Brasil LTDA
#
# Este script garante que o Puma inicie na porta correta
# O Render define a variavel PORT dinamicamente

set -e

# Usar porta do Render ou 9292 como fallback
PORT="${PORT:-9292}"

echo "=========================================="
echo "BRCobranca API - Iniciando..."
echo "Porta: $PORT"
echo "Ambiente: ${RACK_ENV:-development}"
echo "=========================================="

# Iniciar Puma na porta especificada
exec bundle exec puma -p "$PORT" -e "${RACK_ENV:-production}" config.ru
