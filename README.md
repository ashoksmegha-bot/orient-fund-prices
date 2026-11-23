# Orient fund prices

A free job reads the latest fund prices (NAV) every 3 hours from FT Markets
(by ISIN) and, where a link is given, from BlackRock's own fund page. It
saves them in `prices.json`, which the Orient ULIP tools load when they open.

- To add a fund: add a line to `funds.csv` (code, ISIN, currency, name, and
  optionally its BlackRock page link). The job picks it up on its next run.
- To refresh now: Actions tab, "Update fund prices", "Run workflow".
- Each price carries its own NAV date and source. If every source fails for
  a fund, the last good price stays and is marked `"stale": true`.

Prices are market data for illustration, not an official valuation.
