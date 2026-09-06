from __future__ import annotations

import pytest

from core_ai_assistant_evals.fakes import FakeLLMProvider, FakeProductIndex

__all__ = ["FakeLLMProvider", "FakeProductIndex"]


@pytest.fixture
def fake_llm() -> FakeLLMProvider:
    return FakeLLMProvider()


@pytest.fixture
def fake_index() -> FakeProductIndex:
    return FakeProductIndex()
