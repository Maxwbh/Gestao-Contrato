"""U-04: Template filter {{ pk|hashid }} para gerar URLs com hashids."""
from django import template
from core.hashids_utils import encode_id

register = template.Library()


@register.filter(name='hashid')
def hashid_filter(pk):
    """Converte um PK inteiro no seu hashid correspondente."""
    return encode_id(pk)
