"""Gate: todo job do `ci.yml` está ligado ao check agregado `CI OK`.

O ruleset da `main` exige um check só, o `CI OK` (job `ci-ok`). Um job que fica fora do `needs`
dele pode terminar vermelho com o `CI OK` verde, e a merge passa: o job vira enfeite. Ver
docs/branch-strategy.md, "O check agregado e as duas armadilhas".

Este teste lê o workflow e reprova quando um job não é visto pelo agregado.
"""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
AGGREGATE = "ci-ok"


def _workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def test_aggregate_job_exists_with_the_name_the_ruleset_requires():
    job = _workflow()["jobs"][AGGREGATE]
    assert job["name"] == "CI OK", "o ruleset (scripts/setup-rulesets.sh) exige o check `CI OK`"


def test_ruleset_script_requires_the_same_check_name():
    script = (ROOT / "scripts" / "setup-rulesets.sh").read_text(encoding="utf-8")
    assert '"context": "CI OK"' in script


def test_aggregate_runs_even_when_a_job_fails():
    """Sem `if: always()`, um job que falha deixa o agregado *skipped*, e skip não bloqueia merge."""
    assert _workflow()["jobs"][AGGREGATE]["if"] == "always()"


def test_every_job_is_seen_by_the_aggregate():
    jobs = _workflow()["jobs"]
    needs = set(jobs[AGGREGATE]["needs"])
    outside = sorted(set(jobs) - {AGGREGATE} - needs)
    assert not outside, (
        f"jobs fora do `needs` do {AGGREGATE}: {outside}. Job fora da lista nao reprova nada: "
        "ponha o nome dele no `needs` e na checagem de resultado."
    )


def test_every_needed_job_has_its_result_checked():
    """Estar no `needs` não basta: o passo do agregado precisa olhar o `result` de cada um."""
    job = _workflow()["jobs"][AGGREGATE]
    script = "\n".join(step.get("run", "") for step in job["steps"])
    unchecked = sorted(name for name in job["needs"] if f"needs.{name}.result" not in script)
    assert not unchecked, f"jobs no `needs` cujo resultado o {AGGREGATE} nao confere: {unchecked}"


def test_ci_runs_on_pull_request_to_main_only():
    """`push` na main faria o CI rodar duas vezes sobre o mesmo código (docs/branch-strategy.md)."""
    # O PyYAML le a chave `on` como o booleano True (YAML 1.1).
    triggers = _workflow()[True]
    assert set(triggers) == {"pull_request", "workflow_dispatch"}
    assert triggers["pull_request"]["branches"] == ["main"]
