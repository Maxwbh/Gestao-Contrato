"""
HU-24 — Geração Mensal de Boletos (Fluxo da Contadora).

Camada de wizard dirigida por escopo sobre a geração de boletos:
  - resolve as parcelas-alvo por escopo (todos / imobiliaria / contratos / parcela / intermediaria)
  - respeita o bloqueio por reajuste em cascata (HU-06)
  - gera via Parcela.gerar_boleto() (caminho de produção)
  - consolida a notificação por canal quando quantidade > 1 (RN-14)

Desenvolvedor: Maxwell da Silva Oliveira
"""
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

ESCOPOS_VALIDOS = {'todos', 'imobiliaria', 'contratos', 'parcela', 'intermediaria'}


class GeracaoBoletosService:
    """Resolução por escopo + dados do painel da HU-24."""

    # ------------------------------------------------------------------ #
    # Elegibilidade por contrato
    # ------------------------------------------------------------------ #
    def _qs_parcelas_base(self, contrato):
        """Parcelas normais não pagas e sem boleto, em ordem cronológica.

        Usa o cache de prefetch (`to_attr='_parcelas_pendentes'`) quando
        disponível — evita uma consulta por contrato no painel/conferência.
        """
        pend = getattr(contrato, '_parcelas_pendentes', None)
        if pend is not None:
            return pend
        from financeiro.models import StatusBoleto, TipoParcela
        return (
            contrato.parcelas
            .filter(pago=False, status_boleto=StatusBoleto.NAO_GERADO)
            .exclude(tipo_parcela=TipoParcela.INTERMEDIARIA)
            .order_by('numero_parcela')
        )

    def proximas_elegiveis(self, contrato, quantidade, ciclos_aplicados=None):
        """
        Próximas `quantidade` parcelas elegíveis do contrato.
        Respeita a cascata da HU-06: para no primeiro bloqueio (as seguintes
        também estariam bloqueadas). Retorna (elegiveis, bloqueados).

        `ciclos_aplicados` (opcional) é repassado a `pode_gerar_boleto` para
        evitar consulta a Reajuste por parcela quando o chamador já pré-carregou
        os ciclos reajustados do contrato.
        """
        elegiveis, bloqueados = [], []
        for p in self._qs_parcelas_base(contrato):
            if len(elegiveis) >= quantidade:
                break
            pode, motivo = contrato.pode_gerar_boleto(
                p.numero_parcela, ciclos_aplicados=ciclos_aplicados
            )
            if not pode:
                bloqueados.append((p, motivo))
                break  # cascata HU-06
            elegiveis.append(p)
        return elegiveis, bloqueados

    def intermediarias_elegiveis(self, contrato):
        """Intermediárias não pagas sem boleto gerado.

        Usa o cache de prefetch (`to_attr='_intermediarias_pend'`) quando
        disponível — evita consulta + N+1 em `parcela_vinculada` por contrato.
        """
        from financeiro.models import StatusBoleto
        from contratos.models import PrestacaoIntermediaria
        pref = getattr(contrato, '_intermediarias_pend', None)
        if pref is not None:
            itens = pref
        else:
            itens = PrestacaoIntermediaria.objects.filter(
                contrato=contrato, paga=False
            ).select_related('parcela_vinculada')
        res = []
        for it in itens:
            pv = it.parcela_vinculada
            if pv and pv.status_boleto != StatusBoleto.NAO_GERADO:
                continue
            res.append(it)
        return res

    # ------------------------------------------------------------------ #
    # Painel / conferência
    # ------------------------------------------------------------------ #
    def obter_conferencia(self, imobiliarias, imobiliaria_id=None,
                          quantidade=1, incluir_intermediarias=True):
        """
        Monta a conferência agrupada por imobiliária → contrato e os KPIs.
        Retorna dict: {grupos, kpis}.
        """
        from django.db.models import Count, Q, Prefetch
        from contratos.models import Contrato, StatusContrato, PrestacaoIntermediaria
        from financeiro.models import StatusBoleto, TipoParcela, Parcela, Reajuste

        # Pré-carrega tudo o que o laço precisa em poucas consultas (em vez de
        # ~3 consultas por contrato + N+1): parcelas pendentes, intermediárias
        # não pagas e a contagem de já gerados, todos por contrato.
        parcelas_pend_qs = (
            Parcela.objects
            .filter(pago=False, status_boleto=StatusBoleto.NAO_GERADO)
            .exclude(tipo_parcela=TipoParcela.INTERMEDIARIA)
            .order_by('numero_parcela')
        )
        inter_pend_qs = (
            PrestacaoIntermediaria.objects.filter(paga=False)
            .select_related('parcela_vinculada')
        )
        contratos = (
            Contrato.objects.filter(status=StatusContrato.ATIVO, imobiliaria__in=imobiliarias)
            .select_related('imobiliaria', 'comprador')
            .annotate(_ja_gerados=Count(
                'parcelas',
                filter=Q(parcelas__status_boleto__in=[StatusBoleto.GERADO, StatusBoleto.REGISTRADO]),
            ))
            .prefetch_related(
                Prefetch('parcelas', queryset=parcelas_pend_qs, to_attr='_parcelas_pendentes'),
                Prefetch('intermediarias', queryset=inter_pend_qs, to_attr='_intermediarias_pend'),
            )
            .order_by('imobiliaria__nome', 'numero_contrato')
        )
        if imobiliaria_id:
            contratos = contratos.filter(imobiliaria_id=imobiliaria_id)

        contratos = list(contratos)

        # Ciclos já reajustados (aplicado=True) de todos os contratos em 1 consulta
        # — evita uma consulta a Reajuste por parcela em pode_gerar_boleto().
        ciclos_por_contrato: dict = {}
        for cid, ciclo in Reajuste.objects.filter(
            contrato_id__in=[c.pk for c in contratos], aplicado=True
        ).values_list('contrato_id', 'ciclo'):
            ciclos_por_contrato.setdefault(cid, set()).add(ciclo)

        grupos = {}
        kpi_a_gerar = kpi_bloqueados = kpi_intermediarias = 0
        kpi_valor = Decimal('0.00')
        contratos_com_pendencia = set()

        for contrato in contratos:
            ciclos_aplic = ciclos_por_contrato.get(contrato.pk, set())
            elegiveis, bloqueados = self.proximas_elegiveis(
                contrato, quantidade, ciclos_aplicados=ciclos_aplic
            )
            inter = self.intermediarias_elegiveis(contrato) if incluir_intermediarias else []
            ja_gerados = contrato._ja_gerados
            if not elegiveis and not bloqueados and not inter:
                continue

            valor = sum((p.valor_atual for p in elegiveis), Decimal('0.00'))
            valor += sum((it.valor_atual for it in inter), Decimal('0.00'))

            kpi_a_gerar += len(elegiveis)
            kpi_bloqueados += len(bloqueados)
            kpi_intermediarias += len(inter)
            kpi_valor += valor
            if elegiveis or inter:
                contratos_com_pendencia.add(contrato.pk)

            # Status derivado para o badge da linha (espelha o template)
            if bloqueados and not elegiveis:
                status = 'BLOQUEADO'
            elif ja_gerados and elegiveis:
                status = 'PARCIAL'      # parte já gerada, parte pendente
            elif ja_gerados:
                status = 'GERADO'
            else:
                status = 'NAO_GERADO'

            imob = contrato.imobiliaria
            g = grupos.setdefault(imob.pk, {'imobiliaria': imob, 'contratos': []})
            g['contratos'].append({
                'contrato': contrato,
                'comprador': getattr(contrato.comprador, 'nome', ''),
                'elegiveis': len(elegiveis),
                'bloqueados': len(bloqueados),
                'intermediarias': len(inter),
                'ja_gerados': ja_gerados,
                'status': status,
                'valor': valor,
            })

        # total de contratos ativos por imobiliária (pill do cabeçalho do grupo)
        # — uma única consulta agregada em vez de uma por grupo.
        if grupos:
            ativos_por_imob = dict(
                Contrato.objects.filter(
                    status=StatusContrato.ATIVO, imobiliaria_id__in=list(grupos.keys())
                )
                .values('imobiliaria_id')
                .annotate(n=Count('id'))
                .values_list('imobiliaria_id', 'n')
            )
            for imob_pk, g in grupos.items():
                g['total_ativos'] = ativos_por_imob.get(imob_pk, 0)

        return {
            'grupos': sorted(grupos.values(), key=lambda x: x['imobiliaria'].nome),
            'kpis': {
                'a_gerar': kpi_a_gerar,
                'valor_total': kpi_valor,
                'contratos': len(contratos_com_pendencia),
                'bloqueados': kpi_bloqueados,
                'intermediarias': kpi_intermediarias,
            },
        }

    # ------------------------------------------------------------------ #
    # Resolução por escopo → contratos-alvo
    # ------------------------------------------------------------------ #
    def resolver_contratos(self, escopo, imobiliarias, imobiliaria_id=None, contrato_ids=None):
        """Retorna queryset de contratos-alvo validados por acesso (RN-10)."""
        from contratos.models import Contrato, StatusContrato

        qs = Contrato.objects.filter(
            status=StatusContrato.ATIVO, imobiliaria__in=imobiliarias
        ).select_related('imobiliaria', 'comprador')

        if escopo == 'imobiliaria':
            if not imobiliaria_id:
                raise ValueError('imobiliaria_id é obrigatório no escopo "imobiliaria".')
            qs = qs.filter(imobiliaria_id=imobiliaria_id)
        elif escopo == 'contratos':
            if not contrato_ids:
                raise ValueError('contrato_ids é obrigatório no escopo "contratos".')
            qs = qs.filter(pk__in=contrato_ids)
        return qs

    # ------------------------------------------------------------------ #
    # RN-14 — Notificação consolidada por canal
    # ------------------------------------------------------------------ #
    def _pdf_consolidado(self, parcelas):
        """Concatena os PDFs (boleto_pdf_db) das parcelas em 1 PDF via pypdf."""
        try:
            import io
            from pypdf import PdfWriter, PdfReader
            writer = PdfWriter()
            for p in parcelas:
                data = getattr(p, 'boleto_pdf_db', None)
                if not data:
                    continue
                reader = PdfReader(io.BytesIO(bytes(data)))
                for pg in reader.pages:
                    writer.add_page(pg)
            if not writer.pages:
                return None
            buf = io.BytesIO()
            writer.write(buf)
            return buf.getvalue()
        except Exception:
            logger.exception('_pdf_consolidado: falha ao concatenar PDFs')
            return None

    def _enviar_consolidado(self, contrato, parcelas, pdf_bytes, canal):
        """
        Envia 1 mensagem com o PDF consolidado anexado (e-mail ou WhatsApp).
        Best-effort — retorna True se enfileirou/enviou, False caso contrário.
        """
        comprador = contrato.comprador
        nome_arquivo = f"boletos_{contrato.numero_contrato}_{len(parcelas)}.pdf"
        try:
            if canal == 'email':
                if not getattr(comprador, 'email', '') or not getattr(comprador, 'notificar_email', True):
                    return False
                from django.core.mail import EmailMessage
                msg = EmailMessage(
                    subject=f'Seus boletos — Contrato {contrato.numero_contrato}',
                    body=(f'Olá {comprador.nome},\n\nSeguem em anexo {len(parcelas)} '
                          f'boleto(s) do contrato {contrato.numero_contrato}.'),
                    to=[comprador.email],
                )
                if pdf_bytes:
                    msg.attach(nome_arquivo, pdf_bytes, 'application/pdf')
                msg.send(fail_silently=True)
                return True
            if canal == 'whatsapp':
                if not getattr(comprador, 'telefone', '') or not getattr(comprador, 'notificar_whatsapp', True):
                    return False
                # Reaproveita o serviço de WhatsApp quando disponível; best-effort.
                from notificacoes.boleto_notificacao import BoletoNotificacaoService
                svc = BoletoNotificacaoService()
                enviar = getattr(svc, 'enviar_whatsapp_documento', None)
                if callable(enviar):
                    enviar(contrato, pdf_bytes, nome_arquivo)
                    return True
                logger.info('WhatsApp consolidado pendente de provedor (contrato=%s)', contrato.numero_contrato)
                return False
        except Exception:
            logger.exception('_enviar_consolidado: falha no canal %s', canal)
        return False

    def notificar_lote(self, contrato, parcelas):
        """
        RN-14: consolida a notificação por canal.
          • 1 boleto  → notificação individual padrão (todos os canais, via fila).
          • >1 boleto → e-mail e WhatsApp em 1 envio com PDF consolidado; SMS um a um.
        Best-effort: nunca propaga exceção (não bloqueia a geração).
        """
        resumo = {'individual': False, 'sms': 0, 'email_consolidado': False, 'whatsapp_consolidado': False}
        parcelas = list(parcelas)
        if not parcelas:
            return resumo

        from notificacoes.boleto_notificacao import BoletoNotificacaoService
        svc = BoletoNotificacaoService()

        if len(parcelas) == 1:
            try:
                svc.agendar_notificacao_boleto_criado(parcelas[0])
                resumo['individual'] = True
            except Exception:
                logger.exception('notificar_lote: falha no agendamento individual')
            return resumo

        # >1 boleto no mesmo contrato
        from notificacoes.models import TipoTemplate
        for p in parcelas:
            try:
                svc.enviar_sms_boleto(p, TipoTemplate.BOLETO_CRIADO)
                resumo['sms'] += 1
            except Exception:
                logger.exception('notificar_lote: falha SMS parcela pk=%s', p.pk)

        pdf = self._pdf_consolidado(parcelas)
        resumo['email_consolidado'] = self._enviar_consolidado(contrato, parcelas, pdf, 'email')
        resumo['whatsapp_consolidado'] = self._enviar_consolidado(contrato, parcelas, pdf, 'whatsapp')
        return resumo
