"""Generate repeatable Salesforce bulk-load data for the Lakeflow project.

The generated files are written to `data/salesforce-bulk`.

Loadable immediately:

- `load/Account.csv`
- `load/Product_Usage__c.csv`

Prepared after Account IDs are exported from Salesforce:

- `source/Contact.source.csv`
- `source/Opportunity.source.csv`
- `source/Case.source.csv`

Salesforce creates real Account IDs during the Account bulk import. The helper
script `src/prepare_child_bulk_files.py` uses an exported AccountNumber-to-Id
map to create load-ready Contact, Opportunity, and Case files.
"""

from __future__ import annotations

import csv
import random
from datetime import date, datetime, time, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BULK_DIR = PROJECT_ROOT / "data" / "salesforce-bulk"
LOAD_DIR = BULK_DIR / "load"
SOURCE_DIR = BULK_DIR / "source"

RNG = random.Random(20260903)
ACCOUNT_COUNT = 60
USAGE_DAYS = 30

INDUSTRIES = [
    "Technology",
    "Financial Services",
    "Healthcare",
    "Manufacturing",
    "Retail",
    "Education",
    "Logistics",
    "Energy",
]

NAME_PREFIXES = [
    "Acme",
    "Burlington",
    "CloudNova",
    "DeltaPay",
    "Evergreen",
    "FinEdge",
    "GlobeWorks",
    "HelioSoft",
    "IronBridge",
    "Jupiter",
    "Keystone",
    "Luma",
    "MetroGrid",
    "Northstar",
    "Orchid",
    "Prairie",
    "Quantum",
    "Riverbend",
    "Summit",
    "TerraFleet",
]

NAME_SUFFIXES = [
    "Analytics",
    "Systems",
    "Health",
    "Financial",
    "Retail Group",
    "Capital",
    "Manufacturing",
    "Labs",
    "Logistics",
    "Commerce",
    "Learning",
    "Insurance",
]

FIRST_NAMES = [
    "Aarav",
    "Maya",
    "Sophia",
    "Liam",
    "Noah",
    "Emma",
    "Olivia",
    "Ethan",
    "Isha",
    "Kabir",
    "Anika",
    "Rohan",
    "Mia",
    "Lucas",
    "Amelia",
]

LAST_NAMES = [
    "Sharma",
    "Rao",
    "Mehta",
    "Singh",
    "Patel",
    "Johnson",
    "Williams",
    "Brown",
    "Garcia",
    "Chen",
    "Kapoor",
    "Miller",
]

TITLES = [
    "Chief Technology Officer",
    "Chief Financial Officer",
    "VP Customer Success",
    "Director of Operations",
    "Head of Data",
    "Procurement Manager",
    "Engineering Manager",
    "Platform Owner",
]

