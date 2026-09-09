"""
Backfill the Canadian International Merchandise Trade import files into year-partitioned Parquet.

For every year in python/manifest.json: download the imports zip unless a valid one is already on
disk, pull out the HS10 monthly file, load it with every column as text, write it to
data/cimt/parquet/year=YYYY/imports.parquet, check that the Parquet row count equals the rows
read, delete the extracted CSV, keep the HS10 dictionary snapshot the zip shipped with under its
hash, and append one row to python/run_log.csv. A year whose Parquet is present with a row count
that matches its latest ok row in the log is skipped, so the script can be re-run at any time and
does each year's work once. This is batch engineering with a log, not a running production system.

    python backfill_cimt.py                        every year in the manifest
    python backfill_cimt.py --years 2023 2024      one or more years
    python backfill_cimt.py --years 2026 --force   redo a year and re-download its zip
"""
import argparse
import csv
import hashlib
import json
import re
import shutil
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import requests

HERE = Path(__file__).resolve().parent          # 05-additive-trade/python
PROJECT = HERE.parent                            # 05-additive-trade
DATA = PROJECT.parent / "data" / "cimt"          # ignored by git as a whole
ZIPS = DATA / "zips"
PARQUET = DATA / "parquet"
SNAPSHOTS = DATA / "dictionary" / "snapshots"
MANIFEST = HERE / "manifest.json"
LOG = HERE / "run_log.csv"

