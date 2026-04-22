"""
Comando de diagnóstico: valida geração de remessa CNAB via API BRCobrança.

Uso:
    python manage.py testar_api_cnab            # BB CNAB240 + CNAB400
    python manage.py testar_api_cnab --banco 237 --layout CNAB_400
    python manage.py testar_api_cnab --usar-db  # usa dados reais do banco

Sem --usar-db, usa payload mínimo sintético para testar a API sem tocar no banco.
"""
import json
import re
import requests
from django.core.management.base import BaseCommand
from django.conf import settings


BRCOBRANCA_URL = None  # resolvido em handle()

PAYLOAD_BASE = {
    'empresa_mae': 'Imobiliária Teste LTDA',
    'documento_cedente': '12345678000199',
    'agencia': '12341',
    'conta_corrente': '56789',
    'digito_conta': '0',
    'convenio': '0123456',
    'carteira': '18',
    'sequencial_remessa': 1,
    'pagamentos': [
        {
            'nosso_numero': '1',
            'numero': 'TESTE-001',
            'valor': 1500.00,
            'data_vencimento': '2025/12/31',
            'data_emissao': '2025/11/01',
            'nome_sacado': 'Comprador Teste',
            'documento_sacado': '12345678901',
            'endereco_sacado': 'Rua das Flores, 123',
            'bairro_sacado': 'Centro',
            'cep_sacado': '01000000',
            'cidade_sacado': 'São Paulo',
            'uf_sacado': 'SP',
            'identificacao_ocorrencia': '01',
        }
    ],
}

CENARIOS = [
    {
        'label': 'Banco do Brasil CNAB240',
        'bank': 'banco_brasil',
        'type': 'cnab240',
        'extras': {'variacao': '018'},
    },
    {
        'label': 'Banco do Brasil CNAB400',
        'bank': 'banco_brasil',
        'type': 'cnab400',
        'extras_remover': ['variacao'],
        'extras': {'variacao_carteira': '018', 'agencia': '1234'},
    },
    {
        'label': 'Bradesco CNAB400',
        'bank': 'bradesco',
        'type': 'cnab400',
        'extras_remover': ['convenio', 'variacao'],
        'extras': {'codigo_empresa': '1234567', 'agencia': '1234'},
    },
    {
        'label': 'Sicoob CNAB400',
        'bank': 'sicoob',
        'type': 'cnab400',
        'extras_remover': ['variacao'],
        'extras': {
            'agencia': '3073',
            'conta_corrente': '12345678',  # Sicoob: 8 dígitos
            'convenio': '123456789',       # Sicoob: 9 dígitos
            'sequencial_remessa': '0000001',  # Sicoob: 7 dígitos (string)
        },
    },
]