CASE_SUBJECTS = [
    "API latency impacting monthly close",
    "Executive dashboard refresh failure",
    "SSO login issue for regional team",
    "Invoice reconciliation mismatch",
    "Data export timeout for analytics team",
    "Unexpected usage spike in integration workload",
    "Renewal reporting discrepancy",
    "Delayed support response for priority incident",
]


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    """Write dictionaries to CSV with a stable column order."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def account_name(index: int) -> str:
    """Create a realistic but deterministic company name."""

    prefix = NAME_PREFIXES[(index - 1) % len(NAME_PREFIXES)]
    suffix = NAME_SUFFIXES[((index - 1) // len(NAME_PREFIXES)) % len(NAME_SUFFIXES)]
    return f"{prefix} {suffix}"


def account_segment(arr: int) -> str:
    """Return a customer segment derived from ARR."""

    if arr >= 800_000:
        return "Enterprise"
    if arr >= 250_000:
        return "Mid-Market"
    return "Commercial"


def iso_datetime(day: date, hour: int) -> str:
    """Return a Salesforce-friendly timestamp string."""

    return datetime.combine(day, time(hour=hour)).strftime("%Y-%m-%dT%H:%M:%S.000+0000")


def build_accounts(today: date) -> list[dict[str, object]]:
    """Build Account rows for direct Salesforce bulk import."""

    accounts: list[dict[str, object]] = []
    for idx in range(1, ACCOUNT_COUNT + 1):
        arr = RNG.choice([75_000, 120_000, 180_000, 320_000, 550_000, 900_000, 1_400_000])
        renewal_days = RNG.choice([18, 32, 48, 72, 95, 130, 180])
        name = account_name(idx)
        accounts.append(
            {
                "Name": name,
                "AccountNumber": f"RR-{idx:04d}",
                "Industry": RNG.choice(INDUSTRIES),
                "Type": "Customer - Direct",
                "Rating": RNG.choice(["Hot", "Warm", "Cold"]),
                "AnnualRevenue": arr * RNG.choice([8, 10, 12, 15]),
                "NumberOfEmployees": RNG.choice([80, 180, 450, 900, 1800, 4200]),
                # State/Country picklists expect code fields during Bulk API
                # inserts in many Salesforce orgs.
                "BillingCountryCode": "US",
                "BillingStateCode": RNG.choice(["CA", "NY", "TX", "WA", "MA", "IL", "GA"]),
                "Website": f"https://{name.lower().replace(' ', '')}.example.com",
                "Customer_Segment__c": account_segment(arr),
                "ARR__c": arr,
                "Renewal_Date__c": today + timedelta(days=renewal_days),
            }
        )
    return accounts


def build_contacts(accounts: list[dict[str, object]]) -> list[dict[str, object]]:
    """Build Contact source rows keyed by AccountNumber."""

    contacts: list[dict[str, object]] = []
    for account in accounts:
        account_number = str(account["AccountNumber"])
        domain = str(account["Website"]).replace("https://", "")
        contact_count = RNG.choice([2, 2, 3])
        for contact_idx in range(1, contact_count + 1):
            first = RNG.choice(FIRST_NAMES)
            last = RNG.choice(LAST_NAMES)
            title = RNG.choice(TITLES)
            is_decision_maker = any(
                token in title.lower()
                for token in ["chief", "vp", "head", "director"]
            )
            contacts.append(
                {
                    "AccountNumber": account_number,
                    "FirstName": first,
                    "LastName": last,
                    "Email": f"{first.lower()}.{last.lower()}{contact_idx}@{domain}",
                    "Title": title,
                    "Department": RNG.choice(["IT", "Operations", "Finance", "Data"]),
                    "Phone": f"+1-555-{account_number[-4:]}-{contact_idx:04d}",
                    "Is_Decision_Maker__c": str(is_decision_maker).lower(),
                }
            )
    return contacts


def build_opportunities(accounts: list[dict[str, object]]) -> list[dict[str, object]]:
    """Build Opportunity source rows keyed by AccountNumber."""

    stages = [
        "Qualification",
        "Needs Analysis",
        "Proposal/Price Quote",
        "Negotiation/Review",
        "Closed Won",
    ]
    opportunities: list[dict[str, object]] = []
    for account in accounts:
        account_number = str(account["AccountNumber"])
        arr = int(account["ARR__c"])
        renewal_date = account["Renewal_Date__c"]
        renewal_amount = int(arr * RNG.choice([0.92, 1.0, 1.08, 1.18]))
        opportunities.append(
            {
                "AccountNumber": account_number,
                "Name": f"{account['Name']} Renewal",
                "StageName": RNG.choice(stages[:-1]),
                "Amount": renewal_amount,
                "CloseDate": renewal_date,
                "Type": RNG.choice(
                    [
                        "Existing Customer - Upgrade",
                        "Existing Customer - Replacement",
                        "Existing Customer - Downgrade",
                    ]
                ),
                "Probability": RNG.choice([35, 45, 55, 65, 75, 85]),
                "Renewal_Opportunity__c": "true",
                "Expansion_Candidate__c": "false",
                "Days_In_Stage__c": RNG.choice([3, 8, 15, 24, 36, 51]),
            }
        )
        if RNG.random() < 0.7:
            opportunities.append(
                {
                    "AccountNumber": account_number,
                    "Name": f"{account['Name']} Expansion Analytics Add-on",
                    "StageName": RNG.choice(stages),
                    "Amount": int(arr * RNG.choice([0.18, 0.28, 0.4])),
                    "CloseDate": renewal_date + timedelta(days=RNG.choice([20, 45, 90])),
                    "Type": "Existing Customer - Upgrade",
                    "Probability": RNG.choice([20, 35, 50, 65, 90]),
                    "Renewal_Opportunity__c": "false",
                    "Expansion_Candidate__c": "true",
                    "Days_In_Stage__c": RNG.choice([2, 7, 14, 28]),
                }
            )
    return opportunities


def build_cases(accounts: list[dict[str, object]], today: date) -> list[dict[str, object]]:
    """Build Case source rows keyed by AccountNumber."""

    cases: list[dict[str, object]] = []
    for account in accounts:
        account_number = str(account["AccountNumber"])
        renewal_days = (account["Renewal_Date__c"] - today).days
        case_count = RNG.choice([1, 2, 3, 4, 5]) if renewal_days <= 95 else RNG.choice([0, 1, 2, 3])
        for _ in range(case_count):
            priority = RNG.choices(
                ["Low", "Medium", "High", "Critical"],
                weights=[20, 35, 30, 15],
                k=1,
            )[0]
            is_closed = RNG.choice([True, False, False])
            reported_day = today - timedelta(days=RNG.randint(2, 75))
            resolved_day = reported_day + timedelta(days=RNG.randint(1, 18)) if is_closed else ""
            cases.append(
                {
                    "AccountNumber": account_number,
                    "Subject": RNG.choice(CASE_SUBJECTS),
                    "Priority": priority,
                    "Status": "Closed" if is_closed else RNG.choice(["New", "Working", "Escalated"]),
                    "Origin": RNG.choice(["Email", "Phone", "Web"]),
                    "Reported_Date__c": iso_datetime(reported_day, RNG.choice([9, 11, 15])),
                    "Resolved_Date__c": iso_datetime(resolved_day, RNG.choice([10, 14, 17])) if resolved_day else "",
                    "SLA_Breached__c": str(priority in ["High", "Critical"] and not is_closed and RNG.random() < 0.55).lower(),
                }
            )
    return cases


def build_product_usage(accounts: list[dict[str, object]], today: date) -> list[dict[str, object]]:
    """Build Product_Usage__c rows for direct Salesforce bulk import."""

    usage_rows: list[dict[str, object]] = []
    for account in accounts:
        account_number = str(account["AccountNumber"])
        renewal_days = (account["Renewal_Date__c"] - today).days
        declining_usage = renewal_days <= 95 and RNG.random() < 0.65
        for day_offset in range(USAGE_DAYS - 1, -1, -1):
            usage_date = today - timedelta(days=day_offset)
            baseline = RNG.randint(45, 260)
            trend_penalty = int((USAGE_DAYS - day_offset) * RNG.uniform(1.1, 3.4)) if declining_usage else 0
            active_users = max(5, baseline - trend_penalty)
            api_calls = active_users * RNG.randint(25, 80)
            usage_rows.append(
                {
                    "Name": f"{account_number}-{usage_date}",
                    "Account_Number__c": account_number,
                    "Usage_Date__c": usage_date,
                    "Active_Users__c": active_users,
                    "Api_Calls__c": api_calls,
                    "Failed_Api_Calls__c": RNG.randint(0, max(3, active_users // 7)),
                    "Key_Feature_Events__c": active_users * RNG.randint(2, 10),
                }
            )
    return usage_rows


def main() -> None:
    """Generate every Salesforce bulk-load input file."""

    today = date(2026, 9, 3)
    accounts = build_accounts(today)
    contacts = build_contacts(accounts)
    opportunities = build_opportunities(accounts)
    cases = build_cases(accounts, today)
    product_usage = build_product_usage(accounts, today)

    write_csv(
        LOAD_DIR / "Account.csv",
        accounts,
        [
            "Name",
            "AccountNumber",
            "Industry",
            "Type",
            "Rating",
            "AnnualRevenue",
            "NumberOfEmployees",
            "BillingCountryCode",
            "BillingStateCode",
            "Website",
            "Customer_Segment__c",
            "ARR__c",
            "Renewal_Date__c",
        ],
    )
    write_csv(
        SOURCE_DIR / "Contact.source.csv",
        contacts,
        [
            "AccountNumber",
            "FirstName",
            "LastName",
            "Email",
            "Title",
            "Department",
            "Phone",
            "Is_Decision_Maker__c",
        ],
    )
    write_csv(
        SOURCE_DIR / "Opportunity.source.csv",
        opportunities,
        [
            "AccountNumber",
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
    )
    write_csv(
        SOURCE_DIR / "Case.source.csv",
        cases,
        [
            "AccountNumber",
            "Subject",
            "Priority",
            "Status",
            "Origin",
            "Reported_Date__c",
            "Resolved_Date__c",
            "SLA_Breached__c",
        ],
    )
    write_csv(
        LOAD_DIR / "Product_Usage__c.csv",
        product_usage,
        [
            "Name",
            "Account_Number__c",
            "Usage_Date__c",
            "Active_Users__c",
            "Api_Calls__c",
            "Failed_Api_Calls__c",
            "Key_Feature_Events__c",
        ],
    )

    print(f"Wrote {len(accounts)} Account rows")
    print(f"Wrote {len(contacts)} Contact source rows")
    print(f"Wrote {len(opportunities)} Opportunity source rows")
    print(f"Wrote {len(cases)} Case source rows")
    print(f"Wrote {len(product_usage)} Product_Usage__c rows")


if __name__ == "__main__":
    main()
