# PROMPT

1. How many XAUUSD trades are here? What is the net profit/loss?

Can you create short 2 hour time ranges placing all the XAUUSD trades in those ranges depending on their open time. Then for each range update the number of profitable trades and lossing trades and their net profit/loss.


Bring all this information in full without leaving anything out

2. Without adding the dates, just sum up the performance during each specific 2hr range. 


# 25_05_08 - 25_05_21

| Time Range    | Total Trades | Profitable Trades | Losing Trades | Net Profit/Loss |
| ------------- | ------------ | ----------------- | ------------- | --------------- |
| 10:00 - 12:00 | 15           | 5                 | 10            | -243.64         |
| 12:00 - 14:00 | 13           | 3                 | 10            | -371.50         |
| 14:00 - 16:00 | 15           | 7                 | 7             | 137.00          |
| 16:00 - 18:00 | 9            | 5                 | 4             | 69.12           |
| 18:00 - 20:00 | 10           | 3                 | 7             | -257.46         |

* Action - trade betweem 14:00 and 18:00


- Remove lot 0.12 on 7/24/2025
- Remove Friday trading day on 7/26/2025


- Add trading hrs to 24 hrs | remove lot 0.14 & 0.16 0n 8/6/2025

- add mtf analysis on 8/18/2025
- add "is_marabozu" & "candle_type" & MTF utilising M1 0n 8/22/2015

- Update trail.py to utilise M5 - 8/28.2025
