-- Optional agentic SQL workflow using Databricks ai_query.
--
-- This is the lowest-friction agentic layer for a compact project. It
-- proves the pattern before moving to Databricks Apps or AI Search.
--
-- Replace the model name if your workspace exposes a different system.ai model.

SELECT
  account_name,
  risk_band,
  risk_score,
  ai_query(
    'system.ai.gpt-5-mini',
    concat(
      'You are a customer success renewal-risk analyst. ',
      'Using only the facts below, explain why the account is risky and recommend the next action. ',
      'Keep the answer concise and grounded. Facts: ',
      account_summary_text
    )
  ) AS generated_account_briefing
FROM renewal_risk_lakehouse.renewal_risk_dev.gold_account_360_summary
WHERE risk_band IN ('Critical', 'High')
ORDER BY risk_score DESC
LIMIT 5;
