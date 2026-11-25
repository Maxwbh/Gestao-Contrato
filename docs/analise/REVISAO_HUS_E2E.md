# Revisão das HUs + teste ponta a ponta

> Data: 2026-11-11 · Escopo: HU-01..HU-28 e BAPI · Base de teste: `gerar_dados_teste`
> (2 imobiliárias, 8 contas, 57 contratos) com o motor offline real.

## Como foi testado

1. **Suíte automatizada** completa (2018 testes).
2. **Varredura de rotas**: GET em todas as 338 rotas com dados reais (procura de erro 500).
3. **Fluxos ponta a ponta via HTTP** contra o motor de cobrança real: gerar boleto
   (BB, Bradesco, C6, Sicoob), 2ª via, link público, carnê (multi-boleto), ZIP,
   cancelamento, remessa CNAB 240/400, pagamento, quitação, relatórios.
4. **Leitura das HUs** critério a critério contra o código.

## Corrigido nesta entrega

| # | HU | Defeito | Correção |
|---|----|---------|----------|
| 1 | HU-21/28 | Comprador do portal navegava nas telas internas (contratos, compradores, dashboard) e registrava pagamento de qualquer parcela | Middleware `IsolamentoAcessoMiddleware`: comprador fica restrito a `/portal/` e links públicos |
| 2 | HU-04/05/07/09/11/12/14/17 | ~90 views sem checagem de imobiliária: usuário da imobiliária A pagava/renegociava/simulava contrato da B | Mesmo middleware resolve o alvo pela rota (contrato, parcela, reajuste, remessa, retorno, conta, imobiliária) e devolve 403 |
| 3 | HU-18 | Relatórios e exportações traziam dados de todas as imobiliárias | Filtro `imobiliaria_ids` aplicado em todos os relatórios |
| 4 | HU-18 | CSV de "Posição de contratos" e "Previsão de reajustes" saía vazio; filtro por imobiliária na previsão nunca casava | Exportação implementada; item passa a carregar `imobiliaria_id` |
| 5 | HU-08 | 2ª via falhava (HTTP 400) em todos os bancos e consumia um nosso-número a cada tentativa | Reusa o sequencial do boleto emitido, sem tocar no contador; usa a conta que emitiu |
| 6 | HU-16/23 | Remessa enviava o nosso-número formatado: Bradesco recusava ("Número inválido") e Sicoob registrava outro título (seq+DV lido como sequencial) | `Parcela.get_nosso_numero_sequencial()` usado na remessa |
| 7 | HU-16/23 | Recusa do motor aparecia como "verifique os logs" | Mensagem traz o motivo real (ex.: convênio inválido, layout não suportado) |
| 8 | HU-04 | Pagamento em dobro pelo formulário (2 históricos) | Parcela paga não aceita novo pagamento |
| 9 | HU-04 | Data de pagamento futura aceita | Recusada nas 3 entradas (formulário, AJAX, API) |
| 10 | HU-04/09 | Pagar a última parcela via AJAX ou antecipação não quitava o contrato | `sincronizar_quitacao()` chamado |
| 11 | HU-04 | `pagar-ajax` com corpo JSON baixava a parcela com R$ 0,00 | Lê JSON e exige valor > 0 |
| 12 | HU-05 | Desconto em p.p. aplicado duas vezes (8% − 2 → 4% em vez de 6%) | `percentual` é o líquido; não subtrai de novo |
| 13 | HU-05 | API aplicava o mesmo ciclo repetidas vezes e pulava ciclos | Valida sequência pelos ciclos já aplicados |
| 14 | HU-05 | Piso de 0% ignorado no reajuste informado em lote | Testa `is None` |
| 15 | HU-11/12 | Percentual 0% (cessão, fruição, multas, mora) caía no padrão (ex.: cessão 0% cobrava 3%) | Padrão só quando o campo não foi informado |
| 16 | HU-19 | Webhook Evolution no formato Meta aceitava POST anônimo (alterava status de entrega e acionava o chatbot) | Exige apikey da instância |
| 17 | HU-19 | Opção 4 e encaminhamento a atendente do chatbot quebravam (`Contrato.ativo` não existe) | Filtra por `status='ATIVO'` |
| 18 | HU-21 | Auto-cadastro no portal aceitava qualquer e-mail quando o comprador não tinha e-mail cadastrado | Exige e-mail cadastrado e igual |
| 19 | HU-23 | Excluir remessa deixava os boletos presos em "Registrado" | Voltam a "Gerado" |
| 20 | BAPI | Webhook de liquidação sem valor baixava com R$ 0,00; reenvio após falha era descartado como duplicado | Usa o valor do título; só desfechos contam como duplicata |
| 21 | BAPI-42 | Link de pagamento sobrescrevia conta/provider/`cobranca_id` de parcela que já tinha boleto | Boleto vivo é preservado; checkout casa por `ext_ref` |
| 22 | — | GET em excluir contabilidade/contrato/índice dava erro 500 (template ausente) | Template genérico de confirmação |

