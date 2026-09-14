# Databricks Setup Guide

This guide explains how to set up the project from Databricks with GitHub,
Lakeflow Connect, Lakeflow Designer visual data prep, and Lakeflow Jobs.

## 1. Create Or Open Databricks Workspace

1. Log in to Databricks.
2. Confirm Unity Catalog is available.
3. Confirm serverless compute is available.
4. Start or select a serverless SQL warehouse.

Free Edition note: keep the project compact. Free Edition has limits on
concurrent jobs, SQL warehouses, apps, and AI Search endpoints.

## 2. Identify SQL Warehouse ID

The decoupled environment bootstrap job uses a SQL warehouse task. The GitHub
Actions workflow also uses this warehouse ID when it runs the same setup SQL
before bundle deployment.

In Databricks:

1. Open SQL Warehouses.
2. Select the warehouse you want to use.
3. Copy the warehouse ID from the browser URL or warehouse details.
4. Update `databricks.yml`:

```text
sql_warehouse_id: <your-sql-warehouse-id>
```

The GitHub Actions workflow runs the setup SQL before bundle deployment. This
creates the Unity Catalog objects required before the Salesforce ingestion
pipeline is created:

```text
renewal_risk_lakehouse.raw_sfdc_dev
renewal_risk_lakehouse.raw_sfdc_prod
renewal_risk_lakehouse.renewal_risk
renewal_risk_lakehouse.renewal_risk_dev
renewal_risk_lakehouse.pipeline_events
renewal_risk_lakehouse.ai
```

The `pipeline_events` schema is shared, but the Lakeflow Connect event log table
name is target-specific:

```text
dev target  -> lfc_salesforce_ingestion_event_log_dev
prod target -> lfc_salesforce_ingestion_event_log_prod
```

The raw Salesforce schema is also target-specific:

```text
dev target  -> raw_sfdc_dev
prod target -> raw_sfdc_prod
```

This prevents separate dev and prod Lakeflow Connect pipeline IDs from trying
to own the same raw Delta tables.

No raw tables are created by setup SQL. Raw tables are created only by Lakeflow
Connect after Salesforce ingestion runs.

## 3. Create GitHub Repository

1. Create a GitHub repository:

```text
salesforce-renewal-risk-dbx-pipeline
```

2. Keep the repository available as the remote named `origin`.
3. Keep credentials out of GitHub.

Do not commit:

- Salesforce passwords.
- Salesforce OAuth tokens.
- Databricks personal access tokens.
- Databricks app secrets.

## 4. Configure GitHub Actions For Databricks

The GitHub Actions workflow uses Databricks token authentication.

Create a Databricks personal access token from the workspace that will receive
the bundle deployment.

Then in GitHub:

1. Open the repository.
2. Go to `Settings` -> `Secrets and variables` -> `Actions`.
3. Add secret `DATABRICKS_HOST`.
4. Add secret `DATABRICKS_TOKEN`.

Example value for `DATABRICKS_HOST`:

```text
https://dbc-xxxx.cloud.databricks.com
```

Store both values under `Secrets`, not `Variables`. This keeps the workflow
simple and prevents `DATABRICKS_HOST` from resolving as an empty value.

## 5. Connect GitHub To Databricks

In Databricks:

1. Open User Settings.
2. Open Git integration.
3. Connect GitHub.
4. Use OAuth or a Git provider token, depending on workspace configuration.
5. Confirm Databricks can clone repositories from your GitHub account.

## 6. Create Salesforce Connection In Unity Catalog

Create the Databricks Salesforce connection before the first CI/CD deployment.
The bundle deploys a Lakeflow Connect ingestion resource that references this
connection by name.

1. Open Catalog Explorer.
2. Open Connections.
3. Create a new connection.
4. Choose Salesforce.
5. Name it:

```text
salesforce_renewal_risk_conn
```

6. Authenticate with the Salesforce Developer Edition user.
7. Grant yourself `USE CONNECTION`.

Required Databricks privileges:

