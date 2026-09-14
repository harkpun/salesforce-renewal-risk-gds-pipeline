# Lakeflow Designer Visual Build Guide

This guide uses Databricks Lakeflow Designer as the primary transformation
surface. The visual data prep canvas is the project implementation.

## Core Design

```text
Salesforce
  -> Lakeflow Connect
  -> renewal_risk_lakehouse.raw_sfdc_dev
  -> Lakeflow Designer visual data prep
  -> renewal_risk_lakehouse.renewal_risk_dev
  -> account queue, AI briefing
```

Designer does not read directly from Salesforce in this project. It reads the
Unity Catalog raw tables created by Lakeflow Connect.

Incremental Salesforce reads are handled by the target-specific Lakeflow Connect
ingestion pipeline, `lfc_salesforce_ingestion_dev` or
`lfc_salesforce_ingestion_prod`. The Source operators in Designer do not connect
to Salesforce and do not have a separate incremental-read setting. They read the
current raw Delta tables in Unity Catalog. The expected behavior is:

```text
Salesforce incremental read
  -> handled by lfc_salesforce_ingestion_dev or lfc_salesforce_ingestion_prod
  -> writes current raw tables in the target raw schema

Lakeflow Designer Source operators
  -> read renewal_risk_lakehouse.raw_sfdc_dev while building
  -> transform the latest available raw state into serving outputs
```

For deployed runs, the bundle passes `raw_schema` to the Designer notebook:

```text
dev target  -> raw_sfdc_dev
prod target -> raw_sfdc_prod
```

For production-scale transformation efficiency, avoid thinking only in terms of
"new rows." Salesforce can update existing rows, delete rows, or change child
records that affect an existing account's risk score. This project also uses
date-driven fields such as `days_to_renewal`; those values can change even when
the Salesforce source row has not changed.

The production goal is:

```text
Do not re-extract all Salesforce data every run.
Do incrementally refresh affected silver, gold, and serving outputs when the
platform can do so correctly.
```

In Lakeflow Designer, choose Materialized view as the Output type for final gold
and serving datasets when the UI provides that option. Materialized views allow
Databricks to incrementally refresh results when the transformation is eligible.
If a strict row-by-row streaming transformation is required, implement that part
with Lakeflow Declarative Pipelines using streaming tables or Auto CDC, and keep
Designer for the visual modeling walkthrough.

## 1. Place The Visual Data Prep In Git

In Databricks:

1. Clone this GitHub repository into a Databricks Git folder.
2. Open the repo folder.
3. Create a folder named `designer` if it does not already exist.
4. Create a new visual data prep inside that Git folder.
5. Rename the file to:

```text
renewal_risk_visual_data_prep
```

When committed to Git, Databricks stores it as:

```text
designer/renewal_risk_visual_data_prep.designer.ipynb
```

In the Databricks Workspace browser, the same asset can appear as:

```text
Name: renewal_risk_visual_data_prep
Type: Visual data prep
```

That is normal. The Workspace UI shows the native asset type and often hides
the backing notebook extension. The `.designer.ipynb` filename is what you
should see in the Git changes panel, after export, or after pushing/pulling the
repository outside Databricks.

This `.designer.ipynb` file is the versioned visual pipeline artifact.

## 2. Run Salesforce Ingestion First

Before building the Designer canvas, run the Lakeflow Connect ingestion
pipeline:

```text
lfc_salesforce_ingestion_dev
```

Confirm these raw tables exist:

```text
renewal_risk_lakehouse.raw_sfdc_dev.Account
renewal_risk_lakehouse.raw_sfdc_dev.Contact
renewal_risk_lakehouse.raw_sfdc_dev.Opportunity
renewal_risk_lakehouse.raw_sfdc_dev.Case
renewal_risk_lakehouse.raw_sfdc_dev.Product_Usage__c
```

Designer Source operators will read these tables.

## 3. Add Source Operators

Add five Source operators:

```text
src_account
src_contact
src_opportunity
src_case
src_product_usage
```

