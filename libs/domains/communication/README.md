# `revold_communication`

Passagem do checkout para um canal de conversa com a loja.

- **Tipo:** domain · **Ciclo de vida:** pilot · **Manifesto:** [unit.yaml](unit.yaml)
- **Depende de:** `whatsapp`

## O que faz

O resumo do carrinho (`CartSummary`), a porta `CheckoutHandoff` e o adapter `adapters/whatsapp_clicktochat.py`, que escreve a mensagem e monta o link de clique-para-conversar (ADR-0005).

## Camadas

De cima para baixo, uma camada só importa as de baixo (`uv run dev check` reprova o contrário):

| Camada | O que tem |
|---|---|
| `adapters/` | Implementações das portas. Única camada que importa integração ou biblioteca de I/O. |
| `application/` | Casos de uso. Não importa adapters nem cliente de integração. |
| `ports/` | Contratos (Protocols) que os adapters implementam. |
| `domain/` | Regras e modelos. Não importa adapters nem cliente de integração. |

## O que NÃO faz

- **Não conhece o carrinho.** O resumo chega por valor, montado pelo app.
- **Não notifica a loja.** Aviso assíncrono é do domínio `notification`.

## Testes

```powershell
uv run pytest libs/domains/communication/tests -q
```
