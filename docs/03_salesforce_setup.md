# Salesforce Setup Guide

This guide prepares a Salesforce Developer Edition org as the only source
system for the project. Every source object used by Databricks is loaded into
Salesforce first and then ingested into Databricks through Lakeflow Connect.

## 1. Create A Salesforce Developer Edition Org

1. Open https://developer.salesforce.com/signup.
2. Create a free Developer Edition account.
3. Verify your email.
4. Log in to Salesforce Lightning.
5. Open Setup.
6. In Quick Find, search for `Company Information`.
7. Confirm the org is Developer Edition.

Salesforce Developer Edition includes API access by default. Lakeflow Connect
needs API access to read Salesforce objects.

## 2. Confirm API Access

1. In Setup, search for `Profiles`.
2. Open the profile for your user, usually `System Administrator`.
3. Search within the profile for `API Enabled`.
4. Confirm it is enabled.

If Databricks reports an API access error later, this is the first Salesforce
setting to check.

## 3. Install Salesforce CLI

Install Salesforce CLI from:

https://developer.salesforce.com/tools/salesforcecli

Confirm the installation:

```bash
sf --version
```

## 4. Authenticate The Developer Org

From this project folder:

```bash
cd <your-local-path>/salesforce-renewal-risk-dbx-pipeline

sf org login web --alias lakeflow-project --set-default
```

Your browser opens. Log in to the Developer Edition org.

Confirm the org:

```bash
sf org display --target-org lakeflow-project
```

## 5. Understand The Data Volume

The generated dataset contains:

```text
60 Account records
131 Contact records
105 Opportunity records
170 Case records
1800 Product_Usage__c records
2266 total Salesforce records
```

Salesforce Developer Edition has a small data storage allocation. Most standard
and custom object records are estimated at approximately 2 KB each, so this
dataset is intentionally sized for a fresh Developer Edition org while still
being large enough to make Lakeflow ingestion, quality rules, aggregation, and
risk scoring meaningful.

## 6. Deploy Salesforce Metadata

The project adds production-style fields to standard Salesforce objects and one
custom object for product telemetry.

Metadata included:

```text
Account:
  ARR__c
  Customer_Segment__c
  Renewal_Date__c

Contact:
  Is_Decision_Maker__c

Opportunity:
  Renewal_Opportunity__c
  Expansion_Candidate__c
  Days_In_Stage__c

Case:
  Reported_Date__c
  Resolved_Date__c
  SLA_Breached__c

Custom object:
  Product_Usage__c

Permission set:
  Renewal_Risk_Data_Load
```

The permission set grants access to the non-required custom fields on standard
objects and object-level access to `Product_Usage__c`. Required custom fields on
`Product_Usage__c` do not need separate field permission entries.

Deploy the metadata:

```bash
cd <your-local-path>/salesforce-renewal-risk-dbx-pipeline

sf project deploy start \
  --target-org lakeflow-project \
  --source-dir salesforce/force-app

## Multiline Comment 
# PowerShell → `
# Git Bash/Linux → \

sf project deploy start `
  --target-org lakeflow-project `
  --source-dir salesforce/force-app
```

Assign the permission set to the same user that will run the bulk import and
Databricks Salesforce connection:

```bash
sf org assign permset \
  --target-org lakeflow-project \
  --name Renewal_Risk_Data_Load
```

Validate that the Account custom field metadata exists:

```bash
sf data query \
  --target-org lakeflow-project \
  --use-tooling-api \
  --query "SELECT DeveloperName, TableEnumOrId FROM CustomField WHERE TableEnumOrId = 'Account' AND DeveloperName IN ('ARR', 'Customer_Segment', 'Renewal_Date')"
```

Validate that the Account fields are visible to the current user:

```bash
sf data query \
  --target-org lakeflow-project \
  --query "SELECT QualifiedApiName FROM FieldDefinition WHERE EntityDefinition.QualifiedApiName = 'Account' AND QualifiedApiName IN ('ARR__c', 'Customer_Segment__c', 'Renewal_Date__c')"
```

Expected field names:

```text
ARR__c
Customer_Segment__c
Renewal_Date__c
```

Validate the custom object:

```bash
sf data query \
  --target-org lakeflow-project \
  --query "SELECT QualifiedApiName FROM EntityDefinition WHERE QualifiedApiName = 'Product_Usage__c'"
