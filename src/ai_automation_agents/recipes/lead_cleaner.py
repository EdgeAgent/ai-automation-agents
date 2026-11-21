"""Recipe 01 — Lead-list cleaner.

CSV in → cleaned CSV out. Pure standard library: no provider, no network, no
cost. Rows are deduplicated (by normalized email, falling back to phone),
contact details are validated, problems are flagged per row, and every kept
row is graded:

- **A** — name + valid email + valid phone: ready to work.
- **B** — name + one valid contact channel: usable with a gap.
- **C** — missing name, or no valid contact channel: incomplete.
"""

from __future__ import annotations

import csv
import io
import re
from typing import Literal

from pydantic import BaseModel, Field

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
FIELDS = ["name", "email", "phone", "company", "source"]
Grade = Literal["A", "B", "C"]


class CleanedLead(BaseModel):
    """One deduplicated lead row with validation flags and a grade."""

    name: str = ""
    email: str = ""
    phone: str = ""
    company: str = ""
    source: str = ""
    flags: list[str] = Field(default_factory=list)
    grade: Grade = "C"


class CleanResult(BaseModel):
    """The outcome of a cleaning run: rows, rendered CSV, and statistics."""

    rows: list[CleanedLead]
    cleaned_csv: str
    stats: dict[str, int]


def _normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits


def valid_email(email: str) -> bool:
    """Return True for a syntactically plausible email address."""
    return bool(EMAIL_RE.match(email.strip()))


def valid_phone(phone: str) -> bool:
    """Return True for a dialable North-American-style number (10 digits)."""
    return len(_normalize_phone(phone)) == 10


def _grade(name: str, email_ok: bool, phone_ok: bool) -> Grade:
    if not name:
        return "C"
    if email_ok and phone_ok:
        return "A"
    if email_ok or phone_ok:
        return "B"
    return "C"


def clean_leads(csv_text: str) -> CleanResult:
    """Clean ``csv_text`` and return graded rows plus the cleaned CSV.

    Expected columns: name, email, phone, company, source (any may be
    missing). Duplicates are dropped after their first occurrence and counted
    in the stats; the dropped rows' flags note ``duplicate`` in the stats
    only — kept rows are never marked for another row's duplication.
    """
    reader = csv.DictReader(io.StringIO(csv_text))
    seen: set[str] = set()
    rows: list[CleanedLead] = []
    duplicates = 0
    total_in = 0

    for raw_row in reader:
        total_in += 1
        row = {field: (raw_row.get(field) or "").strip() for field in FIELDS}
        email_key = row["email"].lower()
        phone_key = _normalize_phone(row["phone"])
        dedupe_key = f"email:{email_key}" if email_key else f"phone:{phone_key}"
        if dedupe_key in seen and (email_key or phone_key):
            duplicates += 1
            continue
        seen.add(dedupe_key)

        flags: list[str] = []
        email_ok = valid_email(row["email"]) if row["email"] else False
        phone_ok = valid_phone(row["phone"]) if row["phone"] else False
        if not row["email"]:
            flags.append("missing_email")
        elif not email_ok:
            flags.append("invalid_email")
        if not row["phone"]:
            flags.append("missing_phone")
        elif not phone_ok:
            flags.append("invalid_phone")
        if not row["name"]:
            flags.append("missing_name")

        rows.append(
            CleanedLead(
                **row,
                flags=flags,
                grade=_grade(row["name"], email_ok, phone_ok),
            )
        )

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[*FIELDS, "grade", "flags"])
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                **row.model_dump(exclude={"flags", "grade"}),
                "grade": row.grade,
                "flags": ";".join(row.flags),
            }
        )

    stats = {
        "input_rows": total_in,
        "kept_rows": len(rows),
        "duplicates_removed": duplicates,
        "grade_a": sum(1 for row in rows if row.grade == "A"),
        "grade_b": sum(1 for row in rows if row.grade == "B"),
        "grade_c": sum(1 for row in rows if row.grade == "C"),
        "invalid_emails": sum(1 for row in rows if "invalid_email" in row.flags),
        "invalid_phones": sum(1 for row in rows if "invalid_phone" in row.flags),
    }
    return CleanResult(rows=rows, cleaned_csv=output.getvalue(), stats=stats)
