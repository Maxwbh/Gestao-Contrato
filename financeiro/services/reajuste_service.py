"""
Serviço de Reajuste de Contratos

Responsável pela aplicação de reajustes nos contratos, busca de índices
e automação do processo de correção monetária.

Desenvolvedor: Maxwell da Silva Oliveira
Email: maxwbh@gmail.com
Empresa: M&S do Brasil LTDA
"""
import logging
from decimal import Decimal
from datetime import date, timedelta
from typing import Optional, Dict, List, Tuple
from dateutil.relativedelta import relativedelta

from django.db import transaction
from django.utils import timezone

from contratos.models import Contrato, IndiceReajuste, TipoCorrecao
from financeiro.models import Parcela, Reajuste

logger = logging.getLogger(__name__)


class ReajusteService:
    """
    Serviço para gerenciamento de reajustes de contratos.

    Responsabilidades:
    - Buscar índices econômicos (IPCA, IGPM, etc.)
    - Calcular percentuais de reajuste acumulados
    - Aplicar reajustes em parcelas
    - Verificar contratos pendentes de reajuste
    - Simular impacto de reajustes
    """

    # Mapeamento de índices para fontes
    FONTES_INDICES = {
        'IPCA': 'IBGE',
        'INPC': 'IBGE',
        'IGPM': 'FGV',
        'IGPDI': 'FGV',
        'INCC': 'FGV',
        'TR': 'BCB',
        'SELIC': 'BCB',
    }

    def __init__(self):
        self.erros = []
        self.avisos = []

    # =========================================================================
    # BUSCA DE ÍNDICES
    # =========================================================================

    def buscar_indice(self, tipo_indice: str, ano: int, mes: int) -> Optional[IndiceReajuste]:
        """
        Busca um índice específico no banco de dados.

        Args:
            tipo_indice: Tipo do índice (IPCA, IGPM, etc.)
            ano: Ano de referência
            mes: Mês de referência

        Returns:
            IndiceReajuste ou None se não encontrado
        """
        return IndiceReajuste.get_indice(tipo_indice, ano, mes)

    def calcular_acumulado_periodo(
        self,
        tipo_indice: str,
        data_inicio: date,
        data_fim: date
    ) -> Optional[Decimal]:
        """
        Calcula o índice acumulado em um período.

        Args:
            tipo_indice: Tipo do índice
            data_inicio: Data inicial do período
            data_fim: Data final do período

        Returns:
            Percentual acumulado ou None se índices não disponíveis
        """
        return IndiceReajuste.get_acumulado_periodo(
            tipo_indice,
            data_inicio.year, data_inicio.month,
            data_fim.year, data_fim.month
        )

    def verificar_indices_disponiveis(
        self,
        tipo_indice: str,
        data_inicio: date,
        data_fim: date
    ) -> Tuple[bool, List[str]]:
        """
        Verifica se todos os índices do período estão disponíveis.

        Args:
            tipo_indice: Tipo do índice
            data_inicio: Data inicial
            data_fim: Data final

        Returns:
            Tuple (todos_disponiveis, lista_meses_faltantes)
        """
        meses_faltantes = []
        data_atual = data_inicio.replace(day=1)
        data_fim_mes = data_fim.replace(day=1)

        while data_atual <= data_fim_mes:
            indice = self.buscar_indice(tipo_indice, data_atual.year, data_atual.month)
            if not indice:
                meses_faltantes.append(f"{data_atual.month:02d}/{data_atual.year}")
            data_atual = data_atual + relativedelta(months=1)

        return len(meses_faltantes) == 0, meses_faltantes

    # =========================================================================
    # ANÁLISE DE CONTRATOS
    # =========================================================================

    def listar_contratos_reajuste_pendente(
        self,
        imobiliaria=None,
        dias_antecedencia: int = 30
    ) -> List[Dict]:
        """
        Lista contratos que precisam de reajuste nos próximos dias.

        Args:
            imobiliaria: Filtrar por imobiliária (opcional)
            dias_antecedencia: Dias de antecedência para alertar

        Returns:
            Lista de dicionários com informações dos contratos
        """
        from contratos.models import StatusContrato

        hoje = timezone.now().date()
        data_limite = hoje + timedelta(days=dias_antecedencia)

        contratos = Contrato.objects.filter(
            status=StatusContrato.ATIVO
        ).exclude(
            tipo_correcao=TipoCorrecao.FIXO
        )

        if imobiliaria:
            contratos = contratos.filter(imobiliaria=imobiliaria)

        resultado = []

        for contrato in contratos:
            data_proximo = contrato.data_proximo_reajuste
            if data_proximo and data_proximo <= data_limite:
                # Verificar se reajuste já foi aplicado
                ciclo_necessario = contrato.ciclo_reajuste_atual + 1
                reajuste_existente = Reajuste.objects.filter(
                    contrato=contrato,
                    ciclo=ciclo_necessario,
                    aplicado=True
                ).exists()

                if not reajuste_existente:
                    # Calcular dias restantes
                    dias_restantes = (data_proximo - hoje).days

                    # Verificar se índice está disponível
                    indices_ok, meses_faltantes = self.verificar_indices_disponiveis(
                        contrato.tipo_correcao,
                        contrato.data_ultimo_reajuste or contrato.data_contrato,
                        data_proximo
                    )

                    resultado.append({
                        'contrato': contrato,
                        'data_proximo_reajuste': data_proximo,
                        'dias_restantes': dias_restantes,
                        'ciclo': ciclo_necessario,
                        'indice_tipo': contrato.tipo_correcao,
                        'indices_disponiveis': indices_ok,
                        'meses_faltantes': meses_faltantes,
                        'urgente': dias_restantes <= 7,
                        'bloqueado': contrato.bloqueio_boleto_reajuste,
                    })

        # Ordenar por urgência
        resultado.sort(key=lambda x: x['dias_restantes'])

        return resultado

    def verificar_contrato_precisa_reajuste(self, contrato: Contrato) -> Dict:
        """
        Verifica detalhadamente se um contrato precisa de reajuste.

        Args:
            contrato: Contrato a verificar

        Returns:
            Dicionário com status e detalhes
        """
        if contrato.tipo_correcao == TipoCorrecao.FIXO:
            return {
                'precisa_reajuste': False,
                'motivo': 'Contrato sem correção monetária (valor fixo)'
            }

        hoje = timezone.now().date()
        data_proximo = contrato.data_proximo_reajuste

        if not data_proximo:
            return {
                'precisa_reajuste': False,
                'motivo': 'Data de reajuste não calculável'
            }

        # Verificar se já passou a data
        if hoje >= data_proximo:
            ciclo = contrato.ciclo_reajuste_atual + 1
            reajuste_existente = Reajuste.objects.filter(
                contrato=contrato,
                ciclo=ciclo,
                aplicado=True
            ).exists()

            if reajuste_existente:
                return {
                    'precisa_reajuste': False,
                    'motivo': f'Reajuste do ciclo {ciclo} já aplicado'
                }

            return {
                'precisa_reajuste': True,
                'ciclo': ciclo,
                'data_prevista': data_proximo,
                'dias_atraso': (hoje - data_proximo).days,
                'indice_tipo': contrato.tipo_correcao,
                'bloqueio_boleto': contrato.bloqueio_boleto_reajuste
            }

        return {
            'precisa_reajuste': False,
            'proximo_reajuste': data_proximo,
            'dias_restantes': (data_proximo - hoje).days
        }

    # =========================================================================
    # SIMULAÇÃO DE REAJUSTE
    # =========================================================================

    def simular_reajuste(
        self,
        contrato: Contrato,
        percentual: Optional[Decimal] = None,
        ciclo: Optional[int] = None
    ) -> Dict:
        """
        Simula o impacto de um reajuste no contrato.

        Args:
            contrato: Contrato a simular
            percentual: Percentual de reajuste (opcional, busca automático)
            ciclo: Ciclo a simular (opcional, usa próximo ciclo)

        Returns:
            Dicionário com simulação detalhada
        """
        if ciclo is None:
            ciclo = contrato.ciclo_reajuste_atual + 1

        # Calcular intervalo de parcelas do ciclo
        prazo = contrato.prazo_reajuste_meses
        parcela_inicial = (ciclo - 1) * prazo + 1
        parcela_final = min(ciclo * prazo, contrato.numero_parcelas)

        # Buscar percentual se não informado
        if percentual is None:
            # Calcular período para buscar índice
            if contrato.data_ultimo_reajuste:
                data_inicio = contrato.data_ultimo_reajuste
            else:
                data_inicio = contrato.data_contrato

            data_fim = data_inicio + relativedelta(months=prazo - 1)

            percentual = self.calcular_acumulado_periodo(
                contrato.tipo_correcao,
                data_inicio,
                data_fim
            )

            if percentual is None:
                return {
                    'sucesso': False,
                    'erro': f'Índice {contrato.tipo_correcao} não disponível para o período'
                }

        # Buscar parcelas não pagas do ciclo
        parcelas = Parcela.objects.filter(
            contrato=contrato,
            numero_parcela__gte=parcela_inicial,
            numero_parcela__lte=parcela_final,
            pago=False
        )

        fator = 1 + (Decimal(str(percentual)) / 100)

        simulacao_parcelas = []
        valor_anterior_total = Decimal('0.00')
        valor_novo_total = Decimal('0.00')

        for parcela in parcelas:
            valor_anterior = parcela.valor_atual
            valor_novo = valor_anterior * fator
            diferenca = valor_novo - valor_anterior

            simulacao_parcelas.append({
                'numero': parcela.numero_parcela,
                'vencimento': parcela.data_vencimento,
                'valor_anterior': valor_anterior,
                'valor_novo': valor_novo,
                'diferenca': diferenca
            })

            valor_anterior_total += valor_anterior
            valor_novo_total += valor_novo

        # Simular intermediárias do ciclo
        intermediarias = contrato.intermediarias.filter(
            paga=False,
            mes_vencimento__gte=parcela_inicial,
            mes_vencimento__lte=parcela_final
        )

        simulacao_intermediarias = []
        for inter in intermediarias:
            valor_anterior = inter.valor_atual
            valor_novo = valor_anterior * fator

            simulacao_intermediarias.append({
                'numero': inter.numero_sequencial,
                'mes': inter.mes_vencimento,
                'valor_anterior': valor_anterior,
                'valor_novo': valor_novo,
                'diferenca': valor_novo - valor_anterior
            })

        return {
            'sucesso': True,
            'contrato': contrato.numero_contrato,
            'ciclo': ciclo,
            'percentual': percentual,
            'indice_tipo': contrato.tipo_correcao,
            'parcela_inicial': parcela_inicial,
            'parcela_final': parcela_final,
            'total_parcelas': parcelas.count(),
            'parcelas': simulacao_parcelas,
            'intermediarias': simulacao_intermediarias,
            'valor_anterior_total': valor_anterior_total,
            'valor_novo_total': valor_novo_total,
            'diferenca_total': valor_novo_total - valor_anterior_total,
            'impacto_mensal_medio': (valor_novo_total - valor_anterior_total) / max(parcelas.count(), 1)
        }

    # =========================================================================
    # APLICAÇÃO DE REAJUSTE
    # =========================================================================

    @transaction.atomic
    def aplicar_reajuste(
        self,
        contrato: Contrato,
        percentual: Optional[Decimal] = None,
        indice_tipo: Optional[str] = None,
        ciclo: Optional[int] = None,
        manual: bool = False,
        observacoes: str = ''
    ) -> Dict:
        """
        Aplica o reajuste em um contrato.

        Args:
            contrato: Contrato a reajustar
            percentual: Percentual de reajuste (opcional, busca automático)
            indice_tipo: Tipo do índice (opcional, usa do contrato)
            ciclo: Ciclo do reajuste (opcional, usa próximo)
            manual: Se True, marca como aplicação manual
            observacoes: Observações sobre o reajuste

        Returns:
            Dicionário com resultado da aplicação
        """
        if ciclo is None:
            ciclo = contrato.ciclo_reajuste_atual + 1

        if indice_tipo is None:
            indice_tipo = contrato.tipo_correcao

        # Verificar se já existe reajuste para este ciclo
        reajuste_existente = Reajuste.objects.filter(
            contrato=contrato,
            ciclo=ciclo,
            aplicado=True
        ).first()

        if reajuste_existente:
            return {
                'sucesso': False,
                'erro': f'Reajuste do ciclo {ciclo} já foi aplicado em {reajuste_existente.data_aplicacao}'
            }

        # Calcular intervalo de parcelas
        prazo = contrato.prazo_reajuste_meses
        parcela_inicial = (ciclo - 1) * prazo + 1
        parcela_final = min(ciclo * prazo, contrato.numero_parcelas)

        # Buscar percentual se não informado
        if percentual is None:
            if contrato.data_ultimo_reajuste:
                data_inicio = contrato.data_ultimo_reajuste
            else:
                data_inicio = contrato.data_contrato

            data_fim = data_inicio + relativedelta(months=prazo - 1)

            percentual = self.calcular_acumulado_periodo(
                indice_tipo,
                data_inicio,
                data_fim
            )

            if percentual is None:
                return {
                    'sucesso': False,
                    'erro': f'Índice {indice_tipo} não disponível para o período'
                }

        try:
            # Criar registro de reajuste
            reajuste = Reajuste.objects.create(
                contrato=contrato,
                data_reajuste=timezone.now().date(),
                indice_tipo=indice_tipo,
                percentual=percentual,
                parcela_inicial=parcela_inicial,
                parcela_final=parcela_final,
                ciclo=ciclo,
                data_limite_boleto=timezone.now().date() + relativedelta(months=prazo),
                aplicado_manual=manual,
                observacoes=observacoes
            )

            # Aplicar o reajuste
            resultado = reajuste.aplicar_reajuste()

            if resultado.get('sucesso'):
                logger.info(
                    f"Reajuste aplicado: Contrato {contrato.numero_contrato}, "
                    f"Ciclo {ciclo}, {percentual}%, "
                    f"{resultado['parcelas_reajustadas']} parcelas"
                )

                return {
                    'sucesso': True,
                    'reajuste_id': reajuste.id,
                    'ciclo': ciclo,
                    'percentual': percentual,
                    'indice_tipo': indice_tipo,
                    'parcelas_reajustadas': resultado['parcelas_reajustadas'],
                    'valor_anterior': resultado['valor_anterior_total'],
                    'valor_novo': resultado['valor_novo_total'],
                    'diferenca': resultado['diferenca']
                }
            else:
                return resultado

        except Exception as e:
            logger.error(f"Erro ao aplicar reajuste: {e}")
            return {
                'sucesso': False,
                'erro': str(e)
            }

    @transaction.atomic
    def aplicar_reajuste_lote(
        self,
        contratos: List[Contrato],
        percentual: Optional[Decimal] = None,
        indice_tipo: Optional[str] = None
    ) -> Dict:
        """
        Aplica reajuste em lote para múltiplos contratos.

        Args:
            contratos: Lista de contratos
            percentual: Percentual fixo (opcional)
            indice_tipo: Tipo de índice (opcional)

        Returns:
            Dicionário com resumo da operação
        """
        resultados = {
            'total': len(contratos),
            'sucesso': 0,
            'falha': 0,
            'detalhes': []
        }

        for contrato in contratos:
            resultado = self.aplicar_reajuste(
                contrato=contrato,
                percentual=percentual,
                indice_tipo=indice_tipo or contrato.tipo_correcao
            )

            if resultado.get('sucesso'):
                resultados['sucesso'] += 1
            else:
                resultados['falha'] += 1

            resultados['detalhes'].append({
                'contrato': contrato.numero_contrato,
                **resultado
            })

        return resultados

    # =========================================================================
    # HISTÓRICO E RELATÓRIOS
    # =========================================================================

    def listar_reajustes_contrato(self, contrato: Contrato) -> List[Dict]:
        """
        Lista o histórico de reajustes de um contrato.

        Args:
            contrato: Contrato

        Returns:
            Lista de reajustes com detalhes
        """
        reajustes = Reajuste.objects.filter(contrato=contrato).order_by('ciclo')

        resultado = []
        for reajuste in reajustes:
            resultado.append({
                'id': reajuste.id,
                'ciclo': reajuste.ciclo,
                'data_reajuste': reajuste.data_reajuste,
                'indice_tipo': reajuste.indice_tipo,
                'percentual': reajuste.percentual,
                'parcela_inicial': reajuste.parcela_inicial,
                'parcela_final': reajuste.parcela_final,
                'aplicado': reajuste.aplicado,
                'data_aplicacao': reajuste.data_aplicacao,
                'aplicado_manual': reajuste.aplicado_manual,
                'observacoes': reajuste.observacoes
            })

        return resultado

    def gerar_relatorio_reajustes_periodo(
        self,
        data_inicio: date,
        data_fim: date,
        imobiliaria=None
    ) -> Dict:
        """
        Gera relatório de reajustes aplicados em um período.

        Args:
            data_inicio: Data inicial
            data_fim: Data final
            imobiliaria: Filtrar por imobiliária (opcional)

        Returns:
            Dicionário com relatório
        """
        from django.db.models import Sum, Count, Avg

        reajustes = Reajuste.objects.filter(
            data_reajuste__gte=data_inicio,
            data_reajuste__lte=data_fim,
            aplicado=True
        )

        if imobiliaria:
            reajustes = reajustes.filter(contrato__imobiliaria=imobiliaria)

        # Estatísticas gerais
        stats = reajustes.aggregate(
            total=Count('id'),
            percentual_medio=Avg('percentual'),
        )

        # Agrupar por índice
        por_indice = {}
        for tipo in ['IPCA', 'IGPM', 'INPC', 'INCC', 'IGPDI', 'TR', 'SELIC']:
            reaj_tipo = reajustes.filter(indice_tipo=tipo)
            if reaj_tipo.exists():
                por_indice[tipo] = {
                    'quantidade': reaj_tipo.count(),
                    'percentual_medio': reaj_tipo.aggregate(Avg('percentual'))['percentual__avg']
                }

        # Lista detalhada
        lista = []
        for reajuste in reajustes.select_related('contrato', 'contrato__imobiliaria'):
            lista.append({
                'contrato': reajuste.contrato.numero_contrato,
                'imobiliaria': reajuste.contrato.imobiliaria.nome,
                'ciclo': reajuste.ciclo,
                'indice': reajuste.indice_tipo,
                'percentual': reajuste.percentual,
                'data_aplicacao': reajuste.data_aplicacao
            })

        return {
            'periodo': {
                'inicio': data_inicio,
                'fim': data_fim
            },
            'total_reajustes': stats['total'],
            'percentual_medio': stats['percentual_medio'],
            'por_indice': por_indice,
            'reajustes': lista
        }


