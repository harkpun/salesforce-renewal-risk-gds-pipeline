# Problem Statement

## Business Context

A B2B SaaS company sells annual contracts to enterprise customers. Most renewal
signals live in Salesforce:

- Account details identify the customer, segment, industry, revenue proxy, and
  owner context.
- Opportunities show renewal and expansion pipeline.
- Cases show support friction, open blockers, and SLA exposure.
- Contacts show whether a decision maker exists for the account.

Application usage is stored in the Salesforce custom object `Product_Usage__c`
and joined in the lakehouse by `AccountNumber`.

## Business Question

Which accounts are at renewal risk, why are they risky, and what action should
the Customer Success team take this week?

## Data Engineering Goals

The project implements production-oriented data engineering patterns on
Databricks:

1. Ingest SaaS data with Lakeflow Connect.
2. Store source data in governed Unity Catalog tables.
3. Build a source-controlled Lakeflow Designer visual data prep.
4. Use trusted entity, gold, and serving layers.
5. Add visual quality filters and profiling checks.
6. Create a business-facing risk scoring table.
7. Orchestrate ingestion and transformation with Lakeflow Jobs.
8. Version code through Databricks Git folders and GitHub.
9. Serve a small agentic account briefing capability.

