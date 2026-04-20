# Portal do Comprador — Guia do Usuário

**Sistema:** Gestão de Contratos — M&S do Brasil LTDA
**Última atualização:** 2026-04-20

> Este guia é destinado ao **comprador** (cliente final) que deseja acessar o portal para
> consultar seus contratos, baixar boletos e atualizar seus dados.

---

## O que é o Portal do Comprador?

O Portal do Comprador é um ambiente online exclusivo onde você pode:

- Consultar todos os seus contratos de compra de imóvel
- Ver o andamento dos pagamentos e o saldo devedor
- Baixar ou visualizar seus boletos
- Registrar pagamentos e ver o histórico
- Atualizar seus dados de contato e endereço
- Configurar como quer receber notificações (e-mail, SMS, WhatsApp)

---

## Como Acessar

### URL de acesso

```
https://gestao-contrato-web-mt6j.onrender.com/portal/
```

> O portal funciona em qualquer navegador (Chrome, Firefox, Safari, Edge) e é otimizado
> para celular (mobile-first).

---

## Primeiro Acesso — Criar sua Conta

### Pré-requisito

Você precisa ter um contrato cadastrado na imobiliária com seu **CPF ou CNPJ** e o **e-mail
que forneceu no momento da compra**.

### Passo a passo

1. Acesse `/portal/cadastro/`
2. Informe seu **CPF ou CNPJ** (com ou sem pontuação)
3. Informe o **e-mail** cadastrado no contrato
4. Crie uma **senha** (mínimo 8 caracteres)
5. Confirme a senha
6. Clique em **"Criar Conta"**

> Se seu CPF/CNPJ ou e-mail não for encontrado, entre em contato com a imobiliária para
> confirmar os dados cadastrados.

---

## Login (Acessos Seguintes)

### URL de login

```
https://gestao-contrato-web-mt6j.onrender.com/portal/login/
```

### Credenciais

| Campo    | O que informar                                      |
|----------|-----------------------------------------------------|
| CPF/CNPJ | Seu documento (com ou sem pontuação)                |
| Senha    | A senha que você cadastrou                          |

> Após 5 tentativas erradas seguidas, aguarde 1 minuto antes de tentar novamente.

---

## Esqueci Minha Senha

1. Acesse `/portal/esqueci-senha/`
2. Informe seu **CPF ou CNPJ**
3. Clique em **"Enviar Instruções"**
4. Verifique seu e-mail — você receberá um link de redefinição
5. Clique no link (válido por **1 hora**) e crie uma nova senha

---

## Telas do Portal

### Dashboard (Página Inicial)

**URL:** `/portal/`

A primeira tela após o login. Exibe um resumo consolidado de todos os seus contratos:

| Seção                  | O que mostra                                                         |
|------------------------|----------------------------------------------------------------------|
| **Alerta de atraso**   | Banner vermelho se houver parcelas vencidas — aparece no topo        |
| **Resumo (4 cards)**   | Total de contratos · Parcelas pagas · Pendentes · Vencidas           |
| **Próximas parcelas**  | Parcelas vencendo nos próximos 30 dias (até 5 itens)                 |
| **Em atraso**          | Parcelas vencidas não pagas (até 10 itens)                           |
| **Últimos pagamentos** | Últimas 5 parcelas pagas                                             |

---

### Meus Contratos

**URL:** `/portal/contratos/`

Lista todos os contratos vinculados ao seu CPF/CNPJ:

| Informação exibida       | Descrição                                                  |
|--------------------------|------------------------------------------------------------|
| Número do contrato       | Identificador único do contrato                            |
| Imóvel                   | Identificação do lote/imóvel (ex: "Lote 10 Quadra A")      |
| Valor total              | Valor total do contrato                                    |
| Progresso                | Barra visual mostrando % de parcelas pagas                 |
| Status                   | Ativo / Quitado / Cancelado / Suspenso                     |
| Imobiliária              | Nome da empresa responsável                                |
| Botão "Detalhes"         | Abre a tela de detalhe do contrato                         |

---

### Detalhe do Contrato

**URL:** `/portal/contratos/<número>/`

Tela completa de um contrato específico:

| Seção                    | O que mostra                                               |
|--------------------------|------------------------------------------------------------|
| **Cabeçalho**            | Número do contrato e imóvel                                |
| **Progresso**            | % concluído (parcelas pagas / total)                       |
| **Resumo (3 cards)**     | Pagas · Pendentes · Vencidas                               |
| **Resumo Financeiro**    | Valor total · Entrada · Já pago · Saldo devedor            |
| **Lista de Parcelas**    | Todas as parcelas com status e data de vencimento/pagamento |

#### Status das Parcelas

| Ícone / Cor     | Status     | Significado                              |
|-----------------|------------|------------------------------------------|
| ✓ Verde         | Pago       | Pagamento confirmado                     |
| ! Vermelho      | Vencida    | Em atraso — acumulando juros e multa     |
| 🕐 Cinza        | Em aberto  | Dentro do prazo, aguardando pagamento    |

---

### Meus Boletos

**URL:** `/portal/boletos/`

Lista todos os boletos filtráveis por status:

#### Filtros disponíveis

