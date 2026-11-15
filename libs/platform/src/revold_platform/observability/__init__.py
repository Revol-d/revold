"""Observabilidade: uma porta pequena e centralizada para métricas (ADR-0017).

Mesmo raciocínio dos eventos (ADR-0013): melhor um ponto único e um formato único de
instrumentação do que cada módulo inventar o seu jeito de contar e medir. A implementação real
(Prometheus) mora em `libs/integrations/prometheus`.
"""
