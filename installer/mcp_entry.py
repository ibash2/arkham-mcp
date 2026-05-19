from pathlib import Path


def build_mcp_entry(install_dir: Path, api_key: str | None, cookie: str | None) -> dict:
    env: dict[str, str] = {"ARKHAM_BASE_URL": "https://api.arkm.com"}

    if cookie:
        env["ARKHAM_COOKIE"] = cookie
        env["ARKHAM_PROVIDER"] = "playwright"
    elif api_key:
        env["ARKHAM_API_KEY"] = api_key
        env["ARKHAM_PROVIDER"] = "arkham"
    else:
        env["ARKHAM_PROVIDER"] = "arkham"

    return {
        "type": "stdio",
        "command": "uv",
        "args": ["--directory", str(install_dir), "run", "arkham-mcp"],
        "env": env,
    }