Configure them as:

```text
src_account         -> renewal_risk_lakehouse.raw_sfdc_dev.Account
src_contact         -> renewal_risk_lakehouse.raw_sfdc_dev.Contact
src_opportunity     -> renewal_risk_lakehouse.raw_sfdc_dev.Opportunity
src_case            -> renewal_risk_lakehouse.raw_sfdc_dev.Case
src_product_usage   -> renewal_risk_lakehouse.raw_sfdc_dev.Product_Usage__c
```

Use Browse existing in each Source operator and select the Unity Catalog table.

## 4. Prompt-Driven Build Sequence

You can use the prompt box at the bottom of Lakeflow Designer to generate or
extend the canvas. Use these prompts sequentially. After each prompt, review the
operators created by Genie Code, preview the output, rename operators if needed,
and then continue to the next prompt.

Use table mentions with `@` where the UI supports it. If Genie Code cannot add a
Source operator because source selection requires the table picker, add that
Source operator manually and continue with the next prompt.

### Prompt 1: Add All Raw Sources

```text
Create Source operators for the Salesforce raw tables in Unity Catalog. Use these source tables while building in dev:

1. renewal_risk_lakehouse.raw_sfdc_dev.Account as src_account
2. renewal_risk_lakehouse.raw_sfdc_dev.Contact as src_contact
3. renewal_risk_lakehouse.raw_sfdc_dev.Opportunity as src_opportunity
4. renewal_risk_lakehouse.raw_sfdc_dev.Case as src_case
5. renewal_risk_lakehouse.raw_sfdc_dev.Product_Usage__c as src_product_usage

Keep these sources as raw inputs only. Do not join or aggregate yet.
```

### Prompt 2: Prepare Trusted Accounts

```text
From src_account, create a Prepare operator named prep_accounts.

Keep and rename these columns:
Id to account_id
AccountNumber to account_number
Name to account_name
Industry to industry
Customer_Segment__c to customer_segment
ARR__c to arr
Renewal_Date__c to renewal_date

Cast arr as numeric and renewal_date as date. Trim account_number and account_name. Add a Filter operator named filter_valid_accounts where account_id is not null and account_number is not null.
```

### Prompt 3: Prepare Trusted Contacts

```text
From src_contact, create a Prepare operator named prep_contacts.

Keep and rename these columns:
Id to contact_id
AccountId to account_id
Email to email
Title to title
Department to department
Is_Decision_Maker__c to is_decision_maker

Trim email, title, and department. Cast is_decision_maker as boolean. Add a Filter operator named filter_valid_contacts where account_id is not null and email contains @.
```

### Prompt 4: Prepare Trusted Opportunities

```text
From src_opportunity, create a Prepare operator named prep_opportunities.

Keep and rename these columns:
Id to opportunity_id
AccountId to account_id
StageName to stage_name
Amount to amount
CloseDate to close_date
Renewal_Opportunity__c to is_renewal_opportunity
Expansion_Candidate__c to is_expansion_opportunity
Days_In_Stage__c to days_in_stage

Cast amount and days_in_stage as numeric. Cast close_date as date. Cast is_renewal_opportunity and is_expansion_opportunity as boolean. Add a Filter operator named filter_valid_opportunities where account_id is not null.
```

### Prompt 5: Prepare Trusted Cases

```text
From src_case, create a Prepare operator named prep_cases.

Keep and rename these columns:
Id to case_id
AccountId to account_id
CaseNumber to case_number
Priority to priority
Status to status
Reported_Date__c to reported_date
Resolved_Date__c to resolved_date
SLA_Breached__c to sla_breached

Cast reported_date and resolved_date as dates. Cast sla_breached as boolean.

Add these calculated columns:
is_open = true when status is not Closed, otherwise false
case_age_days = number of days between current date and reported_date

Add a Filter operator named filter_valid_cases where account_id is not null and priority is one of Low, Medium, High, or Critical.
```