- `CREATE CONNECTION` if creating the connection.
- `USE CONNECTION` if using an existing connection.
- `USE CATALOG` on `renewal_risk_lakehouse`.
- After schemas exist, `USE SCHEMA` and `CREATE TABLE` on
  `renewal_risk_lakehouse.raw_sfdc_dev` and
  `renewal_risk_lakehouse.raw_sfdc_prod`.

## 7. Publish The Initial Dev Branch

Databricks can clone only branches that already exist in GitHub. Before cloning
the project into a Databricks Git folder, commit the local project and push the
`dev` branch.

From the local project folder:

```bash
git status
git checkout -b dev
git add .
git commit -m "Initial Salesforce renewal risk Databricks project"
git push -u origin dev
```

If your local branch is already named `dev`, use:

```bash
git add .
git commit -m "Initial Salesforce renewal risk Databricks project"
git push -u origin dev
```

After this push, the `dev` branch appears in GitHub and can be selected when
creating the Databricks Git folder. This push also triggers the dev GitHub
Actions deployment workflow.

## 8. Clone The Repo Into A Databricks Git Folder

1. Open Workspace.
2. Open your user home folder.
3. Click Add or Create.
4. Select Git folder.
5. Paste the GitHub repository URL.
6. Select the `dev` branch for active development.
7. Clone.

Expected workspace path:

```text
/Workspace/Users/<your-email>/salesforce-renewal-risk-dbx-pipeline
```

Because this repository contains `databricks.yml`, Databricks recognizes it as a
bundle project. The files in `resources/` describe the Lakeflow pipelines and
job that belong to the project.

Important: the Databricks Git folder is the UI working copy of the same GitHub
repository. It is where you build the Lakeflow Designer file visually and commit
that generated `.designer.ipynb` file back to GitHub.

Do not confuse this Git folder with the `.bundle` folder created by deployment:

```text
Databricks Git folder
  Purpose: human authoring in the Databricks UI
  Edited by: you
  Used for: Lakeflow Designer visual data prep creation and Git commits

.bundle deployment folder
  Purpose: runtime copy created by Databricks bundle deploy
  Edited by: nobody
  Used for: deployed jobs, pipelines, and referenced project files
```

The two folders can exist at the same time. That is expected.

## 9. Deploy The Source-Controlled Project

Deployment happens through GitHub Actions in this project.

After `DATABRICKS_HOST` and `DATABRICKS_TOKEN` are configured in GitHub:

1. Commit changes to the `dev` branch.
2. Push the `dev` branch to GitHub.
3. GitHub Actions runs automatically.
4. The workflow runs `scripts/bootstrap_unity_catalog.py`.
5. The workflow validates the `dev` bundle.
6. The workflow deploys the `dev` bundle.

The workflow executes:

```text
python3 scripts/bootstrap_unity_catalog.py
databricks bundle validate --target dev
databricks bundle deploy --target dev
```

This command creates or updates the deployment copy under Databricks bundle
deployment storage, commonly visible under a `.bundle` path. Do not open that
folder for development and do not edit files there. It is regenerated by future
deployments.

For production, open a pull request from `dev` to `main`. After the pull request
is merged, GitHub Actions deploys the `prod` target automatically.

Expected project resources:

```text
Dev job: job_renewal_risk_environment_bootstrap_dev
Prod job: job_renewal_risk_environment_bootstrap_prod
Dev pipeline: lfc_salesforce_ingestion_dev
Prod pipeline: lfc_salesforce_ingestion_prod
```

The visual transformation file is created separately in Lakeflow Designer. After
it is committed as `designer/renewal_risk_visual_data_prep.designer.ipynb`, you
can enable the visual job template under `resources`.

The same committed Designer file is used for both environments. The bundle
target decides the output schema:

```text
dev target  -> pipeline_schema = renewal_risk_dev
prod target -> pipeline_schema = renewal_risk
```

The visual job passes that value into the Designer notebook as a task parameter.
The Designer canvas can still show the development output schema while you are
editing it, but a deployed job run writes to the schema passed by the target.

## 10. Run Environment Bootstrap Job