class Command(BaseCommand):
    help = 'Valida geração de remessa CNAB contra a API BRCobrança real'

    def add_arguments(self, parser):
        parser.add_argument(
            '--banco',
            default=None,
            help='Código do banco (001=BB, 237=Bradesco, 756=Sicoob). Default: todos os cenários sintéticos.',
        )
        parser.add_argument(
            '--layout',
            default='CNAB_240',
            choices=['CNAB_240', 'CNAB_400'],
            help='Layout CNAB (default: CNAB_240)',
        )
        parser.add_argument(
            '--usar-db',
            action='store_true',
            default=False,
            help='Usa dados reais do banco de dados (primeira conta BB disponível)',
        )
        parser.add_argument(
            '--timeout',
            type=int,
            default=60,
            help='Timeout em segundos para cada chamada à API (default: 60)',
        )
        parser.add_argument(
            '--url',
            default=None,
            help='Override da URL da API (default: settings.BRCOBRANCA_URL)',
        )

    def handle(self, *args, **options):
        global BRCOBRANCA_URL
        BRCOBRANCA_URL = options.get('url') or getattr(
            settings, 'BRCOBRANCA_URL', 'http://localhost:9292'
        )

        self.stdout.write(self.style.HTTP_INFO('=' * 60))
        self.stdout.write(self.style.HTTP_INFO('DIAGNÓSTICO — API BRCobrança /api/remessa'))
        self.stdout.write(self.style.HTTP_INFO(f'API: {BRCOBRANCA_URL}'))
        self.stdout.write(self.style.HTTP_INFO('=' * 60))

        # Verificar conectividade primeiro
        if not self._verificar_conectividade(options['timeout']):
            return

        if options['usar_db']:
            self._testar_com_dados_db(options)
        else:
            self._testar_cenarios_sinteticos(options)

    def _verificar_conectividade(self, timeout):
        """Verifica se a API responde antes de tentar remessa."""
        try:
            resp = requests.get(f'{BRCOBRANCA_URL}/', timeout=timeout)
            self.stdout.write(f'\n[Conectividade] HTTP {resp.status_code} — API acessível')
        except requests.exceptions.ConnectionError:
            self.stderr.write(self.style.ERROR(
                f'\n[ERRO] Não foi possível conectar à API em {BRCOBRANCA_URL}\n'
                '  → Verifique se o container/serviço BRCobrança está rodando.'
            ))
            return False
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'\n[Conectividade] {e} — continuando mesmo assim...'))
        return True

    def _chamar_api(self, payload: dict, bank: str, tipo: str, timeout: int, label: str) -> bool:
        """Chama /api/remessa e imprime resultado. Retorna True se sucesso."""
        self.stdout.write(f'\n[{label}]')
        try:
            resp = requests.post(
                f'{BRCOBRANCA_URL}/api/remessa',
                files={'data': ('remessa.json', json.dumps(payload).encode('utf-8'), 'application/json')},
                data={'bank': bank, 'type': tipo},
                headers={'Accept': 'application/vnd.BoletoApi-v1+json'},
                timeout=timeout,
            )
        except requests.exceptions.ConnectionError as e:
            self.stderr.write(self.style.ERROR(f'  ERRO DE CONEXÃO: {e}'))
            return False
        except requests.exceptions.Timeout:
            self.stderr.write(self.style.ERROR(f'  TIMEOUT após {timeout}s'))
            return False

        if resp.status_code == 200 and resp.content:
            try:
                lines = resp.content.decode('latin-1', errors='replace').splitlines()
            except Exception:
                lines = []
            self.stdout.write(self.style.SUCCESS(
                f'  OK  HTTP 200 — {len(resp.content)} bytes / {len(lines)} linhas'
            ))
            if lines:
                self.stdout.write(f'  Linha 1 ({len(lines[0])} chars): {lines[0][:80]}...')
            return True
        else:
            self.stdout.write(self.style.ERROR(
                f'  FALHA  HTTP {resp.status_code}\n  Resposta: {resp.text[:300]}'
            ))
            return False

    def _testar_cenarios_sinteticos(self, options):
        """Testa usando payloads sintéticos (não altera o banco de dados)."""
        banco_filtro = options['banco']
        timeout = options['timeout']

        cenarios = CENARIOS
        if banco_filtro:
            from financeiro.services.cnab_service import BANCOS_BRCOBRANCA
            bank_id = BANCOS_BRCOBRANCA.get(banco_filtro, banco_filtro)
            layout = options['layout'].lower().replace('_', '')
            cenarios = [
                {
                    'label': f'{banco_filtro} {options["layout"]}',
                    'bank': bank_id,
                    'type': layout,
                    'extras': {},
                }
            ]

        ok = 0
        total = len(cenarios)
        for c in cenarios:
            payload = dict(PAYLOAD_BASE)
            payload['pagamentos'] = list(PAYLOAD_BASE['pagamentos'])
            for k in c.get('extras_remover', []):
                payload.pop(k, None)
            payload.update(c.get('extras', {}))
            if self._chamar_api(payload, c['bank'], c['type'], timeout, c['label']):
                ok += 1

        self.stdout.write('\n' + '=' * 60)
        if ok == total:
            self.stdout.write(self.style.SUCCESS(f'RESULTADO: {ok}/{total} cenários OK'))
        else:
            self.stdout.write(self.style.ERROR(f'RESULTADO: {ok}/{total} cenários OK — {total - ok} FALHA(S)'))

    def _testar_com_dados_db(self, options):
        """Testa usando conta bancária e parcelas reais do banco de dados."""
        from core.models import ContaBancaria
        from financeiro.models import Parcela, StatusBoleto
        from financeiro.services.cnab_service import CNABService, BANCOS_BRCOBRANCA

        layout = options['layout']
        timeout = options['timeout']
        banco_filtro = options['banco'] or '001'

        conta = ContaBancaria.objects.filter(banco=banco_filtro).first()
        if not conta:
            self.stderr.write(self.style.ERROR(
                f'Nenhuma ContaBancaria encontrada para banco={banco_filtro}'
            ))
            return

        self.stdout.write(f'\nConta: {conta} (banco={conta.banco})')

        parcelas = list(
            Parcela.objects.filter(
                conta_bancaria=conta,
                status_boleto=StatusBoleto.GERADO,
                pago=False,
            ).select_related('contrato', 'contrato__comprador', 'contrato__imobiliaria')[:3]
        )

        if not parcelas:
            self.stdout.write(self.style.WARNING(
                '  Nenhuma parcela com boleto gerado. Usando payload sintético como fallback.'
            ))
            self._testar_cenarios_sinteticos(options)
            return

        self.stdout.write(f'Parcelas: {len(parcelas)} encontradas')
        service = CNABService()

        self.stdout.write(f'\n[DB — {conta.get_banco_display()} {layout}]')
        resultado = service.gerar_remessa(
            parcelas=parcelas,
            conta_bancaria=conta,
            layout=layout,
        )

        if resultado.get('sucesso'):
            arq = resultado['arquivo_remessa']
            self.stdout.write(self.style.SUCCESS(
                f'  OK  Remessa #{resultado["numero_remessa"]} gerada — '
                f'{resultado["quantidade_boletos"]} boletos / R$ {resultado["valor_total"]:.2f}'
            ))
            self.stdout.write(f'  Arquivo: {arq.nome_arquivo}')
            # Limpar o registro de teste para não poluir o banco
            arq.delete()
            self.stdout.write('  (Registro de teste removido do banco)')
        else:
            self.stdout.write(self.style.ERROR(f'  FALHA: {resultado.get("erro")}'))
