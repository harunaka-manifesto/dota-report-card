import os

import pytest
from app.core.config import Settings
from app.opendota.client import OpenDotaClient

pytestmark = pytest.mark.live


def test_live_smoke_is_opt_in() -> None:
    if os.getenv("RUN_LIVE_SMOKE") != "1":
        pytest.skip("Live smoke is opt-in and never runs in ordinary CI.")
    assert os.getenv("OPENDOTA_API_KEY"), "OPENDOTA_API_KEY is required for live smoke"


@pytest.mark.asyncio
async def test_live_profile_smoke_without_replay_parse() -> None:
    if os.getenv("RUN_LIVE_SMOKE") != "1":
        pytest.skip("Live smoke is opt-in and never runs in ordinary CI.")
    async with OpenDotaClient(Settings.from_env()) as client:
        profile = await client.get_player(193875165)
    assert profile.get("profile", {}).get("account_id") == 193875165
