from __future__ import annotations

import pytest

from core_identity.domain import Role


async def test_dev_provider_login_flow():
    from adapters_external.identity.dev_provider import DevIdentityProvider

    provider = DevIdentityProvider()
    challenge = provider.start_login(redirect_uri="http://localhost:3000/callback")
    assert challenge.state == "dev"

    user = await provider.complete_login(code="dev", state=challenge.state)
    assert user.provider == "dev"
    assert user.has_role(Role.CUSTOMER)
