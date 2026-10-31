# Quarterly portfolio scorecard: method

How Fjordvik scores its product groups each quarter, and where each part of the method
comes from.

> **Synthetic data only.** Fjordvik Manufacturing Oy is a fictional company. The ratings
> are synthetic and the weights are the company's own stated choice, not published figures.

## The process

1. **Collect** (first two weeks after the quarter closes). The Data and AI Specialist
   refreshes the report and exports, per product group: net sales, margin %, share of net
   sales, the price effect against the prior year, and use-phase emissions per unit.
2. **Prepare** (week 3). Product Managers draft a rating for each of their groups on each
   criterion, with the figures beside them; the analyst checks every group has a rating
   on every criterion and flags any data or classification issue still open.
3. **Review** (week 4). The portfolio review agrees the final ratings. They are entered in
   `fact_product_rating` (one row per quarter, group and criterion) and the report is
   refreshed.
4. **Decide.** The scorecard page sets each group's weighted score beside its figures, so
   the review can see where a high score and weak figures (or the reverse) need a closer look.

## Criteria and weights

| Criterion | Weight | What a high rating means |
| --- | --- | --- |
| Strategic alignment | 25 | Fits where Fjordvik wants to be: efficient pumping for water and industry |
| Product advantage | 20 | Clearly better than competing products for the customer |
| Market attractiveness | 20 | A growing, profitable market |
| Ability to leverage core competencies | 10 | Uses what Fjordvik already does well (hydraulics, motors, controls) |
| Technical feasibility | 10 | Can be made and improved with known technology |
| Reward against risk | 15 | Margin and growth justify the investment and risk |

- **Criteria:** Cooper and Edgett list these six as "Typical main criteria" of a scoring
  model, rated "on 1-10 scales", with factors "calculated via weightings x ratings"
  ([Stage-Gate International, 11 July 2022](https://www.stage-gate.com/blog/portfolio-management-fundamental-for-new-product-success/)).
- **Weights:** no opened source publishes weights (research note, 31 October 2026), so
  these are **Fjordvik's own choice**, held in `dim_score_criterion` and changed only by
  portfolio governance. No weight is typed into a measure.
- **Score:** `Weighted Score` = sum of (rating × weight) ÷ sum of weights, so it stays on
  the 1 to 10 scale.

## Cadence

Quarterly. Cooper and Edgett describe portfolio reviews that "typically" occur "four times
a year" where reviews drive decisions, and the PMI Standard for Portfolio Management
(3rd edition) says reviews "could be scheduled quarterly".

## What it is not

- **Not a BCG growth-share matrix.** That needs market growth and Fjordvik's share of each
  market, which Fjordvik does not hold. Share of Fjordvik's own sales is shown for balance,
  not as market share.
- **Not a formula of the figures.** The ratings are judgements informed by the figures; the
  page keeps both side by side so neither replaces the other.
