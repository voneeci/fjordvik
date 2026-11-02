# Phase 1: synthetic service data with a planted signal

Learning note for the after-sales service build. Phase 1, 2 November 2026. Synthetic data
only: Fjordvik Manufacturing Oy is fictional.

## The business need

The service AI needs history to learn from: pumps, their daily readings, their failures,
the parts they used and the orders customers placed. Fjordvik is fictional, so that
history has to be made. Made-up data is only useful if it behaves like the real thing,
and if we know exactly what is hidden in it.

## The idea in plain English

**Plant a signal, and keep the answer key.** The generator decides, pump by pump, when
each failure happens. Before about two thirds of them it raises vibration or bearing
temperature over two to six weeks, the way a worn bearing does. Before the rest it does
nothing, as with a sudden seal leak or an electrical trip. It writes down which was which
in an answer key kept outside the tables. Later phases can then measure what a model
found against what was really there, which live data never allows.

**Make the noise honest.** Readings wander with the season (heating pumps run most in
winter), with age (old pumps vibrate a little more), and day to day. A pump sometimes
gives one high reading after a start. A model has to tell these from a real warning.

**Add up to what finance already reports.** Parts orders are not made up freely. Every
month's spare parts and service kit sales already sit in `fact_sales`, so the generator
splits each of those rows into order lines. The lines add up to it in units and to the
cent, so the service data and the sales reports can never disagree.

**Same seed, same files.** Every pump has its own random stream, seeded from its id. Run
the generator twice and the files are identical, byte for byte. A test proves it on every
run, and another proves that none of the 22 earlier tables moved.

## How the code does it

`data/src/fjordvik_data/service.py`, in three passes per pump:

1. **Planned running hours** for each day, from the pump's duty, its seasonal profile and
   weekends.
2. **Events.** Each day has a small chance of failure. It grows by 7% for each year of age
   and with the wear since the last overhaul, and in proportion to the day's running hours.
   Preventive visits (one or two a year, by contract) take wear away. A failure picks a mode
   that fits the pump, decides whether it gives warning, and stops the pump until it is
   repaired: one to three days if the part is in stock, its full lead time if not.
3. **Readings.** Vibration, temperature and power from the pump's baseline, its age, the
   season and noise, plus the warning rise on the days before a warned failure.

Then the parts orders: service parts first, in the month they were ordered, then stock
orders from the wider installed base. The mix of stock orders follows the fleet's running
hours and age, which gives the phase 2 forecast real drivers. When a month runs cheap
against its invoiced value, dearer baskets become likelier, so prices stay close to list.

`corpus.py` writes the manuals from the same settings, so a manual can never quote a part
or an alarm limit the data does not have.

## The result

- 600 pumps, 582,996 daily readings (20 MB), 2,554 service events, 53,570 order lines and
  39,600 portal rows; the 22 earlier tables are unchanged.
- 324 failures over three years (100, 99 and 125 a year); 222 of them (69%) gave warning.
  The median failure stopped its pump for 79 hours.
- **A warned failure** (pump A0505, a bearing failure on 4 May 2024, warning from 27 March):
  vibration 2.14 mm/s two months before, 2.44 a month before, 4.40 two weeks before, 6.46
  three days before. Bearing temperature went from 47 to 65 C.
- **A failure with no warning** (pump A0047, an electrical trip on 1 June 2024): vibration
  stayed between 2.8 and 3.3 mm/s. Its bearing temperature rose from 34 to 40 C, but that
  is the season warming up, not a fault: the kind of change phase 3 must not take for a
  warning.
- **Reconciliation:** Tartu's service kit sales to the Baltics in March 2025 are 258 units
  and EUR 172,469.98 in `fact_sales`; its 70 order lines add up to exactly that.
- Data tests: 96 passed (36 new).

## What would change with live data

- There would be no answer key. Whether a failure "gave warning" would have to be judged
  from the readings after the fact, and labels would be noisier.
- Readings would have gaps, sensor faults, recalibrations and firmware changes. Each needs
  a rule in the intake checks, and a model must cope with them.
- Failures would not follow a neat hazard; some customers report late, and some repairs
  are logged with the wrong mode.
- Orders would come from the ERP, not be split from sales; the reconciliation would be a
  check, not a construction.
- Models trained on this data will look better than they would on live data. Each later
  phase says so next to its results.
