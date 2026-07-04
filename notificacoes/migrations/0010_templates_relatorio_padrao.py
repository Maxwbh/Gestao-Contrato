"""
Data migration: cria os templates HTML padrão para Relatório Semanal e Mensal.

Usa get_or_create para não sobrescrever templates já personalizados pelos usuários.
"""
from django.db import migrations


HTML_SEMANAL = """\
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Relatório Semanal</title>
<style>
  body{margin:0;padding:0;background:#f4f6f9;font-family:Arial,Helvetica,sans-serif;color:#333}
  .wrap{max-width:600px;margin:32px auto;background:#fff;border-radius:8px;overflow:hidden;
        box-shadow:0 2px 8px rgba(0,0,0,.1)}
  .header{background:#1565C0;padding:28px 32px;text-align:center}
  .header h1{margin:0;color:#fff;font-size:22px;font-weight:700;letter-spacing:.5px}
  .header p{margin:6px 0 0;color:#BBDEFB;font-size:13px}
  .body{padding:28px 32px}
  .periodo{background:#E3F2FD;border-left:4px solid #1565C0;padding:10px 16px;
            border-radius:4px;margin-bottom:24px;font-size:13px;color:#1565C0}
  .cards{display:table;width:100%;border-collapse:separate;border-spacing:12px}
  .card-row{display:table-row}
  .card{display:table-cell;width:33%;background:#f8fafc;border:1px solid #e0e7ef;
        border-radius:6px;padding:16px;text-align:center;vertical-align:top}
  .card .label{font-size:11px;text-transform:uppercase;letter-spacing:.8px;color:#7a8ba0;
               font-weight:600;margin-bottom:6px}
  .card .count{font-size:26px;font-weight:700;margin-bottom:2px}
  .card .value{font-size:13px;color:#555}
  .card.green .count{color:#2E7D32}
  .card.red   .count{color:#C62828}
  .card.orange .count{color:#E65100}
  .footer{background:#f0f4f8;padding:18px 32px;text-align:center;
          font-size:11px;color:#9aabbc}
  .footer a{color:#1565C0;text-decoration:none}
  @media(max-width:480px){
    .cards,.card-row,.card{display:block;width:100%;box-sizing:border-box}
    .card{margin-bottom:10px}
  }
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <h1>Relatório Semanal</h1>
    <p>%%NOMEIMOBILIARIA%%</p>
  </div>
  <div class="body">
    <div class="periodo">
      📅 Período: <strong>%%PERIODORELATORIO%%</strong>
    </div>

    <table style="width:100%;border-collapse:separate;border-spacing:10px">
      <tr>
        <!-- Card Recebimentos -->
        <td style="width:33%;background:#f8fafc;border:1px solid #c8e6c9;border-radius:6px;
                   padding:16px;text-align:center;vertical-align:top">
          <div style="font-size:11px;text-transform:uppercase;letter-spacing:.8px;
                      color:#7a8ba0;font-weight:600;margin-bottom:6px">✅ Recebimentos</div>
          <div style="font-size:28px;font-weight:700;color:#2E7D32">%%QTDRECEBIMENTOS%%</div>
          <div style="font-size:13px;color:#555;margin-top:2px">%%VALORRECEBIMENTOS%%</div>
        </td>
        <!-- Card Inadimplência -->
        <td style="width:33%;background:#f8fafc;border:1px solid #ffcdd2;border-radius:6px;
                   padding:16px;text-align:center;vertical-align:top">
          <div style="font-size:11px;text-transform:uppercase;letter-spacing:.8px;
                      color:#7a8ba0;font-weight:600;margin-bottom:6px">⚠️ Inadimplência</div>
          <div style="font-size:28px;font-weight:700;color:#C62828">%%QTDINADIMPLENTES%%</div>
          <div style="font-size:13px;color:#555;margin-top:2px">%%VALORINADIMPLENTES%%</div>
        </td>
        <!-- Card A Vencer -->
        <td style="width:33%;background:#f8fafc;border:1px solid #ffe0b2;border-radius:6px;
                   padding:16px;text-align:center;vertical-align:top">
          <div style="font-size:11px;text-transform:uppercase;letter-spacing:.8px;
                      color:#7a8ba0;font-weight:600;margin-bottom:6px">🔔 A Vencer (7d)</div>
          <div style="font-size:28px;font-weight:700;color:#E65100">%%QTDAVENCER%%</div>
          <div style="font-size:13px;color:#555;margin-top:2px">%%VALORAVENCER%%</div>
        </td>
      </tr>
    </table>

    <p style="margin-top:24px;font-size:13px;color:#666;line-height:1.6">
      Este relatório foi gerado automaticamente pelo sistema em <strong>%%DATAATUAL%%</strong>.
      Em caso de dúvidas, entre em contato com o suporte.
    </p>
  </div>
  <div style="background:#f0f4f8;padding:14px 32px;text-align:center;
              font-size:11px;color:#9aabbc">
    Gestão de Contratos &mdash; Relatório automático &mdash; Não responda este e-mail
  </div>
</div>
</body>
</html>
"""

