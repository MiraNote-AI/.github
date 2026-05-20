# Skills and MCP Servers

This file is the canonical registry of Claude Code skills and MCP servers
adopted across MiraNote-AI repos. Entries here are required by Rule 5 in
[CONTRIBUTING.md](../../CONTRIBUTING.md).

To add a skill or MCP server:

1. Add an entry to the relevant section below with a short description and
   a link to its configuration / source.
2. If the skill/MCP is configured at the repo level (e.g., in
   `.claude/settings.json`), reference that configuration here.
3. PR into `MiraNote-AI/.github`.

## Skills

_None yet._

## MCP Servers

### `miranote-discord`

- **Source:** [`mirabot/mcp-server/`](https://github.com/MiraNote-AI/mirabot/tree/main/mcp-server) (Node.js, discord.js)
- **Loaded by:** `.mcp.json` at the root of this repo (`MiraNote-AI/.github/.mcp.json`)
- **Tools exposed:** `discord_whoami`, `discord_list_channels`, `discord_lookup_member`, `discord_read_channel`, `discord_send_message`, `discord_react`, `discord_send_dm`, `discord_read_dms`, `discord_search_messages`, `discord_fetch_url`, `discord_fetch_attachment`
- **Setup**: requires `DISCORD_BOT_TOKEN` in `mirabot/.env` (gitignored) and `npm install` inside `mirabot/mcp-server/`
- **Purpose:** lets Claude Code (and other MCP clients) read and post in the MiraNote Discord server when collaborating with the team
- **Adopted:** 2026-05-19
