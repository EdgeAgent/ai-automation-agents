from decimal import Decimal

from ai_automation_agents.recipes.quote_drafter import QuoteItem, QuoteRequest, build_quote


def _demo_request() -> QuoteRequest:
    return QuoteRequest(
        client="Riverside Dental",
        items=[
            QuoteItem(description="AI receptionist setup", unit_price=Decimal(400)),
            QuoteItem(description="Lead pack — 25 leads", unit_price=Decimal(450)),
        ],
        labor_hours=Decimal(3),
        labor_rate=Decimal(85),
        tax_rate=Decimal(13),
        deposit_percent=Decimal(30),
    )


def test_demo_quote_totals() -> None:
    quote = build_quote(_demo_request())
    assert quote.items_subtotal == Decimal("850.00")
    assert quote.labor_total == Decimal("255.00")
    assert quote.subtotal == Decimal("1105.00")
    assert quote.tax_amount == Decimal("143.65")
    assert quote.total == Decimal("1248.65")


def test_deposit_and_balance_always_sum_to_total() -> None:
    quote = build_quote(_demo_request())
    assert quote.deposit_due == Decimal("374.60")
    assert quote.balance_due == Decimal("874.05")
    assert quote.deposit_due + quote.balance_due == quote.total


def test_markup_applies_before_tax() -> None:
    quote = build_quote(
        QuoteRequest(
            client="Markup Co",
            items=[QuoteItem(description="Widget", unit_price=Decimal(100))],
            markup_percent=Decimal(10),
            tax_rate=Decimal(10),
            deposit_percent=Decimal(50),
        )
    )
    assert quote.markup_amount == Decimal("10.00")
    assert quote.tax_amount == Decimal("11.00")
    assert quote.total == Decimal("121.00")


def test_line_totals_round_half_up() -> None:
    quote = build_quote(
        QuoteRequest(
            client="Rounding Co",
            items=[
                QuoteItem(description="Thirds", quantity=Decimal(3), unit_price=Decimal("0.335"))
            ],
        )
    )
    assert quote.items[0].line_total == Decimal("1.01")
    assert quote.total == Decimal("1.01")


def test_render_contains_client_lines_and_total() -> None:
    rendered = build_quote(_demo_request()).render()
    assert "Riverside Dental" in rendered
    assert "AI receptionist setup" in rendered
    assert "Total: $1248.65" in rendered
    assert "Deposit due (30%): $374.60" in rendered
