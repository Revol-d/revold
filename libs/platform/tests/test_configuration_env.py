"""O parser de ambiente: as regras que o `settings.py` de todo app herda."""

from __future__ import annotations

import pytest

from revold_platform.configuration import (
    env_bool,
    env_int,
    env_list,
    env_required,
    env_snapshot,
    env_str,
)


def test_env_str_blank_counts_as_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REVOLD_SAMPLE", "   ")
    assert env_str("REVOLD_SAMPLE", "fallback") == "fallback"


def test_env_str_strips_the_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REVOLD_SAMPLE", "  value  ")
    assert env_str("REVOLD_SAMPLE") == "value"


@pytest.mark.parametrize("raw", ["1", "true", "TRUE", "yes", "On"])
def test_env_bool_true_spellings(monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    monkeypatch.setenv("REVOLD_SAMPLE", raw)
    assert env_bool("REVOLD_SAMPLE") is True


@pytest.mark.parametrize("raw", ["0", "false", "no", "y", "sim", ""])
def test_env_bool_anything_else_is_false(monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    monkeypatch.setenv("REVOLD_SAMPLE", raw)
    assert env_bool("REVOLD_SAMPLE", default=True) is False


def test_env_bool_missing_uses_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REVOLD_SAMPLE", raising=False)
    assert env_bool("REVOLD_SAMPLE", default=True) is True


def test_env_int_invalid_falls_back_without_raising(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REVOLD_SAMPLE", "sessenta")
    assert env_int("REVOLD_SAMPLE", 60) == 60


def test_env_int_reads_the_number(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REVOLD_SAMPLE", " 42 ")
    assert env_int("REVOLD_SAMPLE", 60) == 42


def test_env_list_drops_blank_items(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REVOLD_SAMPLE", "https://a.example/hook, ,https://b.example/hook ,")
    assert env_list("REVOLD_SAMPLE") == ["https://a.example/hook", "https://b.example/hook"]


def test_env_list_missing_is_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REVOLD_SAMPLE", raising=False)
    assert env_list("REVOLD_SAMPLE") == []


def test_env_required_says_what_it_is_for(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REVOLD_SAMPLE", raising=False)
    with pytest.raises(ValueError, match="REVOLD_SAMPLE.*abrir a conexao"):
        env_required("REVOLD_SAMPLE", purpose="abrir a conexao")


def test_env_snapshot_leaves_blank_values_out(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REVOLD_SAMPLE", "  value ")
    monkeypatch.setenv("REVOLD_BLANK", "  ")
    snapshot = env_snapshot()
    assert snapshot["REVOLD_SAMPLE"] == "value"
    assert "REVOLD_BLANK" not in snapshot


def test_reads_at_call_time_not_at_import(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REVOLD_SAMPLE", "first")
    assert env_str("REVOLD_SAMPLE") == "first"
    monkeypatch.setenv("REVOLD_SAMPLE", "second")
    assert env_str("REVOLD_SAMPLE") == "second"