HTML_MENSAL = """\
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Relatório Mensal</title>
<style>
  body{margin:0;padding:0;background:#f4f6f9;font-family:Arial,Helvetica,sans-serif;color:#333}
  .wrap{max-width:680px;margin:32px auto;background:#fff;border-radius:8px;overflow:hidden;
        box-shadow:0 2px 8px rgba(0,0,0,.1)}
  .header{background:#1B5E20;padding:28px 32px;text-align:center}
  .header h1{margin:0;color:#fff;font-size:22px;font-weight:700;letter-spacing:.5px}
  .header p{margin:6px 0 0;color:#C8E6C9;font-size:13px}
  .body{padding:28px 32px}
  .periodo{background:#E8F5E9;border-left:4px solid #2E7D32;padding:10px 16px;
            border-radius:4px;margin-bottom:24px;font-size:13px;color:#1B5E20}
  .section-title{font-size:13px;font-weight:700;text-transform:uppercase;
                 letter-spacing:.8px;color:#555;margin:24px 0 12px;
                 border-bottom:1px solid #e0e7ef;padding-bottom:6px}
</style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <h1>Relatório Mensal Consolidado</h1>
    <p>%%NOMECONTABILIDADE%% &mdash; %%MESREFERENCIA%%</p>
  </div>
  <div class="body">
    <div class="periodo">
      📅 Período: <strong>%%PERIODORELATORIO%%</strong>
    </div>

    <!-- KPI Cards -->
    <div class="section-title">Resumo do Mês</div>
    <table style="width:100%;border-collapse:separate;border-spacing:8px">
      <tr>
        <td style="width:25%;background:#E3F2FD;border:1px solid #90CAF9;border-radius:6px;
                   padding:14px 10px;text-align:center;vertical-align:top">
          <div style="font-size:10px;text-transform:uppercase;letter-spacing:.7px;
                      color:#1565C0;font-weight:700;margin-bottom:5px">Contratos Ativos</div>
          <div style="font-size:26px;font-weight:700;color:#1565C0">%%QTDCONTRATOSATIVOS%%</div>
        </td>
        <td style="width:25%;background:#E8F5E9;border:1px solid #A5D6A7;border-radius:6px;
                   padding:14px 10px;text-align:center;vertical-align:top">
          <div style="font-size:10px;text-transform:uppercase;letter-spacing:.7px;
                      color:#2E7D32;font-weight:700;margin-bottom:5px">Recebimentos</div>
          <div style="font-size:22px;font-weight:700;color:#2E7D32">%%QTDRECEBIMENTOS%%</div>
          <div style="font-size:12px;color:#555;margin-top:2px">%%VALORRECEBIMENTOS%%</div>
        </td>
        <td style="width:25%;background:#FFF3E0;border:1px solid #FFCC80;border-radius:6px;
                   padding:14px 10px;text-align:center;vertical-align:top">
          <div style="font-size:10px;text-transform:uppercase;letter-spacing:.7px;
                      color:#E65100;font-weight:700;margin-bottom:5px">Inadimplência</div>
          <div style="font-size:22px;font-weight:700;color:#C62828">%%QTDINADIMPLENTES%%</div>
          <div style="font-size:12px;color:#555;margin-top:2px">%%VALORINADIMPLENTES%%</div>
        </td>
        <td style="width:25%;background:#F3E5F5;border:1px solid #CE93D8;border-radius:6px;
                   padding:14px 10px;text-align:center;vertical-align:top">
          <div style="font-size:10px;text-transform:uppercase;letter-spacing:.7px;
                      color:#6A1B9A;font-weight:700;margin-bottom:5px">Reajustes</div>
          <div style="font-size:26px;font-weight:700;color:#6A1B9A">%%QTDREAJUSTES%%</div>
        </td>
      </tr>
    </table>

    <!-- Tabela por imobiliária -->
    <div class="section-title" style="margin-top:28px">Detalhamento por Imobiliária</div>
    %%TABELAIMOBILIARIAS%%

    <p style="margin-top:24px;font-size:12px;color:#777;line-height:1.6">
      Relatório gerado automaticamente em <strong>%%DATAATUAL%%</strong>.
      Os valores refletem o mês de referência <strong>%%MESREFERENCIA%%</strong>.
    </p>
  </div>
  <div style="background:#f0f4f8;padding:14px 32px;text-align:center;
              font-size:11px;color:#9aabbc">
    Gestão de Contratos &mdash; Relatório automático &mdash; Não responda este e-mail
  </div>
</div>
</body>
</html>
"""

ASSUNTO_SEMANAL = "Relatório Semanal — %%NOMEIMOBILIARIA%% — %%PERIODORELATORIO%%"
ASSUNTO_MENSAL = "Relatório Mensal — %%NOMECONTABILIDADE%% — %%MESREFERENCIA%%"


def criar_templates(apps, schema_editor):
    TemplateNotificacao = apps.get_model('notificacoes', 'TemplateNotificacao')

    TemplateNotificacao.objects.get_or_create(
        codigo='RELATORIO_SEMANAL',
        imobiliaria=None,
        defaults=dict(
            nome='Relatório Semanal (padrão)',
            assunto=ASSUNTO_SEMANAL,
            corpo_html=HTML_SEMANAL,
            ativo=True,
        ),
    )

    TemplateNotificacao.objects.get_or_create(
        codigo='RELATORIO_MENSAL',
        imobiliaria=None,
        defaults=dict(
            nome='Relatório Mensal Consolidado (padrão)',
            assunto=ASSUNTO_MENSAL,
            corpo_html=HTML_MENSAL,
            ativo=True,
        ),
    )


def remover_templates(apps, schema_editor):
    TemplateNotificacao = apps.get_model('notificacoes', 'TemplateNotificacao')
    TemplateNotificacao.objects.filter(
        codigo__in=['RELATORIO_SEMANAL', 'RELATORIO_MENSAL'],
        imobiliaria=None,
        nome__in=[
            'Relatório Semanal (padrão)',
            'Relatório Mensal Consolidado (padrão)',
        ],
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('notificacoes', '0009_sessaoconversawhatsapp'),
    ]

    operations = [
        migrations.RunPython(criar_templates, remover_templates),
    ]
