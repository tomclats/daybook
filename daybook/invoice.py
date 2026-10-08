"""Invoice arithmetic and the plain-text sheet a client can read."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

CENT = Decimal("0.01")
HOUR = Decimal("0.01")


class SheetError(Exception):
    """The timesheet or the arguments cannot become an invoice."""


@dataclass(frozen=True)
class Entry:
    date: str
    description: str
    hours: Decimal


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def format_money(value: Decimal) -> str:
    return f"{money(value):.2f}"


def format_hours(value: Decimal) -> str:
    return f"{value.quantize(HOUR):.2f}"


def parse_date(text: str, label: str) -> str:
    raw = text.strip()
    try:
        parsed = datetime.strptime(raw, "%Y-%m-%d")
    except ValueError as exc:
        raise SheetError(f"{label} must be YYYY-MM-DD") from exc
    return parsed.strftime("%Y-%m-%d")


def parse_amount(text: str, label: str, places: int) -> Decimal:
    raw = text.strip()
    if raw == "":
        raise SheetError(f"{label} is empty")
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise SheetError(f"{label} is not a number") from exc
    if not value.is_finite():
        raise SheetError(f"{label} is not a number")
    quantum = Decimal(1).scaleb(-places)
    if value != value.quantize(quantum):
        raise SheetError(f"{label} has more than {places} decimal places")
    return value


def load_timesheet(path: Path) -> list[Entry]:
    if not path.is_file():
        raise SheetError(f"{path} not found")
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise SheetError(f"{path}: {exc.strerror}") from exc
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise SheetError(f"{path}: missing header")
    fields = [(name or "").strip() for name in reader.fieldnames]
    if any(name == "" for name in fields):
        raise SheetError(f"{path}: header has an empty column")
    required = {"date", "description", "hours"}
    present = set(fields)
    missing = sorted(required - present)
    if missing:
        raise SheetError(f"{path}: missing column {missing[0]}")
    extra = sorted(present - required)
    if extra:
        raise SheetError(f"{path}: unexpected column {extra[0]}")
    entries: list[Entry] = []
    for row in reader:
        values = {key.strip(): (value or "").strip() for key, value in row.items() if key}
        if not any(values.values()):
            continue
        try:
            description = values["description"]
            if description == "" or "\n" in description or "\r" in description:
                raise SheetError("description is empty")
            hours = parse_amount(values["hours"], "hours", 2)
            if hours < 0:
                raise SheetError("hours cannot be negative")
            entries.append(
                Entry(
                    date=parse_date(values["date"], "date"),
                    description=description,
                    hours=hours,
                )
            )
        except SheetError as exc:
            raise SheetError(f"{path}: row {reader.line_num}: {exc}") from exc
    return entries


def _plain(text: str, label: str) -> str:
    cleaned = text.strip()
    if cleaned == "" or any(char in cleaned for char in "\n\r"):
        raise SheetError(f"{label} is empty")
    return cleaned


def render_invoice(
    entries: list[Entry],
    rate: Decimal,
    client: str,
    number: str,
    due: str,
) -> str:
    client = _plain(client, "client")
    number = _plain(number, "number")
    due = parse_date(due, "due")
    rate = parse_amount(format(rate, "f"), "rate", 2)
    if rate < 0:
        raise SheetError("rate cannot be negative")
    lines: list[tuple[Entry, Decimal]] = []
    for entry in entries:
        lines.append((entry, money(entry.hours * rate)))
    total_hours = sum((entry.hours for entry, _amount in lines), Decimal(0))
    total = sum((amount for _entry, amount in lines), Decimal(0))
    desc_width = max([len("description"), *(len(entry.description) for entry, _amount in lines)])
    header = _join(
        ["date".ljust(10), "description".ljust(desc_width), "hours".rjust(5), "amount".rjust(8)]
    )
    body = [header]
    for entry, amount in lines:
        body.append(
            _join(
                [
                    entry.date.ljust(10),
                    entry.description.ljust(desc_width),
                    format_hours(entry.hours).rjust(5),
                    format_money(amount).rjust(8),
                ]
            )
        )
    sheet = [
        f"INVOICE {number}",
        f"Client: {client}",
        f"Due: {due}",
        f"Rate: {format_money(rate)}",
        "",
        *body,
        "",
        f"Hours: {format_hours(total_hours)}",
        f"Total: {format_money(total)}",
        "",
    ]
    return "\n".join(sheet)


def _join(cells: list[str]) -> str:
    return "  ".join(cells)
