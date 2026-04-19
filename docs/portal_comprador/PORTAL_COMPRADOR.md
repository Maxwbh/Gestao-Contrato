# Portal do Comprador — Documentação Técnica

## Visão Geral

O Portal do Comprador é uma interface web mobile-first que permite aos compradores acompanhar seus contratos, visualizar e baixar boletos, consultar histórico de pagamentos e atualizar dados de contato — sem depender de atendimento presencial.

Um comprador pode ter **múltiplos contratos** simultâneos. Toda a navegação do portal é filtrada pelo comprador autenticado, exibindo todos os contratos e parcelas correspondentes.

---

## Arquitetura

```
portal_comprador/
├── models.py          # AcessoComprador, LogAcessoComprador
├── views.py           # 16 views + 4 endpoints de API
├── forms.py           # AutoCadastroForm, LoginCompradorForm,
│                      # DadosPessoaisForm, AlterarSenhaCompradorForm
├── urls.py            # 14 rotas /portal/...
└── admin.py           # Painel admin para gestão de acessos e logs

templates/portal_comprador/
├── portal_base.html   # Layout base com navbar topo + nav inferior
├── login.html
├── auto_cadastro.html
├── dashboard.html
├── meus_contratos.html
├── detalhe_contrato.html
├── meus_boletos.html
├── meus_dados.html
└── alterar_senha.html
```

### Modelos

#### `AcessoComprador`
Vínculo OneToOne entre `core.Comprador` e `auth.User`.

| Campo             | Tipo       | Descrição                                    |
|-------------------|------------|----------------------------------------------|
| `comprador`       | FK         | Comprador (pode ter N contratos)             |
| `usuario`         | FK         | Usuário Django para autenticação             |
| `ativo`           | bool       | `False` bloqueia login e acesso ao portal    |
| `email_verificado`| bool       | Reservado para verificação futura            |
| `token_verificacao`| char      | Token gerado para verificação de e-mail      |
| `ultimo_acesso`   | datetime   | Atualizado a cada login                      |

#### `LogAcessoComprador`
Histórico de acessos do comprador (IP, user-agent, página, timestamp).

---

## Autenticação

### Auto-cadastro (`/portal/cadastro/`)

1. Comprador informa CPF ou CNPJ e cria uma senha.
2. O sistema busca um `Comprador` com esse documento — se não encontrado, rejeita.
3. O e-mail informado deve coincidir com o e-mail cadastrado no contrato.
4. Se já existe `AcessoComprador` para esse comprador, redireciona para login.
5. Cria `User` com username `comprador_<documento>` e vincula via `AcessoComprador`.

### Login (`/portal/login/`)

- Autenticação via CPF/CNPJ + senha.
- **Campo `ativo`**: se `AcessoComprador.ativo = False`, o login é bloqueado mesmo com credenciais válidas. O admin desativa acessos pelo painel Django.
- Registra `LogAcessoComprador` e atualiza `ultimo_acesso` a cada login.

### Logout (`/portal/logout/`)

- Encerra a sessão Django e redireciona para login.

---

## Páginas do Portal

### Dashboard (`/portal/`)

Visão consolidada de **todos os contratos** do comprador:

- **KPIs**: total de contratos ativos, parcelas pagas, pendentes e vencidas (agregado)
- **Alerta de atraso**: banner vermelho se houver parcelas vencidas
- **Próximas parcelas**: até 5 parcelas a vencer nos próximos 30 dias
- **Em atraso**: até 10 parcelas vencidas mais antigas
- **Últimos pagamentos**: 5 últimas parcelas quitadas

Todos os agregados são feitos em uma única query com `aggregate()` — não há N+1.

### Meus Contratos (`/portal/contratos/`)

Lista **todos os contratos** do comprador, independentemente de status (ATIVO, QUITADO, CANCELADO, etc.), ordenados por data decrescente.

Cada card exibe:
- Número do contrato e identificação do imóvel
- Valor total
- Contagem de parcelas pagas / total (via `annotate()` — sem query extra por card)
- Barra de progresso (% quitado)
- Status com badge colorido
- Link para detalhe

> Um comprador com 3 contratos vê 3 cards — o portal é projetado para N contratos.

### Detalhe do Contrato (`/portal/contratos/<id>/`)

Exibe parcelas do contrato selecionado com:
- Estatísticas (total, pagas, pendentes, vencidas, valor pago, valor pendente)
- Lista de parcelas ordenada por número
- Prestações intermediárias (se existirem)
- Resumo financeiro (se disponível via `get_resumo_financeiro()`)
- Barra de progresso