### Prompt 6: Prepare Trusted Product Usage

```text
From src_product_usage, create a Prepare operator named prep_product_usage.

Keep and rename these columns:
Account_Number__c to account_number
Usage_Date__c to usage_date
Active_Users__c to active_users
Api_Calls__c to api_calls
Failed_Api_Calls__c to failed_api_calls
Key_Feature_Events__c to key_feature_events

Trim account_number. Cast usage_date as date. Cast active_users, api_calls, failed_api_calls, and key_feature_events as numeric.

Add a Filter operator named filter_valid_usage where account_number is not null, usage_date is not null, active_users is greater than or equal to 0, api_calls is greater than or equal to 0, and failed_api_calls is greater than or equal to 0.
```

### Prompt 7: Build Support Exposure Aggregate

```text
From filter_valid_cases, create an Aggregate operator named agg_support_exposure grouped by account_id.

Create these metrics:
open_case_count = count of rows where is_open is true
open_high_priority_case_count = count of rows where is_open is true and priority is High or Critical
open_sla_breach_count = count of rows where is_open is true and sla_breached is true
max_open_case_age_days = maximum case_age_days for open cases

Keep one row per account_id.
```

### Prompt 8: Build Pipeline Health Aggregate

```text
From filter_valid_opportunities, create an Aggregate operator named agg_pipeline_health grouped by account_id.

Create these metrics:
renewal_pipeline_amount = sum of amount where is_renewal_opportunity is true
stalled_renewal_opportunity_count = count of rows where is_renewal_opportunity is true, stage_name is not Closed Won, stage_name is not Closed Lost, and days_in_stage is greater than 30
active_expansion_opportunity_count = count of rows where is_expansion_opportunity is true and stage_name is not Closed Won and stage_name is not Closed Lost
latest_renewal_close_date = maximum close_date where is_renewal_opportunity is true

Keep one row per account_id.
```

### Prompt 9: Build Decision-Maker Coverage Aggregate

```text
From filter_valid_contacts, create an Aggregate operator named agg_decision_makers grouped by account_id.

Create these metrics:
contact_count = count of contacts
decision_maker_contact_count = count of rows where is_decision_maker is true
has_decision_maker = true when decision_maker_contact_count is greater than 0, otherwise false

Keep one row per account_id.
```

### Prompt 10: Build Usage Trend Aggregate

```text
Join filter_valid_usage to filter_valid_accounts using account_number. Name the Join operator join_usage_accounts.

From join_usage_accounts, create calculated columns:
latest_window_flag = true when usage_date is within the latest 14 days available in the usage table
previous_window_flag = true when usage_date is in the 14 days before the latest window

Create an Aggregate operator named agg_usage_trend grouped by account_id.

Create these metrics:
avg_active_users_latest_14_days = average active_users where latest_window_flag is true
avg_active_users_previous_14_days = average active_users where previous_window_flag is true
api_calls_latest_14_days = sum api_calls where latest_window_flag is true
failed_api_calls_latest_14_days = sum failed_api_calls where latest_window_flag is true
key_feature_events_latest_14_days = sum key_feature_events where latest_window_flag is true
api_failure_rate_latest_14_days = failed_api_calls_latest_14_days divided by api_calls_latest_14_days, using 0 when api_calls_latest_14_days is 0
active_user_growth_rate = avg_active_users_latest_14_days minus avg_active_users_previous_14_days divided by avg_active_users_previous_14_days, using 0 when avg_active_users_previous_14_days is 0

Keep one row per account_id.
```

### Prompt 11: Join Account Risk Signals

```text
Starting from filter_valid_accounts, join the account-level aggregates by account_id in this order:

1. agg_support_exposure
2. agg_pipeline_health
3. agg_usage_trend
4. agg_decision_makers

Use left joins so every valid account remains in the output. Name the join operators:
join_support_exposure
join_pipeline_health
join_usage_trend
join_decision_makers

After the joins, create a Prepare operator named prep_account_risk_features. Replace null numeric metrics with 0 and replace null has_decision_maker with false.
```

