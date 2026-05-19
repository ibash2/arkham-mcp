import json
import os
import tempfile
from pathlib import Path


def merge_arkham_entry(config_path: Path, entry: dict[str, object]) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)

    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Config file is not valid JSON: {config_path}") from exc
    else:
        config = {}

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    config["mcpServers"]["arkham"] = entry

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=config_path.parent,
        suffix=".tmp",
        delete=False,
    ) as fh:
        fh.write(json.dumps(config, indent=2, ensure_ascii=False))
        tmp_path = Path(fh.name)

    os.replace(tmp_path, config_path)
