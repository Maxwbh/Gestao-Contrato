"""
Conteúdo HTML e assuntos padrão para os e-mails de relatório.

Importado tanto pela data migration quanto pelo management command
`criar_templates_relatorio`, evitando duplicação.
"""

ASSUNTO_SEMANAL = "Relatório Semanal — %%NOMEIMOBILIARIA%% — %%PERIODORELATORIO%%"
ASSUNTO_MENSAL = "Relatório Mensal — %%NOMECONTABILIDADE%% — %%MESREFERENCIA%%"

HTML_SEMANAL = """\
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Relatório Semanal</title>
</head>
<body style="margin:0;padding:0;background:#f4f6f9;font-family:Arial,Helvetica,sans-serif;color:#333">
<div style="max-width:600px;margin:32px auto;background:#fff;border-radius:8px;overflow:hidden;
            box-shadow:0 2px 8px rgba(0,0,0,.1)">

  <!-- Cabeçalho -->
  <div style="background:#1565C0;padding:28px 32px;text-align:center">
    <h1 style="margin:0;color:#fff;font-size:22px;font-weight:700;letter-spacing:.5px">
      Relatório Semanal
    </h1>
    <p style="margin:6px 0 0;color:#BBDEFB;font-size:13px">%%NOMEIMOBILIARIA%%</p>
  </div>

  <!-- Corpo -->
  <div style="padding:28px 32px">

    <!-- Período -->
    <div style="background:#E3F2FD;border-left:4px solid #1565C0;padding:10px 16px;
                border-radius:4px;margin-bottom:24px;font-size:13px;color:#1565C0">
      📅 Período: <strong>%%PERIODORELATORIO%%</strong>
    </div>

    <!-- KPI Cards -->
    <table cellpadding="0" cellspacing="0" style="width:100%;border-collapse:separate;border-spacing:10px">
      <tr>
        <!-- Recebimentos -->
        <td style="width:33%;background:#f8fafc;border:1px solid #c8e6c9;border-radius:6px;
                   padding:16px 10px;text-align:center;vertical-align:top">
          <div style="font-size:10px;text-transform:uppercase;letter-spacing:.8px;
                      color:#7a8ba0;font-weight:700;margin-bottom:6px">✅ Recebimentos</div>
          <div style="font-size:28px;font-weight:700;color:#2E7D32;line-height:1.1">%%QTDRECEBIMENTOS%%</div>
          <div style="font-size:13px;color:#555;margin-top:4px">%%VALORRECEBIMENTOS%%</div>
        </td>
        <!-- Inadimplência -->
        <td style="width:33%;background:#f8fafc;border:1px solid #ffcdd2;border-radius:6px;
                   padding:16px 10px;text-align:center;vertical-align:top">
          <div style="font-size:10px;text-transform:uppercase;letter-spacing:.8px;
                      color:#7a8ba0;font-weight:700;margin-bottom:6px">⚠️ Inadimplência</div>
          <div style="font-size:28px;font-weight:700;color:#C62828;line-height:1.1">%%QTDINADIMPLENTES%%</div>
          <div style="font-size:13px;color:#555;margin-top:4px">%%VALORINADIMPLENTES%%</div>
        </td>
        <!-- A Vencer -->
        <td style="width:33%;background:#f8fafc;border:1px solid #ffe0b2;border-radius:6px;
                   padding:16px 10px;text-align:center;vertical-align:top">
          <div style="font-size:10px;text-transform:uppercase;letter-spacing:.8px;
                      color:#7a8ba0;font-weight:700;margin-bottom:6px">🔔 A Vencer (7d)</div>
          <div style="font-size:28px;font-weight:700;color:#E65100;line-height:1.1">%%QTDAVENCER%%</div>
          <div style="font-size:13px;color:#555;margin-top:4px">%%VALORAVENCER%%</div>
        </td>
      </tr>
    </table>

    <p style="margin-top:24px;font-size:13px;color:#666;line-height:1.6">
      Este relatório foi gerado automaticamente em <strong>%%DATAATUAL%%</strong>.
      Em caso de dúvidas, entre em contato com o suporte.
    </p>
  </div>

  <!-- Rodapé -->
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
</head>
<body style="margin:0;padding:0;background:#f4f6f9;font-family:Arial,Helvetica,sans-serif;color:#333">
<div style="max-width:680px;margin:32px auto;background:#fff;border-radius:8px;overflow:hidden;
            box-shadow:0 2px 8px rgba(0,0,0,.1)">

  <!-- Cabeçalho -->
  <div style="background:#1B5E20;padding:28px 32px;text-align:center">
    <h1 style="margin:0;color:#fff;font-size:22px;font-weight:700;letter-spacing:.5px">
      Relatório Mensal Consolidado
    </h1>
    <p style="margin:6px 0 0;color:#C8E6C9;font-size:13px">
      %%NOMECONTABILIDADE%% &mdash; %%MESREFERENCIA%%
    </p>
  </div>

  <!-- Corpo -->
  <div style="padding:28px 32px">

    <!-- Período -->
    <div style="background:#E8F5E9;border-left:4px solid #2E7D32;padding:10px 16px;
                border-radius:4px;margin-bottom:24px;font-size:13px;color:#1B5E20">
      📅 Período: <strong>%%PERIODORELATORIO%%</strong>
    </div>

    <!-- Título seção KPIs -->
    <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;
                color:#555;margin-bottom:12px;border-bottom:1px solid #e0e7ef;padding-bottom:6px">
      Resumo do Mês
    </div>

    <!-- KPI Cards -->
    <table cellpadding="0" cellspacing="0" style="width:100%;border-collapse:separate;border-spacing:8px">
      <tr>
        <td style="width:25%;background:#E3F2FD;border:1px solid #90CAF9;border-radius:6px;
                   padding:14px 8px;text-align:center;vertical-align:top">
          <div style="font-size:10px;text-transform:uppercase;letter-spacing:.7px;
                      color:#1565C0;font-weight:700;margin-bottom:5px">Contratos Ativos</div>
          <div style="font-size:26px;font-weight:700;color:#1565C0">%%QTDCONTRATOSATIVOS%%</div>
        </td>
        <td style="width:25%;background:#E8F5E9;border:1px solid #A5D6A7;border-radius:6px;
                   padding:14px 8px;text-align:center;vertical-align:top">
          <div style="font-size:10px;text-transform:uppercase;letter-spacing:.7px;
                      color:#2E7D32;font-weight:700;margin-bottom:5px">Recebimentos</div>
          <div style="font-size:22px;font-weight:700;color:#2E7D32">%%QTDRECEBIMENTOS%%</div>
          <div style="font-size:12px;color:#555;margin-top:3px">%%VALORRECEBIMENTOS%%</div>
        </td>
        <td style="width:25%;background:#FFF3E0;border:1px solid #FFCC80;border-radius:6px;
                   padding:14px 8px;text-align:center;vertical-align:top">
          <div style="font-size:10px;text-transform:uppercase;letter-spacing:.7px;
                      color:#E65100;font-weight:700;margin-bottom:5px">Inadimplência</div>
          <div style="font-size:22px;font-weight:700;color:#C62828">%%QTDINADIMPLENTES%%</div>
          <div style="font-size:12px;color:#555;margin-top:3px">%%VALORINADIMPLENTES%%</div>
        </td>
        <td style="width:25%;background:#F3E5F5;border:1px solid #CE93D8;border-radius:6px;
                   padding:14px 8px;text-align:center;vertical-align:top">
          <div style="font-size:10px;text-transform:uppercase;letter-spacing:.7px;
                      color:#6A1B9A;font-weight:700;margin-bottom:5px">Reajustes</div>
          <div style="font-size:26px;font-weight:700;color:#6A1B9A">%%QTDREAJUSTES%%</div>
        </td>
      </tr>
    </table>

    <!-- Tabela imobiliárias -->
    <div style="font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.8px;
                color:#555;margin:28px 0 12px;border-bottom:1px solid #e0e7ef;padding-bottom:6px">
      Detalhamento por Imobiliária
    </div>
    %%TABELAIMOBILIARIAS%%

    <p style="margin-top:24px;font-size:12px;color:#777;line-height:1.6">
      Relatório gerado automaticamente em <strong>%%DATAATUAL%%</strong>.
      Os valores refletem o mês de referência <strong>%%MESREFERENCIA%%</strong>.
    </p>
  </div>

  <!-- Rodapé -->
  <div style="background:#f0f4f8;padding:14px 32px;text-align:center;
              font-size:11px;color:#9aabbc">
    Gestão de Contratos &mdash; Relatório automático &mdash; Não responda este e-mail
  </div>
</div>
</body>
</html>
"""
