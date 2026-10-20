# Praxis Agent plugin for Claude Code

This plugin adds one remote MCP server, `praxis-agent`, to Claude Code. It
has no skills, commands, agents or hooks.

Praxis Agent answers questions on **public US law**: statutes, court rules,
case law and federal regulations. Every answer links to its sources. It is
not legal advice. It never sees firm or client data. Do not put client names
or facts in a question.

| Item | Value |
|---|---|
| MCP server URL | `https://praxis-agent.fly.dev/mcp/agent` |
| Transport | Streamable HTTP |
| Sign-in | OAuth, in the browser. No key goes in a file. |
| Full guide | <https://praxis-agent.fly.dev/connect> |
| Support | luis@lefv.io |

## What you need

- Claude Code.
- Your email and an access credential (`pa_cred_…`) from the operator. The
  operator shares it as a 1Password item.

## Install in Claude Code

In a Claude Code session:

```text
/plugin marketplace add lefv-org/praxis-claude-plugin
/plugin install praxis@lefv
```

Or in a shell:

```bash
claude plugin marketplace add lefv-org/praxis-claude-plugin
claude plugin install praxis@lefv
```

On Claude Code 2.1.275 or later, one line does both:

```text
/plugin install praxis --marketplace lefv-org/praxis-claude-plugin
```

Then **start a new Claude Code session**.

## Sign in

1. In the new session, run `/mcp`.
2. Select `plugin:praxis:praxis-agent`. It says **Needs authentication**.
   Select **Authenticate**. A Praxis sign-in page opens in the browser.
3. Sign in with **1Password autofill**: your email, and your access
   credential in the **Access code** field. Click **Sign in with code**.
4. Read the consent page. Click **Approve**. Go back to Claude Code.

Do steps 2 to 4 within **10 minutes**. The connection lasts **90 days**.
Then sign in again the same way.

Check it: `claude mcp list` must show `plugin:praxis:praxis-agent` as
`Connected`.

### You already added `praxis-agent` by hand

If `claude mcp list` also shows a `praxis-agent` line that you added with
`claude mcp add`, you have the same tools twice. Keep one. To keep the
plugin, run `claude mcp remove praxis-agent -s user`.

### You have a key file, not a credential

The plugin uses OAuth only. A developer who has a key file from the operator
does not need this plugin. Use the `claude mcp add … --header` command in
<https://praxis-agent.fly.dev/connect> (Claude Code).

## Claude Desktop

- **Code tab (local or SSH session):** click **+** next to the prompt box,
  then **Add plugins**. Add the marketplace `lefv-org/praxis-claude-plugin` and install
  `praxis`. Then sign in as in § Sign in.
- **Chat and Cowork tabs:** these do not use Claude Code plugins. Add Praxis
  as a **custom connector** instead: **Customize** → **Connectors** →
  **Add** → **Add custom connector**. Name: `Praxis`. URL:
  `https://praxis-agent.fly.dev/mcp/agent`. Click **Connect** and sign in.
  The connector syncs through your claude.ai account, so a connector you
  add on claude.ai also shows in Desktop. Steps:
  <https://praxis-agent.fly.dev/connect>.

A Desktop extension (`.mcpb`) is for a server that runs on your machine.
Praxis Agent is remote, so there is no `.mcpb` file.

## Uninstall

```bash
claude plugin uninstall praxis@lefv
claude plugin marketplace remove lefv
```

To end the Praxis connection too, run `/mcp`, select the server, and select
**Clear authentication** before you uninstall.

## Support

Email luis@lefv.io.

## Maintainers

- Marketplace file: `.claude-plugin/marketplace.json`. Marketplace name: `lefv`.
- Plugin files: `.claude-plugin/plugin.json` and `.mcp.json`. Keep the version
  in `plugin.json` and in the marketplace entry the same.
- Check after each edit: `claude plugin validate --strict .`
