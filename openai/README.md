# Praxis Agent plugin for ChatGPT and Codex (OpenAI)

This folder is the OpenAI plugin package for Praxis Agent. You upload it at
<https://platform.openai.com/plugins> (**With MCP**). It uses the portable
Agent Plugins format that OpenAI documents in
<https://developers.openai.com/apps-sdk/deploy/submission>.

| Item | Value |
|---|---|
| MCP server | `https://praxis-agent.fly.dev/mcp/agent`, streamable HTTP |
| Sign-in | OAuth 2.0 with Dynamic Client Registration (`dcr`). No client ID, secret or header is in the package. |
| Publisher | CCL Consulting LLC, luis@lefv.io |
| Countries | US |

## Files

| File | In the ZIP | Purpose |
|---|---|---|
| `plugin.json` | Yes | Package identity, listing text, links, icon, starter prompts, test cases, release notes, countries (`extensions.com.openai`). |
| `mcp.json` | Yes | The one MCP server and its OAuth (`dcr`) setting. |
| `assets/logo.png` | Yes | 512×512 icon, rendered from `apps/praxis_web/priv/static/favicon.svg` in `lefv-org/praxis`. Used as `logo` and `composerIcon`. |
| `skills/public-law-research/SKILL.md` | Yes | Tells the model which Praxis tool fits which question. A public ZIP must contain at least one skill. |
| `REVIEW.md` | **No** | Review details for the portal: test account, test cases, release notes, demo shot list. |
| `build-zip.sh` | No | Builds `../dist/praxis-openai-plugin-<version>.zip`. |
| `check_package.py` | No | Checks the package against OpenAI's published limits (OpenAI has no offline validator). |

## Build

```bash
./openai/build-zip.sh
```

The script copies the four package files to a temporary folder, checks
them, writes the ZIP to `dist/` (git-ignored), checks the ZIP, and lists its
contents. It stops on the first error.

## Change a value

1. Edit `plugin.json` or `mcp.json`.
2. Increase `version` (OpenAI refuses an update with the same version).
3. If you change a test-case prompt, change it in `REVIEW.md` too. The
   check fails when the two differ.
4. Run `./openai/build-zip.sh` and upload the new ZIP.

## Known schema conflict

OpenAI's docs put the OAuth setting at
`mcpServers.<name>.extensions["com.openai"].auth` in `mcp.json`. The
published Agent Plugins 1.0.0 MCP schema does not allow `extensions` on a
server, so a strict JSON-schema check of `mcp.json` fails. This package
follows OpenAI's docs. If the portal rejects `mcp.json`, delete the
`extensions` block: the server's OAuth discovery
(`/.well-known/oauth-protected-resource` and
`/.well-known/oauth-authorization-server`) supplies the registration
endpoint for `dcr`.