Segurança: `get_object_or_404(..., comprador=comprador)` — garante que o comprador só acessa seus próprios contratos.

### Meus Boletos (`/portal/boletos/`)

Lista todas as parcelas de **todos os contratos** do comprador, com:

- **Filtros** por status: Todos / A pagar / Vencidos / Pagos
- **Filtro** por contrato (dropdown com todos os contratos do comprador)
- **Paginação**: 20 itens por página com navegação Anterior/Próxima
- **Botão de download**: aparece para qualquer boleto gerado (`tem_boleto = True`, i.e., `nosso_numero` preenchido e status ≠ `NAO_GERADO`) — inclui GERADO, REGISTRADO e VENCIDO

KPIs no topo: total / a pagar / vencidos / pagos (query única).

#### Download e Visualização de Boletos

| Rota | Comportamento |
|------|---------------|
| `GET /portal/boletos/<id>/download/` | Retorna PDF como `attachment` |
| `GET /portal/boletos/<id>/visualizar/` | Retorna PDF como `inline` |

Ambas as views verificam que a parcela pertence ao comprador autenticado antes de servir o arquivo.

### Meus Dados (`/portal/meus-dados/`)

Permite atualização de:
- Endereço de correspondência (CEP, logradouro, número, complemento, bairro, cidade, estado)
- E-mail, telefone, celular
- Preferências de notificação (e-mail, SMS, WhatsApp)

O campo **nome** é exibido como somente leitura — não pode ser alterado pelo comprador.

### Alterar Senha (`/portal/alterar-senha/`)

- Exige senha atual para confirmar identidade.
- Usa `update_session_auth_hash()` para manter a sessão ativa após troca.

---

## APIs JSON

Todas as APIs retornam `{"sucesso": true/false, ...}` e exigem autenticação (`@login_required`).

### `GET /portal/api/contratos/<id>/parcelas/`

Retorna parcelas de um contrato em JSON.

```json
{
  "sucesso": true,
  "parcelas": [
    {
      "id": 42,
      "numero_parcela": 3,
      "data_vencimento": "2025-03-05",
      "valor": 1664.47,
      "pago": false,
      "data_pagamento": null,
      "valor_pago": null,
      "dias_atraso": 0,
      "tem_boleto": true
    }
  ],
  "total": 120
}
```

### `GET /portal/api/resumo-financeiro/`

Resumo agregado de todas as parcelas do comprador.

```json
{
  "sucesso": true,
  "resumo": {
    "total": 120, "pagas": 10, "pendentes": 110, "vencidas": 2,
    "valor_total": 180000.0, "valor_pago": 16644.7,
    "valor_pendente": 163355.3, "valor_vencido": 3328.94
  }
}
```

### `GET /portal/api/vencimentos/` (P2)

Vencimentos pendentes/vencidos/a vencer com paginação e filtros.

**Parâmetros:**
| Param | Valores | Default |
|-------|---------|---------|
| `status` | `pendente`, `vencido`, `a_vencer`, `pago` | `pendente` |
| `data_inicio` | `YYYY-MM-DD` | — |
| `data_fim` | `YYYY-MM-DD` | — |
| `contrato` | ID do contrato | — |
| `page` | inteiro ≥ 1 | `1` |
| `per_page` | 1–100 | `50` |

Retorna `parcelas[]` com `dias_atraso`, `status_boleto`, `linha_digitavel`, `tem_boleto`.

### `GET /portal/api/boletos/` (P2)

Lista boletos gerados (exclui `NAO_GERADO`).

**Parâmetros:** `status_boleto` (GERADO/REGISTRADO/PAGO/VENCIDO/CANCELADO), `contrato`, `page`, `per_page`.

Retorna `boletos[]` com `nosso_numero`, `linha_digitavel`, `url_visualizar`, `url_download`.

### `POST /portal/api/boletos/<id>/segunda-via/` (P3)

Gera segunda via com juros/multa recalculados pela BRCobrança.

- **Rate limit**: 10 requisições por minuto por usuário.
- Rejeita parcela já paga ou sem `nosso_numero`.
- Retorna `nosso_numero`, `linha_digitavel`, `valor`, `vencimento`, `url_pdf`.

### `GET /portal/api/boletos/<id>/linha-digitavel/` (P3)

Retorna a linha digitável sem gerar nova via.

```json
{
  "sucesso": true,
  "parcela_id": 42,
  "numero_parcela": 3,
  "nosso_numero": "00000123456",
  "linha_digitavel": "12345.67890 ...",
  "codigo_barras": "...",
  "valor": 1664.47,
  "data_vencimento": "2025-03-05",
  "pago": false
}
```

---

## Segurança

