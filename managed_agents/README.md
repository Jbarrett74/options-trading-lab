# Options desk on Claude Managed Agents

A premarket research team that runs every weekday at about 8:35am ET, alongside the existing Claude Code scheduled runs, so the two can be compared. It never places, cancels or changes an order.

Built on Claude Managed Agents (beta): Anthropic hosts the agent loop and a sandbox per run. Billing is API usage (tokens plus session runtime), separate from a Claude subscription. Session history is kept until deleted.

## Team

| Agent | Model | Job |
|---|---|---|
| Desk Lead (coordinator) | Opus 5.5 | Plans, delegates, publishes the report. Computes no prices itself. |
| Market Data Analyst | Sonnet 5.5 | Overseas closes, VIX, premarket, calendar, news; a source for every number |
| Strategy Researcher | Sonnet 5.5 | Turns a strategy (e.g. a GitHub bot) into an exact rule file, unchanged, with its license |
| Quant Backtester | Opus 5.5 | Held-out backtest of one rule file at 3 IV settings; workflow runs fan out across many |
| Trade Structurer | Sonnet 5.5 | At most 3 trades, only from strategies that passed; $45 max loss; four checks |
| Paper Ledger Clerk | Haiku 5.5 | Open positions, deadlines, P&L per arm, read-only |
| Risk Auditor | Opus 5.5 | Independent re-check from raw files; veto is final and published word for word |

Limit: Managed Agents allows one level of delegation, so the auditor cannot sit structurally above the lead. Its authority is enforced by the lead's instructions and the rubric (item 6), not by the platform.

Dynamic workflows are on for the lead, limited to Quant Backtester agents, for testing many strategies or parameter sets at once. Every agent in a run uses tokens. To turn them off, set `workflows: {type: disabled}` in `agents/desk-lead.md` and run `ant apply` again.

## Setup (on your own computer, once)

1. Install the `ant` CLI (1.40.0 or later) and log in:

```bash
brew install anthropics/tap/ant
```

```bash
ant auth login
```

On Linux, download the release from github.com/anthropics/anthropic-cli/releases instead of using brew.

2. From the repository root, preview and create the agents, environment and vault:

```bash
ant apply --dry-run -v managed_agents/agents/*.md managed_agents/environments/desk-env.yaml managed_agents/vaults/desk-vault.yaml
```

```bash
ant apply managed_agents/agents/*.md managed_agents/environments/desk-env.yaml managed_agents/vaults/desk-vault.yaml
```

3. In the Anthropic Console, open the vault `options-desk-vault` and add two environment-variable credentials (values are never written to this repo):
   - `GITHUB_TOKEN`: a fine-grained personal access token for Jbarrett74/options-trading-lab only, permission Contents read and write. Allowed host `api.github.com`.
   - `FMP_API_KEY`: your Financial Modeling Prep key. Allowed host `financialmodelingprep.com`.

4. Copy the vault ID (`vlt_...`) from `claude-lock.json` into `managed_agents/deployments/premarket.md` in place of `vlt_REPLACE_AFTER_VAULT_APPLY`, then create the schedule:

```bash
ant apply managed_agents/deployments/premarket.md
```

5. Commit `claude-lock.json`. Without it, the next `ant apply` creates duplicates.

## Test it now instead of waiting for 8:35am

Take the deployment ID from `claude-lock.json`, then:

```bash
curl -sS -X POST "https://api.anthropic.com/v1/deployments/$DEPLOYMENT_ID/run" -H "x-api-key: $ANTHROPIC_API_KEY" -H "anthropic-version: 2023-06-01" -H "anthropic-beta: managed-agents-2026-04-01"
```

Watch it live in the Console under Sessions. The report lands in `reports/desk/<date>.md` in this repo.

## Cost control

Each run is capped at $5.00 (`budget` in `deployments/premarket.md`, in cents). Check real costs in the Console after a week, then adjust. To pause the schedule, use the Console's deployment page (pause is reversible; archive is not).

## Known gaps

- No live option quotes: Robinhood's connection is not reachable from a hosted agent as far as we know. Trade prices are model estimates and must be re-priced at the open. Gamma maps stay in the Claude Code session.
- FMP is called with the key in an `apikey` header. If FMP refuses that form, market data falls back to web sources and the report says so.
- No backtested strategy has passed yet (docs/findings.md), so expect "no candidate" reports until one does.
