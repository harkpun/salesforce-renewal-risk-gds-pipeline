"""Prepare child-object Salesforce bulk files after Account import.

Salesforce generates Account IDs during bulk import. Contact, Opportunity, and
Case require the generated `AccountId`, so this script reads an exported
AccountNumber-to-Id map and produces load-ready child CSV files.

Expected mapping file columns:

- `Id`
- `AccountNumber`

Example:

```bash
sf data query \
  --target-org lakeflow-project \
  --result-format csv \
  --query "SELECT Id, AccountNumber FROM Account WHERE AccountNumber LIKE 'RR-%'" \
  > data/salesforce-bulk/account_id_map.csv

python3 src/prepare_child_bulk_files.py
```
"""

from __future__ import annotations

import csv
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BULK_DIR = PROJECT_ROOT / "data" / "salesforce-bulk"
SOURCE_DIR = BULK_DIR / "source"
LOAD_DIR = BULK_DIR / "load"
ACCOUNT_MAP_FILE = BULK_DIR / "account_id_map.csv"


def read_account_id_map(path: Path) -> dict[str, str]:
    """Read Salesforce Account IDs keyed by AccountNumber."""

    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required_columns = {"Id", "AccountNumber"}
        missing_columns = required_columns - set(reader.fieldnames or [])
        if missing_columns:
            raise ValueError(f"Missing columns in {path}: {sorted(missing_columns)}")

        account_ids: dict[str, str] = {}
        for row in reader:
            account_number = row["AccountNumber"].strip()
            account_id = row["Id"].strip()
            if account_number and account_id:
                account_ids[account_number] = account_id
        return account_ids


def prepare_child_file(
    source_file: Path,
    output_file: Path,
    output_fields: list[str],
    account_ids: dict[str, str],
) -> int:
    """Replace AccountNumber with Salesforce AccountId and write a load file."""

    output_file.parent.mkdir(parents=True, exist_ok=True)
    row_count = 0

    with source_file.open(newline="", encoding="utf-8") as source_handle:
        reader = csv.DictReader(source_handle)
        with output_file.open("w", newline="", encoding="utf-8") as output_handle:
            writer = csv.DictWriter(output_handle, fieldnames=output_fields)
            writer.writeheader()

            for row in reader:
                account_number = row.pop("AccountNumber").strip()
                if account_number not in account_ids:
                    raise ValueError(f"No Salesforce AccountId found for {account_number}")

                row["AccountId"] = account_ids[account_number]
                writer.writerow({field: row.get(field, "") for field in output_fields})
                row_count += 1

    return row_count


def main() -> None:
    """Create load-ready Contact, Opportunity, and Case files."""

    account_ids = read_account_id_map(ACCOUNT_MAP_FILE)

    contact_count = prepare_child_file(
        SOURCE_DIR / "Contact.source.csv",
        LOAD_DIR / "Contact.csv",
        [
            "AccountId",
            "FirstName",
            "LastName",
            "Email",
            "Title",
            "Department",
            "Phone",
            "Is_Decision_Maker__c",
        ],
        account_ids,
    )
    opportunity_count = prepare_child_file(
        SOURCE_DIR / "Opportunity.source.csv",
        LOAD_DIR / "Opportunity.csv",
        [
            "AccountId",
            "Name",
            "StageName",
            "Amount",
            "CloseDate",
            "Type",
            "Probability",
            "Renewal_Opportunity__c",
            "Expansion_Candidate__c",
            "Days_In_Stage__c",
        ],
        account_ids,
    )
    case_count = prepare_child_file(
        SOURCE_DIR / "Case.source.csv",
        LOAD_DIR / "Case.csv",
        [
            "AccountId",
            "Subject",
            "Priority",
            "Status",
            "Origin",
            "Reported_Date__c",
            "Resolved_Date__c",
            "SLA_Breached__c",
        ],
        account_ids,
    )

    print(f"Wrote {contact_count} Contact rows to {LOAD_DIR / 'Contact.csv'}")
    print(f"Wrote {opportunity_count} Opportunity rows to {LOAD_DIR / 'Opportunity.csv'}")
    print(f"Wrote {case_count} Case rows to {LOAD_DIR / 'Case.csv'}")


if __name__ == "__main__":
    main()
