import pytest

from src.arkham_mcp.client import ArkhamClient

from src.arkham_mcp.providers import playwright
from src.arkham_mcp.config import Settings


async def test_get_transfers():
    settings = Settings(
        cookie="AMP_f072531383=JTdCJTIyZGV2aWNlSWQlMjIlM0ElMjIyMGQ4NGEyYi1kMjNkLTQzYzctYTFiMS01YTM4NDg4MDMxMDUlMjIlMkMlMjJzZXNzaW9uSWQlMjIlM0ExNzczMjQ0NjM2MzY3JTJDJTIyb3B0T3V0JTIyJTNBZmFsc2UlMkMlMjJsYXN0RXZlbnRUaW1lJTIyJTNBMTc3MzI0NDY2ODg0MiUyQyUyMmxhc3RFdmVudElkJTIyJTNBMiUyQyUyMnBhZ2VDb3VudGVyJTIyJTNBMCUyQyUyMmNvb2tpZURvbWFpbiUyMiUzQSUyMi5hcmttLmNvbSUyMiU3RA==;",
        base_url="https://api.arkm.com",
    )
    client = playwright.create_provider(settings)
    # client = ArkhamClient(base_url="https://api.arkm.com", cookie=cookie)
    async with client as s:
        transfer = await s.get_transfers(base="0x595E21b20E78674F8a64C1566A20b2b316Bc3511", limit=100)
    assert len(transfer) == 1