### Prompt 12: Create Renewal Risk Score

```text
From prep_account_risk_features, create a Prepare operator named prep_renewal_risk.

Add these calculated columns:
days_to_renewal = number of days between current date and renewal_date

risk_score =
30 points when days_to_renewal is between 0 and 90
25 points when open_high_priority_case_count is greater than 0
15 points when open_sla_breach_count is greater than 0
15 points when stalled_renewal_opportunity_count is greater than 0
15 points when active_user_growth_rate is less than or equal to -0.10
10 points when has_decision_maker is false
10 points when arr is greater than or equal to 250000
minus 10 points when active_expansion_opportunity_count is greater than 0

Clamp risk_score so it is never below 0 and never above 100.

risk_band =
Critical when risk_score is greater than or equal to 80
High when risk_score is greater than or equal to 60
Medium when risk_score is greater than or equal to 40
Low otherwise

recommended_action =
Executive escalation when risk_band is Critical
CSM renewal save plan when risk_band is High
Adoption and stakeholder follow-up when risk_band is Medium
Monitor account health when risk_band is Low
```

### Prompt 13: Create Gold Account Renewal Risk Output

```text
From prep_renewal_risk, create an Output operator for renewal_risk_lakehouse.renewal_risk_dev.gold_account_renewal_risk.

Use Output type Materialized view if that option is available. If the UI does not allow this output to be a materialized view, write it as a managed Unity Catalog table for the hands-on implementation.

Include these columns:
account_id
account_number
account_name
industry
customer_segment
arr
renewal_date
days_to_renewal
open_case_count
open_high_priority_case_count
open_sla_breach_count
max_open_case_age_days
renewal_pipeline_amount
stalled_renewal_opportunity_count
active_expansion_opportunity_count
avg_active_users_latest_14_days
avg_active_users_previous_14_days
api_failure_rate_latest_14_days
active_user_growth_rate
decision_maker_contact_count
has_decision_maker
risk_score
risk_band
recommended_action
```

### Prompt 14: Create CSM Priority Queue

```text
From prep_renewal_risk, create a Filter operator named filter_actionable_accounts where risk_band is Critical, High, or Medium.

Sort the result by risk_score descending, arr descending, and days_to_renewal ascending.

Create an Output operator for renewal_risk_lakehouse.renewal_risk_dev.gold_csm_priority_queue. Use Output type Materialized view if available. If not available, write it as a managed Unity Catalog table for the hands-on implementation.

Include the account identity fields, renewal fields, risk fields, top risk signals, and recommended_action.
```

### Prompt 15: Create Account 360 Summary

```text
From prep_renewal_risk, create a Prepare operator named prep_account_360_summary.

Add a calculated text column named account_summary_text. The text should summarize:
account name
customer segment
ARR
renewal date
risk score
risk band
support exposure
pipeline health
usage trend
decision-maker coverage
recommended action

Create an Output operator for renewal_risk_lakehouse.renewal_risk_dev.gold_account_360_summary. Use Output type Materialized view if available. If not available, write it as a managed Unity Catalog table for the hands-on implementation.
```

### Prompt 16: Create AI Briefing Documents

```text
From prep_account_360_summary, create a Prepare operator named prep_ai_account_briefing_documents.

Create these columns:
document_id = account_id
account_id = account_id
account_name = account_name
content = account_summary_text
source_table = renewal_risk_lakehouse.renewal_risk_dev.gold_account_360_summary
created_at = current timestamp only if the output is a managed table. If the output is a materialized view, omit created_at to keep the expression deterministic.

Create an Output operator for renewal_risk_lakehouse.renewal_risk_dev.ai_account_briefing_documents. Use Output type Materialized view if available. If not available, write it as a managed Unity Catalog table for the hands-on implementation.
```

### Prompt 17: Final Canvas Review

