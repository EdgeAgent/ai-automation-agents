"""Recipe 02 — Quote drafter.

Job details in → an itemized quote out. The math is deterministic and done
in ``Decimal``: line items, optional labor, markup, tax, totals, and a
deposit/balance split. No provider is involved, so a quote can be recomputed
and audited cent-for-cent — which is exactly what money documents need.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel, Field

CENTS = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(CENTS, rounding=ROUND_HALF_UP)


class QuoteItem(BaseModel):
    """One itemized line: a description, a quantity, and a unit price."""

    description: str
    quantity: Decimal = Decimal(1)
    unit_price: Decimal

    @property
    def line_total(self) -> Decimal:
        return _money(self.quantity * self.unit_price)


class QuoteRequest(BaseModel):
    """Everything needed to draft a quote."""

    client: str
    items: list[QuoteItem] = Field(min_length=1)
    labor_hours: Decimal = Decimal(0)
    labor_rate: Decimal = Decimal(0)
    markup_percent: Decimal = Decimal(0)
    tax_rate: Decimal = Decimal(0)
    deposit_percent: Decimal = Decimal(30)


class Quote(BaseModel):
    """A computed quote. ``deposit_due + balance_due == total`` always."""

    client: str
    items: list[QuoteItem]
    items_subtotal: Decimal
    labor_total: Decimal
    subtotal: Decimal
    markup_amount: Decimal
    tax_amount: Decimal
    total: Decimal
    deposit_due: Decimal
    balance_due: Decimal
    tax_rate: Decimal
    deposit_percent: Decimal

    def render(self) -> str:
        """Render the quote as plain text suitable for review or sending."""
        lines = [f"QUOTE — prepared for {self.client}", ""]
        for item in self.items:
            lines.append(
                f"- {item.description}: {item.quantity} x ${item.unit_price} = ${item.line_total}"
            )
        if self.labor_total:
            lines.append(f"- Labor: ${self.labor_total}")
        lines.append("")
        lines.append(f"Subtotal: ${self.subtotal}")
        if self.markup_amount:
            lines.append(f"Markup: ${self.markup_amount}")
        lines.append(f"Tax ({self.tax_rate}%): ${self.tax_amount}")
        lines.append(f"Total: ${self.total}")
        lines.append(f"Deposit due ({self.deposit_percent}%): ${self.deposit_due}")
        lines.append(f"Balance on completion: ${self.balance_due}")
        return "\n".join(lines)


def build_quote(request: QuoteRequest) -> Quote:
    """Compute a quote from ``request``. Pure function; no side effects."""
    items_subtotal = _money(sum((item.line_total for item in request.items), Decimal(0)))
    labor_total = _money(request.labor_hours * request.labor_rate)
    subtotal = _money(items_subtotal + labor_total)
    markup_amount = _money(subtotal * request.markup_percent / Decimal(100))
    taxable = subtotal + markup_amount
    tax_amount = _money(taxable * request.tax_rate / Decimal(100))
    total = _money(taxable + tax_amount)
    deposit_due = _money(total * request.deposit_percent / Decimal(100))
    balance_due = _money(total - deposit_due)
    return Quote(
        client=request.client,
        items=request.items,
        items_subtotal=items_subtotal,
        labor_total=labor_total,
        subtotal=subtotal,
        markup_amount=markup_amount,
        tax_amount=tax_amount,
        total=total,
        deposit_due=deposit_due,
        balance_due=balance_due,
        tax_rate=request.tax_rate,
        deposit_percent=request.deposit_percent,
    )
