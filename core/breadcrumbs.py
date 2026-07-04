"""
Helpers para construção de breadcrumbs.

Uso em uma view:
    from core.breadcrumbs import bc, bc_dashboard

    context['breadcrumb'] = [
        bc_dashboard(),
        bc('Compradores', 'core:listar_compradores'),
        bc(comprador.nome),  # último item, sem URL
    ]

O template `includes/breadcrumb.html` renderiza a lista automaticamente
quando passada no contexto como `breadcrumb`.
"""
from django.urls import reverse, NoReverseMatch


def bc(label, url_name=None, *args, icon=None, **kwargs):
    """Cria um item de breadcrumb.

    label: texto exibido.
    url_name: nome de URL Django (ex.: 'core:listar_compradores'). Opcional.
    args/kwargs: passados para reverse() se houver url_name.
    icon: classe CSS de ícone Font Awesome (ex.: 'fas fa-home'). Opcional.
    """
    item = {'label': label}
    if icon:
        item['icon'] = icon
    if url_name:
        try:
            item['url'] = reverse(url_name, args=args, kwargs=kwargs)
        except NoReverseMatch:
            pass
    return item


def bc_dashboard():
    """Item raiz padrão apontando para o dashboard."""
    return bc('Dashboard', 'core:dashboard', icon='fas fa-home')
