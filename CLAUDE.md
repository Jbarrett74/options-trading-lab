# Options Trading Lab

At the start of every task in this repo (user request, scheduled run, or message from another session), read and follow `.claude/skills/fable-playbook/SKILL.md`, then read `STATUS.md`.

Hard rules:
- Never place, cancel, replace or close a real order, and never change a scheduled task, without the user's explicit yes in this conversation for that specific action.
- Real limits: $45 max loss per trade, $125 total open risk. Paper trades are logged in `paper_trading/log.csv`, real ones in `paper_trading/real_trades.csv`.
- Never invent numbers. Write "not found" when data is missing.
