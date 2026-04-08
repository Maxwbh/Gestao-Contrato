# Consulta de CPF e Considerações LGPD

**Desenvolvedor:** Maxwell da Silva Oliveira
**Email:** maxwbh@gmail.com
**Empresa:** M&S do Brasil LTDA

## ⚖️ Aspectos Legais - LGPD

### O que diz a Lei Geral de Proteção de Dados (LGPD)?

A **Lei nº 13.709/2018** regula o tratamento de dados pessoais no Brasil. CPF é considerado um **dado pessoal sensível** e sua consulta/divulgação sem autorização configura violação da LGPD.

### ❌ O que NÃO é permitido:

1. **Consulta Pública de CPF sem consentimento**
   - APIs públicas que retornam nome, endereço, data de nascimento a partir do CPF
   - Scraping de dados da Receita Federal
   - Compra de bases de dados de terceiros não autorizados

2. **Compartilhamento não autorizado**
   - Venda de bases de CPF
   - Disponibilização de CPF em sistemas públicos
   - Transferência para terceiros sem consentimento

3. **Armazenamento excessivo**
   - Guardar CPF sem necessidade
   - Manter dados após término da relação contratual

### ✅ O que É permitido:

1. **Validação de CPF (dígitos verificadores)**
   - Algoritmo público para verificar se CPF é válido
   - Não acessa nenhuma base de dados externa
   - Implementado neste sistema

2. **Consulta com Consentimento**
   - Titular do dado autoriza expressamente
   - Finalidade específica e legítima
   - Prazo determinado

3. **Bases de Dados Privadas**
   - APIs comerciais autorizadas (Serasa, SPC, etc.)
   - Convênios com órgãos públicos
   - Contrato de prestação de serviço

## 🔍 Validação de CPF Implementada

### O que faz:

```javascript
// Valida se CPF é válido (dígitos verificadores)
const cpf = '123.456.789-09';
const valido = window.GestaoContratos.validarCPF(cpf);
// Retorna true ou false
```

### O que NÃO faz:

- ❌ Não consulta nome do titular
- ❌ Não consulta endereço
- ❌ Não consulta data de nascimento
- ❌ Não consulta situação na Receita Federal
- ❌ Não acessa nenhuma API externa

### Algoritmo de Validação:

A validação implementada segue o **algoritmo público dos Correios/Receita Federal**:

1. Verifica se tem 11 dígitos
2. Verifica se não são todos iguais (111.111.111-11 = inválido)
3. Calcula o primeiro dígito verificador
4. Calcula o segundo dígito verificador
5. Compara com os dígitos informados

**Código-fonte:** `static/js/custom.js:200-230`

## 🔐 APIs Comerciais Autorizadas

Se você precisa consultar dados a partir do CPF, considere estas opções **legais e autorizadas**:

### 1. Serasa Experian
- **Produto:** Serasa Consumidor API
- **Dados:** Nome, CPF, Score de crédito
- **Autorização:** Consentimento do titular via biometria facial
- **Custo:** Consultas pagas
- **Site:** https://www.serasaexperian.com.br/

### 2. SPC Brasil
- **Produto:** Consulta de Crédito
- **Dados:** Nome, CPF, restrições financeiras
- **Autorização:** Termo de consentimento assinado
- **Custo:** Plano mensal ou por consulta
- **Site:** https://www.spcbrasil.org.br/

### 3. Receita Federal (Consulta Situação Cadastral)
- **Serviço:** Consulta CPF
- **Dados:** Situação cadastral, nome (parcial)
- **Autorização:** Apenas para o próprio titular ou com procuração
- **Custo:** Gratuito
- **Site:** https://servicos.receita.fazenda.gov.br/

### 4. Boa Vista SCPC
- **Produto:** Consulta Completa
- **Dados:** Nome, endereço, score
- **Autorização:** Consentimento expresso
- **Custo:** Consultas pagas
- **Site:** https://www.boavistaservicos.com.br/

## 🛡️ Como Implementar Consulta LGPD-Compliant

### Passo 1: Obter Consentimento

```html
<!-- Exemplo de termo de consentimento -->
<form>
    <label>
        <input type="checkbox" name="consentimento_lgpd" required>
        Autorizo a consulta de meus dados cadastrais (CPF, nome, endereço)
        para fins de análise de crédito, conforme Lei 13.709/2018 (LGPD).
    </label>

    <label>
        <input type="checkbox" name="consentimento_terceiros" required>
        Autorizo o compartilhamento destes dados com bureaus de crédito
        (Serasa, SPC, Boa Vista) exclusivamente para esta finalidade.
    </label>

    <p>
        <strong>Finalidade:</strong> Análise de crédito para compra de imóvel<br>
        <strong>Prazo:</strong> 90 dias após conclusão da análise<br>
        <strong>Direitos:</strong> Acesso, correção, exclusão conforme LGPD Art. 18
    </p>
</form>
```

### Passo 2: Registrar Consentimento

