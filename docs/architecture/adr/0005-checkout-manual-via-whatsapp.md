# ADR-0005: Checkout manual via WhatsApp, com porta para automação futura

**Status:** Aceito

## Contexto
Não há CNPJ ainda, o que impede meios de pagamento formais (gateway de pagamento, emissão de nota fiscal). A decisão de negócio é: o cliente monta o carrinho no site e, ao final, é direcionado para conversar com a Nick por WhatsApp para fechar o pagamento manualmente. A WhatsApp Business API oficial exige aprovação da Meta e é desnecessária só para isso.

## Decisão
`core-cart`/`core-communication` definem uma porta `CheckoutHandoff` com o método essencial "gerar um resumo do carrinho e encaminhar para conversa". A primeira implementação (`adapters/external/whatsapp-clicktochat`) monta um link `wa.me/<numero>?text=<resumo do carrinho>` — sem necessidade de aprovação da Meta, sem custo por mensagem.

Quando o CNPJ e a aprovação de app da Meta existirem, uma segunda implementação da mesma porta (`adapters/external/whatsapp-business-api`) passa a existir para automação (confirmação de pedido, notificações). A troca entre as duas é configuração, não mudança de código em `core-cart`/`core-communication` nem no storefront.

O carrinho em si é sempre persistido no backend (`core-cart`), independente da forma de checkout — isso não muda.

## Consequências
- MVP funcional sem depender de nenhuma aprovação externa.
- Sem confirmação automática de pagamento — a conciliação é manual pela Nick, o que é aceito como trade-off consciente nesta fase.
- O storefront precisa de uma tela de "revisão do carrinho antes de ir para o WhatsApp" já compatível com a futura automação (mesmos dados, mesma estrutura), para não precisar refazer a experiência quando a API oficial chegar.
