"""core-cart: bounded context de carrinho (PENDENTE de implementação).

Escopo previsto: Cart, CartItem (referenciando SKUs do core-catalog só por
valor, nunca por import direto), porta CartRepository (persistência do
carrinho por sessão/usuário) e porta CheckoutHandoff (ver ADR-0005 —
implementada primeiro pelo adapter whatsapp-clicktochat).
Próximo passo: escrever cores/core-cart/src/core_cart/domain.py e ports.py
seguindo o mesmo padrão de core_catalog (ver domain.py/ports.py/use_cases.py
lá como referência).
"""
