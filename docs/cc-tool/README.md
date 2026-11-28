# Credit Card Split Calculator (Borrowers A & T)

Single-page tool that tracks a **shared credit card** for two people.

**UI skin:** **Indigo Split** (dual A | T columns + center interest bridge). Other directions live under `mockups/`.

- Splits each month’s **interest** by each borrower’s share of the balance  
- Uses **Interest charged** and **Minimum payment** from your statement snapshot  
- Lets each borrower pay their **min share** or **more**  
- Rolls balances forward month to month  
- Shows a **running total** of interest acquired (all, A, and T) and of what each payer has paid  
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

Jul–Nov 2026 are already in the ledger. Setup stays locked while that history is present. **Reset everything** reloads these five months and the default transfers.

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
**Reset everything** reloads the Jul–Nov 2026 ledger and the default transfers.

The December form is blank. Enter that statement’s interest and minimum when it arrives, then apply it the same way.

The summary cards and the ledger footer keep a running total of interest acquired (all, A, and T) and of what each payer has paid.

## Seeded ledger (Jul–Nov 2026)

Payments are the amounts posted on that statement. Interest is split by opening-balance share. Each closing total matches the statement new balance.

| Month | Interest | Min due | Pay A | Pay T | Close total |
|--|--:|--:|--:|--:|--:|
| Jul 2026 (stmt 07/09) | $83.66 | $389.00 | $0.00 | $0.00 | $30,681.25 |
| Aug 2026 (stmt 08/09) | $104.12 | $406.00 | $0.00 | $400.00 | $30,385.37 |
| Sep 2026 (stmt 09/09) | $102.77 | $399.00 | $500.00 | $200.00 | $29,788.14 |
| Oct 2026 (stmt 10/09) | $96.46 | $382.00 | $1,000.00 | $200.00 | $28,684.60 |
| Nov 2026 (stmt 11/09) | $94.14 | $356.00 | $2,000.00 | $450.00 | $26,328.74 |

**Who paid**

- **August:** the only payment is $400. That is **T**. A paid $0.
- **September:** $700 posted. T paid $200. A paid the other **$500**.
- **October:** $1,200 posted. A paid $1,000. T paid $200.
- **November:** $2,450 posted. A paid $2,000. T paid $450.
- **July:** a $402.41 payment cleared the $402.41 balance that existed before the transfers. It is not part of this split. No payment was made against the transfer balances in that cycle.

After November the balances are **A $16,190.64** and **T $10,138.10**. Paid so far: A $3,500, T $1,250. Interest acquired so far: $481.15 (A $306.17, T $174.98).

July interest split (opening $19,384.47 / $11,213.12): A $53.00, T $30.66. Statement interest is used as-is. The first cycle used average daily balance, so it will not match a simple 3.99%÷12 on the full transfer total. August and September interest include a few cents of purchase interest ($0.32 and $0.24); that stays in the statement total and is split the same way.

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
