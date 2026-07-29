"""
Base de dados brasileiros VÁLIDOS para geração de massa de teste.

Substitui os endereços genéricos do Faker (que produzia CEP e logradouro sem
relação entre si) por combinações reais e coerentes: cada CEP pertence de fato
ao logradouro/bairro/cidade/UF indicados, e o DDD do telefone bate com a cidade.

CPF/CNPJ são gerados com dígitos verificadores válidos pelo algoritmo oficial
da Receita — os mesmos que ferramentas como o 4devs aplicam.
"""
import random

# ---------------------------------------------------------------------------
# Endereços reais (CEP ↔ logradouro ↔ bairro ↔ cidade ↔ UF ↔ DDD)
# ---------------------------------------------------------------------------
# Faixas e logradouros existentes; usados apenas para popular massa de teste.
ENDERECOS = [
    # Sete Lagoas / MG (praça do sistema)
    {'cep': '35700-004', 'logradouro': 'Avenida Prefeito Alberto Moura', 'bairro': 'Centro',
     'cidade': 'Sete Lagoas', 'uf': 'MG', 'ddd': '31'},
    {'cep': '35700-030', 'logradouro': 'Rua Domingos Luiz de Oliveira', 'bairro': 'Centro',
     'cidade': 'Sete Lagoas', 'uf': 'MG', 'ddd': '31'},
    {'cep': '35701-057', 'logradouro': 'Avenida Dr. Renato Azeredo', 'bairro': 'Jardim Cambuí',
     'cidade': 'Sete Lagoas', 'uf': 'MG', 'ddd': '31'},
    {'cep': '35702-031', 'logradouro': 'Rua Coronel Randolfo Silva', 'bairro': 'Progresso',
     'cidade': 'Sete Lagoas', 'uf': 'MG', 'ddd': '31'},
    {'cep': '35703-057', 'logradouro': 'Rua Elias Salomão', 'bairro': 'Canaã',
     'cidade': 'Sete Lagoas', 'uf': 'MG', 'ddd': '31'},
    # Belo Horizonte / MG
    {'cep': '30130-009', 'logradouro': 'Avenida Afonso Pena', 'bairro': 'Centro',
     'cidade': 'Belo Horizonte', 'uf': 'MG', 'ddd': '31'},
    {'cep': '30140-071', 'logradouro': 'Rua Antônio de Albuquerque', 'bairro': 'Savassi',
     'cidade': 'Belo Horizonte', 'uf': 'MG', 'ddd': '31'},
    {'cep': '30170-133', 'logradouro': 'Rua dos Timbiras', 'bairro': 'Funcionários',
     'cidade': 'Belo Horizonte', 'uf': 'MG', 'ddd': '31'},
    {'cep': '31270-901', 'logradouro': 'Avenida Presidente Antônio Carlos', 'bairro': 'Pampulha',
     'cidade': 'Belo Horizonte', 'uf': 'MG', 'ddd': '31'},
    # Contagem / Betim / MG
    {'cep': '32010-130', 'logradouro': 'Avenida João César de Oliveira', 'bairro': 'Eldorado',
     'cidade': 'Contagem', 'uf': 'MG', 'ddd': '31'},
    {'cep': '32510-010', 'logradouro': 'Avenida Amazonas', 'bairro': 'Centro',
     'cidade': 'Betim', 'uf': 'MG', 'ddd': '31'},
    # São Paulo / SP
    {'cep': '01310-100', 'logradouro': 'Avenida Paulista', 'bairro': 'Bela Vista',
     'cidade': 'São Paulo', 'uf': 'SP', 'ddd': '11'},
    {'cep': '01415-001', 'logradouro': 'Rua Oscar Freire', 'bairro': 'Jardim Paulista',
     'cidade': 'São Paulo', 'uf': 'SP', 'ddd': '11'},
    {'cep': '04538-133', 'logradouro': 'Avenida Brigadeiro Faria Lima', 'bairro': 'Itaim Bibi',
     'cidade': 'São Paulo', 'uf': 'SP', 'ddd': '11'},
    # Campinas / SP
    {'cep': '13015-904', 'logradouro': 'Avenida Francisco Glicério', 'bairro': 'Centro',
     'cidade': 'Campinas', 'uf': 'SP', 'ddd': '19'},
    # Rio de Janeiro / RJ
    {'cep': '20031-170', 'logradouro': 'Avenida Rio Branco', 'bairro': 'Centro',
     'cidade': 'Rio de Janeiro', 'uf': 'RJ', 'ddd': '21'},
    {'cep': '22071-900', 'logradouro': 'Avenida Atlântica', 'bairro': 'Copacabana',
     'cidade': 'Rio de Janeiro', 'uf': 'RJ', 'ddd': '21'},
    # Curitiba / PR
    {'cep': '80020-320', 'logradouro': 'Rua XV de Novembro', 'bairro': 'Centro',
     'cidade': 'Curitiba', 'uf': 'PR', 'ddd': '41'},
    # Porto Alegre / RS
    {'cep': '90010-150', 'logradouro': 'Rua dos Andradas', 'bairro': 'Centro Histórico',
     'cidade': 'Porto Alegre', 'uf': 'RS', 'ddd': '51'},
    # Goiânia / GO
    {'cep': '74023-010', 'logradouro': 'Avenida Goiás', 'bairro': 'Setor Central',
     'cidade': 'Goiânia', 'uf': 'GO', 'ddd': '62'},
]

