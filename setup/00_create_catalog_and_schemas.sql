-- This script is executed by the target-specific environment bootstrap job.
--
-- It creates the Unity Catalog objects used by the Salesforce Lakeflow Connect
-- ingestion path and the downstream Lakeflow Designer visual data prep.

CREATE CATALOG IF NOT EXISTS renewal_risk_lakehouse
COMMENT 'Project catalog for the Salesforce Renewal Risk Lakeflow project.';

CREATE SCHEMA IF NOT EXISTS renewal_risk_lakehouse.raw_sfdc_dev
COMMENT 'Development raw Salesforce objects ingested by Lakeflow Connect.';

CREATE SCHEMA IF NOT EXISTS renewal_risk_lakehouse.raw_sfdc_prod
COMMENT 'Production raw Salesforce objects ingested by Lakeflow Connect.';

CREATE SCHEMA IF NOT EXISTS renewal_risk_lakehouse.renewal_risk
COMMENT 'Production-style Lakeflow Designer output schema.';

CREATE SCHEMA IF NOT EXISTS renewal_risk_lakehouse.renewal_risk_dev
COMMENT 'Developer-mode Lakeflow Designer output schema for UI iteration.';

CREATE SCHEMA IF NOT EXISTS renewal_risk_lakehouse.pipeline_events
COMMENT 'Lakeflow event logs and quality metrics.';

CREATE SCHEMA IF NOT EXISTS renewal_risk_lakehouse.ai
COMMENT 'AI Search and agent serving assets.';