| Filtro     | O que mostra                                               |
|------------|------------------------------------------------------------|
| **Todos**  | Todas as parcelas (pagas e não pagas)                      |
| **A pagar**| Parcelas não pagas com vencimento futuro                   |
| **Vencidos**| Parcelas não pagas com vencimento passado                 |
| **Pagos**  | Apenas parcelas já quitadas                                |

#### Paginação

20 boletos por página. Use os botões **"< Anterior"** e **"Próxima >"** para navegar.

#### Ações por boleto

| Botão             | O que faz                                      |
|-------------------|------------------------------------------------|
| **Boleto**        | Faz o download do PDF do boleto                |
| **Quitado** (✓)   | Indica que a parcela já foi paga (sem ação)    |

---

### Download de Boleto

**URL:** `/portal/boletos/<id>/download/`

Baixa o PDF do boleto diretamente para o seu dispositivo.

> **Atenção:** o PDF do boleto é gerado pela imobiliária. Se o botão de download não aparecer,
> entre em contato com a imobiliária para solicitar a geração do boleto.

---

### Visualizar Boleto (online)

**URL:** `/portal/boletos/<id>/visualizar/`

Exibe o boleto diretamente no navegador (sem fazer download).

---

### Meus Dados

**URL:** `/portal/meus-dados/`

Tela de perfil. Permite atualizar suas informações de contato:

#### O que pode ser editado

| Campo                | Editável? | Observação                              |
|----------------------|-----------|-----------------------------------------|
| Nome                 | ❌ Não    | Alterado somente pela imobiliária       |
| CPF / CNPJ           | ❌ Não    | Documento imutável                      |
| CEP                  | ✅ Sim    | Preenchimento automático de endereço    |
| Endereço completo    | ✅ Sim    | Logradouro, número, bairro, cidade, UF  |
| E-mail               | ✅ Sim    | E-mail de contato                       |
| Telefone             | ✅ Sim    | Telefone fixo                           |
| Celular              | ✅ Sim    | Número de celular                       |
| Notificar por E-mail | ✅ Sim    | Receber alertas por e-mail              |
| Notificar por SMS    | ✅ Sim    | Receber alertas por SMS                 |
| Notificar por WhatsApp | ✅ Sim  | Receber alertas por WhatsApp            |

Após preencher, clique em **"Salvar Alterações"**.

#### Alterar senha

Na mesma tela, clique em **"Alterar >"** para ir à tela de troca de senha.

---

### Alterar Senha

**URL:** `/portal/alterar-senha/`

| Campo              | O que informar            |
|--------------------|---------------------------|
| Senha Atual        | Sua senha de acesso atual |
| Nova Senha         | Nova senha (mín. 8 chars) |
| Confirmar          | Repetir a nova senha      |

Clique em **"Confirmar Alteração"**. Você permanecerá logado após a troca.

---

### Sair do Portal (Logout)

**URL:** `/portal/logout/`

Clique em **"Sair do Portal"** na tela **Meus Dados** ou acesse a URL diretamente.
Você será redirecionado para a tela de login.

---

## Resumo de Todas as Telas

| Tela                  | URL                                    | Acesso         |
|-----------------------|----------------------------------------|----------------|
| Login                 | `/portal/login/`                       | Público        |
| Criar conta           | `/portal/cadastro/`                    | Público        |
| Esqueci minha senha   | `/portal/esqueci-senha/`              | Público        |
| Redefinir senha       | `/portal/redefinir-senha/<token>/`    | Link por e-mail |
| Dashboard             | `/portal/`                             | Login obrigatório |
| Meus Contratos        | `/portal/contratos/`                   | Login obrigatório |
| Detalhe do Contrato   | `/portal/contratos/<id>/`             | Login obrigatório |
| Meus Boletos          | `/portal/boletos/`                     | Login obrigatório |
| Download do Boleto    | `/portal/boletos/<id>/download/`      | Login obrigatório |
| Visualizar Boleto     | `/portal/boletos/<id>/visualizar/`    | Login obrigatório |
| Meus Dados            | `/portal/meus-dados/`                  | Login obrigatório |
| Alterar Senha         | `/portal/alterar-senha/`              | Login obrigatório |
| Sair                  | `/portal/logout/`                      | Login obrigatório |

---

## Dúvidas Frequentes

**Por que não consigo criar minha conta?**
Seu CPF/CNPJ ou e-mail pode não corresponder ao cadastrado no contrato. Entre em contato com a imobiliária.

**Não recebi o e-mail de redefinição de senha. O que fazer?**
Verifique a pasta de spam/lixo eletrônico. O link expira em 1 hora. Se necessário, repita o processo.

**O botão de download do boleto não aparece.**
O boleto ainda não foi gerado pela imobiliária. Entre em contato para solicitar.

**Como atualizo meu número de WhatsApp para receber notificações?**
Acesse **Meus Dados**, atualize o campo **Celular** e marque **"Notificar por WhatsApp"**.

**Meu contrato aparece como "Suspenso". O que significa?**
O contrato está temporariamente paralisado. Entre em contato com a imobiliária para esclarecimentos.

**Posso acessar o portal pelo celular?**
Sim. O portal é otimizado para dispositivos móveis (mobile-first). Funciona em qualquer navegador de celular.

---

## Contato com a Imobiliária

Para questões relacionadas ao contrato, boletos ou cadastro, entre em contato diretamente com
a imobiliária responsável pelo seu contrato.