```text
Review this visual data prep and organize the canvas from left to right:

1. raw source operators
2. trusted prepare and filter operators
3. account-level aggregate operators
4. joins into account risk features
5. renewal risk scoring
6. final output tables

Do not remove existing output operators. Make operator names readable and consistent with the project naming pattern.
```

## 5. Build Trusted Entity Branches

For each source, add a Prepare operator. Use it to select, rename, and clean
columns.

### Account Branch

```text
src_account -> prep_accounts
```

Prepare actions:

```text
Id                  -> account_id
AccountNumber       -> account_number
Name                -> account_name
Industry            -> industry
Customer_Segment__c -> customer_segment
ARR__c              -> arr
Renewal_Date__c     -> renewal_date
```

Add filters:

```text
account_id is not null
account_number is not null
```

Output:

```text
silver_accounts
```

### Contact Branch

```text
src_contact -> prep_contacts -> filter_valid_contacts
```

Prepare actions:

```text
Id                    -> contact_id
AccountId             -> account_id
Email                 -> email
Title                 -> title
Department            -> department
Is_Decision_Maker__c  -> is_decision_maker
```

Filter:

```text
account_id is not null
email contains @
```

Output:

```text
silver_contacts
```

### Opportunity Branch

```text
src_opportunity -> prep_opportunities -> filter_valid_opportunities
```

Prepare actions:

```text
Id                       -> opportunity_id
AccountId                -> account_id
StageName                -> stage_name
Amount                   -> amount
CloseDate                -> close_date
Renewal_Opportunity__c   -> is_renewal_opportunity
Expansion_Candidate__c   -> is_expansion_opportunity
Days_In_Stage__c         -> days_in_stage
```

Filter:

```text
account_id is not null
```

Output:

```text
silver_opportunities
```

### Case Branch

```text
src_case -> prep_cases -> filter_valid_cases
```

Prepare actions:

```text
Id                -> case_id
AccountId         -> account_id
CaseNumber        -> case_number
Priority          -> priority
Status            -> status
Reported_Date__c  -> reported_date
Resolved_Date__c  -> resolved_date
SLA_Breached__c   -> sla_breached
```

Add custom columns:

```text
is_open = status not in Closed
case_age_days = date difference between current date and reported_date
```

Filter:

```text
account_id is not null
priority is one of Low, Medium, High, Critical
```

Output:

```text
silver_cases
```

### Product Usage Branch

```text
src_product_usage -> prep_product_usage -> filter_valid_usage
```

Prepare actions:

```text
Account_Number__c       -> account_number
Usage_Date__c           -> usage_date
Active_Users__c         -> active_users
Api_Calls__c            -> api_calls
Failed_Api_Calls__c     -> failed_api_calls
Key_Feature_Events__c   -> key_feature_events
```

Filter:

```text
account_number is not null
usage_date is not null
active_users >= 0
api_calls >= 0
failed_api_calls >= 0
```

Output:

```text
silver_product_usage_daily
```

## 6. Build Gold Aggregates

Add Aggregate operators from the silver branches.

### Support Exposure

```text
silver_cases -> agg_support_exposure
```

Group by:

```text
account_id
```

Aggregations:

```text
count open cases
count open high-priority cases
count open SLA breaches
max case_age_days
```

Output:

```text
gold_open_support_exposure
```

### Pipeline Health

```text
silver_opportunities -> agg_pipeline_health
```

Group by:

```text
account_id
```

Aggregations:

```text
sum renewal amount
count stalled renewal opportunities
count active expansion opportunities
max renewal close date
```

Output:

```text
gold_pipeline_health
```

### Decision Maker Coverage

```text
silver_contacts -> agg_decision_makers
```

Group by:

```text
account_id
```

Aggregation:

```text
count decision-maker contacts
```

### Usage Trend

```text
silver_product_usage_daily -> join_usage_accounts -> agg_usage_trend
```

Join:

```text
silver_product_usage_daily.account_number = silver_accounts.account_number
```

Aggregate by:

```text
account_id
```

Metrics:

