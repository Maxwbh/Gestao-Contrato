# Manual — Cadastro e Gestão de Usuários

> Para **administradores**. Explica como criar e gerenciar os usuários internos
> (funcionários de contabilidade/imobiliária). Compradores **não** são criados
> aqui — eles se cadastram sozinhos pelo Portal do Comprador (por CPF/CNPJ).

---

## Quem pode cadastrar usuários

Apenas **administradores** (usuários com o perfil *Administrador* ou
superusuários do sistema). Um usuário comum não vê o menu **Cadastros →
Usuários** e, se tentar abrir a tela pela URL, recebe *acesso negado* (o evento
fica registrado no Log de Auditoria).

## Os dois tipos de usuário

| | 👤 Comprador (portal) | 🧑‍💼 Usuário do Sistema (interno) |
|---|---|---|
| Como entra | Auto-cadastro no portal, por CPF/CNPJ | Criado por um administrador |
| Enxerga | Somente os próprios contratos | Os dados das imobiliárias a que tem acesso |
| Onde se cadastra | `/portal/` (fluxo próprio) | **Cadastros → Usuários → Novo usuário** |

---

## Passo a passo — cadastrar um usuário

Acesse **Cadastros → Usuários** e clique em **Novo usuário**.

![Tela de cadastro de usuário](screenshots/cadastro-usuario.png)

### 1. Dados do usuário
- **Nome** e **Sobrenome**.
- **E-mail** — será também o **login** do usuário. Precisa ser único; se já
  existir um usuário com esse e-mail, o cadastro é bloqueado.
- **Perfil de acesso** — o interruptor **Administrador**:
  - **Desligado** (padrão) → *Usuário comum*: só **opera** os módulos a que
    tem acesso.
  - **Ligado** → *Administrador*: além de operar, pode **cadastrar e gerenciar
    usuários** — sempre **limitado ao próprio escopo**.
- **Credencial de acesso** — duas formas:
  - **Senha inicial** (padrão): você define a senha aqui. O usuário será
    **obrigado a trocá-la no primeiro acesso**.
  - **Enviar convite por e-mail**: ligue o interruptor para não definir senha —
    o usuário recebe um link e define a própria senha (válido por 72h).

### 2. Acessos
Marque as **imobiliárias** que o usuário poderá acessar, agrupadas por
contabilidade. **Só aparecem as contabilidades e imobiliárias a que _você_ tem
acesso.** Para cada imobiliária marcada, defina as permissões:
- **Editar** — criar/alterar registros (marcado por padrão);
- **Excluir** — remover registros.

É obrigatório selecionar **pelo menos uma** imobiliária.

Clique em **Criar usuário**.

---

## Acompanhar e gerenciar

A lista de **Usuários** mostra o perfil e a situação de cada um.

![Lista de usuários](screenshots/usuarios-lista.png)

Situações possíveis:
- **Ativo** — pode usar o sistema normalmente.
- **Troca de senha pendente** — foi criado com senha inicial e ainda não trocou.
- **Convite pendente** — foi criado por convite e ainda não definiu a senha
  (é possível **reenviar o convite** pelo botão de ação).
- **Desativado** — sem acesso.

Ações disponíveis por linha:
- **Reenviar convite** (quando o convite ainda está pendente).
- **Desativar** — bloqueia o acesso do usuário (você não pode desativar a
  própria conta).

Para ajustar **quais imobiliárias** um usuário acessa depois de criado, use
**Cadastros → (Admin) Acessos de Usuários** — as opções também respeitam o seu
escopo.

---

## Perguntas frequentes

**Um usuário pode atender mais de uma contabilidade/imobiliária?**
Sim. Marque quantas imobiliárias quiser (de contabilidades diferentes) no bloco
de Acessos — desde que estejam no seu escopo.

**Qual a diferença entre "Administrador" e as permissões "Editar/Excluir"?**
São coisas independentes. **Administrador** diz *se a pessoa gerencia usuários*;
**Editar/Excluir** dizem *o que ela faz nos dados de cada imobiliária*.

**Esqueci de marcar "Administrador" / marquei por engano.**
Ajuste o perfil pelo Django Admin (superusuário) ou recadastre — em breve a
edição de perfil estará na própria tela de usuários.

**Referência técnica:** [HU-28](analise/historias-usuario/HU-28.md).