```

If Account bulk import fails with `Field name not found`, stop and redeploy the
metadata, assign `Renewal_Risk_Data_Load`, and validate field visibility before
retrying the import. The CSV columns depend on the custom fields being present
and accessible in Salesforce.

## 7. Generate Bulk Load Files

The repository already contains generated data, but you can regenerate it:

```bash
python3 src/generate_project_data.py
```

Generated files:

```text
data/salesforce-bulk/load/Account.csv
data/salesforce-bulk/load/Product_Usage__c.csv
data/salesforce-bulk/source/Contact.source.csv
data/salesforce-bulk/source/Opportunity.source.csv
data/salesforce-bulk/source/Case.source.csv
```

The child source files use `AccountNumber` because Salesforce Account IDs do
not exist until Account records are inserted.

`Account.csv` uses `BillingCountryCode` and `BillingStateCode` instead of
`BillingCountry` and `BillingState`. This works with Salesforce orgs where
State and Country/Territory Picklists are enabled.

## 8. Bulk Load Account

Load Account first:

```bash
sf data import bulk \
  --target-org lakeflow-project \
  --sobject Account \
  --file data/salesforce-bulk/load/Account.csv \
  --line-ending CRLF \
  --wait 10
```

The prepared CSV files use `CRLF` line endings, so every Salesforce bulk import
command passes `--line-ending CRLF` explicitly. Without this flag, Salesforce CLI
defaults to `LF` on macOS and Linux, which can cause a Bulk API line-ending
error.

If Salesforce rejects all Account rows with a Billing State/Province error,
confirm that `Account.csv` has these two columns:

```text
BillingCountryCode
BillingStateCode
```

Validate:

```bash
sf data query \
  --target-org lakeflow-project \
  --query "SELECT count() FROM Account WHERE AccountNumber LIKE 'RR-%'"
```

## 9. Export Salesforce Account ID Map

After Account bulk import, export the generated Salesforce IDs:

```bash
sf data query \
  --target-org lakeflow-project \
  --result-format csv \
  --query "SELECT Id, AccountNumber FROM Account WHERE AccountNumber LIKE 'RR-%'" \
  > data/salesforce-bulk/account_id_map.csv
```

This file is required because Contact, Opportunity, and Case need `AccountId`.

## 10. Prepare Child Bulk Files

Run:

```bash
python3 src/prepare_child_bulk_files.py
```

This creates:

```text
data/salesforce-bulk/load/Contact.csv
data/salesforce-bulk/load/Opportunity.csv
data/salesforce-bulk/load/Case.csv
```

Each generated child file contains the real Salesforce `AccountId`.

## 11. Bulk Load Contact

```bash
sf data import bulk \
  --target-org lakeflow-project \
  --sobject Contact \
  --file data/salesforce-bulk/load/Contact.csv \
  --line-ending CRLF \
  --wait 10
```

## 12. Bulk Load Opportunity

```bash
sf data import bulk \
  --target-org lakeflow-project \
  --sobject Opportunity \
  --file data/salesforce-bulk/load/Opportunity.csv \
  --line-ending CRLF \
  --wait 10
```

## 13. Bulk Load Case

```bash
sf data import bulk \
  --target-org lakeflow-project \
  --sobject Case \
  --file data/salesforce-bulk/load/Case.csv \
  --line-ending CRLF \
  --wait 10
```

## 14. Bulk Load Product Usage

```bash
sf data import bulk \
  --target-org lakeflow-project \
  --sobject Product_Usage__c \
  --file data/salesforce-bulk/load/Product_Usage__c.csv \
  --line-ending CRLF \
  --wait 10
```

## 15. Validate Salesforce Data

Run:

```bash
sf data query --target-org lakeflow-project --query "SELECT count() FROM Account WHERE AccountNumber LIKE 'RR-%'"
sf data query --target-org lakeflow-project --query "SELECT count() FROM Contact WHERE Account.AccountNumber LIKE 'RR-%'"
sf data query --target-org lakeflow-project --query "SELECT count() FROM Opportunity WHERE Account.AccountNumber LIKE 'RR-%'"
sf data query --target-org lakeflow-project --query "SELECT count() FROM Case WHERE Account.AccountNumber LIKE 'RR-%'"
sf data query --target-org lakeflow-project --query "SELECT count() FROM Product_Usage__c WHERE Account_Number__c LIKE 'RR-%'"
```

Spot-check source records:

```bash
sf data query \
  --target-org lakeflow-project \
  --query "SELECT Id, Name, AccountNumber, ARR__c, Customer_Segment__c, Renewal_Date__c FROM Account WHERE AccountNumber LIKE 'RR-%' LIMIT 5"
```

```bash
sf data query \
  --target-org lakeflow-project \
  --query "SELECT Name, Account_Number__c, Usage_Date__c, Active_Users__c FROM Product_Usage__c LIMIT 5"
```

## 16. Salesforce UI Verification

In Salesforce, inspect:

1. Accounts.
2. Contacts.
3. Opportunities.
4. Cases.
5. Product Usage object records.

The expected operational shape is:

```text
Account, Contact, Opportunity, Case = customer relationship and renewal context
Product_Usage__c = daily product telemetry keyed by AccountNumber
```
