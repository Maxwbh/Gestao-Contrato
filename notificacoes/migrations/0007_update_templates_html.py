"""
Migration 0007: Atualiza corpo_html dos templates padrão de boleto

Aplica o novo layout HTML responsivo (table-based, inline CSS) nos quatro
templates globais (imobiliaria=None):
  - BOLETO_CRIADO   — verde
  - BOLETO_5_DIAS   — azul (lembrete)
  - BOLETO_VENCE_AMANHA — laranja (urgente)
  - BOLETO_VENCEU_ONTEM — vermelho (vencido)
"""

from django.db import migrations


HTML_BOLETO_CRIADO = """\
<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f6f8;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f8;padding:30px 0;">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0"
           style="max-width:600px;width:100%;background:#fff;border-radius:8px;
                  overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">
      <tr>
        <td style="background:#27ae60;padding:28px 32px;text-align:center;">
          <div style="font-size:32px;margin-bottom:8px;">&#127968;</div>
          <h1 style="margin:0;color:#fff;font-size:22px;">Boleto Gerado</h1>
          <p style="margin:6px 0 0;color:rgba(255,255,255,.85);font-size:14px;">
            Ol&#225;, %%NOMECOMPRADOR%%! Seu boleto est&#225; dispon&#237;vel para pagamento.
          </p>
        </td>
      </tr>
      <tr>
        <td style="padding:28px 32px;">
          <table width="100%" cellpadding="0" cellspacing="0"
                 style="border:1px solid #e8eaed;border-radius:6px;overflow:hidden;">
            <tr><td style="background:#f8f9fa;padding:12px 16px;" colspan="2">
              <span style="font-size:12px;font-weight:700;color:#888;text-transform:uppercase;">Detalhes do Boleto</span>
            </td></tr>
            <tr>
              <td style="padding:8px 16px;color:#555;font-size:14px;border-bottom:1px solid #f0f0f0;"><strong>Contrato:</strong></td>
              <td style="padding:8px 16px;color:#222;font-size:14px;border-bottom:1px solid #f0f0f0;text-align:right;">%%NUMEROCONTRATO%%</td>
            </tr>
            <tr>
              <td style="padding:8px 16px;color:#555;font-size:14px;border-bottom:1px solid #f0f0f0;"><strong>Im&#243;vel:</strong></td>
              <td style="padding:8px 16px;color:#222;font-size:14px;border-bottom:1px solid #f0f0f0;text-align:right;">%%IMOVEL%% &#8212; %%LOTEAMENTO%%</td>
            </tr>
            <tr>
              <td style="padding:8px 16px;color:#555;font-size:14px;border-bottom:1px solid #f0f0f0;"><strong>Parcela:</strong></td>
              <td style="padding:8px 16px;color:#222;font-size:14px;border-bottom:1px solid #f0f0f0;text-align:right;">%%PARCELA%%</td>
            </tr>
            <tr>
              <td style="padding:8px 16px;color:#555;font-size:14px;border-bottom:1px solid #f0f0f0;"><strong>Vencimento:</strong></td>
              <td style="padding:8px 16px;color:#222;font-size:14px;border-bottom:1px solid #f0f0f0;text-align:right;">%%DATAVENCIMENTO%%</td>
            </tr>
            <tr>
              <td style="padding:8px 16px;color:#555;font-size:14px;"><strong>Valor:</strong></td>
              <td style="padding:8px 16px;font-size:18px;color:#27ae60;font-weight:700;text-align:right;">%%VALORBOLETO%%</td>
            </tr>
          </table>
          <div style="background:#f8f9fa;padding:12px 16px;border-radius:6px;margin:20px 0;">
            <p style="margin:0 0 6px;font-size:12px;font-weight:700;color:#888;text-transform:uppercase;">Linha Digit&#225;vel</p>
            <code style="font-size:13px;word-break:break-all;color:#333;">%%LINHADIGITAVEL%%</code>
          </div>
          <p style="color:#666;font-size:13px;">O boleto segue em anexo para sua comodidade.</p>
        </td>
      </tr>
      <tr>
        <td style="background:#f8f9fa;padding:16px 32px;text-align:center;border-top:1px solid #e8eaed;">
          <p style="margin:0;font-size:13px;font-weight:700;color:#444;">%%NOMEIMOBILIARIA%%</p>
          <p style="margin:4px 0 0;font-size:12px;color:#888;">%%TELEFONEIMOBILIARIA%% &nbsp;|&nbsp; %%EMAILIMOBILIARIA%%</p>
          <p style="margin:8px 0 0;font-size:11px;color:#bbb;">Voc&#234; recebe este e-mail por ter uma parcela em aberto.</p>
        </td>
      </tr>
    </table>
  </td></tr>
</table>
</body>
</html>"""


