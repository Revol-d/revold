"""Domínio do assistente de IA.

Porta LLMProvider (ver ADR-0006), orquestração via LangGraph e RAG sobre o
catálogo indexado em pgvector (ADR-0011). As implementações da porta
LLMProvider (desenvolvimento, Azure OpenAI e DeepSeek) e a factory que
escolhe entre elas moram em revold_ai_assistant.adapters.llm.
"""