GitHub Actions already runs the same setup SQL before bundle deployment by using
`scripts/bootstrap_unity_catalog.py`. The deployed job remains available for
manual repair or verification because the SQL is idempotent.

Open Jobs & Pipelines and run:

```text
job_renewal_risk_environment_bootstrap_dev
```

This job runs:

```text
setup/00_create_catalog_and_schemas.sql
```

The pre-deploy script creates the catalog and schemas before the pipeline is
created. This job keeps the same setup SQL runnable and idempotent for repair or
verification, so rerunning it is safe.

Confirm these schemas exist in Catalog Explorer:

```text
renewal_risk_lakehouse.raw_sfdc_dev
renewal_risk_lakehouse.raw_sfdc_prod
renewal_risk_lakehouse.renewal_risk
renewal_risk_lakehouse.renewal_risk_dev
renewal_risk_lakehouse.pipeline_events
renewal_risk_lakehouse.ai
```

In `pipeline_events`, expect separate event log tables for dev and prod bundle
targets:

```text
lfc_salesforce_ingestion_event_log_dev
lfc_salesforce_ingestion_event_log_prod
```

## 11. Validate Lakeflow Connect Ingestion Configuration

Open pipeline:

```text
lfc_salesforce_ingestion_dev
```

Confirm it uses:

```text
Connection: salesforce_renewal_risk_conn
Destination catalog: renewal_risk_lakehouse
Destination schema: raw_sfdc_dev for dev, raw_sfdc_prod for prod
Objects:
  Account
  Contact
  Opportunity
  Case
  Product_Usage__c
```

Run the pipeline.

Expected ingestion behavior:

```text
First successful run      -> initial load of the selected Salesforce objects
Later successful runs     -> incremental reads based on Salesforce cursor columns
Manual full refresh       -> repair/backfill action only, not the normal path
```

For Salesforce, Lakeflow Connect selects a cursor column automatically from
available Salesforce system fields, preferring `SystemModstamp`, then
`LastModifiedDate`, then `CreatedDate`, then `LoginTime`. The source objects in
this project are standard/custom Salesforce objects that expose these system
fields, so the ingestion pipeline is designed to run incrementally after the
initial load.

After the run, confirm these raw tables exist:

```text
renewal_risk_lakehouse.raw_sfdc_dev.Account
renewal_risk_lakehouse.raw_sfdc_dev.Contact
renewal_risk_lakehouse.raw_sfdc_dev.Opportunity
renewal_risk_lakehouse.raw_sfdc_dev.Case
renewal_risk_lakehouse.raw_sfdc_dev.Product_Usage__c
```

Validate counts:

```sql
SELECT count(*) FROM renewal_risk_lakehouse.raw_sfdc_dev.Account;
SELECT count(*) FROM renewal_risk_lakehouse.raw_sfdc_dev.Contact;
SELECT count(*) FROM renewal_risk_lakehouse.raw_sfdc_dev.Opportunity;
SELECT count(*) FROM renewal_risk_lakehouse.raw_sfdc_dev.`Case`;
SELECT count(*) FROM renewal_risk_lakehouse.raw_sfdc_dev.Product_Usage__c;
```

## 12. Open Lakeflow Designer

Open the Git folder and create or open:

```text
designer/renewal_risk_visual_data_prep
```

Use Lakeflow Designer to build the visual transformation canvas.

The committed visual file appears in Git as:

```text
designer/renewal_risk_visual_data_prep.designer.ipynb
```

The Workspace browser can still show the file name without `.designer.ipynb`
and with type `Visual data prep`. That is expected. Check the Databricks Git
changes panel, GitHub, or your local repo after pull to see the backing
`.designer.ipynb` filename.

Run the visual data prep after Salesforce ingestion completes.

## 13. Version Changes Back To GitHub

After editing the Designer canvas or resource YAML in Databricks:

1. Open the Git panel for the Git folder.
2. Review changed files.
3. Commit with a clear message.
4. Push to GitHub.

This is the source-control story:

```text
Build in Databricks UI.
Version in GitHub.
Deploy project resources from the Git-backed bundle.
```
