# Project Runbook

This runbook defines the recommended end-to-end implementation sequence for the
Salesforce Renewal Risk Intelligence Platform.

## Prerequisites

1. Create a Salesforce Developer Edition org.
2. Deploy Salesforce metadata with Salesforce CLI.
3. Bulk load `data/salesforce-bulk/load/Account.csv`.
4. Export the Account ID map.
5. Run `src/prepare_child_bulk_files.py`.
6. Bulk load Contact, Opportunity, Case, and Product_Usage__c files from
   `data/salesforce-bulk/load`.
7. Create or open a Unity Catalog-enabled Databricks workspace.
8. Start or select a SQL warehouse and set `sql_warehouse_id`.
9. Create the Salesforce connection in Unity Catalog.
10. Push this project to GitHub.
11. Clone the GitHub repository into a Databricks Git folder.
12. Deploy the bundle project from the Databricks UI.
13. Run `job_renewal_risk_environment_bootstrap_dev` when manual repair or verification is needed.
14. Run the Lakeflow Connect ingestion pipeline.
15. Run the Lakeflow Designer visual data prep.
16. Test `setup/03_ai_query_account_briefing.sql` if AI functions are enabled.

## Implementation Sequence

### 1. Business Context

Start with the final business question:

```text
Which customers are at renewal risk, why, and what action should CSM take?
```

Confirm the final serving table:

```sql
SELECT *
FROM renewal_risk_lakehouse.renewal_risk_dev.gold_csm_priority_queue
ORDER BY priority_rank;
```

### 2. Salesforce Source System

Validate the operational source objects:

- Accounts.
- Contacts.
- Opportunities.
- Cases.
- Product Usage records.

Confirm why the operational model is not directly analytics-ready.

### 3. Lakeflow Connect

Create or validate:

- Bundle deployment has created the required Unity Catalog objects.
- Environment bootstrap job has verified or repaired the Unity Catalog objects.
- Unity Catalog Salesforce connection.
- Data Ingestion pipeline.
- Salesforce object selection, including `Product_Usage__c`.
- Destination raw schema.
- Pipeline run.
- Raw Delta tables.

All source tables must be created by Lakeflow Connect from Salesforce.

### 4. GitHub And Databricks Git Folder

Validate:

- GitHub repository.
- Databricks Git folder.
- Visual data prep file.
- Source-control workflow.
- Secret-free repository structure.

### 5. Lakeflow Designer Visual Prep

Build and run:

1. Source operators for raw Salesforce tables.
2. Prepare and Filter operators for trusted entities.
3. Join and Aggregate operators for support, pipeline, and usage signals.
4. Prepare or AI Function operators for risk score and briefing context.
5. Output operators for gold and serving tables.

Validate:

- Canvas lineage.
- Node-level preview.
- Full visual data prep run.
- Quality filters.
- Data preview.

### 6. Quality And Monitoring

Review:

- Filtered invalid rows.
- Data profile.
- Canvas lineage.
- Data preview.
- Lineage.
- How Designer differs from a plain notebook job.

### 7. Lakeflow Job

Create or validate:

```text
job_renewal_risk_daily_refresh_dev
```

Task sequence:

```text
Salesforce ingestion -> visual data prep -> AI context
```

### 8. Agentic Serving Layer

Run:

```text
setup/03_ai_query_account_briefing.sql
```

Optionally deploy the Databricks App from:

```text
src/app
```

### 9. Versioning Workflow

Change the risk threshold or recommended-action text.

Validate:

1. Lakeflow file edit.
2. Pipeline run.
3. Git diff.
4. Commit.
5. Push to GitHub.

## Constraint Handling

If Salesforce authentication fails, fix the Salesforce connection before running
the data pipeline. The project does not include a non-Salesforce ingestion path.

If AI functions are unavailable, use the generated `account_summary_text` as the
agent prompt context.

If Databricks Apps are unavailable, use SQL.

If bundle validation takes too long, validate the UI-created pipeline first and
return to bundle deployment later.

## Final Outcome

By the end, developers should understand:

- How Lakeflow Connect ingests SaaS data.
- How Lakeflow Designer models trusted, gold, and serving layers visually.
- How visual filters and profiling make quality observable.
- How the Databricks UI and GitHub work together.
- How Lakeflow Jobs orchestrate cross-pipeline work.
- How trusted gold tables become safe context for an AI/agentic layer.
