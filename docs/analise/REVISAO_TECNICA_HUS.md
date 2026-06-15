# Revisão Técnica Completa das Histórias de Usuário (HU-01 … HU-24)

> Revisão consolidada das 24 HUs do Sistema de Gestão de Contratos.
> Foco em **detalhes técnicos** (regras, fórmulas, estados, validações, fluxos),
> **sem referência a tecnologias** (linguagens, frameworks, bancos de dados) nem a
> **estilos/bibliotecas visuais**. Onde aplicável, cada HU traz *Observações da Revisão*
> (consistências, riscos e lacunas).
>
> Convenções: "registro" = entidade persistida; "serviço" = componente de regra de
> negócio reutilizável; "rota" = ponto de entrada da aplicação; "provedor de mensagens" =
> canal externo de e-mail/SMS/conversa; "gerador de documento" = produção de arquivo
> imprimível.
>
> **Serviço de boletos = BRCobrança.** O componente externo que produz o título (código de
> barras, linha digitável, pagamento instantâneo, documento imprimível) e também lê o extrato
> bancário é o **BRCobrança**. Onde o texto diz "serviço de boletos"/"serviço de registro",
> leia **BRCobrança**. Importante: o BRCobrança **gera** o boleto, mas **não o registra** no
> banco — o registro continua sendo feito pelo arquivo de remessa bancária (HU-23).

---

## Visão Geral do Domínio

| Entidade | Papel |
|----------|-------|
| Contabilidade | Agrupa várias imobiliárias |
| Imobiliária | Beneficiária financeira dos contratos; dona das contas bancárias |
| Imóvel | Lote/terreno/casa/apartamento/comercial, com coordenadas opcionais |
| Comprador | Pessoa física ou jurídica adquirente |
| Contrato | Até 360 parcelas, até 30 intermediárias, reajuste e amortização configuráveis |
| Parcela | Unidade de cobrança mensal, com ciclo de reajuste e estado de boleto |
| Prestação Intermediária | Reforço/aporte fora do fluxo mensal, materializável em parcela |
| Conta Bancária | Dados de emissão/registro do título (convênio, agência, carteira, layout) |

**Ciclo macro da operação:** criar contrato → gerar parcelas → gerar boletos → cobrar
(link público, segunda via, notificações, atendimento) → conciliar pagamentos (manual,
extrato, retorno bancário) → reajustar anualmente → encerrar (quitação, rescisão, cessão).

---

## APIs e Serviços Externos

As integrações externas a seguir são **identificadas explicitamente** nesta revisão (exceção
deliberada à regra de não citar tecnologias), por serem dependências operacionais do sistema:

| Serviço | Uso | Observações | HUs |
|---------|-----|-------------|-----|
| **Banco Central do Brasil — API** | Índices econômicos (IPCA, IGP-M, SELIC, e demais) | Fonte oficial dos números-índice e variações usados no reajuste | HU-05, HU-15 |
| **BRCobrança — API** | Geração de boletos e arquivos CNAB; leitura de extrato | Auto-hospedado em contêiner (Docker self-hosted). **Gera** o boleto e produz o layout de remessa, mas **não registra** no banco — o registro é feito pelo envio do arquivo de remessa (HU-23). Pode ter inicialização lenta quando ocioso (tratada com espera/retentativa) | HU-03, HU-07, HU-08, HU-10, HU-14, HU-16, HU-23, HU-24 |
| **Twilio** | Envio de SMS e mensagens de WhatsApp | Provedor de mensagens; telefones normalizados ao padrão internacional antes do envio | HU-19, HU-20 |
| **cron-job.org** | Agendador de tarefas via chamadas HTTP | Substitui processos de segundo plano (Celery) no plano gratuito de hospedagem, que não mantém *workers*. Aciona os pontos de entrada de notificação/cobrança | HU-20 |
| **SMTP** | Envio de e-mail | Canal de e-mail das notificações, cobranças e avisos internos | HU-03, HU-19, HU-20, HU-24 |

> Demais fontes auxiliares (consulta de CEP, consulta de cadastro de pessoa jurídica) existem no
> sistema, mas não são centrais ao fluxo financeiro coberto por estas HUs.

---

## HU-01 — Criação de Contrato (Assistente Guiado)

**Objetivo:** cadastrar um contrato em etapas (`básico → juros → intermediárias → preview`),
persistindo tudo em uma única operação atômica.

**Mecânica técnica:**
- Dados intermediários ficam em estado de sessão entre etapas; nada é persistido até o passo final.
- Validações de entrada: número de contrato único por imobiliária; entrada estritamente menor
  que o valor total; número de parcelas entre 1 e 360; dia de vencimento 1–31; prazo de
  reajuste 1–120 (padrão 12); soma das intermediárias ≤ 80% do valor financiado.
- Tabela de juros escalante por ciclo (linhas `ciclo_início`, `ciclo_fim`, `juros_mensal`);
  etapa opcional — sem ela, opera em modo simples.
- Cálculo de amortização:
  - **Sistema de prestação constante:** `PMT = PV × i / (1 − (1+i)^−n)`, com `i = taxa_mensal/100`.
  - **Sistema de amortização constante:** `amortização = PV/n`; prestação decrescente.
- Ciclo de cada parcela: `ciclo = (número_da_parcela − 1) ÷ prazo_reajuste + 1`.
- Operação final, atômica e indivisível: cria contrato + tabela de juros + intermediárias +
  gera parcelas + recalcula amortização. Falha em qualquer passo reverte tudo.