# Nomes próprios brasileiros comuns (IBGE) — compõem nomes completos plausíveis.
_PRENOMES_M = [
    'Miguel', 'Arthur', 'Gael', 'Théo', 'Heitor', 'Ravi', 'Davi', 'Bernardo',
    'Noah', 'Gabriel', 'Samuel', 'Anthony', 'João', 'Pedro', 'Lucas', 'Rafael',
    'Carlos', 'Eduardo', 'Marcelo', 'Roberto', 'Fernando', 'Ricardo', 'Paulo',
]
_PRENOMES_F = [
    'Helena', 'Alice', 'Laura', 'Maria', 'Sophia', 'Manuela', 'Isabella',
    'Heloísa', 'Valentina', 'Cecília', 'Eloá', 'Ana', 'Júlia', 'Beatriz',
    'Fernanda', 'Patrícia', 'Cláudia', 'Simone', 'Adriana', 'Luciana',
]
_SOBRENOMES = [
    'Silva', 'Santos', 'Oliveira', 'Souza', 'Rodrigues', 'Ferreira', 'Alves',
    'Pereira', 'Lima', 'Gomes', 'Costa', 'Ribeiro', 'Martins', 'Carvalho',
    'Almeida', 'Lopes', 'Soares', 'Fernandes', 'Vieira', 'Barbosa', 'Rocha',
    'Dias', 'Nascimento', 'Andrade', 'Moreira', 'Nunes', 'Marques', 'Machado',
]

_RAMOS_EMPRESA = [
    'Construtora', 'Incorporadora', 'Empreendimentos', 'Participações',
    'Investimentos Imobiliários', 'Urbanismo', 'Engenharia',
]
_PROFISSOES = [
    'Engenheiro Civil', 'Professora', 'Advogado', 'Médica', 'Contador',
    'Analista de Sistemas', 'Enfermeira', 'Vendedor', 'Administradora',
    'Técnico em Edificações', 'Comerciante', 'Servidor Público', 'Arquiteta',
    'Motorista', 'Eletricista', 'Nutricionista', 'Farmacêutico', 'Dentista',
]


# ---------------------------------------------------------------------------
# Documentos com dígito verificador válido
# ---------------------------------------------------------------------------

def gerar_cpf(rnd=random, formatado=True) -> str:
    """CPF com DV válido (algoritmo da Receita). Nunca gera sequência repetida."""
    while True:
        base = [rnd.randint(0, 9) for _ in range(9)]
        if len(set(base)) > 1:
            break
    soma = sum((10 - i) * base[i] for i in range(9))
    base.append((soma * 10 % 11) % 10)
    soma = sum((11 - i) * base[i] for i in range(10))
    base.append((soma * 10 % 11) % 10)
    d = ''.join(map(str, base))
    return f'{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}' if formatado else d


def gerar_cnpj(rnd=random, formatado=True) -> str:
    """CNPJ com DV válido (matriz 0001)."""
    base = [rnd.randint(0, 9) for _ in range(8)] + [0, 0, 0, 1]
    for pesos in ([5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2],
                  [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]):
        soma = sum(v * p for v, p in zip(base, pesos))
        resto = soma % 11
        base.append(0 if resto < 2 else 11 - resto)
    d = ''.join(map(str, base))
    return (f'{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}'
            if formatado else d)


def validar_cpf(cpf: str) -> bool:
    """Confere o DV de um CPF (usado nos testes da massa gerada)."""
    d = ''.join(ch for ch in str(cpf) if ch.isdigit())
    if len(d) != 11 or len(set(d)) == 1:
        return False
    for pos, peso_ini in ((9, 10), (10, 11)):
        soma = sum(int(d[i]) * (peso_ini - i) for i in range(pos))
        if int(d[pos]) != (soma * 10 % 11) % 10:
            return False
    return True


def validar_cnpj(cnpj: str) -> bool:
    """Confere os DVs de um CNPJ."""
    d = ''.join(ch for ch in str(cnpj) if ch.isdigit())
    if len(d) != 14 or len(set(d)) == 1:
        return False
    for pesos, pos in (([5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2], 12),
                       ([6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2], 13)):
        soma = sum(int(d[i]) * pesos[i] for i in range(pos))
        resto = soma % 11
        if int(d[pos]) != (0 if resto < 2 else 11 - resto):
            return False
    return True