Testes de regressão: `tests/unit/test_revisao_hus_regressao.py` (26 casos).

## Pendências (não alteradas — precisam de decisão ou são mudanças maiores)

**Dinheiro / regra de negócio**

- **HU-10** — OFX baixa parcela só por coincidência de valor (±R$ 0,10) ou por número do
  contrato no histórico, sem conferir data nem ambiguidade. A HU manda para revisão manual.
- **HU-10** — FITID já usado ainda é reportado como conciliado; FITID vazio não deduplica.
- **HU-16** — Retorno CNAB casa nosso-número por "termina com": `…18` casa `018` e `118`.
- **HU-16** — Arquivo com entrada (02) e liquidação (06) do mesmo título: a 2ª ocorrência é ignorada.
- **HU-05** — Índice acumulado é calculado mesmo faltando mês do período (aplica 11 de 12).
- **HU-05** — Reajuste corrige intermediárias mesmo com `intermediarias_reajustadas=False`.
- **HU-05** — Modo Price: fórmula difere da HU (`PMT×(1+idx)×(1+i)^prazo` × `PMT(saldo×(1+idx))`). Decisão de negócio.
- **HU-14** — Editar qualquer campo de uma intermediária recalcula todas as parcelas pelo
  valor do ciclo 1 (apaga reajustes, inclusive em parcelas pagas).
- **HU-14** — Pagar intermediária não gera histórico nem baixa o boleto; rescisão soma a
  intermediária e a parcela vinculada (devolução inflada).
- **HU-01/14** — Limite de 80% das intermediárias não é validado.
- **HU-04** — Estorno de pagamento não tem tela/URL.
- **HU-17** — Renegociação não grava auditoria nem cancela/regenera o boleto emitido.
- **HU-02** — "Completar parcelas" usa o valor do ciclo 1 após reajustes; sem resíduo na última parcela.

**Fluxo / estado**

- **HU-25** — Remessa nunca vira "Processada" após o retorno; passo 3 do hub fica pendente
  e o banner "Ciclo concluído" aparece sem retorno.
- **HU-23** — `api/cnab/remessas/gerar/` não aplica RN-G10/G11 (vencidos e boletos já enviados).
- **HU-03/13** — Regerar boleto troca o token público: o link já enviado por e-mail morre.
- **HU-06** — `bloqueio_boleto_reajuste` não é lido por nenhuma trava de geração.
- **HU-20** — `TEST_MODE` fixo em `False`; dois caminhos de envio ignoram a salvaguarda.
- **HU-19** — Comprovante enviado pelo WhatsApp não é salvo (só gera notificação).
- **HU-22** — Página do loteamento não filtra pela imobiliária do usuário.

**Motor / dados de teste**

- Bradesco e C6 não têm CNAB 240 no motor (só 400) — a tela ainda oferece os dois.
- BB CNAB 240 recusa convênio de 8 dígitos (a massa de teste usa 8).
- Sicredi segue recusado pelo motor (defeito externo já conhecido).
- `obter_proximos_nosso_numero` não é atômico (duas gerações simultâneas podem repetir o número).

**Documentação desatualizada**

- HU-28 está implementada (índice marca ⬜). HU-07 (GET do carnê), HU-09 (`ANTECIPACAO`),
  HU-13 (token expira/rotaciona), HU-14 (`mes_vencimento`), HU-18 (`?formato=`), HU-25 (`?imobiliaria=`).
