# Versioning And Orchestration

This project uses Lakeflow Designer as the primary transformation surface.

The important mental model is:

```text
Lakeflow Connect = Salesforce ingestion into raw Unity Catalog tables
Lakeflow Designer = visual transformation canvas
Databricks Git folder = UI working copy of the GitHub repo
GitHub = source of truth for reviewed project files
Lakeflow Job = orchestration across Salesforce ingestion and visual prep
CI/CD = automation that deploys and runs the approved version
```

## Two Databricks Folders, Two Different Purposes

This project intentionally uses two Databricks workspace locations.

```text
Databricks Git folder
  Example: /Workspace/Users/<your-email>/salesforce-renewal-risk-dbx-pipeline
  Created by: cloning the GitHub repository in Databricks
  Purpose: interactive authoring
  You edit this: yes
  Main use: create and change the Lakeflow Designer visual data prep

.bundle deployment folder
  Example: /Workspace/Users/<runner-or-user>/.bundle/...
  Created by: databricks bundle deploy from GitHub Actions
  Purpose: deployed runtime copy
  You edit this: no
  Main use: run deployed jobs and pipelines
```

These are not competing approaches. They are two parts of the same lifecycle:

```text
Author in Databricks Git folder
  -> commit to GitHub
  -> GitHub Actions deploys to .bundle runtime copy
  -> Databricks jobs and pipelines run from the deployed version
```

Never edit files under `.bundle`. Those files are deployment artifacts and can
be replaced by the next CI/CD run.

## What Gets Versioned

Version in GitHub:

```text
designer/*.designer.ipynb
databricks.yml
resources/*.yml
setup/*.sql
src/app/*
salesforce/force-app/**
data/salesforce-bulk/**
docs/*.md
```

`designer/*.designer.ipynb` is the critical file for the visual pipeline. It is
created by Lakeflow Designer and appears in Git as a notebook file.

Do not version:

```text
Salesforce OAuth tokens
Databricks tokens
Personal access tokens
Secrets
Org-specific exported Salesforce IDs
```

## What You Literally Do In The UI

1. Push the local `dev` branch to GitHub.
2. Let GitHub Actions deploy the `dev` bundle.
3. In Databricks, create a Git folder from the same GitHub repo on `dev`.
4. Open the Git folder.
5. Go to `Visual Data Prep`.
6. Create a visual data prep inside the repo's `designer` folder.
7. Name it `renewal_risk_visual_data_prep`.
8. Add Source operators for the Lakeflow Connect raw Salesforce tables.
9. Add Prepare, Filter, Join, Aggregate, AI Function, and Output operators.
10. Preview each node while building.
11. Run the visual data prep.
12. Confirm output tables in `renewal_risk_lakehouse.renewal_risk_dev`.
13. Open the Git panel in Databricks.
14. Review the changed `.designer.ipynb` file.
15. Commit.
16. Push to GitHub.
17. Let GitHub Actions redeploy the updated `dev` bundle.

That is the sync path:

```text
Designer canvas edit
  -> Databricks workspace file
  -> designer/renewal_risk_visual_data_prep.designer.ipynb
  -> Git commit from Databricks Git panel
  -> GitHub
```

## What The Canvas Represents

The visual data prep file is not only a picture. Designer stores the workflow as
a notebook-backed artifact. The canvas operators are backed by generated code,
and Databricks can run the visual data prep as a job.

In this project, the canvas should contain:

```text
Source nodes:
  src_account
  src_contact
  src_opportunity
  src_case
  src_product_usage

Transform nodes:
  prep_accounts
  prep_contacts
  prep_opportunities
  prep_cases
  prep_product_usage
  filter_valid_contacts
  filter_valid_cases
  agg_support_exposure
  agg_pipeline_health
  agg_decision_makers
  agg_usage_trend
  join_support_exposure
  join_pipeline_health
  join_usage_trend
  join_decision_makers
  prep_renewal_risk
  filter_actionable_accounts
  prep_account_briefing

Output nodes:
  silver_accounts
  silver_contacts
  silver_opportunities
  silver_cases
  silver_product_usage_daily
  gold_open_support_exposure
  gold_pipeline_health
  gold_usage_trend
  gold_account_renewal_risk
  gold_csm_priority_queue
  gold_account_360_summary
  ai_account_briefing_documents
```

For a compact implementation, write only the final gold and serving outputs.
Keep the intermediate silver/gold aggregate nodes on the canvas and preview
them without writing every intermediate table.

## What The Bundle Still Does

The bundle still matters for the pieces that should be reproducible:

```text
databricks.yml
resources/environment_bootstrap_job.yml
resources/salesforce_ingestion_pipeline.yml
resources/renewal_risk_visual_job.yml.example
```

The bundle deploys the environment bootstrap job and Lakeflow Connect ingestion
pipeline by default. The visual job template is intentionally not included until
the visual data prep file exists in Git. After you create and commit the
Designer file, copy `resources/renewal_risk_visual_job.yml.example` to
`resources/renewal_risk_visual_job.yml` and deploy again.

The clean production sequence is:

```text
deploy bootstrap and ingestion resources
run environment bootstrap job
create or validate Salesforce connection
deploy Salesforce ingestion pipeline
run Salesforce ingestion
run Designer visual data prep
run account briefing or app serving step
```

