"""core-observability: porta pequena e centralizada para métricas (ADR-0017).

Mesmo raciocínio do core-events (ADR-0013): melhor um ponto único e um
formato único de instrumentação do que cada módulo inventar seu próprio
jeito de contar/medir coisa — evita nome de métrica divergente entre
partes do sistema que medem "a mesma coisa" de jeitos diferentes.
"""