HTML_BOLETO_5_DIAS = """\
<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f6f8;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f8;padding:30px 0;">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0"
           style="max-width:600px;width:100%;background:#fff;border-radius:8px;
                  overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">
      <tr>
        <td style="background:#2980b9;padding:28px 32px;text-align:center;">
          <div style="font-size:32px;margin-bottom:8px;">&#128197;</div>
          <h1 style="margin:0;color:#fff;font-size:22px;">Lembrete de Vencimento</h1>
          <p style="margin:6px 0 0;color:rgba(255,255,255,.85);font-size:14px;">
            Ol&#225;, %%NOMECOMPRADOR%%! Seu boleto vence em 5 dias.
          </p>
        </td>
      </tr>
      <tr>
        <td style="padding:28px 32px;">
          <table width="100%" cellpadding="0" cellspacing="0"
                 style="border:1px solid #e8eaed;border-radius:6px;overflow:hidden;">
            <tr><td style="background:#f8f9fa;padding:12px 16px;" colspan="2">
              <span style="font-size:12px;font-weight:700;color:#888;text-transform:uppercase;">Detalhes do Boleto</span>
            </td></tr>
            <tr>
              <td style="padding:8px 16px;color:#555;font-size:14px;border-bottom:1px solid #f0f0f0;"><strong>Contrato:</strong></td>
              <td style="padding:8px 16px;color:#222;font-size:14px;border-bottom:1px solid #f0f0f0;text-align:right;">%%NUMEROCONTRATO%%</td>
            </tr>
            <tr>
              <td style="padding:8px 16px;color:#555;font-size:14px;border-bottom:1px solid #f0f0f0;"><strong>Parcela:</strong></td>
              <td style="padding:8px 16px;color:#222;font-size:14px;border-bottom:1px solid #f0f0f0;text-align:right;">%%PARCELA%%</td>
            </tr>
            <tr>
              <td style="padding:8px 16px;color:#555;font-size:14px;border-bottom:1px solid #f0f0f0;"><strong>Vencimento:</strong></td>
              <td style="padding:8px 16px;color:#222;font-size:14px;border-bottom:1px solid #f0f0f0;text-align:right;">%%DATAVENCIMENTO%%</td>
            </tr>
            <tr>
              <td style="padding:8px 16px;color:#555;font-size:14px;"><strong>Valor:</strong></td>
              <td style="padding:8px 16px;font-size:18px;color:#27ae60;font-weight:700;text-align:right;">%%VALORBOLETO%%</td>
            </tr>
          </table>
          <div style="background:#2980b9;color:#fff;padding:12px 16px;border-radius:6px;margin:20px 0;font-size:13px;">
            Efetue o pagamento at&#233; %%DATAVENCIMENTO%% para evitar juros e multa.
          </div>
          <div style="background:#f8f9fa;padding:12px 16px;border-radius:6px;margin:16px 0;">
            <p style="margin:0 0 6px;font-size:12px;font-weight:700;color:#888;text-transform:uppercase;">Linha Digit&#225;vel</p>
            <code style="font-size:13px;word-break:break-all;color:#333;">%%LINHADIGITAVEL%%</code>
          </div>
          <p style="color:#666;font-size:13px;">O boleto segue em anexo para sua comodidade.</p>
        </td>
      </tr>
      <tr>
        <td style="background:#f8f9fa;padding:16px 32px;text-align:center;border-top:1px solid #e8eaed;">
          <p style="margin:0;font-size:13px;font-weight:700;color:#444;">%%NOMEIMOBILIARIA%%</p>
          <p style="margin:4px 0 0;font-size:12px;color:#888;">%%TELEFONEIMOBILIARIA%% &nbsp;|&nbsp; %%EMAILIMOBILIARIA%%</p>
          <p style="margin:8px 0 0;font-size:11px;color:#bbb;">Voc&#234; recebe este e-mail por ter uma parcela em aberto.</p>
        </td>
      </tr>
    </table>
  </td></tr>
</table>
</body>
</html>"""


