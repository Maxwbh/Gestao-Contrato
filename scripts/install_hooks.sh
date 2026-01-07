#!/bin/bash
#
# Instala os git hooks do projeto
#
# Desenvolvedor: Maxwell da Silva Oliveira
# Email: maxwbh@gmail.com
# LinkedIn: /maxwbh
# Empresa: M&S do Brasil LTDA - www.msbrasil.inf.br
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
GIT_HOOKS_DIR="$PROJECT_ROOT/.git/hooks"

echo "==> Instalando Git Hooks..."

# Criar diretorio de hooks se nao existir
mkdir -p "$GIT_HOOKS_DIR"

# Copiar hooks
cp "$SCRIPT_DIR/hooks/pre-commit" "$GIT_HOOKS_DIR/pre-commit"
cp "$SCRIPT_DIR/hooks/post-commit" "$GIT_HOOKS_DIR/post-commit"

# Tornar executaveis
chmod +x "$GIT_HOOKS_DIR/pre-commit"
chmod +x "$GIT_HOOKS_DIR/post-commit"

echo "==> Configurando autor padrao dos commits..."
cd "$PROJECT_ROOT"
git config user.name "Maxwell Oliveira"
git config user.email "maxwbh@gmail.com"

echo ""
echo "Git Hooks instalados com sucesso!"
echo ""
echo "Configuracao do autor:"
echo "  Nome: $(git config user.name)"
echo "  Email: $(git config user.email)"
echo ""
echo "Hooks ativos:"
echo "  - pre-commit: Incrementa a versao automaticamente"
echo "  - post-commit: Exibe informacoes do commit"
echo ""