**Observações da Revisão:**
- Boa separação preview × commit: o passo de pré-visualização nunca persiste.
- Risco controlado: a atomicidade evita contratos "meio-criados" sem parcelas.
- Lacuna potencial: a regra de 80% das intermediárias depende de o valor financiado já estar
  definido na etapa básica — confirmar a ordem de validação quando o usuário volta etapas.

---

## HU-02 — Geração de Parcelas

**Objetivo:** materializar o cronograma financeiro completo do contrato.

**Mecânica técnica:**
- Gera exatamente `número_de_parcelas` registros do tipo NORMAL; adiciona 1 registro ENTRADA
  se houver valor de entrada; cria 1 registro INTERMEDIARIA por prestação configurada.
- Vencimentos avançam mês a mês a partir do primeiro vencimento, com **ajuste para meses curtos**
  (ex.: vencimento 31 cai para o último dia em fevereiro).
- Cada parcela nasce com `pago = falso`, estado de boleto `não gerado`, `valor_original = valor_atual`
  e identificador público próprio.
- `completar_parcelas_faltantes()` cria apenas as ausentes (verifica o maior número existente),
  nunca duplicando — suporta carga incremental (`gerar até o mês atual`).

**Observações da Revisão:**
- A idempotência de "completar faltantes" é o ponto crítico e está coberta por verificação
  do maior número de parcela existente.
- Conferir tolerância de R$ 0,01 na soma (NORMAL + entrada = total) para arredondamentos de prestação.

---

## HU-03 — Gerar Boleto Individual

**Objetivo:** emitir o título de uma parcela (código de barras, linha digitável, pagamento instantâneo).

**Mecânica técnica:**
- Pré-checagens: parcela não paga; **bloqueio por reajuste** (HU-06) salvo modo forçado;
  se já existe boleto e não é forçado, retorna o existente sem reemitir.
- Após sucesso, a parcela recebe: número de controle (em três formas para conciliação),
  código de barras, linha digitável, número do documento, documento imprimível em
  **armazenamento de arquivo e em armazenamento binário** (este garante recuperação mesmo em
  ambiente de armazenamento volátil), dados de pagamento instantâneo, estado `gerado` e data de geração.
- Notificação ao comprador é agendada de forma assíncrona (não bloqueia a resposta).
- Rotas auxiliares: consultar estado, cancelar (com motivo, estado → `cancelado`), baixar
  documento, visualizar página.
- Mapeamento de campos por instituição (convênio/carteira/posto/variação conforme o banco).

**Observações da Revisão:**
- O título e seus dados são produzidos pelo **BRCobrança** (serviço de boletos externo).
- O duplo armazenamento (arquivo + binário) é uma decisão acertada para ambientes efêmeros.
- A regra "já existe → retorna existente" evita consumo desnecessário do BRCobrança.
- A inicialização lenta do BRCobrança (quando ocioso) é tratada com espera/retentativa na
  geração, de modo que a primeira chamada do período não falhe por indisponibilidade temporária.
- Verificar que o cancelamento não invalide conciliações já realizadas.

---

## HU-04 — Pagamento de Parcela

**Objetivo:** registrar pagamento com encargos corretos e, quando aplicável, quitar o contrato.

**Mecânica técnica:**
- Cálculo de encargos por data de referência:
  - No prazo → juros e multa zero.
  - Em atraso → `multa = valor_atual × %multa/100` (uma vez) e
    `juros = valor_atual × (%juros_mora/100) × (dias_atraso/30)` (proporcional aos dias).
  - Desconto disponível se `vencimento − dias_desconto ≤ hoje ≤ vencimento`.
  - Total = `valor_atual − desconto + juros + multa`.
- Validação: data de pagamento não pode ser futura.
- Registra histórico de pagamento (origem manual); marca parcela paga e boleto `pago`.
- **Quitação automática:** quando todas as parcelas NORMAL + INTERMEDIARIA estão pagas, o
  contrato passa a `quitado` (parcelas de ENTRADA não bloqueiam a quitação).
- Reversão de pagamento cria histórico com valor negativo, preservando a trilha original.

**Observações da Revisão:**
- A reversão por compensação (valor negativo) preserva auditoria — correto.
- Confirmar que a verificação de quitação ocorre sempre após o registro e considera intermediárias.

---

## HU-05 — Reajuste de Parcelas

**Objetivo:** aplicar a correção econômica anual conforme o índice contratado.

**Mecânica técnica:**
- Os índices (IPCA, IGP-M, SELIC e demais) provêm da **API do Banco Central do Brasil**,
  importados pela HU-15; o reajuste consome esses números-índice/variações já cadastrados.
- Pré-visualização não persiste; aplicação ocorre em operação atômica.
- Período de referência: `início = data_contrato + (ciclo−2)×prazo + 1 mês`;
  `fim = data_contrato + (ciclo−1)×prazo`.
- Percentual:
  - Método 1 (prioritário): `% = número_índice_fim / número_índice_base − 1`.
  - Método 2 (alternativa): produto das variações mensais `∏(1 + valor_k/100) − 1`.
  - Aplica, em ordem: spread → desconto → piso → teto.
- Modos de aplicação:
  - **Simples:** `novo_valor = valor_atual × (1 + %final/100)`.
  - **Prestação constante:** atualiza o saldo (`saldo × (1 + %bruto/100)`) e recalcula a
    prestação para as parcelas restantes.
