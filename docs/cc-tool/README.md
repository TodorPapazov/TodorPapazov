# Credit Card Split Calculator (Borrowers A & T)

Single-page tool that tracks a **shared credit card** for two people.

**UI skin:** **Indigo Split** (dual A | T columns + center interest bridge). Other directions live under `mockups/`.

- Splits each month’s **interest** by each borrower’s share of the balance  
- Uses **Interest charged** and **Minimum payment** from your statement snapshot  
- Lets each borrower pay their **min share** or **more**  
- Rolls balances forward month to month  
- Supports **pay remaining in full** (e.g. at promo end 07/09/2027)

No install. Data stays in your browser (`localStorage`).

## Open the tool

**Public (GitHub Pages):**  
https://todorpapazov.github.io/cc-tool/

Local:

1. Open this folder
2. Double-click **`index.html`**

```powershell
Invoke-Item ".\docs\cc-tool\index.html"
```

## Seed balances (from `01/` statement)

| Transfer        | Amount      | Borrower |
|-----------------|-------------|----------|
| Wells Fargo     | $3,833.12   | **T**    |
| Discover        | $7,380.00   | **T**    |
| Chase Card S    | $19,384.47  | **A**    |

- **A** starts at **$19,384.47**  
- **T** starts at **$11,213.12**  
- Promo APR **3.99%** through **07/09/2027**

You can reassign transfers or edit amounts in **Setup** before any months are applied.

## Monthly workflow

1. When you get a new statement (photos like `01/Balance.jpg` and `01/Payment.jpg`):
   - Enter **Interest charged**
   - Enter **Total minimum payment due**
   - Optionally set month label and due date  
2. Review the split:
   - Interest A / T (proportional to **opening** balances)
   - Min share A / T (proportional to **after-interest** balances)
3. Enter each person’s payment, or click:
   - **Pay min** — their share of the card minimum  
   - **Pay remaining** — pay off their balance after interest  
   - **Both pay remaining** — pay the card off  
4. Click **Apply month → ledger**  
5. Next cycle: paste the next statement’s interest + min and repeat  

**Undo last month** restores that month to the form.  
**Export CSV** downloads the ledger.  
**Reset everything** clears history and restores default transfers.

## Month 1 example (July 2026 statement)

| | A | T | Total |
|--|--:|--:|--:|
| Opening | $19,384.47 | $11,213.12 | $30,597.59 |
| Interest ($83.66) | ~$52.99 | ~$30.67 | $83.66 |
| After interest | ~$19,437.46 | ~$11,243.79 | **$30,681.25** |
| Min share of $389 | ~$246.50 | ~$142.50 | $389.00 |

Statement interest is used as-is (first cycle used average daily balance, so it will not match a simple 3.99%÷12 on the full transfer total).

## How interest is split

```
share_A = open_A / (open_A + open_T)
interest_A = total_interest × share_A
interest_T = total_interest − interest_A   (exact cents)
```

Minimum payment uses the same idea on **post-interest** balances.

## Files

```
CC-tool/
  index.html      ← the calculator
  README.md
  mockups/        ← 5 modern HUD skins (gallery + pick/mix)
    index.html
    01-cyan-command.html … 05-indigo-split.html
  01/
    Balance.jpg   ← source statement (transactions / APR)
    Payment.jpg   ← source statement (min due / new balance)
```

### HUD mockups (visual only)

Open `mockups/index.html` to browse five medium-density HUD directions (Cyan Command, Amber Ops, Violet Glass, Emerald Ledger, Indigo Split). Pick one or mix layout + palette before applying a skin to the live calculator.

## Notes

- Overpayment on one borrower does not reduce the other person’s balance.  
- After promo ends, use **Both pay remaining** (or each **Pay remaining**) to clear what’s left.  
- Estimated interest at 3.99%/12 is a helper only; the statement amount always wins.
