# Agentic Layer

The project includes three levels of agentic capability. Choose the level that
fits the time and workspace features available.

## Level 1: SQL-Based Account Briefing

Use:

```text
setup/03_ai_query_account_briefing.sql
```

Flow:

```text
gold_account_360_summary
        |
        v
ai_query prompt
        |
        v
grounded account briefing
```

This is the best compact option because it is easy to explain and stays
inside Databricks SQL.

Example question:

```text
Why is this account high risk and what should the CSM do next?
```

Expected answer style:

```text
Acme Data Systems is high risk because renewal is due soon, it has open
high-priority support cases, and usage has declined. The CSM should schedule an
executive renewal review and involve support leadership.
```

## Level 2: AI Search Index

Use table:

```text
renewal_risk_lakehouse.renewal_risk_dev.ai_account_briefing_documents
```

Create AI Search endpoint:

```text
renewal-risk-search-endpoint
```

Create index:

```text
renewal_risk_lakehouse.ai.account_briefing_index
```

Source table:

```text
renewal_risk_lakehouse.renewal_risk_dev.ai_account_briefing_documents
```

Primary key:

```text
document_id
```

Text column:

```text
briefing_text
```

Use this when you want retrieval over multiple accounts or longer account notes.

## Level 3: Databricks App

Use:

```text
src/app/
```

The app shows:

- Priority queue.
- Account selector.
- Governed account summary.
- Place where an LLM response can be added.

Deployment idea:

1. Open Databricks Apps.
2. Create custom app.
3. Use Git source or workspace folder source.
4. Select `src/app`.
5. Set `DATABRICKS_WAREHOUSE_ID` in `app.yaml`.
6. Deploy.

If using live SQL from the app, configure secure authentication using your
workspace-supported Databricks Apps pattern. Avoid hard-coding personal tokens.

## Production Agent Design

Production agents should not freely query raw Salesforce tables.

Use this pattern:

```text
User question
  -> intent routing
  -> governed SQL query against gold tables
  -> optional AI Search retrieval
  -> model response
  -> trace and evaluate
```

Recommended governed tables:

```text
gold_account_renewal_risk
gold_csm_priority_queue
gold_account_360_summary
ai_account_briefing_documents
```

## Example Production Prompts

Account explanation:

```text
You are a renewal risk analyst. Use only the account facts provided. Explain the
top risk drivers and recommend the next action. Do not invent missing facts.
```

CSM priority summary:

```text
Summarize the top five accounts the CSM team should act on this week. Group by
risk driver and include only accounts present in the provided table.
```

## Evaluation Ideas

Evaluate:

- Does the response mention only real facts from the gold table?
- Does it identify the correct risk band?
- Does it mention the most important driver?
- Does it recommend the correct action?
- Does it avoid exposing raw PII unnecessarily?

## Implementation Recommendation

For the main implementation, use Level 1.

For a polished project walkthrough, show Level 2 or Level 3 after the pipeline is
working.