```text
average active users in latest 14 days
average active users in previous 14 days
failed API calls in latest 14 days
API calls in latest 14 days
API failure rate
active user growth rate
```

Output:

```text
gold_usage_trend
```

## 7. Build Account Renewal Risk

Use Join operators to combine:

```text
silver_accounts
gold_open_support_exposure
gold_pipeline_health
gold_usage_trend
agg_decision_makers
```

Recommended join path:

```text
silver_accounts
  -> join_support_exposure
  -> join_pipeline_health
  -> join_usage_trend
  -> join_decision_makers
  -> prep_renewal_risk
```

In `prep_renewal_risk`, add custom columns for:

```text
days_to_renewal
risk_score
risk_band
recommended_action
```

Risk scoring rules:

```text
+30 renewal due within 90 days
+25 open high-priority support case exists
+15 open SLA breach exists
+15 stalled renewal opportunity exists
+15 product usage dropped by at least 10 percent
+10 no decision-maker contact exists
+10 high-value account by ARR
-10 active expansion opportunity exists
```

Output:

```text
gold_account_renewal_risk
```

## 8. Build CSM Priority Queue

From `gold_account_renewal_risk`, add:

```text
filter_actionable_accounts -> sort_priority_queue -> output_priority_queue
```

Filter:

```text
risk_band is Critical, High, or Medium
```

Sort:

```text
risk_score descending
arr descending
days_to_renewal ascending
```

Output:

```text
gold_csm_priority_queue
```

## 9. Build AI Briefing Context

From `gold_account_renewal_risk`, add a Prepare or AI Function operator.

Create:

```text
account_summary_text
```

The text should include:

```text
account name
segment
ARR
renewal date
risk band
risk score
support exposure
usage trend
decision-maker coverage
recommended action
```

Outputs:

```text
gold_account_360_summary
ai_account_briefing_documents
```

## 10. Output Locations

During development, write outputs to:

```text
renewal_risk_lakehouse.renewal_risk_dev
```

When promoting, write outputs to:

```text
renewal_risk_lakehouse.renewal_risk
```

Use Output operators for the final gold and serving datasets. Prefer
Materialized view outputs when available because Databricks can incrementally
refresh eligible materialized views from upstream changes. Use managed table
outputs only when the UI does not support materialized view output for the
specific node.

For CI/CD, do not manually maintain a separate production Designer file. Keep
the canvas output configured to the development schema while building:

```text
renewal_risk_lakehouse.renewal_risk_dev
```

The bundle job passes `pipeline_schema` into the Designer notebook:

```text
dev target  -> renewal_risk_dev
prod target -> renewal_risk
```

At runtime, the committed Designer notebook overrides the final Output operator
schema from this parameter. That is how the same `.designer.ipynb` file writes
to development after a `dev` branch push and production after a merged
`dev`-to-`main` pull request.

For a compact implementation, you can skip physical bronze outputs and keep
bronze-style normalization inside the early Prepare operators.

## 11. Use Genie Code Carefully

Use Genie Code for expressions such as:

```text
Create a risk_score column using these scoring rules...
Create a risk_band column from risk_score...
Create an account_summary_text column using these fields...
```

Review generated expressions before running the full workflow.

## 12. Commit The Visual Pipeline

After the canvas works:

1. Open the Git panel.
2. Review the changed file:

```text
designer/renewal_risk_visual_data_prep.designer.ipynb
```

3. Commit.
4. Push to GitHub.

That file is the source-controlled visual pipeline.

## 13. Schedule Or Add To A Job

From Designer:

1. Click Schedule to create a job for the visual data prep.
2. Or open Jobs & Pipelines and add the visual data prep as a task.

Recommended job order:

```text
refresh_salesforce_ingestion
  -> run_renewal_risk_visual_data_prep
```

The first task is Lakeflow Connect ingestion. The second task is the Designer
visual pipeline. The environment bootstrap remains a separate idempotent job and
is also run by GitHub Actions before bundle deployment.
