---
name: Options desk - premarket
agent: ../agents/desk-lead.md
environment_id: ../environments/desk-env.yaml
vault_ids:
  - vlt_REPLACE_AFTER_VAULT_APPLY   # copy the vault ID from claude-lock.json after step 3 of README.md
schedule:
  type: cron
  expression: "35 8 * * 1-5"       # 8:35am ET weekdays; the platform may start it up to 9 minutes late
  timezone: America/New_York
budget:
  type: limit
  max_list_cost: {amount: "500", currency: USD}   # $5.00 per run cap (amount is in cents). Raise after a week of real costs.
initial_events:
  - type: user.define_outcome
    description: "Run today's premarket options desk and publish the daily report as described in your instructions."
    max_iterations: 2
    rubric:
      type: text
      content: |
        Starter rubric - tune after the first week.
        1. The report exists at /mnt/session/outputs/desk_report_<date>.md and was committed to reports/desk/<date>.md, and nothing else in the repository changed.
        2. Every market number has a source URL or endpoint and a timestamp, or says "not found".
        3. At least one market figure is confirmed by a second, independent source, or the report says it could not be.
        4. Every strategy is listed as passed, failed, insufficient data or untested, and each passed one links to a backtest folder with out-of-sample results at three IV settings.
        5. Every candidate trade lists ticker, strikes, expiry, a price labeled as an estimate to re-price at the open, max loss at or under $45 including fees, a cancel condition, and each of the four checks marked pass or fail.
        6. The "Auditor verdict" section is present, is the Risk Auditor's text unedited, and every vetoed trade appears only under "Vetoed".
        7. Open paper positions with a deadline today or tomorrow are listed first, with their exit rules.
        8. No order was placed, cancelled or changed, and the report says so.
        9. No em dashes; important claims are tagged [Certain], [Likely] or [Uncertain].
---
