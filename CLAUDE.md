# Arkham MCP — Agent Instructions

## Wallet Investigation

When the user asks to investigate, research, analyze, or study a specific wallet address or transaction,
ALWAYS use the `investigate_address` MCP prompt (depth="full") before responding.

Trigger phrases (not exhaustive):
- "исследуй / изучи / проанализируй кошелек / адрес"
- "investigate / analyze / look into [address]"
- "кто владеет / чей это адрес"
- "что за кошелек"

Call the prompt with the address extracted from the user message:
```
mcp__arkham__investigate_address(address="0x...", depth="full")
```

For quick/brief requests ("quickly check", "быстро глянь"):
```
mcp__arkham__investigate_address(address="0x...", depth="quick")
```

## Token Investigation

When the user asks to investigate, research, analyze, or study a specific token or coin,
ALWAYS use the `investigate_token` tool before responding.

Trigger phrases (not exhaustive):
- "исследуй / изучи / проанализируй токен / монету"
- "investigate / analyze / look into [token]"
- "что за токен / что за монета"
- "кто держит / кто накапливает [token]"

Call the tool with the token ID extracted from the user message:
```
mcp__arkham__investigate_token(token="skyai", depth="full")
```

For quick/brief requests:
```
mcp__arkham__investigate_token(token="skyai", depth="quick")
```
