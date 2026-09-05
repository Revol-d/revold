"""Adapters externos — implementações de portas que falam com serviços de
terceiros (provedores de identidade, WhatsApp, provedores de LLM). Cada
integração tem, no mínimo, um adapter de desenvolvimento (fake/sandbox) além
do real, para permitir construir e testar o sistema inteiro mesmo antes de
uma credencial de produção existir (ver docs/guides/development.md)."""
