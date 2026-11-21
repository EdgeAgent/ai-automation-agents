# Example — Recipe 02, quote drafter

**Input:** `input.json` — a `QuoteRequest`: two items, 3 hours of labor at
$85, 13% tax, 30% deposit.

**Run:**

```bash
ai-agents run quote-drafter --demo
```

(or in code: `build_quote(QuoteRequest(**json.load(open("input.json")))).render()`)

**Expected output:** `expected-quote.txt`. Check the invariants the tests
check: items $850 + labor $255 = subtotal $1,105; tax $143.65; total
$1,248.65; deposit $374.60 + balance $874.05 = the total, exactly.