HTML_BOLETO_VENCE_AMANHA = """\
<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f6f8;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f8;padding:30px 0;">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0"
           style="max-width:600px;width:100%;background:#fff;border-radius:8px;
                  overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">
      <tr>
        <td style="background:#e67e22;padding:28px 32px;text-align:center;">
          <div style="font-size:32px;margin-bottom:8px;">&#9200;</div>
          <h1 style="margin:0;color:#fff;font-size:22px;">Boleto Vence AMANH&#195;!</h1>
          <p style="margin:6px 0 0;color:rgba(255,255,255,.85);font-size:14px;">
            Ol&#225;, %%NOMECOMPRADOR%%! Aten&#231;&#227;o: seu boleto vence amanh&#227;.
          </p>
        </td>
      </tr>
      <tr>
        <td style="padding:28px 32px;">
          <table width="100%" cellpadding="0" cellspacing="0"
                 style="border:1px solid #e8eaed;border-radius:6px;overflow:hidden;">
            <tr><td style="background:#f8f9fa;padding:12px 16px;" colspan="2">
              <span style="font-size:12px;font-weight:700;color:#888;text-transform:uppercase;">Detalhes do Boleto</span>
            </td></tr>
            <tr>
              <td style="padding:8px 16px;color:#555;font-size:14px;border-bottom:1px solid #f0f0f0;"><strong>Contrato:</strong></td>
              <td style="padding:8px 16px;color:#222;font-size:14px;border-bottom:1px solid #f0f0f0;text-align:right;">%%NUMEROCONTRATO%%</td>
            </tr>
            <tr>
              <td style="padding:8px 16px;color:#555;font-size:14px;border-bottom:1px solid #f0f0f0;"><strong>Parcela:</strong></td>
              <td style="padding:8px 16px;color:#222;font-size:14px;border-bottom:1px solid #f0f0f0;text-align:right;">%%PARCELA%%</td>
            </tr>
            <tr>
              <td style="padding:8px 16px;color:#555;font-size:14px;border-bottom:1px solid #f0f0f0;"><strong>Vencimento:</strong></td>
              <td style="padding:8px 16px;color:#e67e22;font-size:14px;font-weight:700;border-bottom:1px solid #f0f0f0;text-align:right;">%%DATAVENCIMENTO%% (AMANH&#195;)</td>
            </tr>
            <tr>
              <td style="padding:8px 16px;color:#555;font-size:14px;"><strong>Valor:</strong></td>
              <td style="padding:8px 16px;font-size:18px;color:#27ae60;font-weight:700;text-align:right;">%%VALORBOLETO%%</td>
            </tr>
          </table>
          <div style="background:#e67e22;color:#fff;padding:12px 16px;border-radius:6px;margin:20px 0;font-size:13px;">
            Pague hoje para evitar multas e juros a partir de amanh&#227;!
          </div>
          <div style="background:#f8f9fa;padding:12px 16px;border-radius:6px;margin:16px 0;">
            <p style="margin:0 0 6px;font-size:12px;font-weight:700;color:#888;text-transform:uppercase;">Linha Digit&#225;vel</p>
            <code style="font-size:13px;word-break:break-all;color:#333;">%%LINHADIGITAVEL%%</code>
          </div>
          <p style="color:#666;font-size:13px;">O boleto segue em anexo para sua comodidade.</p>
        </td>
      </tr>
      <tr>
        <td style="background:#f8f9fa;padding:16px 32px;text-align:center;border-top:1px solid #e8eaed;">
          <p style="margin:0;font-size:13px;font-weight:700;color:#444;">%%NOMEIMOBILIARIA%%</p>
          <p style="margin:4px 0 0;font-size:12px;color:#888;">%%TELEFONEIMOBILIARIA%% &nbsp;|&nbsp; %%EMAILIMOBILIARIA%%</p>
          <p style="margin:8px 0 0;font-size:11px;color:#bbb;">Voc&#234; recebe este e-mail por ter uma parcela em aberto.</p>
        </td>
      </tr>
    </table>
  </td></tr>
</table>
</body>
</html>"""


