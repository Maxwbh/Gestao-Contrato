# Integração com ViaCEP - Busca Automática de Endereços

**Desenvolvedor:** Maxwell da Silva Oliveira
**Email:** maxwbh@gmail.com
**Empresa:** M&S do Brasil LTDA

## 📍 O que é ViaCEP?

O [ViaCEP](https://viacep.com.br/) é uma API pública e gratuita que permite buscar informações de endereço a partir do CEP (Código de Endereçamento Postal).

## ✨ Funcionalidades Implementadas

### 1. Busca Automática de Endereço

Quando o usuário digita um CEP válido nos formulários de **Comprador** ou **Imobiliária**, o sistema:

1. ✅ Aplica máscara automática (`99999-999`)
2. ✅ Valida se o CEP tem 8 dígitos
3. ✅ Busca o endereço na API ViaCEP
4. ✅ Preenche automaticamente os campos:
   - Logradouro (rua, avenida, etc.)
   - Bairro
   - Cidade
   - Estado (UF)
5. ✅ Exibe feedback visual (loading e toast notification)
6. ✅ Foca automaticamente no campo "Número"

### 2. Campos de Endereço Estruturados

Os modelos **Comprador** e **Imobiliaria** agora possuem campos separados:

```python
cep             # CEP formatado (99999-999)
logradouro      # Nome da rua/avenida
numero          # Número do imóvel
complemento     # Apartamento, sala, bloco, etc.
bairro          # Bairro
cidade          # Cidade
estado          # UF (sigla do estado)
```

## 🎯 Como Usar

### No Formulário Web:

1. Acesse o formulário de cadastro (Comprador ou Imobiliária)
2. No campo **CEP**, digite os 8 dígitos do CEP
3. Pressione **Tab** ou clique fora do campo
4. Aguarde a mensagem "Buscando..."
5. O endereço será preenchido automaticamente!
6. Complete o campo **Número** (obrigatório)
7. Revise e ajuste os dados se necessário

### Exemplo:

```
CEP digitado:    30130100
CEP formatado:   30130-100
Resultado:
  Logradouro:    Avenida Afonso Pena
  Bairro:        Centro
  Cidade:        Belo Horizonte
  Estado:        MG
```

## 💻 Uso Programático (JavaScript)

O sistema expõe funções globais que podem ser usadas em outros scripts:

```javascript
// Buscar CEP
const resultado = await window.GestaoContratos.buscarCEP('30130100');

if (!resultado.erro) {
    console.log(resultado.logradouro); // "Avenida Afonso Pena"
    console.log(resultado.bairro);     // "Centro"
    console.log(resultado.localidade); // "Belo Horizonte"
    console.log(resultado.uf);         // "MG"
}

// Preencher campos automaticamente
window.GestaoContratos.preencherEndereco(resultado);

// Aplicar máscara de CEP
const cepFormatado = window.GestaoContratos.mascaraCEP('30130100');
// Resultado: "30130-100"
```

## 🔧 Configuração Técnica

### Models (core/models.py)

```python
class Comprador(TimeStampedModel):
    # ... outros campos ...

    cep = models.CharField(max_length=9, blank=True, verbose_name='CEP')
    logradouro = models.CharField(max_length=200, blank=True, verbose_name='Logradouro')
    numero = models.CharField(max_length=10, blank=True, verbose_name='Número')
    complemento = models.CharField(max_length=100, blank=True, verbose_name='Complemento')
    bairro = models.CharField(max_length=100, blank=True, verbose_name='Bairro')
    cidade = models.CharField(max_length=100, blank=True, verbose_name='Cidade')
    estado = models.CharField(max_length=2, blank=True, verbose_name='UF', choices=[...])
```

### Forms (core/forms.py)

```python
class CompradorForm(forms.ModelForm):
    class Meta:
        widgets = {
            'cep': forms.TextInput(attrs={
                'placeholder': '99999-999',
                'data-viacep': 'true',
                'class': 'cep-input'
            }),
        }
```

### JavaScript (static/js/custom.js)

A integração é automática! Basta adicionar a classe `cep-input` ou o atributo `data-viacep="true"` ao input.

## ⚠️ Tratamento de Erros

O sistema trata os seguintes cenários:

### CEP Inválido
- **Erro:** CEP com menos/mais de 8 dígitos
- **Ação:** Toast de aviso amarelo
- **Campo:** Marcado com borda vermelha (`is-invalid`)

### CEP Não Encontrado
- **Erro:** CEP válido mas não existe nos Correios
- **Ação:** Toast: "CEP não encontrado"
- **Campo:** Marcado com borda vermelha

### Erro de Conexão
- **Erro:** Falha na API ViaCEP
- **Ação:** Toast: "Erro ao buscar CEP. Tente novamente."
- **Campo:** CEP permanece digitável

### CEP Encontrado com Sucesso
- **Ação:** Toast verde: "Endereço encontrado! Verifique e complete os dados."
- **Campo:** Marcado com borda verde (`is-valid`)
- **Comportamento:** Foco automático no campo "Número"

## 📊 Formato da Resposta da API

```json
{
  "cep": "30130-100",
  "logradouro": "Avenida Afonso Pena",
  "complemento": "de 2421 a 3652 - lado par",
  "bairro": "Centro",
  "localidade": "Belo Horizonte",
  "uf": "MG",
  "ibge": "3106200",
  "gia": "",
  "ddd": "31",
  "siafi": "4123"
}
```

## 🔒 Privacidade e Segurança

- ✅ Não armazena dados sensíveis
- ✅ Comunicação HTTPS com ViaCEP
- ✅ Não envia dados do usuário para API
- ✅ Campos editáveis após preenchimento automático
- ✅ Validação no frontend E backend

## 🌐 Compatibilidade

- ✅ Navegadores modernos (Chrome, Firefox, Edge, Safari)
- ✅ Dispositivos móveis (iOS, Android)
- ✅ Funciona offline (campos ficam editáveis manualmente)
- ✅ Graceful degradation (se API falhar, usuário pode digitar)

## 📱 Migração de Dados Antigos

O campo `endereco` (TextField) foi mantido como **legacy** e marcado como `blank=True`:

```python
endereco = models.TextField(
    blank=True,
    verbose_name='Endereço Completo (legacy)',
    help_text='Campo legado - use os campos separados acima'
)
```

Isso garante:
- ✅ Compatibilidade com dados existentes
- ✅ Sem quebra de funcionalidades antigas
- ✅ Migração gradual para novo formato

## 🚀 Melhorias Futuras

### Já Planejadas:
- [ ] Cache de CEPs consultados (Redis)
- [ ] Autocomplete de endereços (sugestões)
- [ ] Validação de número e complemento
- [ ] Geocodificação (latitude/longitude)

### Em Análise:
- [ ] Integração com Google Maps
- [ ] Cálculo de distâncias entre endereços
- [ ] Validação de existência de logradouro

## 📚 Referências

- [ViaCEP - Documentação Oficial](https://viacep.com.br/)
- [ViaCEP - GitHub](https://github.com/viacep)
- [Códigos de Endereçamento Postal - Correios](https://buscacepinter.correios.com.br/)

## 🆘 Suporte

Em caso de problemas:

1. Verifique sua conexão com internet
2. Tente novamente após alguns segundos
3. Se persistir, preencha manualmente os campos
4. Reporte o problema ao desenvolvedor

**Desenvolvedor:** Maxwell da Silva Oliveira
**Email:** maxwbh@gmail.com
**Empresa:** M&S do Brasil LTDA