LOG_COLUMNS = {
    "year": "the calendar year the zip covers",
    "started_at": "UTC time the year's run began",
    "finished_at": "UTC time it ended, whether it succeeded or failed",
    "zip_url": "the resource URL from the manifest",
    "zip_bytes": "size of the zip on disk",
    "zip_sha256": "hash of the zip, so a later re-pull can be compared with this one",
    "zip_downloaded": "true if this run downloaded the zip, false if it reused the one on disk",
    "member": "the HS10 monthly file inside the zip",
    "rows_written": "rows in the Parquet, checked equal to the rows read from the CSV",
    "months": "distinct months in the file, 12 for a completed year",
    "dict_sha256": "hash of the HS10 dictionary snapshot the zip shipped with",
    "status": "ok or failed",
    "note": "partial year, the error text, or empty",
}
HDRS = {"User-Agent": "data-analytics-portfolio/1.0 (public open data pull)"}
TIMEOUT = 600
ZIP_MAGIC = b"PK\x03\x04"
DATA_MEMBER = re.compile(r"ODPFN014_\d{6}[A-Z]\.csv$")
DICT_MEMBER = re.compile(r"ODPF_1_HS10Desc\.(txt|TXT)$")
# The header every year's file must carry, spelled as the publisher spells it, accents included.
EXPECTED_HEADER = [
    "YearMonth/AnnéeMois", "HS10", "Country/Pays", "Province", "State/État",
    "Value/Valeur", "Quantity/Quantité", "Unit of Measure/Unité de Mesure",
]


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_log():
    if not LOG.exists():
        with open(LOG, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(LOG_COLUMNS)
    return LOG


def read_log():
    ensure_log()
    with open(LOG, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def append_log(row):
    ensure_log()
    with open(LOG, "a", newline="", encoding="utf-8") as f:
        csv.DictWriter(f, fieldnames=list(LOG_COLUMNS)).writerow(row)


def fetch_zip(url, target, force=False):
    """Download url to target unless a valid zip is already there. Returns True if it downloaded.

    The status line proves nothing on its own: a publisher can answer a missing file with an HTML
    page at HTTP 200. Nothing is written until the content type says zip and the first four bytes
    are the zip signature, and the file lands under a temporary name until it is complete.
    """
    if target.exists() and not force and zipfile.is_zipfile(target):
        return False
    reply = requests.get(url, headers=HDRS, timeout=TIMEOUT, stream=True)
    reply.raise_for_status()
    content_type = (reply.headers.get("content-type") or "").lower()
    chunks = reply.iter_content(1 << 20)
    first = next(chunks, b"")
    if "zip" not in content_type or not first.startswith(ZIP_MAGIC):
        raise ValueError(f"{url}: not a zip (content type {content_type!r}, first bytes {first[:4]!r})")
    partial = target.with_suffix(".part")
    with open(partial, "wb") as out:
        out.write(first)
        for chunk in chunks:
            out.write(chunk)
    partial.replace(target)
    return True


def one_member(archive, pattern, what):
    hits = [name for name in archive.namelist() if pattern.search(name)]
    if len(hits) != 1:
        raise ValueError(f"expected exactly one {what} in {Path(archive.filename).name}, found {hits}")
    return hits[0]


def parquet_rows(path):
    con = duckdb.connect()
    try:
        return con.execute(f"SELECT COUNT(*) FROM read_parquet('{path.as_posix()}')").fetchone()[0]
    finally:
        con.close()


def parquet_path(year):
    return PARQUET / f"year={year}" / "imports.parquet"


def already_done(year, log_rows):
    target = parquet_path(year)
    if not target.exists():
        return False
    ok_rows = [r for r in log_rows if r["year"] == str(year) and r["status"] == "ok"]
    if not ok_rows:
        return False
    try:
        return int(ok_rows[-1]["rows_written"]) == parquet_rows(target)
    except Exception:
        return False


def convert(year, zip_path):
    """Extract the HS10 file, load it as text, write Parquet, verify, delete the CSV."""
    with zipfile.ZipFile(zip_path) as archive:
        member = one_member(archive, DATA_MEMBER, "HS10 monthly file")
        dict_member = one_member(archive, DICT_MEMBER, "HS10 dictionary")
        dict_bytes = archive.read(dict_member)
        dict_sha = hashlib.sha256(dict_bytes).hexdigest()
        SNAPSHOTS.mkdir(parents=True, exist_ok=True)
        snapshot = SNAPSHOTS / f"hs10_desc_{dict_sha[:16]}.txt"
        if not snapshot.exists():
            snapshot.write_bytes(dict_bytes)
        csv_path = ZIPS / f"_extract_{year}.csv"
        with archive.open(member) as src, open(csv_path, "wb") as dst:
            shutil.copyfileobj(src, dst, 1 << 20)
    con = duckdb.connect()
    try:
        con.execute(f"CREATE TABLE t AS SELECT * FROM read_csv('{csv_path.as_posix()}', header = true, all_varchar = true)")
        header = [r[0] for r in con.execute("DESCRIBE t").fetchall()]
        if header != EXPECTED_HEADER:
            raise ValueError(f"{year}: header differs from the expected layout: {header}")
        rows_read = con.execute("SELECT COUNT(*) FROM t").fetchone()[0]
        months = con.execute(f'SELECT COUNT(DISTINCT "{EXPECTED_HEADER[0]}") FROM t').fetchone()[0]
        out = parquet_path(year)
        out.parent.mkdir(parents=True, exist_ok=True)
        con.execute(f"COPY t TO '{out.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    finally:
        con.close()
        csv_path.unlink(missing_ok=True)
    rows_written = parquet_rows(out)
    if rows_written != rows_read:
        out.unlink(missing_ok=True)
        raise ValueError(f"{year}: Parquet holds {rows_written} rows, the CSV had {rows_read}")
    return {"member": Path(member).name, "rows_written": rows_written, "months": months, "dict_sha256": dict_sha}


def run_year(entry, force=False):
    year = int(entry["year"])
    zip_path = ZIPS / Path(entry["url"]).name
    row = {column: "" for column in LOG_COLUMNS}
    row.update(year=year, started_at=utc_now(), zip_url=entry["url"], status="failed")
    try:
        row["zip_downloaded"] = str(fetch_zip(entry["url"], zip_path, force=force)).lower()
        row["zip_bytes"] = zip_path.stat().st_size
        row["zip_sha256"] = sha256_of(zip_path)
        row.update(convert(year, zip_path))
        row["status"] = "ok"
        row["note"] = "" if row["months"] == 12 else f"partial year: {row['months']} months"
    except Exception as err:
        row["note"] = f"{type(err).__name__}: {err}"[:300]
    row["finished_at"] = utc_now()
    append_log(row)
    return row


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--years", nargs="*", type=int, help="years to run; default is every year in the manifest")
    parser.add_argument("--force", action="store_true", help="redo the years given even if present, re-downloading the zip")
    args = parser.parse_args(argv)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    entries = sorted(manifest["imports"], key=lambda e: int(e["year"]))
    if args.years:
        wanted = set(args.years)
        entries = [e for e in entries if int(e["year"]) in wanted]
    ZIPS.mkdir(parents=True, exist_ok=True)
    PARQUET.mkdir(parents=True, exist_ok=True)
    log_rows = read_log()
    failed = 0
    for entry in entries:
        year = int(entry["year"])
        if not args.force and already_done(year, log_rows):
            print(f"{year}: Parquet present with a matching log row, skipped")
            continue
        t0 = time.time()
        row = run_year(entry, force=args.force)
        secs = time.time() - t0
        if row["status"] == "ok":
            source = "downloaded" if row["zip_downloaded"] == "true" else "zip reused"
            print(f"{year}: ok, {row['rows_written']:,} rows, {row['months']} months, {source}, {secs:.0f}s {row['note']}".rstrip())
        else:
            failed += 1
            print(f"{year}: FAILED after {secs:.0f}s: {row['note']}")
    print(f"done: {len(entries)} years requested, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
