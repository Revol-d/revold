"""`store-settings`: dados administrativos da loja editáveis pela Nick.

Core novo e pequeno (mesmo raciocínio de `revold_platform.events`/`revold_platform.observability`,
ver ADR-0013/ADR-0017): CNPJ, informações de contato, dados da loja e uma
configuração geral (limiar de estoque baixo) vivem aqui como um único
registro de configuração, em vez de cada core inventar seu próprio jeito
de guardar dado administrativo e cada tela do admin-dashboard bater direto
num core de negócio (catálogo, estoque) para editar algo que não é
catálogo nem estoque — é dado da empresa (ADR-0019).
"""