- Sequência obrigatória de ciclos (não pula); fallback de índice quando o principal falha.
- **Detecção antecipada:** o contrato aparece como pendente 1 mês antes do aniversário (por
  mês, não por dia). Há grid de pendentes com aprovação/edição individual e aplicação em lote
  (calculado ou informado).
- Após aplicar: avança o ciclo atual e regenera boletos já emitidos do ciclo com o novo valor.
- Registro de reajuste guarda snapshot dos parâmetros (spread/piso/teto) e auditoria (usuário, origem, data).

**Observações da Revisão:**
- Preferir o Método 1 (número-índice) é tecnicamente mais preciso que o produto de variações.
- A regeneração automática de boletos do ciclo é essencial para coerência com HU-06.
- Risco: aplicação em lote "informado" deve registrar claramente que o percentual foi manual.

---

## HU-06 — Bloqueio de Boleto por Reajuste

**Objetivo:** impedir emissão de cobrança com valor desatualizado.

**Mecânica técnica:**
- Função de elegibilidade retorna `(permitido, motivo)` antes de qualquer emissão.
- Cascata: para uma parcela no ciclo N, verifica ciclos 2..N:
  - se `hoje < vencimento_do_ciclo` → interrompe e libera (período ainda futuro);
  - se há reajuste aplicado do ciclo → avança;
  - caso contrário → bloqueia com "Reajuste do ciclo k pendente".
- Vencimento do ciclo: `data_contrato + (ciclo−1) × prazo`.
- Ciclo 1 e correção fixa nunca bloqueiam. Quitação manual e conciliação por extrato ignoram o bloqueio.
- Modo forçado (uso administrativo) ignora o bloqueio.

**Observações da Revisão:**
- A cascata cobre o caso de múltiplos ciclos vencidos acumulados — correto.
- Consistência verificada com HU-03, HU-07 e HU-24, todos consultando a mesma função.

---

## HU-07 — Gerar Carnê (Lote de Boletos)

**Objetivo:** produzir um conjunto de boletos de um contrato de uma vez (documento consolidado + individuais).

**Mecânica técnica:**
- Seleção: próximas N parcelas não pagas (padrão 20; alternativa 6), ordenadas por vencimento.
- Cada parcela passa pelo bloqueio por reajuste; se uma estiver bloqueada, aborta com motivo claro.
- Emissão em lotes de 15 por chamada ao **BRCobrança** (limite para evitar estouro de tempo).
- **Tolerância a falha parcial:** falha individual não derruba o lote; erros são reportados.
- Saídas: documento consolidado para impressão e pacote com documentos individuais; também há
  consolidação de múltiplos contratos.
- Quando restam menos que N, gera só as disponíveis (sem erro). Aviso informativo (não bloqueante)
  quando o reajuste está próximo.

**Observações da Revisão (achado 07×24 — revisado contra o código):**
- A especificação sugeria que o carnê **aborta** ao encontrar bloqueio; na prática o código já é
  **tolerante** (conta os bloqueados e segue com os demais). A divergência real frente à HU-24 não
  é "abortar vs. seguir", e sim o **mecanismo de bloqueio**:
  - **HU-24** consulta `contrato.pode_gerar_boleto(numero_parcela)` por parcela (fonte canônica).
  - **HU-07 (carnê)** usa um **corte por ciclo** próprio (`max_parcela_lote`), mais restritivo:
    bloqueia parcelas de **ciclos futuros** no lote (só permite individualmente), mesmo quando o
    `pode_gerar_boleto()` as liberaria por ainda não terem vencido.