HTML_BOLETO_VENCEU_ONTEM = """\
<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f6f8;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f8;padding:30px 0;">
  <tr><td align="center">
    <table width="600" cellpadding="0" cellspacing="0"
           style="max-width:600px;width:100%;background:#fff;border-radius:8px;
                  overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.08);">
      <tr>
        <td style="background:#c0392b;padding:28px 32px;text-align:center;">
          <div style="font-size:32px;margin-bottom:8px;">&#9888;&#65039;</div>
          <h1 style="margin:0;color:#fff;font-size:22px;">Boleto Vencido</h1>
          <p style="margin:6px 0 0;color:rgba(255,255,255,.85);font-size:14px;">
            Ol&#225;, %%NOMECOMPRADOR%%! Identificamos um boleto em atraso.
          </p>
        </td>
      </tr>
      <tr>
        <td style="padding:28px 32px;">
          <table width="100%" cellpadding="0" cellspacing="0"
                 style="border:1px solid #e8eaed;border-radius:6px;overflow:hidden;">
            <tr><td style="background:#f8f9fa;padding:12px 16px;" colspan="2">
              <span style="font-size:12px;font-weight:700;color:#888;text-transform:uppercase;">Detalhes do Boleto</span>
            </td></tr>
            <tr>
              <td style="padding:8px 16px;color:#555;font-size:14px;border-bottom:1px solid #f0f0f0;"><strong>Contrato:</strong></td>
              <td style="padding:8px 16px;color:#222;font-size:14px;border-bottom:1px solid #f0f0f0;text-align:right;">%%NUMEROCONTRATO%%</td>
            </tr>
            <tr>
              <td style="padding:8px 16px;color:#555;font-size:14px;border-bottom:1px solid #f0f0f0;"><strong>Parcela:</strong></td>
              <td style="padding:8px 16px;color:#222;font-size:14px;border-bottom:1px solid #f0f0f0;text-align:right;">%%PARCELA%%</td>
            </tr>
            <tr>
              <td style="padding:8px 16px;color:#555;font-size:14px;border-bottom:1px solid #f0f0f0;"><strong>Venceu em:</strong></td>
              <td style="padding:8px 16px;color:#c0392b;font-size:14px;font-weight:700;border-bottom:1px solid #f0f0f0;text-align:right;">%%DATAVENCIMENTO%%</td>
            </tr>
            <tr>
              <td style="padding:8px 16px;color:#555;font-size:14px;"><strong>Valor:</strong></td>
              <td style="padding:8px 16px;font-size:18px;color:#c0392b;font-weight:700;text-align:right;">%%VALORBOLETO%%</td>
            </tr>
          </table>
          <div style="background:#c0392b;color:#fff;padding:12px 16px;border-radius:6px;margin:20px 0;font-size:13px;">
            Regularize o pagamento para evitar acr&#233;scimo de juros, multa e protesto do t&#237;tulo.
          </div>
          <p style="color:#666;font-size:13px;">
            Entre em contato conosco: <strong>%%TELEFONEIMOBILIARIA%%</strong> | %%EMAILIMOBILIARIA%%
          </p>
        </td>
      </tr>
      <tr>
        <td style="background:#f8f9fa;padding:16px 32px;text-align:center;border-top:1px solid #e8eaed;">
          <p style="margin:0;font-size:13px;font-weight:700;color:#444;">%%NOMEIMOBILIARIA%%</p>
          <p style="margin:4px 0 0;font-size:12px;color:#888;">%%TELEFONEIMOBILIARIA%% &nbsp;|&nbsp; %%EMAILIMOBILIARIA%%</p>
          <p style="margin:8px 0 0;font-size:11px;color:#bbb;">Voc&#234; recebe este e-mail por ter uma parcela em aberto.</p>
        </td>
      </tr>
    </table>
  </td></tr>
</table>
</body>
</html>"""


UPDATES = {
    'BOLETO_CRIADO': HTML_BOLETO_CRIADO,
    'BOLETO_5_DIAS': HTML_BOLETO_5_DIAS,
    'BOLETO_VENCE_AMANHA': HTML_BOLETO_VENCE_AMANHA,
    'BOLETO_VENCEU_ONTEM': HTML_BOLETO_VENCEU_ONTEM,
}


def update_templates_html(apps, schema_editor):
    TemplateNotificacao = apps.get_model('notificacoes', 'TemplateNotificacao')
    for codigo, html in UPDATES.items():
        TemplateNotificacao.objects.filter(
            codigo=codigo,
            imobiliaria=None,
        ).update(corpo_html=html)


def reverse_templates_html(apps, schema_editor):
    TemplateNotificacao = apps.get_model('notificacoes', 'TemplateNotificacao')
    # BOLETO_CRIADO tinha HTML básico; os demais tinham corpo_html vazio
    TemplateNotificacao.objects.filter(
        codigo__in=list(UPDATES.keys()),
        imobiliaria=None,
    ).update(corpo_html='')


class Migration(migrations.Migration):

    dependencies = [
        ('notificacoes', '0006_notificacao_rastreamento_entrega'),
    ]

    operations = [
        migrations.RunPython(
            update_templates_html,
            reverse_code=reverse_templates_html,
        ),
    ]
