# Política de Segurança

## Como reportar uma vulnerabilidade

Envie um e-mail para **maxwbh@gmail.com** com o assunto `[SECURITY]` descrevendo
o problema. Não abra issues públicas para falhas de segurança.

---

## Gestão de segredos

Este projeto **nunca** deve versionar credenciais reais. Toda configuração
sensível é lida de variáveis de ambiente ou do banco (`ParametroSistema`):

- **Infraestrutura** (`settings.py`): lida via `python-decouple` do arquivo
  `.env` (ignorado pelo Git) ou do painel do Render.
- **Operacional** (e-mail SMTP, Twilio, WhatsApp): armazenada em
  `ParametroSistema` / `ConfiguracaoEmail`, editável no Admin.

O arquivo `.env` está no `.gitignore`. Apenas `.env.example` (somente
placeholders) é versionado.

### Barreiras automáticas contra vazamento

| Camada | Onde | O que faz |
| --- | --- | --- |
| Local | `scripts/hooks/pre-commit` | Bloqueia o commit de arquivos `.env` e de valores literais atribuídos a chaves sensíveis (senha SMTP/IMAP, tokens, `SECRET_KEY`, chaves privadas). |
| CI | `tests/unit/test_security.py::test_nenhum_segredo_hardcoded_no_codigo` | Faz a mesma varredura em todos os arquivos versionados; falha o build se encontrar um segredo. |

Instale o hook local com:

```bash
bash scripts/install_hooks.sh
```

Falso positivo comprovado pode ser ignorado pontualmente com
`git commit --no-verify`.

---

## Remediação de um segredo exposto (ex.: alerta GitGuardian)

Se uma credencial for detectada como exposta, siga esta ordem. **A rotação é
obrigatória**: um segredo que já foi enviado a um repositório deve ser
considerado comprometido, mesmo após ser removido do código — o valor
permanece no histórico do Git e em caches externos.

### 1. Rotacionar a credencial (ação prioritária)

Para as **credenciais SMTP Zoho** (`EMAIL_HOST_PASSWORD`):

1. Acesse <https://accounts.zoho.com> → **Segurança → Senhas de aplicativo**.
2. **Revogue** a senha de aplicativo atual do e-mail de envio
   (`teste@msbrasil.inf.br`).
3. **Gere uma nova** senha de aplicativo.
4. Atualize o novo valor em:
   - **Render** → serviço `gestao-contrato-web` → **Environment** →
     `EMAIL_HOST_PASSWORD` (definido com `sync: false`, ou seja, manual).
   - **Admin** → *Gestão Principal → Parâmetros do Sistema* →
     `EMAIL_HOST_PASSWORD`, se estiver usando a camada operacional.
   - `.env` local, se aplicável.
5. Envie um e-mail de teste (`python manage.py testar_notificacoes`) para
   confirmar que o novo segredo funciona.

O mesmo procedimento vale para `BOUNCE_IMAP_PASSWORD`, `TWILIO_AUTH_TOKEN`,
`SECRET_KEY`, `TASK_TOKEN` e `GEMINI_API_KEY`.

### 2. Remover do código

Confirme que nenhum arquivo versionado contém o valor real:

```bash
git grep -nI "<valor-do-segredo>" $(git rev-list --all)
```

Substitua qualquer ocorrência por leitura de variável de ambiente e faça o
commit da correção.

### 3. Purgar do histórico (se o valor foi realmente commitado)

Se o segredo apareceu em algum commit, o valor continua acessível no histórico
mesmo após a correção. Reescreva o histórico com
[`git filter-repo`](https://github.com/newren/git-filter-repo):

```bash
git filter-repo --replace-text <(echo '<valor-do-segredo>==>REDACTED')
git push --force-with-lease --all
git push --force-with-lease --tags
```

> Reescrever o histórico é uma operação destrutiva e coordenada — avise a
> equipe antes e refaça os clones em seguida.

### 4. Fechar o alerta

Depois de rotacionar **e** remover/purgar, marque o alerta como resolvido no
GitGuardian. Nunca marque como resolvido apenas removendo o código sem
rotacionar: a credencial antiga continua válida até ser revogada no provedor.
