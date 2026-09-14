# Data Model

## Source Objects

Prepared source volume:

```text
60 Account records
131 Contact records
105 Opportunity records
170 Case records
1800 Product_Usage__c records
```

### Account

Salesforce customer entity.

Important fields:

- `Id`
- `AccountNumber`
- `Name`
- `Industry`
- `Type`
- `Rating`
- `AnnualRevenue`
- `NumberOfEmployees`
- `BillingCountry`
- `BillingState`
- `Website`
- `Customer_Segment__c`
- `ARR__c`
- `Renewal_Date__c`

The bulk-load file uses `BillingCountryCode` and `BillingStateCode` so it works
with Salesforce orgs that enforce State and Country/Territory Picklists.

`ARR__c`, `Customer_Segment__c`, and `Renewal_Date__c` are deployed as custom
fields on Account.

### Contact

People associated with an Account.

Important fields:

- `Id`
- `AccountId`
- `FirstName`
- `LastName`
- `Email`
- `Title`
- `Department`
- `Phone`
- `Is_Decision_Maker__c`

Decision-maker status is sourced from `Is_Decision_Maker__c`.

### Opportunity

Renewal and expansion pipeline.

Important fields:

- `Id`
- `AccountId`
- `Name`
- `StageName`
- `Amount`
- `CloseDate`
- `Type`
- `Probability`
- `Renewal_Opportunity__c`
- `Expansion_Candidate__c`
- `Days_In_Stage__c`

Renewal and expansion opportunity behavior is sourced from custom fields.

### Case

Support tickets and customer friction.

Important fields:

- `Id`
- `AccountId`
- `CaseNumber`
- `Subject`
- `Priority`
- `Status`
- `Origin`
- `Reported_Date__c`
- `Resolved_Date__c`
- `SLA_Breached__c`

SLA breach and case aging are sourced from custom fields.

### Product_Usage__c

Salesforce custom object for daily product telemetry.

Important fields:

- `Name`
- `Account_Number__c`
- `Usage_Date__c`
- `Active_Users__c`
- `Api_Calls__c`
- `Failed_Api_Calls__c`
- `Key_Feature_Events__c`

The object is keyed to Account with `Account_Number__c`. This avoids needing a
Salesforce lookup relationship while still modeling a realistic integration
join.

## Visual Transformation Model

The model is implemented in Lakeflow Designer as a visual data prep.

### Source-Aligned Preparation

Designer operators:

```text
Source
Prepare
Filter
```

Tables:

- `silver_accounts`
- `silver_contacts`
- `silver_opportunities`
- `silver_cases`
- `silver_product_usage_daily`

Purpose:

- Normalize source names.
- Cast obvious field types.
- Filter invalid records.
- Preserve the operational meaning of Salesforce data.

### Gold Aggregation

Designer operators:

```text
Join
Aggregate
Prepare
```

Tables:

- `gold_open_support_exposure`
- `gold_pipeline_health`
- `gold_usage_trend`
- `gold_account_renewal_risk`

Purpose:

- Summarize support exposure.
- Summarize renewal and expansion pipeline health.
- Calculate usage trends.
- Score account renewal risk.

### Serving And AI Context

Designer operators:

```text
Filter
Sort
Prepare
AI Function
Output
```

Tables:

- `gold_csm_priority_queue`
- `gold_account_360_summary`
- `ai_account_briefing_documents`

Purpose:

- Score renewal risk.
- Explain risk drivers.
- Rank Customer Success actions.
- Prepare AI-serving context.

## Risk Score

The risk score is deterministic and easy to explain:

```text
+30 renewal due within 90 days
+25 open high-priority support case exists
+15 open SLA breach exists
+15 stalled renewal opportunity exists
+15 product usage dropped by at least 10 percent
+10 no decision-maker contact exists
+10 high-value account by revenue proxy
-10 active expansion opportunity exists
```

Risk bands:

```text
80-100 Critical
60-79  High
35-59  Medium
0-34   Low
```

## Salesforce Custom Object Design

The project includes one custom object:

```text
Product_Usage__c
```

Standard Salesforce objects carry customer, relationship, sales, and support
context. The custom object carries usage context. In production, fields such as
ARR, renewal date, customer segment, and SLA breach would usually be modeled as
real Salesforce fields or imported from their owning operational systems.
