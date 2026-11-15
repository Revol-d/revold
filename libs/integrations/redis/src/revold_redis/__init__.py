"""Cliente do Redis assíncrono, compartilhado pelos apps.

Só monta a conexão. Os repositórios que guardam dado no Redis (carrinho, sessão, limite de
requisições) moram na camada `adapters/redis/` do domínio dono da porta e recebem o cliente pronto.
"""

from revold_redis.client import make_redis_client

__all__ = ["make_redis_client"]
