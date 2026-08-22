| app | base | A | B | Bv | C | D | K |
|---|---|---|---|---|---|---|---|
| grok_01_apiary (7 observed) | 0/7 | 1/7 | 3/7 | 3/7 | 4/7 | 4/7 | 5/7 |
| grok_02_observatory (5 observed) | 0/5 | 1/5 | 1/5 | 2/5 | 2/5 | 4/5 | 5/5 |
| grok_03_pharmacy (6 observed) | 0/7 | 1/7 | 3/7 | 3/7 | 4/7 | 4/7 | 5/7 |
| grok_04_climbing (5 observed) | 0/6 | 1/6 | 2/6 | 2/6 | 3/6 | 3/6 | 3/6 |
| claude_01_airport_gates (6 observed) | 0/7 | 2/7 | 4/7 | 4/7 | 6/7 | 6/7 | 6/7 |
| claude_02_pharmacy_dispensary (4 observed) | 0/4 | 1/4 | 1/4 | 1/4 | 3/4 | 3/4 | 3/4 |
| claude_03_museum_loans (6 observed) | 0/6 | 0/6 | 4/6 | 4/6 | 6/6 | 6/6 | 6/6 |
| claude_04_datacenter_racks (3 observed) | 0/5 | 1/5 | 0/5 | 0/5 | 2/5 | 2/5 | 3/5 |
| **total** | **0/47** | **8/47** | **18/47** | **19/47** | **30/47** | **32/47** | **36/47** |

