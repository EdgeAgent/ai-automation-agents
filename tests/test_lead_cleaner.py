from ai_automation_agents.demo_data import SAMPLE_CSV
from ai_automation_agents.recipes.lead_cleaner import clean_leads, valid_email, valid_phone


def test_sample_csv_stats() -> None:
    result = clean_leads(SAMPLE_CSV)
    assert result.stats == {
        "input_rows": 5,
        "kept_rows": 4,
        "duplicates_removed": 1,
        "grade_a": 2,
        "grade_b": 1,
        "grade_c": 1,
        "invalid_emails": 1,
        "invalid_phones": 1,
    }


def test_grades_and_flags_per_row() -> None:
    result = clean_leads(SAMPLE_CSV)
    by_name = {row.name: row for row in result.rows}
    assert by_name["Dana White"].grade == "A"
    assert by_name["Marcus Lee"].grade == "A"
    assert by_name["Sam Ortiz"].grade == "B"
    assert "missing_phone" in by_name["Sam Ortiz"].flags
    assert by_name["Pat Nope"].grade == "C"
    assert "invalid_email" in by_name["Pat Nope"].flags
    assert "invalid_phone" in by_name["Pat Nope"].flags


def test_cleaned_csv_is_valid_and_deduplicated() -> None:
    result = clean_leads(SAMPLE_CSV)
    assert result.cleaned_csv.count("dana@northwind.example") == 1
    assert result.cleaned_csv.splitlines()[0] == "name,email,phone,company,source,grade,flags"


def test_dedupe_falls_back_to_phone_when_email_missing() -> None:
    csv_text = (
        "name,email,phone,company,source\n"
        "Jo One,,3135550100,One Co,form\n"
        "Jo Two,,(313) 555-0100,Two Co,form\n"
    )
    result = clean_leads(csv_text)
    assert result.stats["kept_rows"] == 1
    assert result.stats["duplicates_removed"] == 1


def test_missing_name_forces_grade_c() -> None:
    csv_text = "name,email,phone,company,source\n,valid@example.com,3135550100,Co,form\n"
    result = clean_leads(csv_text)
    assert result.rows[0].grade == "C"
    assert "missing_name" in result.rows[0].flags


def test_validators() -> None:
    assert valid_email("dana@northwind.example")
    assert not valid_email("not-an-email")
    assert not valid_email("")
    assert valid_phone("(313) 555-0142")
    assert valid_phone("+1 313 555 0142")
    assert not valid_phone("123")