class IndiceEconomicoService:
    """
    Serviço para busca e importação de índices econômicos.

    Fontes:
    - IBGE (IPCA, INPC)
    - FGV (IGPM, IGPDI, INCC)
    - BCB (TR, SELIC)
    """

    def __init__(self):
        self.erros = []

    def buscar_indice_bcb(
        self,
        codigo_serie: int,
        data_inicio: date,
        data_fim: date
    ) -> List[Dict]:
        """
        Busca índice na API do Banco Central.

        Args:
            codigo_serie: Código da série temporal no BCB
            data_inicio: Data inicial
            data_fim: Data final

        Returns:
            Lista de valores
        """
        import requests

        # Códigos das séries no BCB
        # TR: 226
        # SELIC: 4189 (meta)

        url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo_serie}/dados"
        params = {
            'formato': 'json',
            'dataInicial': data_inicio.strftime('%d/%m/%Y'),
            'dataFinal': data_fim.strftime('%d/%m/%Y')
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            dados = response.json()

            resultado = []
            for item in dados:
                data = item.get('data', '').split('/')
                if len(data) == 3:
                    resultado.append({
                        'data': date(int(data[2]), int(data[1]), int(data[0])),
                        'valor': Decimal(str(item.get('valor', 0)))
                    })

            return resultado

        except Exception as e:
            self.erros.append(f"Erro ao buscar BCB: {e}")
            return []

    def importar_indice(
        self,
        tipo_indice: str,
        ano: int,
        mes: int,
        valor: Decimal,
        fonte: str = ''
    ) -> IndiceReajuste:
        """
        Importa um índice para o banco de dados.

        Args:
            tipo_indice: Tipo do índice
            ano: Ano
            mes: Mês
            valor: Valor percentual
            fonte: Fonte dos dados

        Returns:
            Objeto IndiceReajuste criado ou atualizado
        """
        indice, created = IndiceReajuste.objects.update_or_create(
            tipo_indice=tipo_indice,
            ano=ano,
            mes=mes,
            defaults={
                'valor': valor,
                'fonte': fonte,
                'data_importacao': timezone.now()
            }
        )

        return indice

    def importar_indices_periodo(
        self,
        tipo_indice: str,
        dados: List[Dict]
    ) -> Dict:
        """
        Importa múltiplos índices.

        Args:
            tipo_indice: Tipo do índice
            dados: Lista de dicionários com data e valor

        Returns:
            Resumo da importação
        """
        criados = 0
        atualizados = 0
        erros = 0

        for item in dados:
            try:
                data = item.get('data')
                valor = item.get('valor')

                if data and valor is not None:
                    _, created = IndiceReajuste.objects.update_or_create(
                        tipo_indice=tipo_indice,
                        ano=data.year,
                        mes=data.month,
                        defaults={
                            'valor': Decimal(str(valor)),
                            'fonte': 'API',
                            'data_importacao': timezone.now()
                        }
                    )

                    if created:
                        criados += 1
                    else:
                        atualizados += 1

            except Exception as e:
                erros += 1
                self.erros.append(str(e))

        return {
            'criados': criados,
            'atualizados': atualizados,
            'erros': erros,
            'total': len(dados)
        }