## Dev And Prod Promotion

Development target:

```text
Input:  renewal_risk_lakehouse.raw_sfdc_dev
Output: renewal_risk_lakehouse.renewal_risk_dev
Git:    dev branch
```

Production target:

```text
Input:  renewal_risk_lakehouse.raw_sfdc_prod
Output: renewal_risk_lakehouse.renewal_risk
Git:    main branch
```

The Designer canvas is built against `raw_sfdc_dev` and `renewal_risk_dev` for
interactive work. For deployed runs, the bundle target passes `raw_schema` and
`pipeline_schema` into the visual notebook task:

```text
dev target  -> raw_schema = raw_sfdc_dev,  pipeline_schema = renewal_risk_dev
prod target -> raw_schema = raw_sfdc_prod, pipeline_schema = renewal_risk
```

The committed `.designer.ipynb` file uses those parameters to override the
Source operator schema and final Output operator schema at runtime. This keeps
one versioned visual pipeline file while still separating development and
production raw/output tables.

Lakeflow Connect event logs are also target-specific:

```text
dev target  -> lfc_salesforce_ingestion_event_log_dev
prod target -> lfc_salesforce_ingestion_event_log_prod
```

This avoids dev and prod ingestion pipelines fighting over the same event log
table in the shared `pipeline_events` schema.

## CI/CD Flow

CI/CD does not rebuild the canvas manually. It uses the committed file.

Branch behavior:

```text
push to dev                -> validate and deploy dev target
merged PR from dev to main -> validate and deploy prod target
```

There are no path filters. Any push to `dev` runs the dev deployment workflow.
Production deployment runs only when a pull request from `dev` into `main` is
closed with `merged = true`.

The `prod` target uses `mode: production`, so `databricks.yml` also sets an
explicit `workspace.root_path`. This is required by Databricks Asset Bundles to
keep production deployment in one stable workspace location.

## GitHub Actions Authentication

This project uses token-based Databricks authentication for GitHub Actions.

Create these values in GitHub:

```text
DATABRICKS_HOST   -> secret
DATABRICKS_TOKEN  -> secret
```

`DATABRICKS_HOST` is the workspace URL:

```text
https://dbc-xxxx.cloud.databricks.com
```

`DATABRICKS_TOKEN` is a Databricks personal access token created from the target
workspace. Store it only as a GitHub secret.

Store both values under GitHub Actions `Secrets`, not `Variables`.

Recommended setup:

1. In Databricks, create a PAT for the user or automation identity that will run
   bundle deployment.
2. In GitHub, open the repository.
3. Go to `Settings` -> `Secrets and variables` -> `Actions`.
4. Add repository or environment secret `DATABRICKS_HOST`.
5. Add repository or environment secret `DATABRICKS_TOKEN`.
6. If using GitHub environments named `dev` and `prod`, create both
   environments and set the correct host/token values in each environment.

The workflow passes these into Databricks CLI:

```yaml
env:
  DATABRICKS_HOST: ${{ secrets.DATABRICKS_HOST }}
  DATABRICKS_TOKEN: ${{ secrets.DATABRICKS_TOKEN }}
```

No `DATABRICKS_CLIENT_ID` is required for this token-based setup.

Minimal pull request flow:

```text
Create or edit visual data prep in Databricks
  -> commit .designer.ipynb to dev
  -> push dev
  -> validate and deploy dev
  -> open pull request from dev to main
  -> review Designer file, docs, and bundle resources
  -> merge to main
  -> validate and deploy prod
```

Minimal deployment flow:

```text
CI/CD checks out repo
  -> authenticates to Databricks
  -> runs setup SQL through SQL Statement Execution API
  -> validates bundle resources
  -> deploys bootstrap and ingestion resources
  -> runs or schedules the Lakeflow Job
```

Automatic production deployment happens only after a pull request from `dev` to
`main` is merged.

The job should run:

```text
refresh_salesforce_ingestion
  -> run_renewal_risk_visual_data_prep
```

The setup SQL is used in two places:

```text
scripts/bootstrap_unity_catalog.py
  -> setup/00_create_catalog_and_schemas.sql
  -> runs before bundle deployment in GitHub Actions

job_renewal_risk_environment_bootstrap_dev / job_renewal_risk_environment_bootstrap_prod
  -> create_catalog_and_schemas
  -> manual repair or verification job after deployment
```

The pre-deploy script is required because the Salesforce ingestion pipeline
cannot be created until its destination catalog and schemas already exist.

## UI Scheduling Option

For a practical first implementation, use the Designer Schedule button:

1. Open `designer/renewal_risk_visual_data_prep`.
2. Click Schedule.
3. Create a job for the visual data prep.
4. Add a dependency so Salesforce ingestion runs before visual prep, or keep the
   ingestion run manual while building.

Once the visual pipeline is stable, move the job definition into the bundle so
the orchestration is reproducible.

## Important Rule

If you change the visual canvas, commit the `.designer.ipynb` file.

If you change job or pipeline resource settings, make sure the change is also
represented in YAML. UI-only resource changes can be overwritten later by a
bundle deployment.
