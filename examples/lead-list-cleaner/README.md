# Example — Recipe 01, lead-list cleaner

**Input:** `input.csv` — five raw rows, including one exact duplicate, one
row with an invalid email and an undialable phone, and one row missing a
phone.

**Run:**

```bash
ai-agents run lead-list-cleaner --demo
```

(or in code: `clean_leads(open("input.csv").read())`)

**Expected output:** `expected-output.csv` — four kept rows, graded
A/A/C/B with per-row flags, plus statistics:
`input_rows=5, kept_rows=4, duplicates_removed=1, grade_a=2, grade_b=1,
grade_c=1, invalid_emails=1, invalid_phones=1`.