| app | cond | types | attrs | rels | RTC | GTC | learned / spurious | view-FP transitions | fail. rejection |
|---|---|---|---|---|---|---|---|---|---|
| grok_01_apiary | base | 2/4 | 0/11 | 0/5 | 0.0 | 0.0 | 1 / 1 | 8/13 | 0.0 |
| grok_01_apiary | A | 4/4 | 0/11 | 0/5 | 0.085 | 0.085 | 1 / 0 | 0/5 | 0.0 |
| grok_01_apiary | B | 4/4 | 8/11 | 3/5 | 0.746 | 1.0 | 10 / 3 | 0/44 | 0.11 |
| grok_01_apiary | Bv | 4/4 | 8/11 | 3/5 | 0.746 | 1.0 | 10 / 3 | 0/44 | 0.11 |
| grok_01_apiary | C | 4/4 | 8/11 | 3/5 | 1.0 | 1.0 | 13 / 5 | 0/59 | 0.11 |
| grok_01_apiary | D | 4/4 | 8/11 | 3/5 | 1.0 | 1.0 | 13 / 6 | 0/59 | 0.1 |
| grok_01_apiary | K | 4/4 | 10/11 | 3/5 | - | 1.0 | 11 / 0 | -/- | 0.47 |
| grok_02_observatory | base | 1/4 | 0/12 | 0/9 | 0.0 | 0.0 | 0 / 0 | 4/7 | 0.0 |
| grok_02_observatory | A | 4/4 | 0/12 | 0/9 | 0.118 | 0.324 | 3 / 1 | 2/13 | 0.0 |
| grok_02_observatory | B | 4/4 | 6/12 | 3/9 | 0.794 | 1.0 | 6 / 2 | 2/36 | 0.06 |
| grok_02_observatory | Bv | 4/4 | 6/12 | 3/9 | 0.853 | 1.0 | 6 / 1 | 0/34 | 0.06 |
| grok_02_observatory | C | 4/4 | 6/12 | 3/9 | 1.0 | 1.0 | 5 / 0 | 0/34 | 0.09 |
| grok_02_observatory | D | 4/4 | 6/12 | 3/9 | 1.0 | 1.0 | 6 / 0 | 0/34 | 0.06 |
| grok_02_observatory | K | 4/4 | 11/12 | 3/9 | - | 1.0 | 8 / 0 | -/- | 0.94 |
| grok_03_pharmacy | base | 3/4 | 1/11 | 1/5 | 0.0 | 0.804 | 2 / 2 | 26/30 | 0.0 |
| grok_03_pharmacy | A | 4/4 | 0/11 | 0/5 | 0.059 | 0.059 | 1 / 0 | 0/3 | 0.0 |
| grok_03_pharmacy | B | 4/4 | 7/11 | 3/5 | 0.824 | 1.0 | 12 / 0 | 0/44 | 0.35 |
| grok_03_pharmacy | Bv | 4/4 | 7/11 | 3/5 | 0.824 | 1.0 | 12 / 0 | 0/44 | 0.35 |
| grok_03_pharmacy | C | 4/4 | 7/11 | 3/5 | 1.0 | 1.0 | 15 / 2 | 0/53 | 0.35 |
| grok_03_pharmacy | D | 4/4 | 7/11 | 3/5 | 1.0 | 1.0 | 15 / 2 | 0/53 | 0.35 |
| grok_03_pharmacy | K | 4/4 | 10/11 | 3/5 | - | 1.0 | 14 / 0 | -/- | 0.55 |
| grok_04_climbing | base | 2/4 | 1/12 | 0/9 | 0.012 | 0.024 | 3 / 3 | 18/19 | 0.0 |
| grok_04_climbing | A | 3/4 | 0/12 | 0/9 | 0.037 | 0.061 | 2 / 1 | 0/5 | 0.0 |
| grok_04_climbing | B | 3/4 | 5/12 | 2/9 | 0.976 | 1.0 | 3 / 1 | 0/82 | 0.0 |
| grok_04_climbing | Bv | 3/4 | 5/12 | 2/9 | 0.976 | 1.0 | 3 / 1 | 0/82 | 0.0 |
| grok_04_climbing | C | 4/4 | 6/12 | 3/9 | 1.0 | 1.0 | 3 / 0 | 0/82 | 0.0 |
| grok_04_climbing | D | 4/4 | 6/12 | 3/9 | 1.0 | 1.0 | 3 / 0 | 0/82 | 0.81 |
| grok_04_climbing | K | 4/4 | 11/12 | 3/9 | - | 1.0 | 3 / 0 | -/- | 0.81 |
| claude_01_airport_gates | base | 1/4 | 3/12 | 0/5 | 0.0 | 0.353 | 0 / 0 | 0/0 | 0.0 |
| claude_01_airport_gates | A | 4/4 | 0/12 | 0/5 | 0.294 | 0.294 | 2 / 0 | 0/10 | 0.0 |
| claude_01_airport_gates | B | 4/4 | 6/12 | 3/5 | 0.647 | 1.0 | 4 / 0 | 0/22 | 0.0 |
| claude_01_airport_gates | Bv | 4/4 | 6/12 | 3/5 | 0.647 | 1.0 | 4 / 0 | 0/22 | 0.0 |
| claude_01_airport_gates | C | 4/4 | 9/12 | 3/5 | 1.0 | 1.0 | 6 / 0 | 0/34 | 0.0 |
| claude_01_airport_gates | D | 4/4 | 9/12 | 3/5 | 1.0 | 1.0 | 6 / 0 | 0/34 | 0.12 |
| claude_01_airport_gates | K | 4/4 | 11/12 | 3/5 | - | 1.0 | 6 / 0 | -/- | 0.4 |
| claude_02_pharmacy_dispensary | base | 2/4 | 2/13 | 0/9 | 0.276 | 0.379 | 0 / 0 | 8/16 | 0.0 |
| claude_02_pharmacy_dispensary | A | 4/4 | 0/13 | 0/9 | 0.379 | 0.379 | 1 / 0 | 0/11 | 0.0 |
| claude_02_pharmacy_dispensary | B | 4/4 | 8/13 | 3/9 | 0.759 | 1.0 | 8 / 4 | 1/25 | 0.0 |
| claude_02_pharmacy_dispensary | Bv | 4/4 | 8/13 | 3/9 | 0.759 | 1.0 | 8 / 4 | 0/24 | 0.0 |
| claude_02_pharmacy_dispensary | C | 4/4 | 8/13 | 3/9 | 1.0 | 1.0 | 9 / 0 | 0/29 | 0.0 |
| claude_02_pharmacy_dispensary | D | 4/4 | 8/13 | 3/9 | 1.0 | 1.0 | 6 / 0 | 0/29 | 0.0 |
| claude_02_pharmacy_dispensary | K | 4/4 | 11/13 | 3/9 | - | 1.0 | 6 / 0 | -/- | 0.0 |
| claude_03_museum_loans | base | 1/4 | 2/13 | 0/5 | 0.0 | 0.0 | 0 / 0 | 0/0 | 0.0 |
| claude_03_museum_loans | A | 3/4 | 0/13 | 0/5 | 0.0 | 0.121 | 0 / 0 | 0/0 | 0.0 |
| claude_03_museum_loans | B | 3/4 | 6/13 | 2/5 | 0.31 | 1.0 | 5 / 0 | 0/18 | 0.0 |
| claude_03_museum_loans | Bv | 3/4 | 6/13 | 2/5 | 0.31 | 1.0 | 5 / 0 | 0/18 | 0.0 |
| claude_03_museum_loans | C | 4/4 | 9/13 | 3/5 | 1.0 | 1.0 | 6 / 0 | 0/58 | 0.0 |
| claude_03_museum_loans | D | 4/4 | 9/13 | 3/5 | 1.0 | 1.0 | 6 / 0 | 0/58 | 0.12 |
| claude_03_museum_loans | K | 4/4 | 11/13 | 3/5 | - | 1.0 | 6 / 0 | -/- | 0.12 |
| claude_04_datacenter_racks | base | 2/4 | 1/13 | 0/5 | 0.0 | 0.0 | 0 / 0 | 7/9 | 0.0 |
| claude_04_datacenter_racks | A | 3/4 | 0/13 | 0/5 | 0.364 | 0.364 | 1 / 0 | 0/4 | 0.0 |
| claude_04_datacenter_racks | B | 3/4 | 7/13 | 2/5 | 0.364 | 0.364 | 1 / 1 | 0/4 | 0.0 |
| claude_04_datacenter_racks | Bv | 3/4 | 7/13 | 2/5 | 0.364 | 0.364 | 1 / 1 | 0/4 | 0.0 |
| claude_04_datacenter_racks | C | 4/4 | 9/13 | 3/5 | 1.0 | 1.0 | 4 / 0 | 0/11 | 0.0 |
| claude_04_datacenter_racks | D | 4/4 | 9/13 | 3/5 | 1.0 | 1.0 | 4 / 0 | 0/11 | 0.0 |
| claude_04_datacenter_racks | K | 4/4 | 11/13 | 3/5 | - | 1.0 | 4 / 0 | -/- | 0.0 |
