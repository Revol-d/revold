"""Leitura de configuração do ambiente. É o ÚNICO lugar de `libs/` que toca `os.environ`.

`env.py` é o parser único. A decisão de **quais** variáveis existem continua no `settings.py` de
cada app, que lê e injeta por parâmetro. As libs e o produto nunca leem o ambiente: recebem um
valor já resolvido, ou um mapeamento que o app montou com `env_snapshot()`.
"""

from revold_platform.configuration.env import (
    env_bool,
    env_int,
    env_list,
    env_required,
    env_snapshot,
    env_str,
)

__all__ = ["env_bool", "env_int", "env_list", "env_required", "env_snapshot", "env_str"]