- **Melhoria recomendada (decisão: unificar):** o carnê deve passar a usar
  `contrato.pode_gerar_boleto()` por parcela como **fonte única de verdade** do bloqueio por
  reajuste (mesma regra da HU-24), padronizando inclusive a mensagem ("Reajuste do ciclo N
  pendente"). Efeito: parcelas de ciclos futuros ainda não vencidos passam a ser permitidas no
  lote do carnê; bloqueia-se apenas o reajuste efetivamente pendente. Remove a heurística
  duplicada `max_parcela_lote` e elimina o risco de duas definições de "elegível" divergirem.
- *Esta é uma recomendação de revisão; a implementação no código foi mantida fora do escopo desta
  rodada (somente documentação).*

---

## HU-08 — Segunda Via de Boleto

**Objetivo:** emitir via atualizada com encargos calculados para o dia.

**Mecânica técnica:**
- Pré-visualização exibe valor, juros e multa de hoje; emissão produz documento **fresco** via
  **BRCobrança** com os encargos recalculados — não reutiliza o documento armazenado.
- Fórmulas idênticas à HU-04 (juros proporcionais aos dias; multa única; zero se no prazo).
- Não altera o estado do boleto nem sobrescreve o documento original; reutiliza o número de
  controle existente (preserva a conciliação).
- Parcela paga → redireciona com aviso; data de referência é sempre o dia atual.

**Observações da Revisão:**
- Manter o número de controle original na segunda via é o ponto crítico para conciliação — coberto.

---

## HU-09 — Quitação Manual / Simulador de Antecipação

**Objetivo:** simular e registrar quitação antecipada com desconto, gerando recibo.

**Mecânica técnica:**
- Pré-visualização (sem persistir) lista parcelas NORMAL não pagas, aplica desconto (% ou valor)
  e calcula valor final por parcela e total.
- Aplicação: cria histórico (origem manual, marcado como antecipado), aplica desconto sobre o
  valor atual, marca paga; gera documento de recibo (partes, parcelas, desconto, valor, assinaturas).
- Desconto nunca pode superar o valor da parcela; só parcelas NORMAL entram; **não** sofre bloqueio
  por reajuste; quita o contrato se todas as NORMAL forem pagas.

**Observações da Revisão:**
- Tratamento de intermediárias é separado — coerente com HU-14.
- Validar a borda "desconto = valor da parcela" (valor final zero) como caso permitido ou não.

---

## HU-10 — Quitação via Extrato Bancário

**Objetivo:** conciliar pagamentos em massa a partir do extrato, com deduplicação.

**Mecânica técnica:**
- A leitura do extrato é feita pelo **BRCobrança**, com **alternativa interna** quando o
  BRCobrança está indisponível — o processamento nunca para por falha externa.
- Conciliação por prioridade: (1) número de controle no descritivo; (2) número de contrato no
  descritivo; (3) valor exato ± R$ 0,10 dentro de janela de ±5 dias do vencimento; (4) sem match
  → fila de conciliação manual.
- Cada match cria histórico (origem extrato) com identificador único da transação.
- **Idempotência:** identificador de transação único — reimportar o mesmo extrato não duplica.
- Apenas créditos viram pagamento; débitos são ignorados. Empate (duas parcelas, mesmo valor,
  mesma semana) → não concilia automaticamente, vai para revisão. Arquivo inválido → erro sem efeito.

**Observações da Revisão:**
- A alternativa interna de leitura (quando o BRCobrança falha) é uma boa proteção de continuidade.
- A regra de empate evita baixas erradas — correta para operação financeira.

---

## HU-11 — Cálculo de Rescisão

**Objetivo:** calcular valor a devolver ao comprador na rescisão, com detalhamento.

**Mecânica técnica:**
- Detalhamento: total pago (entrada + parcelas + intermediárias) vs. retenções.
- Retenções sobre o saldo devedor:
  - `fruição = saldo × %fruição/100 × meses_ocupados`
  - `multa_penal = saldo × %multa_penal/100`
  - `despesas_adm = saldo × %adm/100`
- `meses_ocupados = (ano_rescisão − ano_contrato)×12 + (mês_rescisão − mês_contrato)`.
- `devolução = max(0, total_pago − total_retenções)` (nunca negativa).
- Saldo devedor difere por amortização (prestação constante: soma dos valores atuais não pagos;
  amortização constante: soma das amortizações).
- Cálculo é **apenas informativo** — não altera o contrato; o resultado permanece visível
  (sem desaparecer) e a ação de calcular não pede confirmação.

**Observações da Revisão (verificado contra o código):**
- **Saldo devedor já reutiliza a função canônica** `Contrato.calcular_saldo_devedor()` — sem
  duplicação de fórmula. ✅
- Há tratamento legal adicional embutido: limite de retenção (pena convencional ≤ 25% do total
  pago) com alerta e cálculo de devolução alternativo conforme esse teto — bom ponto de conformidade.
- Bom: persistência visual do resultado e ausência de efeito colateral.
- Confirmar arredondamento e exibição quando retenções superam o pago (devolução zero + aviso).

---

## HU-12 — Cálculo de Cessão de Direitos

**Objetivo:** calcular a taxa de transferência do contrato a terceiros.

**Mecânica técnica:**
- `taxa_cessão = saldo_devedor × %cessão/100` (percentual padrão 3%, configurável por contrato).
- Saldo devedor pelo mesmo critério da rescisão (por tipo de amortização).
- Data de referência opcional (padrão hoje); considera parcelas com vencimento posterior à data.
- **Apenas informativo** — não gera cobrança nem altera estado.

**Observações da Revisão (verificado contra o código):**
- **Reaproveita corretamente** a mesma função canônica `Contrato.calcular_saldo_devedor()` da
  HU-11 — consistência boa, fórmula única. ✅

---

## HU-13 — Link Público de Boleto

**Objetivo:** acesso do comprador ao boleto por link opaco, sem autenticação.

**Mecânica técnica:**
- Cada parcela tem identificador público opaco, único e imutável após criação; link no formato
  `/b/<identificador>/`, sem expor identificadores internos, nome do sistema ou dados sensíveis.
- Acesso sem credencial retorna a página; identificador inválido retorna "não encontrado".
- A página **exibe**: imobiliária (nome/logo), nome do comprador, parcela, vencimento, valor (com
  juros recalculados em tempo real se vencida), linha digitável, pagamento instantâneo, download.
- A página **não exibe**: documento do comprador, dados bancários, identificadores internos, ações administrativas.
- Download serve o documento priorizando o **armazenamento binário** (resiliente a ambiente
  efêmero) e recorrendo ao armazenamento em arquivo; sem documento → "não encontrado".
- Compartilhamento interno via recurso nativo do dispositivo ou cópia para a área de transferência.

**Observações da Revisão:**
- Privacidade (documento do comprador nunca no conteúdo público) é regra global — verificada por teste de conteúdo.
- O token não expira: avaliar se isso é aceitável do ponto de vista de exposição de longo prazo
  (possível evolução: expiração/rotação opcional — já existe rotação em outro fluxo de geração).

---

## HU-14 — Gestão de Prestações Intermediárias

**Objetivo:** administrar intermediárias após a criação do contrato (criar, editar, excluir, pagar, emitir).

**Mecânica técnica:**
- Operações retornam resposta estruturada. Criar valida a regra dos 80% do valor financiado.
- Editar/excluir só são permitidos enquanto **não paga**.
- Pagar cria histórico (origem manual, tipo intermediária) e marca paga.
- Emitir boleto usa a conta ativa da imobiliária e respeita o mesmo bloqueio por reajuste das normais.
- Excluir intermediária **não** recalcula automaticamente a prestação das normais (operação manual).

**Observações da Revisão:**
- A regra "excluir não recalcula prestação" é uma decisão de negócio explícita — manter destacada
  para evitar expectativa equivocada de re-amortização automática.

---

## HU-15 — Importação de Índices Econômicos

**Objetivo:** obter índices oficiais (vários tipos) automaticamente para os cálculos de reajuste.

**Mecânica técnica:**
- Cadastro manual e importação automática por tipo de índice, tendo a **API do Banco Central do
  Brasil** como fonte oficial (IPCA, IGP-M, SELIC e demais), com fontes complementares quando aplicável.
- Cada registro: tipo, ano, mês, variação %, número-índice (quando disponível), fonte, data de importação.
- **Idempotência:** chave única (tipo, ano, mês) — reimportar atualiza só se o valor divergir.
- Falha de uma fonte não aborta as demais; resultado reporta importados/atualizados/erros por fonte.
- Acumulado por período prioriza número-índice (Método 1) e recorre ao produto de variações (Método 2).
- Correção fixa nunca consulta índices.

**Observações da Revisão:**
- Resiliência por fonte (uma cai, as outras seguem) é adequada.
- O número-índice como método primário melhora a precisão dos reajustes (alinhado à HU-05).

---

## HU-16 — Remessa e Retorno Bancário (Base Técnica)

**Objetivo:** gerar arquivos de registro de boletos no banco e processar arquivos de confirmação.

**Mecânica técnica:**
- **Remessa:** inclui apenas boletos com número de controle preenchido e em estado elegível;
  monta o arquivo no layout da instituição, calcula dígitos verificadores e cria o registro de remessa.
- **Retorno:** concilia por número de controle; liquidação → cria histórico (origem retorno) e
  marca pago; baixa/cancelamento → marca cancelado.
- **Idempotência:** reprocessar o mesmo retorno não duplica (valida por número de controle + data).
- Arquivos de retorno são guardados como binário para auditoria; itens vinculados às parcelas
  para rastreabilidade.

**Observações da Revisão:**
- Esta HU é a fundação técnica que a HU-23 simplifica para a persona contadora.
- A idempotência do retorno é crítica e é também regra global do sistema.

---

## HU-17 — Renegociação de Parcelas

**Objetivo:** ajustar valor/data/encargos de parcelas em aberto, com auditoria.

**Mecânica técnica:**
- Apenas parcelas não pagas; preserva o **valor original**, alterando só o valor atual.
- Registra valores antes/depois, usuário, data e motivo (auditoria completa).
- Boletos já emitidos das parcelas renegociadas são cancelados e reemitidos com os novos valores.
- Independe do ciclo de reajuste (não interfere no bloqueio).

**Observações da Revisão:**
- Preservar o valor original é regra global (`valor_original` imutável) — coerente com HU-05.
- A reemissão obrigatória após renegociar evita boletos com valores divergentes em circulação.

---

## HU-18 — Relatórios Financeiros e Painel

**Objetivo:** consolidar e exportar a posição financeira e a previsão de fluxo.

**Mecânica técnica:**
- Relatórios: a pagar (não pagas até a data-limite), pagas (histórico por data), posição dos
  contratos (total/pago/a pagar/saldo/progresso) e previsão de reajustes (próximos N meses).
- Exportação em formato tabular, documento imprimível e planilha.
- Painel por imobiliária com série de 12 meses (5 passados a 6 futuros) e três séries de fluxo:
  previsto (não pagas no período), realizado (pagamentos efetuados) e pendente (vencidas não pagas).

**Observações da Revisão (achado de saldo — revisado contra o código):**
- **Aqui está a única divergência real:** o relatório de posição **não** chama
  `Contrato.calcular_saldo_devedor()`. Para evitar consulta por contrato (problema de desempenho
  N+1 num relatório em massa), ele **recalcula a fórmula inline** numa **agregação única**:
  amortização constante → soma das amortizações (com recurso à soma dos valores atuais quando
  ausente); demais → soma dos valores atuais. A lógica é **idêntica** à da função canônica, mas
  **duplicada** em outro ponto.
- **Melhoria recomendada:** extrair a **fórmula** do saldo para um auxiliar puro e compartilhado
  (ex.: `Contrato.saldo_devedor_de_componentes(tipo_amortizacao, soma_amortizacao, soma_valor)`),
  consumido tanto por `calcular_saldo_devedor()` (caminho por contrato) quanto pelo relatório
  (caminho em massa). Mantém o desempenho da agregação única e elimina a duplicação — assim
  HU-11/HU-12/HU-18 passam a depender de **uma só regra**, sem risco de divergir no futuro.
- *Recomendação de revisão; implementação mantida fora do escopo desta rodada (somente documentação).*

---

## HU-19 — Atendimento Automático por Conversa (Comprador)

**Objetivo:** autoatendimento do comprador (segunda via, atrasos, comprovante, resumo) por conversa.

**Mecânica técnica:**
- Conversa por **WhatsApp (Twilio)**; o aviso ao administrador sobre comprovante recebido vai por
  **e-mail (SMTP)**. A segunda via é produzida pelo **BRCobrança** e enviada como anexo na conversa.
- Mensagens recebidas (não enviadas pelo próprio sistema) são roteadas a um serviço de atendimento.
- Identificação por telefone normalizado ao padrão internacional; fallback por documento (até 3 tentativas).
- Máquina de estados de sessão: ocioso → aguardando documento → menu → aguardando seleção (segunda
  via / comprovante) → aguardando arquivo. Sessões inativas além de 30 min são limpas; aviso de
  inatividade após 20 min.
- Fluxos: segunda via com encargos do dia (anexo + linha digitável); atrasos com encargos
  detalhados; recebimento de comprovante (salvo como arquivo, gera tarefa de revisão e aviso à
  imobiliária); resumo financeiro consolidado; opção de transferir a atendente humano.
- Palavras-chave de cancelamento reiniciam o menu.

**Observações da Revisão:**
- O comprovante exige **aprovação manual** — o atendimento não dá baixa sozinho (proteção contra fraude).
- A segunda via gerada com encargos do dia (não o documento antigo) é coerente com HU-08.
- Status: marcado como implementação parcial — confirmar cobertura de testes ponta a ponta.

---

## HU-20 — Notificações e Cobrança Automática

**Objetivo:** enviar lembretes e cobranças por múltiplos canais conforme régua configurável.

**Mecânica técnica:**
- Canais: **e-mail (SMTP)**, **SMS e WhatsApp (Twilio)** — além de outros provedores de conversa.
- Gatilhos padrão: lembrete 5 dias antes do vencimento; inadimplência 3 dias após (configurável).
- Régua configurável por imobiliária (gatilho "antes"/"depois" + nº de dias); sem régua, usa os padrões.
- Templates unificados com três conteúdos (corpo de e-mail rico, texto curto ≤255 caracteres,
  mensagem de conversa) e ~31 marcadores substituíveis; validação de comprimento do texto curto
  com contador que considera a substituição dos marcadores.
- **Salvaguarda de ambiente:** fora de produção, todos os envios são redirecionados para destinos
  de teste — nunca atinge compradores reais em desenvolvimento.
- **Deduplicação:** mesma parcela + mesmo gatilho não envia duas vezes no mesmo dia.
- Normalização de telefone ao padrão internacional antes do envio via **Twilio**.
- Disparo manual individual disponível; execuções periódicas acionadas pelo **cron-job.org**
  (agendador HTTP que substitui processos de segundo plano/Celery no plano gratuito de hospedagem,
  que não mantém *workers*), chamando pontos de entrada dedicados.

**Observações da Revisão:**
- A salvaguarda de ambiente é uma proteção crítica e deve ser testada (já há cenário dedicado).
- Suporte a múltiplos provedores de mensagem (Twilio e alternativos) aumenta a resiliência, mas
  amplia a superfície de configuração — garantir validação de credenciais por provedor.
- Dependência do **cron-job.org** como agendador externo: monitorar a execução dos jobs (uma falha
  silenciosa do agendador interrompe lembretes/cobranças sem erro visível no sistema).

---

## HU-21 — Portal do Comprador

**Objetivo:** autoatendimento web do comprador (contratos, boletos, histórico, dados).

**Mecânica técnica:**
- Auto-cadastro valida que o documento existe como comprador **e** que o e-mail confere com o
  cadastrado; cria o acesso vinculado. Acesso desativado bloqueia o login mesmo com senha correta.
- Cada login registra trilha (endereço de origem, agente, página, data/hora).
- Painel agrega, em consulta única, indicadores de **todos** os contratos do comprador (ativos,
  pagas, pendentes, vencidas), com alertas e listas das parcelas mais relevantes.
- Suporta múltiplos contratos por comprador; cada acesso a contrato/boleto é verificado por
  propriedade (comprador só vê o que é seu); documento do comprador nunca aparece em página pública.
- Pontos de entrada de dados estruturados: parcelas, resumo, próximos vencimentos e segunda via
  (com limite de taxa de requisições; parcela paga → "não encontrado").
- Edição de dados pessoais e preferências de canal; nome é somente leitura.

**Observações da Revisão:**
- Verificação de propriedade em todas as rotas é o controle de segurança central — coberto por cenário.
- Consulta agregada única evita degradação com muitos contratos/parcelas — boa decisão de desempenho.

---

## HU-22 — Mapa Interativo de Lotes

**Objetivo:** visualizar o portfólio de imóveis geograficamente, por status, com filtros e indicadores.

**Mecânica técnica:**
- Todos os imóveis com coordenadas são entregues de uma vez (sem paginação) para permitir
  agrupamento por proximidade no lado do cliente.
- Marcadores por status (disponível/vendido); agrupamento automático com contagem; resumo ao
  passar o cursor; troca de camadas de base; filtros de loteamento e status combináveis e
  aplicados sem recarregar; contador dinâmico de visíveis; "perto de mim" via localização do
  dispositivo com raio de 50 km.
- Imóveis sem coordenadas são ignorados (sem erro). Página por loteamento com indicadores
  (total, disponíveis, vendidos, valores médio/mín/máx, progresso) e acesso restrito ao usuário.

**Observações da Revisão:**
- Entregar tudo de uma vez é adequado para o volume previsto, mas merece atenção de desempenho se
  o portfólio crescer muito (possível evolução: carga por região/limite).
- Status: marcado como parcial — confirmar itens pendentes de mapa/indicadores.

---

## HU-23 — Ciclo Mensal de Cobrança Bancária (Persona Contadora)

**Objetivo:** simplificar, para uma persona não técnica, **(1)** a geração/envio dos arquivos de
registro e **(2)** o recebimento dos arquivos de confirmação com baixa automática — em duas telas.

**Mecânica técnica:**
- **Elegibilidade do boleto para registro:** estado `gerado`; número de controle preenchido;
  vencimento ≥ hoje; e não estar já incluído em uma remessa enviada/processada.
- **Agrupamento e escopos:** conferência agrupa por (conta bancária, layout). Geração por um único
  ponto de entrada dirigido por `escopo`: `todos`, `imobiliaria`, `conta`, `boleto`.
- **Invariante central:** 1 arquivo = 1 conta bancária. Qualquer escopo resolve para N arquivos =
  N contas envolvidas. A resposta é **sempre uma lista**, tolerante a falha parcial.
- **Sequência de arquivo (numeração por conta):** só é consumida em geração bem-sucedida; falha não
  cria buraco; regeneração de arquivo ainda não enviado preserva o número.
- **Transições:** ao gerar a remessa, o boleto passa de `gerado` para `registrado`. Estados de
  arquivo: gerado → (baixado, derivado de "já foi baixado") → enviado (marcação manual) → processado;
  ou erro. Cancelar envio reverte para gerado.
- **Anti-duplicidade:** geração para (conta, mês) é serializada para impedir remessas duplicadas
  por duplo clique/concorrência — risco direto de cobrança em dobro.
- **Controle de acesso:** revalida vínculo usuário → imobiliária → conta em toda geração
  (proteção contra manipulação de identificador no envio).
- **Exclusões inteligentes:** bancos/carteiras "sem registro" ou que só registram por integração
  online não aparecem como grupo; boletos sem número de controle são silenciosamente excluídos
  e contabilizados; alerta (não bloqueante) para vencimento muito próximo.
- **Validação pré-geração determinística:** detecta inconsistências (endereço/documento do sacado,
  número de controle ausente, valor inválido, vencimento em data não útil) — a detecção é sempre
  por regra; humanização de mensagem é opcional.
- **Retorno em um passo:** o envio do arquivo de confirmação cria e processa imediatamente —
  liquidações dão baixa; rejeições marcam o item como rejeitado e devolvem o boleto a `gerado`
  (reelegível); cancelamentos marcam cancelado. Herda a idempotência global do retorno.
- **Auditoria:** geração e envio registram usuário e data.

**Observações da Revisão:**
- Esta HU já passou por revisão crítica formal (12 falhas corrigidas: transição de estado do
  boleto, anti-duplicidade, sequência de arquivo, exclusão de bancos sem registro, prazo de
  registro, auditoria, proteção de acesso, tratamento de rejeição). A revisão atual confirma que
  as correções estão refletidas em regras, critérios e cenários.
- Ponto forte: a anti-duplicidade e a sequência por conta endereçam os riscos financeiros mais caros.
- **Importante (papel do BRCobrança):** o BRCobrança **gera** o boleto, mas **não o registra** no
  banco — o registro é feito pelo arquivo de remessa desta HU. Logo, o ciclo de cobrança depende de
  ambos: BRCobrança (geração — HU-03/HU-24) + remessa CNAB (registro — esta HU).
- Pendência prática conhecida (corrigida no código recente): o formato de agência/dígito e a
  validação de convênio por instituição precisam acompanhar o que o **BRCobrança** espera (tanto na
  geração do boleto quanto no layout de remessa) — manter cobertura de teste por banco.

---

## HU-24 — Geração Mensal de Boletos (Persona Contadora)

**Objetivo:** gerar os boletos do período (parcelas **e** intermediárias) por escopo, etapa
anterior à remessa (HU-23).

**Mecânica técnica:**
- **Elegibilidade:** parcela não paga, estado `não gerado`, não bloqueada por reajuste e dentro do
  período/quantidade resolvidos pelo escopo. Intermediária elegível se não paga e ainda sem parcela
  vinculada com boleto.
- **Escopos** por ponto de entrada único: `todos`, `imobiliaria`, `contratos`, `parcela`,
  `intermediaria`. Parâmetros do lote: `quantidade` (próximos N por contrato, por ordem de
  vencimento), `tipo` (folha = individuais; carnê = documento consolidado por contrato) e
  `incluir_intermediarias`.
- **Mecanismo de geração:** reutiliza a geração individual de produção (mesmo caminho preciso de
  documento/dados por boleto), em laço **tolerante a falha parcial**; cada parcela passa antes pela
  função de bloqueio por reajuste.
- **Cascata de quantidade:** ao encontrar a primeira parcela bloqueada de um contrato, a geração
  daquele contrato para naquele ponto (as seguintes também estariam bloqueadas).
- **Resposta:** sumário com gerados/bloqueados/erros, detalhamento por imobiliária e listas de
  bloqueados e erros; quando carnê, expõe o documento consolidado por contrato.
- **Idempotência:** já gerado é contado como "ignorado", não regerado sem modo forçado (que não
  existe nesta rota da contadora — uso administrativo permanece na geração individual).
- **Conta bancária:** a vinculada à parcela ou a principal da imobiliária quando ausente.
- **Notificação consolidada (quando quantidade > 1):** e-mail e conversa recebem 1 envio com todos
  os boletos do contrato em 1 documento; texto curto vai um a um (não comporta anexo). Envio
  assíncrono, respeitando configurações de canal e a salvaguarda de ambiente.
- **Encadeamento:** ao final, atalho para a remessa (HU-23) dos boletos recém-gerados.

**Observações da Revisão:**
- Diferença importante frente à HU-07: aqui o bloqueio **não aborta** o lote (exclui a parcela e
  segue); na HU-07 ele aborta. Ambas consultam a mesma função de bloqueio — a diferença é de
  política de lote, e deve permanecer documentada.
- A reutilização do caminho de produção de geração individual garante paridade de qualidade de
  documento/dados entre a tela da contadora e o detalhe do contrato (alinhamento recentemente
  reforçado no código: resolução explícita da conta pela imobiliária, rotação de identificador,
  auditoria e atualização do marcador de último boleto gerado).
- A consolidação por canal é coerente com HU-20; confirmar que o documento consolidado anexado é
  o mesmo artefato do carnê (HU-07), independentemente do tipo escolhido para impressão.

---

## Achados Transversais (Cross-Cutting)

1. **Bloqueio por reajuste** (HU-06): consumido por `pode_gerar_boleto()` em HU-03, HU-14 e HU-24,
   mas o **carnê (HU-07) usa um corte por ciclo próprio** (`max_parcela_lote`), mais restritivo.
   **Recomendação:** unificar o carnê em `pode_gerar_boleto()` (fonte única) — ver achado da HU-07.
2. **Saldo devedor por tipo de amortização** (HU-11, HU-12, HU-18): HU-11 e HU-12 **já reusam** a
   função canônica `Contrato.calcular_saldo_devedor()`; **apenas a HU-18 duplica a fórmula inline**
   (por desempenho, em agregação única). **Recomendação:** extrair um auxiliar puro de fórmula
   compartilhado entre os dois caminhos (ver achado da HU-18) — sem perder o desempenho do relatório.
3. **Idempotência** é princípio recorrente e bem aplicado: conciliação por extrato (HU-10),
   importação de índices (HU-15), retorno bancário (HU-16/HU-23) e geração em lote (HU-24).
4. **Preservação do valor original** (`valor_original` imutável) é regra global respeitada em
   reajuste (HU-05) e renegociação (HU-17).
5. **Privacidade do documento do comprador** em superfícies públicas (HU-13, HU-21) é regra global,
   verificada por teste de conteúdo.
6. **Resiliência a indisponibilidade externa:** leitura de extrato pelo **BRCobrança** com
   alternativa interna (HU-10), importação de índices tolerante a falha por fonte (HU-15) e
   tratamento da **inicialização lenta do BRCobrança** quando ocioso (espera/retentativa na
   geração) — padrão maduro de degradação graciosa.
7. **Tolerância a falha parcial em lotes** (HU-07, HU-23, HU-24) com relato individual de sucesso/erro.
8. **Controle de acesso multi-inquilino** revalidado por operação sensível (HU-21, HU-23, HU-24),
   com proteção explícita contra manipulação de identificador no envio.
9. **Salvaguarda de ambiente** para notificações (HU-20) protege compradores reais em desenvolvimento —
   aplicável também à notificação consolidada da HU-24.
10. **Duplo armazenamento do documento (arquivo + binário)** (HU-03, HU-07, HU-13) garante
    recuperação em ambiente de armazenamento volátil.

## Itens de Atenção / Possíveis Evoluções

- **Expiração/rotação de link público** (HU-13): hoje o identificador não expira; já existe rotação
  em outro fluxo de geração — avaliar unificar a política.
- **Escala do mapa** (HU-22): carga total de marcadores pode exigir carregamento por região no futuro.
- **Cobertura de testes ponta a ponta** do atendimento por conversa (HU-19) e dos itens parciais do
  mapa (HU-22), ambos marcados como parciais.
- **Paridade por banco no BRCobrança** (HU-03/HU-23): manter testes por instituição para formato de
  agência/dígito, convênio e layout, acompanhando o que o **BRCobrança** espera — lembrando que o
  BRCobrança **gera** o boleto e produz o layout de remessa, mas o **registro** efetivo no banco
  depende do envio do arquivo (HU-23).
- **Unificar o bloqueio por reajuste do carnê (HU-07) em `pode_gerar_boleto()`** — hoje o carnê usa
  um corte por ciclo próprio, mais restritivo que a HU-24; unificar elimina duas definições de
  "elegível".
- **Reuso do cálculo de saldo devedor (HU-18):** extrair um auxiliar puro de fórmula compartilhado
  com `calcular_saldo_devedor()` (HU-11/HU-12 já o reusam; só o relatório em massa duplica a fórmula).

---

*Revisão consolidada a partir das especificações em `docs/analise/historias-usuario/HU-01..HU-24`,
do índice mestre `INDICE.md` e da verificação contra o código atual. Mantém o escopo
funcional/técnico sem referências a tecnologias de implementação ou de apresentação visual —
**com exceção das APIs e serviços externos** listados na seção "APIs e Serviços Externos"
(Banco Central do Brasil, BRCobrança, Twilio, cron-job.org e SMTP), identificados explicitamente
por serem dependências operacionais do sistema (decisão de revisão).*

> **Nota desta revisão (atualização):** achados de 07×24 e HU-11/12/18 reavaliados contra o
> código real — HU-11/HU-12 já reusam o cálculo canônico de saldo; só a HU-18 duplica a fórmula;
> o carnê (HU-07) usa corte por ciclo próprio em vez de `pode_gerar_boleto()`. Recomendações
> registradas (unificar o carnê em `pode_gerar_boleto()`; extrair auxiliar de fórmula de saldo).
> As recomendações são **somente de documentação** nesta rodada — sem alteração de código.
