# CC Split Calculator — HUD mock gallery

Five **modern medium-density HUD** skins for the shared credit-card calculator (borrowers **A** & **T**).
Open in a browser, compare, then **pick one or mix** (e.g. layout of Indigo Split + palette of Emerald Ledger).

## Open

- Gallery: double-click [`index.html`](index.html)
- Or: `Invoke-Item ".\CC-tool\mockups\index.html"`

Live calculator (functional, **Indigo Split** skin applied):  
https://todorpapazov.github.io/cc-tool/ · local [`../index.html`](../index.html)

## The five directions

| # | File | Name | Feel |
|---|------|------|------|
| 1 | [`01-cyan-command.html`](01-cyan-command.html) | **Cyan Command** | Mission-control telemetry · corner brackets · dual A/T rails |
| 2 | [`02-amber-ops.html`](02-amber-ops.html) | **Amber Ops** | Ops board strip · dense status chips · ledger-forward table |
| 3 | [`03-violet-glass.html`](03-violet-glass.html) | **Violet Glass** | Soft glass cards · violet glow · calmer medium density |
| 4 | [`04-emerald-ledger.html`](04-emerald-ledger.html) | **Emerald Ledger** | Finance HUD · side rail metrics · ledger as primary surface |
| 5 | [`05-indigo-split.html`](05-indigo-split.html) | **Indigo Split** | Full dual-column A | T · center interest bridge · indigo frame |

## Shared surfaces (every mock)

- Borrower **A** / **T** balances and shares  
- Statement **interest** + proportional split  
- **Minimum payment** + per-borrower min share  
- **Payment** actions (min / remaining / apply)  
- **Ledger** row with sample Jul 2026 figures  

## Direction note

User asked to **open in the browser** to compare. Density: **medium**.  
Palette lock deferred → **bold multi-palette spread** for pick/mix.

## Regenerate

```powershell
python .\CC-tool\mockups\_generate_cc_hud_mocks.py
```

## Tests

```powershell
python .\CC-tool\mockups\test_mock_structure.py
```