```python
# models.py
class ConsentimentoLGPD(models.Model):
    comprador = models.ForeignKey(Comprador, on_delete=models.CASCADE)
    data_consentimento = models.DateTimeField(auto_now_add=True)
    finalidade = models.TextField()
    prazo_dias = models.IntegerField(default=90)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()

    # Tipos de consentimento
    consulta_cpf = models.BooleanField(default=False)
    consulta_credito = models.BooleanField(default=False)
    compartilhamento_terceiros = models.BooleanField(default=False)

    revogado = models.BooleanField(default=False)
    data_revogacao = models.DateTimeField(null=True, blank=True)
```

### Passo 3: Integrar com API Autorizada

```python
# services/consulta_cpf.py
import requests
from django.conf import settings

def consultar_cpf_serasa(cpf, comprador_id):
    """
    Consulta CPF na API Serasa (exemplo)
    Requer consentimento LGPD prévio
    """
    # Verifica consentimento
    consentimento = ConsentimentoLGPD.objects.filter(
        comprador_id=comprador_id,
        consulta_cpf=True,
        revogado=False,
        data_consentimento__gte=timezone.now() - timedelta(days=90)
    ).first()

    if not consentimento:
        raise ValueError('Consentimento LGPD não encontrado ou expirado')

    # Consulta API
    response = requests.post(
        'https://api.serasa.com.br/v1/consulta-cpf',
        headers={
            'Authorization': f'Bearer {settings.SERASA_API_KEY}',
            'Content-Type': 'application/json'
        },
        json={
            'cpf': cpf,
            'consentimento_id': consentimento.id
        }
    )

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f'Erro na consulta: {response.text}')
```

### Passo 4: Registrar Consulta (Auditoria)

```python
# models.py
class LogConsultaCPF(models.Model):
    comprador = models.ForeignKey(Comprador, on_delete=models.CASCADE)
    consentimento = models.ForeignKey(ConsentimentoLGPD, on_delete=models.CASCADE)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    data_consulta = models.DateTimeField(auto_now_add=True)
    servico_utilizado = models.CharField(max_length=50)  # 'Serasa', 'SPC', etc.
    dados_retornados = models.JSONField()
    finalidade = models.TextField()

    class Meta:
        verbose_name = 'Log de Consulta CPF'
        verbose_name_plural = 'Logs de Consultas CPF'
```

## 📋 Checklist de Compliance LGPD

Antes de implementar consulta de CPF, garanta:

- [ ] Termo de consentimento claro e específico
- [ ] Registro da data/hora do consentimento
- [ ] IP e user agent do titular
- [ ] Finalidade específica e legítima
- [ ] Prazo determinado de armazenamento
- [ ] Possibilidade de revogação fácil
- [ ] Log de todas as consultas realizadas
- [ ] Contrato com bureau de crédito autorizado
- [ ] DPO (Encarregado de Dados) designado
- [ ] Política de Privacidade atualizada
- [ ] Procedimento de resposta a solicitações (Art. 18)
- [ ] Relatório de Impacto (RIPD) se necessário

## ⚠️ Penalidades por Violação

A LGPD prevê multas de até:
- **R$ 50 milhões** por infração
- **2% do faturamento** da empresa
- **Publicização** da infração
- **Bloqueio** de dados
- **Eliminação** de dados

**Casos conhecidos:**
- Magazine Luiza: R$ 6,5 milhões (vazamento de dados)
- Serasa: R$ 6 milhões (consulta indevida)
- Hapvida: R$ 500 mil (tratamento inadequado)

## ✅ Boas Práticas

1. **Minimização de Dados**
   - Colete apenas o necessário
   - CPF só se realmente precisar

2. **Segurança**
   - Criptografe dados em repouso
   - Use HTTPS sempre
   - Hash de CPF quando possível

3. **Transparência**
   - Explique claramente o uso
   - Facilite acesso aos dados
   - Permita correção/exclusão

4. **Governança**
   - Treine equipe em LGPD
   - Nomeie um DPO
   - Faça auditorias regulares

## 🔗 Recursos Adicionais

### Legislação:
- [Lei 13.709/2018 (LGPD)](http://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm)
- [ANPD - Autoridade Nacional](https://www.gov.br/anpd/pt-br)

### Guias:
- [Guia de Boas Práticas LGPD](https://www.gov.br/anpd/pt-br/assuntos/guias)
- [Perguntas Frequentes ANPD](https://www.gov.br/anpd/pt-br/assuntos/faq)

### Cursos:
- [LGPD Academy](https://academy.lgpd.me/)
- [Serpro - Curso LGPD](https://www.serpro.gov.br/)

## 📞 Contato

Para dúvidas sobre implementação LGPD-compliant:

**Desenvolvedor:** Maxwell da Silva Oliveira
**Email:** maxwbh@gmail.com
**Empresa:** M&S do Brasil LTDA

---

**Aviso Legal:** Este documento tem caráter informativo. Para questões jurídicas específicas, consulte um advogado especializado em Direito Digital e Proteção de Dados.
