# daybook

Turn a timesheet CSV into a client invoice. One rate, one currency, no account.

```
python3 -m daybook invoice fixtures/acre.csv --rate 85 --client "Acre Studio" --number 18 --due 2026-11-01
```

```
INVOICE 18
Client: Acre Studio
Due: 2026-11-01
Rate: 85.00

date        description            hours    amount
2026-10-01  API review              1.50    127.50
2026-10-02  Fix checkout rounding   3.00    255.00

Hours: 4.50
Total: 382.50
```

The CSV header is `date,description,hours`. Dates are `YYYY-MM-DD`. Hours have at most two decimal places. Each line is `hours × rate`, rounded half up to the cent, and the total is the sum of those rounded lines. The same file and the same flags always print the same text. There is no clock in the invoice.

## Will not do

- Tax, discounts, or more than one rate
- Currency conversion
- PDF, email, or a hosted account
- Guessing a column that is not in the header

## Tests

```
python3 -m unittest discover -s tests -v
```

Python 3.11 or newer. The standard library is enough.

## License

MIT.