| Mecanismo | Implementação |
|-----------|---------------|
| **Autenticação** | `@login_required(login_url='portal_comprador:login')` em todas as views |
| **Isolamento de dados** | Todas as queries filtram por `comprador` do usuário autenticado |
| **Acesso desativado** | `AcessoComprador.ativo=False` bloqueia login e retorna `None` em `get_comprador_from_request` |
| **Propriedade de objetos** | `get_object_or_404(..., comprador=comprador)` — 404 para acesso cruzado |
| **Rate limiting** | 10 req/min na API de segunda via (cache Django) |
| **Auditoria** | `LogAcessoComprador` registra IP, user-agent, página e timestamp |
| **Sessão pós-troca de senha** | `update_session_auth_hash()` mantém sessão ativa |

---

## Multi-Contratos

O portal é projetado para compradores com **qualquer número de contratos**:

- `meus_contratos`: lista todos os contratos via `Contrato.objects.filter(comprador=comprador)`.
- `meus_boletos`: agrega parcelas via `Parcela.objects.filter(contrato__comprador=comprador)` — abrange todos os contratos simultaneamente.
- Filtro por contrato em `meus_boletos` permite navegar entre contratos específicos.
- `dashboard`: KPIs consolidados de todos os contratos ativos.

**Não há limite** de contratos por comprador. O account (`AcessoComprador`) é único por comprador (OneToOne), mas o comprador pode ser vinculado a N contratos.

---

## Fluxo Completo

```
Comprador chega → /portal/cadastro/
     ↓ CPF/CNPJ + e-mail + senha
Busca Comprador no DB ← verifica CPF/CNPJ
     ↓ encontrado + e-mail confere
Cria User + AcessoComprador → login automático
     ↓
/portal/ (dashboard) ← KPIs de todos os contratos
     ↓ clica em "Meus Contratos"
/portal/contratos/ ← cards de cada contrato
     ↓ clica em "Detalhes"
/portal/contratos/<id>/ ← parcelas do contrato
     ↓ clica em "Meus Boletos"
/portal/boletos/ ← todos os boletos, filtros, paginação
     ↓ clica em "Boleto" (botão download)
/portal/boletos/<id>/download/ ← PDF
```

---

## Configuração no Admin Django

### Ativar/Desativar Acesso

`/admin/portal_comprador/acessocomprador/` → editar → campo **Ativo**.

Com `ativo=False` o comprador não consegue fazer login. A conta pode ser reativada a qualquer momento.

### Ver Logs de Acesso

`/admin/portal_comprador/logacessocomprador/` — filtros por data, comprador e página acessada.

---

## URLs

```
/portal/                               dashboard
/portal/cadastro/                      auto-cadastro
/portal/login/                         login
/portal/logout/                        logout
/portal/contratos/                     lista de contratos (todos, N contratos)
/portal/contratos/<id>/                detalhe de um contrato
/portal/boletos/                       lista de boletos (todos os contratos, paginado)
/portal/boletos/<id>/download/         download PDF
/portal/boletos/<id>/visualizar/       visualização inline PDF
/portal/meus-dados/                    editar dados pessoais
/portal/alterar-senha/                 trocar senha
/portal/api/contratos/<id>/parcelas/   JSON parcelas de um contrato
/portal/api/resumo-financeiro/         JSON resumo agregado
/portal/api/vencimentos/               JSON vencimentos com filtros (P2)
/portal/api/boletos/                   JSON boletos gerados com filtros (P2)
/portal/api/boletos/<id>/segunda-via/  POST gerar segunda via (P3, rate-limited)
/portal/api/boletos/<id>/linha-digitavel/  GET linha digitável (P3)
```

---

## Stack do Frontend

- **CSS**: Materialize CSS 1.0.0 (teal como cor primária: `#00897b`)
- **Ícones**: Font Awesome 6 + Material Icons
- **Layout**: mobile-first, navbar fixa no topo + bottom navigation de 4 itens
- **Sem JavaScript pesado**: formulários são HTML puro; APIs consumidas opcionalmente

---

## Testes

Cobertura em `tests/unit/portal_comprador/` e `tests/integration/`:

| Arquivo | O que testa |
|---------|-------------|
| `test_models.py` | `AcessoComprador`, `LogAcessoComprador` |
| `test_auth.py` | Login, logout, auto-cadastro, flag `ativo`, helpers |
| `test_views.py` | Dashboard, contratos, boletos, dados, senha |
| `test_api.py` | APIs P1/P2/P3: parcelas, resumo, vencimentos, boletos, linha-digitável |
| `test_portal_comprador.py` | Integração: fluxo login → dashboard → contratos |