# ---------------------------------------------------------------------------
# Pessoas e endereços
# ---------------------------------------------------------------------------

def gerar_pessoa(rnd=random) -> dict:
    """Pessoa física plausível: nome, sexo, profissão e documentos válidos."""
    sexo = rnd.choice(['M', 'F'])
    prenome = rnd.choice(_PRENOMES_M if sexo == 'M' else _PRENOMES_F)
    nome = f'{prenome} {rnd.choice(_SOBRENOMES)} {rnd.choice(_SOBRENOMES)}'
    return {
        'nome': nome,
        'sexo': sexo,
        'cpf': gerar_cpf(rnd),
        'rg': f'MG-{rnd.randint(10, 99)}.{rnd.randint(100, 999)}.{rnd.randint(100, 999)}',
        'profissao': rnd.choice(_PROFISSOES),
    }


def gerar_empresa(rnd=random) -> dict:
    """Pessoa jurídica plausível: razão social, fantasia e CNPJ válido."""
    sobrenome = rnd.choice(_SOBRENOMES)
    ramo = rnd.choice(_RAMOS_EMPRESA)
    return {
        'razao_social': f'{sobrenome} {ramo} LTDA',
        'nome_fantasia': f'{sobrenome} {ramo.split()[0]}',
        'cnpj': gerar_cnpj(rnd),
    }


def gerar_endereco(rnd=random) -> dict:
    """Endereço real: CEP, logradouro, bairro, cidade e UF coerentes entre si."""
    base = dict(rnd.choice(ENDERECOS))
    base['numero'] = str(rnd.randint(10, 2500))
    base['complemento'] = rnd.choice(['', '', '', 'Apto 101', 'Sala 2', 'Casa 2', 'Bloco B'])
    return base


def gerar_telefones(ddd: str, rnd=random) -> dict:
    """Fixo e celular com o DDD da cidade (celular com o 9 obrigatório)."""
    return {
        'telefone': f'({ddd}) {rnd.randint(2, 5)}{rnd.randint(100, 999)}-{rnd.randint(1000, 9999)}',
        'celular': f'({ddd}) 9{rnd.randint(6000, 9999)}-{rnd.randint(1000, 9999)}',
    }


# ---------------------------------------------------------------------------
# Geolocalização — coordenadas reais das cidades atendidas
# ---------------------------------------------------------------------------
# Centro aproximado de cada cidade; os imóveis recebem um deslocamento pequeno
# (dentro da malha urbana) para que o mapa mostre lotes vizinhos, e não todos
# empilhados no mesmo ponto.
COORDENADAS_CIDADE = {
    'Sete Lagoas': (-19.4658, -44.2467),
    'Belo Horizonte': (-19.9227, -43.9451),
    'Contagem': (-19.9317, -44.0536),
    'Betim': (-19.9679, -44.1983),
    'São Paulo': (-23.5505, -46.6333),
    'Campinas': (-22.9099, -47.0626),
    'Rio de Janeiro': (-22.9068, -43.1729),
    'Curitiba': (-25.4284, -49.2733),
    'Porto Alegre': (-30.0346, -51.2177),
    'Goiânia': (-16.6869, -49.2648),
}


def gerar_coordenadas(cidade: str, rnd=random, raio_km=4.0):
    """
    Coordenadas dentro da malha urbana da cidade (lat, lon) como Decimal com 7
    casas — o mesmo formato dos campos `Imovel.latitude/longitude`.

    Sem isso, os imóveis da massa de teste ficam sem geolocalização e o mapa da
    tela de edição aparece vazio.
    """
    from decimal import Decimal
    base = COORDENADAS_CIDADE.get(cidade, COORDENADAS_CIDADE['Sete Lagoas'])
    # 1 grau de latitude ~ 111 km; longitude encurta com o cosseno da latitude.
    import math
    d_lat = (rnd.uniform(-raio_km, raio_km)) / 111.0
    d_lon = (rnd.uniform(-raio_km, raio_km)) / (111.0 * math.cos(math.radians(base[0])))
    return (Decimal(f'{base[0] + d_lat:.7f}'), Decimal(f'{base[1] + d_lon:.7f}'))


def gerar_email(nome: str, dominio='email.com.br') -> str:
    """E-mail derivado do nome, sem acentos e sem espaços."""
    import unicodedata
    txt = unicodedata.normalize('NFKD', nome).encode('ascii', 'ignore').decode()
    partes = [p for p in txt.lower().split() if p]
    if not partes:
        return f'contato@{dominio}'
    usuario = f'{partes[0]}.{partes[-1]}' if len(partes) > 1 else partes[0]
    return f'{usuario}@{dominio}'
