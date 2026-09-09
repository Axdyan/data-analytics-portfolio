"""Re-run every number this portfolio quotes, on a fresh pull of its sources.

Each shipped project has a manifest under ci/manifests/ listing the figures its
README and findings memo quote, with one SQL query per figure against the tables
the project's own notebook builds. This runner executes the notebook top to
bottom in its own folder (which re-pulls the data, rebuilds the DuckDB file,
rewrites the crosswalks and the charts), records whether the source bytes
changed against the committed pull manifest, re-measures every figure, and
classifies each one under the drift contract in ci/policy.yml.

Two regimes. Same source bytes: every figure must come back exactly at the
precision the memo prints it, anything else is a failure to reproduce. Different
bytes: a moved figure is publisher drift, and the policy says how far it may move
before the memo needs a dated update.

Usage
  python ci/reproduce.py --project 06-ontario-demand-forecast
  python ci/reproduce.py --project 03-defence-procurement --no-execute
  python ci/reproduce.py --all
  python ci/reproduce.py --aggregate
  python ci/reproduce.py --project 06-ontario-demand-forecast --root C:/scratch/repo_copy

Exit code is 1 when any figure failed to reproduce on unchanged bytes, when the
notebook stopped on unchanged bytes, or when the runner itself errored. Drift
never fails the run.
"""

# %% imports
import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import yaml

# %% constants
HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = HERE.parent

STATUS_ORDER = [
    "reproduced", "drift", "drift_outside_band", "failed", "not_run", "not_reproducible",
]
STATUS_LABEL = {
    "reproduced": "reproduced",
    "drift": "drift, inside band",
    "drift_outside_band": "drift, outside band",
    "failed": "FAILED",
    "not_run": "not run",
    "not_reproducible": "not reproducible in CI",
}
KINDS = {"count", "money", "pct", "mw", "stat", "ratio", "text", "constant"}
COMPARES = {"eq", "lt", "le", "gt", "ge"}
FINGERPRINT_KINDS = {"manifest_json", "file_sizes", "file_hashes"}

# exceptions that mean the network let the notebook down, not that the notebook stopped;
# a run that hits one of these is executed a second time before it counts as a stop
TRANSIENT_ERRORS = {
    "ReadTimeout", "ConnectTimeout", "ConnectionError", "ChunkedEncodingError", "SSLError",
    "RemoteDisconnected", "ProtocolError", "IncompleteRead", "URLError", "TimeoutError", "timeout",
}


def is_transient(error):
    if not error:
        return False
    if error.get("ename") in TRANSIENT_ERRORS:
        return True
    text = (error.get("evalue") or "")
    return "Max retries exceeded" in text or "Read timed out" in text or "Connection reset" in text


def utc_today():
    return datetime.now(timezone.utc).date().isoformat()


# %% small helpers
# ----------------------------------------------------------------------------

class Log:
    """Print to stdout and append to a log file, with a wall-clock stamp."""

    def __init__(self, path=None):
        self.path = path
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("", encoding="utf-8")

    def __call__(self, msg):
        line = datetime.now(timezone.utc).strftime("%H:%M:%S") + "  " + str(msg)
        print(line, flush=True)
        if self.path is not None:
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")


def load_yaml(path):
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def decimals_of(value):
    """How many decimals a quoted number carries, so 57.2 is compared at one decimal."""
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return 0
    if isinstance(value, float):
        exp = Decimal(str(value)).as_tuple().exponent
        return max(0, -exp) if isinstance(exp, int) else 0
    return 0


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def to_number(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fmt(value, nd=None):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    num = to_number(value)
    if num is None:
        return str(value)
    if nd is None:
        nd = decimals_of(num) if isinstance(num, float) else 0
    if nd <= 0:
        return format(round(num, nd), ",.0f")
    return format(round(num, nd), ",." + str(nd) + "f")


def opening_words(cell_source, width=90):
    for line in cell_source.splitlines():
        text = line.strip()
        if text:
            return text.lstrip("# ").strip()[:width]
    return ""


def git(root, *args):
    """Run git in root, but only when root is itself the top of a checkout.

    A scratch copy under the home folder would otherwise pick up whatever repository
    sits above it and report its files as changes.
    """
    try:
        top = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=60)
        if top.returncode != 0 or Path(top.stdout.strip()).resolve() != Path(root).resolve():
            return None
        out = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=60)
        return out.stdout.strip() if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


# %% sources: pulling what the notebooks cannot pull themselves, and fingerprinting
# ----------------------------------------------------------------------------

class SourceUnavailable(Exception):
    pass


def kaggle_executable():
    candidates = [
        Path(sys.executable).with_name("kaggle.exe"),
        Path(sys.executable).with_name("kaggle"),
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    found = shutil.which("kaggle")
    if found:
        return found
    return None


def kaggle_credentials_present():
    if os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY"):
        return True
    cfg = Path(os.environ.get("KAGGLE_CONFIG_DIR", Path.home() / ".kaggle")) / "kaggle.json"
    return cfg.exists()


def ensure_kaggle_source(source, project_dir, log):
    """Download a Kaggle dataset into the notebook's data folder when the files are absent.

    The notebooks read the CSVs from ../data/<name>/ and assume they exist. On a
    fresh clone nothing does, so the runner fetches them first. Credentials come
    from KAGGLE_USERNAME and KAGGLE_KEY or from ~/.kaggle/kaggle.json.
    """
    folder = (project_dir / source["folder"]).resolve()
    files = source.get("files", [])
    present = [f for f in files if (folder / f).exists()]
    if files and len(present) == len(files):
        log("source " + source["id"] + ": all " + str(len(files)) + " files present, no download")
        return "present"
    if not kaggle_credentials_present():
        raise SourceUnavailable("Kaggle credentials not configured (KAGGLE_USERNAME and KAGGLE_KEY), "
                                "so " + source["dataset"] + " cannot be downloaded")
    exe = kaggle_executable()
    if exe is None:
        raise SourceUnavailable("the kaggle command line client is not installed")
    folder.mkdir(parents=True, exist_ok=True)
    cmd = [exe, "datasets", "download", "-d", source["dataset"], "-p", str(folder), "--unzip", "-q"]
    log("source " + source["id"] + ": downloading " + source["dataset"] + " into " + str(folder))
    t0 = time.time()
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    if out.returncode != 0:
        raise SourceUnavailable("kaggle download failed: " + (out.stderr or out.stdout).strip()[-800:])
    missing = [f for f in files if not (folder / f).exists()]
    if missing:
        raise SourceUnavailable("kaggle download finished but these files are missing: " + ", ".join(missing))
    log("source " + source["id"] + ": downloaded in " + str(round(time.time() - t0)) + "s")
    return "downloaded"


def read_manifest_fingerprint(project_dir, spec):
    """Read the hashes the notebook itself wrote into its pull manifest.

    spec.path is the manifest file, spec.value the field holding the hash. When the
    manifest holds a list of files (spec.list), spec.key names the field that
    identifies each entry, and include or exclude narrow the entries.
    """
    path = project_dir / spec["path"]
    if not path.exists():
        raise SourceUnavailable("pull manifest not found: " + str(path))
    data = json.loads(path.read_text(encoding="utf-8"))
    value_field = spec.get("value", "sha256")
    if "list" in spec:
        entries = data.get(spec["list"], [])
        key_field = spec.get("key", "file")
        include = spec.get("include")
        exclude = set(spec.get("exclude", []))
        result = {}
        for entry in entries:
            name = str(entry.get(key_field))
            if include is not None and name not in include:
                continue
            if name in exclude:
                continue
            result[name] = entry.get(value_field)
        return result
    return {"": data.get(value_field)}


def read_file_fingerprint(project_dir, spec, use_hash):
    folder = (project_dir / spec["folder"]).resolve()
    result = {}
    for name in spec.get("files", []):
        p = folder / name
        if not p.exists():
            result[name] = None
        elif use_hash:
            result[name] = sha256_of(p)
        else:
            result[name] = p.stat().st_size
    return result


def fingerprint_source(source, project_dir):
    spec = source.get("fingerprint", {})
    kind = spec.get("kind")
    if kind == "manifest_json":
        return read_manifest_fingerprint(project_dir, spec)
    if kind == "file_sizes":
        return read_file_fingerprint(project_dir, spec, use_hash=False)
    if kind == "file_hashes":
        return read_file_fingerprint(project_dir, spec, use_hash=True)
    raise ValueError("unknown fingerprint kind: " + str(kind))


def fingerprints_path(project):
    return HERE / "manifests" / (project + ".fingerprints.json")


def committed_fingerprints(project, manifest):
    """The fingerprints the committed figures were measured on.

    They live beside the manifest in <project>.fingerprints.json, written by
    --record-fingerprints after a hand run of the notebook; a manifest may also
    carry them inline under each source's `committed` key.
    """
    path = fingerprints_path(project)
    recorded = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    out = {}
    for s in manifest.get("sources", []):
        out[s["id"]] = recorded.get(s["id"], s.get("committed", {}))
    return out


def record_fingerprints(project, root, log):
    """Read every source fingerprint from the project folder as it stands and save it.

    Run this after the notebook has been run by hand and its pull manifest committed,
    so the CI compares later pulls against the bytes the memo was written from.
    """
    manifest = load_yaml(HERE / "manifests" / (project + ".yml"))
    project_dir = root / project
    recorded = {}
    for s in manifest.get("sources", []):
        observed = fingerprint_source(s, project_dir)
        recorded[s["id"]] = observed
        log("recorded " + s["id"] + ": " + str(len(observed)) + " entries")
    path = fingerprints_path(project)
    path.write_text(json.dumps({"project": project, "recorded_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                **recorded}, indent=2, sort_keys=False), encoding="utf-8")
    log("written " + str(path))
    return path


def compare_fingerprint(committed, observed):
    """Return (status, detail). Status is unchanged, changed or missing."""
    committed = {str(k): v for k, v in (committed or {}).items()}
    observed = {str(k): v for k, v in (observed or {}).items()}
    if not observed or all(v is None for v in observed.values()):
        return "missing", "no fingerprint could be read after the run"
    changed = [k for k in committed if observed.get(k) != committed[k]]
    new = [k for k in observed if k not in committed]
    if not changed and not new:
        return "unchanged", "identical to the committed fingerprint (" + str(len(committed)) + " entries)"
    parts = []
    if changed:
        parts.append(str(len(changed)) + " of " + str(len(committed)) + " entries differ: " +
                     ", ".join(k or "(file)" for k in changed[:6]) + ("..." if len(changed) > 6 else ""))
    if new:
        parts.append(str(len(new)) + " new: " + ", ".join(new[:6]))
    return "changed", "; ".join(parts)


# %% executing the notebook
# ----------------------------------------------------------------------------

def execute_notebook(project_dir, notebook_name, log, out_path=None, cell_timeout=7200):
    """Run the notebook top to bottom in its own folder, cell by cell, logging each.

    Returns a dict with the cell count, how many code cells ran, the elapsed time,
    and the error (position, opening words, exception name and message) if a cell
    raised. Positions are 1-based over every cell in the file, code or not, which
    is how the project hand-offs name them.
    """
    import nbformat
    from nbclient import NotebookClient
    from nbclient.exceptions import CellExecutionError

    nb_path = project_dir / notebook_name
    nb = nbformat.read(nb_path, as_version=4)
    client = NotebookClient(
        nb,
        timeout=cell_timeout,
        kernel_name="python3",
        resources={"metadata": {"path": str(project_dir)}},
        allow_errors=False,
        record_timing=True,
    )
    result = {"cells": len(nb.cells), "code_cells": sum(c.cell_type == "code" for c in nb.cells),
              "executed": 0, "elapsed_s": 0.0, "error": None, "cell_times": []}
    t_start = time.time()
    client.reset_execution_trackers()
    with client.setup_kernel():
        for idx, cell in enumerate(nb.cells):
            if cell.cell_type != "code":
                continue
            words = opening_words(cell.source)
            t0 = time.time()
            try:
                client.execute_cell(cell, idx)
            except CellExecutionError as exc:
                dt = time.time() - t0
                result["error"] = {
                    "position": idx + 1,
                    "opening": words,
                    "ename": exc.ename,
                    "evalue": (exc.evalue or "")[:2000],
                    "elapsed_s": round(dt, 1),
                }
                log("cell " + str(idx + 1).rjust(3) + "  " + format(dt, "7.1f") + "s  ERROR " + exc.ename + ": " +
                    (exc.evalue or "")[:300].replace("\n", " "))
                break
            dt = time.time() - t0
            result["executed"] += 1
            result["cell_times"].append({"position": idx + 1, "seconds": round(dt, 1), "opening": words})
            log("cell " + str(idx + 1).rjust(3) + "  " + format(dt, "7.1f") + "s  " + words)
    result["elapsed_s"] = round(time.time() - t_start, 1)
    if out_path is not None:
        try:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            nbformat.write(nb, out_path)
        except Exception as exc:  # the executed copy is a convenience, never a reason to fail
            log("could not write the executed notebook copy: " + str(exc))
    return result


# %% measuring and classifying
# ----------------------------------------------------------------------------

def notebook_output_text(nb_path):
    """The printed output of every code cell, as a list of (position, text).

    Some figures a memo quotes are computed in the notebook's Python and printed,
    never written to a table: a Wald statistic, a bootstrap standard error, a
    decomposition weight. A manifest entry with `print_match` reads those back from
    the executed notebook with a regular expression, the way a reader would from the
    cell under the sentence. Positions are 1-based over every cell in the file.
    """
    import nbformat
    nb = nbformat.read(nb_path, as_version=4)
    out = []
    for idx, cell in enumerate(nb.cells):
        if cell.cell_type != "code":
            continue
        parts = []
        for o in cell.get("outputs", []):
            if o.get("output_type") == "stream":
                parts.append("".join(o.get("text", "")))
            elif o.get("output_type") in ("execute_result", "display_data"):
                data = o.get("data", {})
                if "text/plain" in data:
                    parts.append("".join(data["text/plain"]))
        out.append((idx + 1, "\n".join(parts)))
    return out


def match_printed(outputs, spec):
    """Apply a manifest print_match spec to the notebook outputs; return (value, detail).

    spec is a regular expression, or a mapping with `pattern` and optionally `cell`
    (restrict to that 1-based cell position), `occurrence` (1-based, default 1) and
    `group` (which capture group holds the value, default 1). With no group in the
    pattern the whole match is the value.
    """
    import re
    if isinstance(spec, str):
        spec = {"pattern": spec}
    pattern = re.compile(spec["pattern"], re.MULTILINE)
    cell = spec.get("cell")
    occurrence = int(spec.get("occurrence", 1))
    group = int(spec.get("group", 1))
    seen = 0
    for pos, text in outputs:
        if cell is not None and pos != cell:
            continue
        for m in pattern.finditer(text):
            seen += 1
            if seen == occurrence:
                value = m.group(group) if m.groups() else m.group(0)
                return value.replace(",", "").strip(), "printed in cell " + str(pos)
    where = "cell " + str(cell) if cell is not None else "any cell"
    return None, "pattern not found in " + where + ": " + spec["pattern"]


def values_match(measured, expected, nd, compare="eq", tolerance=None):
    if isinstance(expected, str):
        return str(measured).strip() == expected.strip()
    m = to_number(measured)
    e = to_number(expected)
    if m is None or e is None:
        return False
    if tolerance is not None and compare == "eq":
        return abs(m - e) <= float(tolerance) + 1e-9
    if compare == "lt":
        return m < e
    if compare == "le":
        return m <= e
    if compare == "gt":
        return m > e
    if compare == "ge":
        return m >= e
    if round(m, nd) == round(e, nd):
        return True
    return abs(m - e) <= 0.5 * 10 ** (-nd) + 1e-9


def within_band(measured, expected, band):
    if not band:
        return False
    m = to_number(measured)
    e = to_number(expected)
    if m is None or e is None:
        return False
    diff = m - e
    direction = band.get("direction", "any")
    if direction == "up" and diff < 0:
        return False
    if direction == "down" and diff > 0:
        return False
    if "points" in band:
        return abs(diff) <= band["points"]
    if "rel" in band:
        return abs(diff) <= band["rel"] * max(abs(e), 1e-12)
    if "abs" in band:
        return abs(diff) <= band["abs"]
    if "direction" in band:
        return True
    return False


def measure_numbers(manifest, project_dir, source_status, policies, notebook_error, log, notebook_path=None):
    import duckdb

    outputs = None
    outputs_error = None

    def printed_outputs():
        nonlocal outputs, outputs_error
        if outputs is None and outputs_error is None:
            try:
                outputs = notebook_output_text(notebook_path)
            except Exception as exc:
                outputs_error = "could not read the notebook outputs: " + str(exc)[:200]
        return outputs

    db_path = project_dir / manifest["database"]
    con = None
    open_error = None
    if db_path.exists():
        try:
            con = duckdb.connect(str(db_path), read_only=True)
            con.execute("SET file_search_path = '" + project_dir.as_posix() + "'")
        except Exception as exc:
            open_error = str(exc)
    else:
        open_error = "database file not found: " + str(db_path)

    sources_by_id = {s["id"]: s for s in manifest.get("sources", [])}
    all_source_ids = list(sources_by_id)
    rows = []
    for n in manifest.get("numbers", []):
        row = {
            "id": n["id"],
            "quote": n.get("quote", ""),
            "where": n.get("where", []),
            "kind": n.get("kind", "stat"),
            "expected": n.get("expected"),
            "measured": None,
            "status": None,
            "reason": "",
            "note": str(n.get("note", "")).strip(),
        }
        src_ids = n.get("sources", all_source_ids)
        statuses = [source_status.get(s, {}).get("status", "missing") for s in src_ids]
        any_changed = any(s == "changed" for s in statuses)
        any_missing = any(s == "missing" for s in statuses)

        declared = n.get("not_reproducible")
        if declared is not None and "query" not in n and "print_match" not in n:
            row["status"] = "not_reproducible"
            row["reason"] = str(declared)
            rows.append(row)
            continue

        def finish(row):
            # a figure declared not reproducible can still carry a query, so the report
            # shows what this run gave beside what the memo prints; the status stays declared
            if declared is not None:
                seen = fmt(row["measured"], n.get("round", decimals_of(n.get("expected")))) if row["measured"] is not None else "no value"
                row["status"] = "not_reproducible"
                row["reason"] = str(declared).rstrip(".") + ". This run: " + seen + "."
            rows.append(row)

        nd = n.get("round", decimals_of(n.get("expected")))
        compare = n.get("compare", "eq")

        if "print_match" in n:
            outs = printed_outputs()
            if outs is None:
                row["status"] = "not_run"
                row["reason"] = outputs_error or "no notebook outputs"
                finish(row)
                continue
            measured, detail = match_printed(outs, n["print_match"])
            if measured is None:
                if notebook_error is not None or any_changed or any_missing:
                    row["status"] = "not_run"
                    row["reason"] = detail + ("" if notebook_error is None else
                                              " (the notebook stopped at cell " + str(notebook_error["position"]) + ")")
                else:
                    row["status"] = "failed"
                    row["reason"] = "on unchanged bytes, " + detail
                finish(row)
                continue
            if not isinstance(n.get("expected"), str):
                num = to_number(measured)
                measured = measured if num is None else num
            row["reason"] = detail
        else:
            if con is None:
                row["status"] = "not_run"
                row["reason"] = open_error or "no database"
                finish(row)
                continue
            try:
                cur = con.execute(n["query"])
                fetched = cur.fetchone()
                measured = None if fetched is None else fetched[0]
            except Exception as exc:
                msg = str(exc).split("\n")[0][:300]
                if notebook_error is not None or any_changed or any_missing:
                    row["status"] = "not_run"
                    why = "query failed: " + msg
                    if notebook_error is not None:
                        why += " (the notebook stopped at cell " + str(notebook_error["position"]) + ")"
                    row["reason"] = why
                else:
                    row["status"] = "failed"
                    row["reason"] = "query failed on unchanged bytes: " + msg
                finish(row)
                continue

        if isinstance(measured, Decimal):
            measured = float(measured)
        if hasattr(measured, "item"):
            try:
                measured = measured.item()
            except Exception:
                pass
        if "scale" in n and to_number(measured) is not None and not isinstance(n.get("expected"), str):
            measured = to_number(measured) * float(n["scale"])
        row["measured"] = measured if isinstance(measured, (int, float, str)) or measured is None else str(measured)

        if measured is None:
            row["status"] = "not_run" if (notebook_error is not None or any_changed) else "failed"
            row["reason"] = "the query returned NULL"
            finish(row)
            continue

        if values_match(measured, n.get("expected"), nd, compare, n.get("tolerance")):
            row["status"] = "reproduced"
            if any_changed:
                row["reason"] = "unchanged although a source moved"
        elif any_changed:
            bands = []
            for s in src_ids:
                if source_status.get(s, {}).get("status") != "changed":
                    continue
                policy = policies.get(sources_by_id.get(s, {}).get("policy", ""), {})
                bands.append(policy.get("bands", {}).get(row["kind"]))
            if any(within_band(measured, n.get("expected"), b) for b in bands):
                row["status"] = "drift"
                row["reason"] = "source changed; inside the band for kind " + row["kind"]
            else:
                row["status"] = "drift_outside_band"
                row["reason"] = "source changed; outside the band for kind " + row["kind"]
        elif any_missing:
            row["status"] = "not_run"
            row["reason"] = "source fingerprint could not be read, so the difference cannot be classified"
        else:
            row["status"] = "failed"
            row["reason"] = "same bytes, different value"
        finish(row)
    if con is not None:
        con.close()
    return rows


# %% reports
# ----------------------------------------------------------------------------

def count_statuses(rows):
    counts = {s: 0 for s in STATUS_ORDER}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return counts


def verdict_line(counts, run_date):
    total = sum(counts.values())
    parts = [str(counts["reproduced"]) + " of " + str(total) + " listed figures reproduced on " + run_date]
    if counts["drift"]:
        parts.append(str(counts["drift"]) + " drifted inside the band")
    if counts["drift_outside_band"]:
        parts.append(str(counts["drift_outside_band"]) + " drifted outside the band")
    if counts["failed"]:
        parts.append(str(counts["failed"]) + " FAILED to reproduce")
    if counts["not_run"]:
        parts.append(str(counts["not_run"]) + " not run")
    if counts["not_reproducible"]:
        parts.append(str(counts["not_reproducible"]) + " not reproducible in CI by design")
    return "; ".join(parts) + "."


def write_project_report(result, out_dir):
    proj_dir = out_dir / result["project"]
    proj_dir.mkdir(parents=True, exist_ok=True)
    md = proj_dir / (result["run_date"] + ".md")
    lines = []
    lines.append("# " + result["label"] + ": reproducibility report, " + result["run_date"])
    lines.append("")
    lines.append("Run at " + result["run_at_utc"] + " UTC on " + result["environment"]["platform"] +
                 ", Python " + result["environment"]["python"] + ", DuckDB " + result["environment"]["duckdb"] +
                 (", commit " + result["environment"]["git_sha"][:10] if result["environment"].get("git_sha") else "") +
                 (", GitHub Actions run " + result["environment"]["github_run_id"] if result["environment"].get("github_run_id") else ", local run") + ".")
    lines.append("")
    lines.append("**Verdict.** " + result["verdict"])
    if result.get("job_failed"):
        lines.append("")
        lines.append("**This run counts as a failure.** " + result.get("failure_reason", ""))
    lines.append("")
    lines.append("## Sources")
    lines.append("")
    lines.append("| Source | Refresh | Committed measured on | This run | Status |")
    lines.append("|---|---|---|---|---|")
    for s in result["sources"]:
        lines.append("| " + s["id"] + " | " + s.get("refresh", "") + " | " + result["measured_on"] + " | " +
                     s["detail"] + " | " + s["status"] + " |")
    lines.append("")
    lines.append("## Notebook")
    lines.append("")
    nbres = result["notebook"]
    if nbres.get("skipped"):
        lines.append("Not executed on this run (`--no-execute`); the figures were measured against the DuckDB file already in the folder.")
    elif nbres.get("unavailable"):
        lines.append("Not executed: " + nbres["unavailable"])
    else:
        lines.append(result["notebook_name"] + ": " + str(nbres["code_cells"]) + " code cells, " + str(nbres["executed"]) +
                     " ran, " + format(nbres["elapsed_s"] / 60, ".1f") + " minutes.")
        if nbres.get("error"):
            e = nbres["error"]
            lines.append("")
            lines.append("**Stopped at cell " + str(e["position"]) + "** (\"" + e["opening"] + "\") with " + e["ename"] + ":")
            lines.append("")
            lines.append("```")
            lines.append(e["evalue"])
            lines.append("```")
            if result.get("blocked_rule"):
                lines.append("")
                lines.append("That is the notebook's own rule " + result["blocked_rule"] +
                             " stopping the build, which is what it is written to do when the source changes shape.")
        if nbres.get("retried_after"):
            first = nbres["retried_after"]
            lines.append("")
            lines.append("The first attempt stopped at cell " + str(first["position"]) + " with " + first["ename"] +
                         ", a network error rather than the notebook's own, and the notebook was executed a second time after 60 seconds.")
        slow = sorted(nbres.get("cell_times", []), key=lambda c: -c["seconds"])[:5]
        if slow:
            lines.append("")
            lines.append("Slowest cells: " + "; ".join("cell " + str(c["position"]) + " " + format(c["seconds"], ".0f") + "s" for c in slow) + ".")
    if result.get("has_print_matches"):
        lines.append("")
        lines.append("Figures matched against printed output were read from " + result.get("printed_from", "the notebook") + ".")
    lines.append("")
    lines.append("## Figures")
    lines.append("")
    lines.append("| # | Quoted as | Where | Expected | Measured | Status | Note |")
    lines.append("|---:|---|---|---:|---:|---|---|")
    for i, r in enumerate(result["numbers"], 1):
        nd = r.get("round")
        exp = fmt(r["expected"], nd) if r["expected"] is not None else ""
        mea = fmt(r["measured"], nd) if r["measured"] is not None else ""
        note = r["reason"]
        if r.get("note"):
            note = (note + " " if note else "") + r["note"]
        lines.append("| " + str(i) + " | " + r["quote"].replace("|", "/") + " | " + ", ".join(r["where"]) + " | " +
                     exp + " | " + mea + " | " + STATUS_LABEL[r["status"]] + " | " + note.replace("|", "/") + " |")
    lines.append("")
    lines.append("## Working tree after the run")
    lines.append("")
    if result.get("working_tree") is None:
        lines.append("Not a git checkout, so no diff was taken.")
    elif not result["working_tree"]:
        lines.append("No committed file changed.")
    else:
        lines.append("Files the run rewrote, as `git status --porcelain` lists them. Charts and the pull manifest are expected here on every run; a crosswalk or a memo is not.")
        lines.append("")
        lines.append("```")
        lines.extend(result["working_tree"])
        lines.append("```")
    lines.append("")
    md.write_text("\n".join(lines), encoding="utf-8")
    (proj_dir / "latest.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    (proj_dir / (result["run_date"] + ".json")).write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    return md


# %% one project
# ----------------------------------------------------------------------------

def validate_manifest(manifest, policies):
    """Return the problems with a manifest, as strings; an empty list means it is usable.

    A typo in a kind or a policy name would otherwise pass silently as "no band", and a
    duplicated id would make the report ambiguous. Checked before any notebook runs and
    by `--check`, which is cheap enough for a pre-commit habit.
    """
    problems = []
    for key in ("project", "notebook", "database", "sources", "numbers"):
        if key not in manifest:
            problems.append("missing top-level key " + key)
    if problems:
        return problems
    source_ids = []
    for s in manifest["sources"]:
        sid = s.get("id", "(no id)")
        source_ids.append(sid)
        if s.get("policy") not in policies:
            problems.append("source " + sid + " names an unknown policy " + str(s.get("policy")))
        fp = s.get("fingerprint", {})
        if fp.get("kind") not in FINGERPRINT_KINDS:
            problems.append("source " + sid + " has an unknown fingerprint kind " + str(fp.get("kind")))
        if fp.get("kind") == "manifest_json" and "path" not in fp:
            problems.append("source " + sid + " fingerprint needs a path")
        if fp.get("kind") in ("file_sizes", "file_hashes") and not fp.get("files"):
            problems.append("source " + sid + " fingerprint needs a files list")
        if s.get("kind") == "kaggle" and not (s.get("dataset") and s.get("folder")):
            problems.append("source " + sid + " is a kaggle source without dataset or folder")
    if len(set(source_ids)) != len(source_ids):
        problems.append("duplicate source ids")
    seen = set()
    for i, n in enumerate(manifest["numbers"], 1):
        nid = n.get("id")
        if not nid:
            problems.append("number " + str(i) + " has no id")
            continue
        if nid in seen:
            problems.append("duplicate id " + nid)
        seen.add(nid)
        if not n.get("quote"):
            problems.append(nid + ": no quote")
        if not n.get("where"):
            problems.append(nid + ": no where")
        if n.get("kind", "stat") not in KINDS:
            problems.append(nid + ": unknown kind " + str(n.get("kind")))
        has_query = "query" in n or "print_match" in n
        if not has_query and "not_reproducible" not in n:
            problems.append(nid + ": needs a query, a print_match or a not_reproducible reason")
        if has_query and "expected" not in n:
            problems.append(nid + ": has a query but no expected value")
        if n.get("compare", "eq") not in COMPARES:
            problems.append(nid + ": unknown compare " + str(n.get("compare")))
        for s in n.get("sources", []):
            if s not in source_ids:
                problems.append(nid + ": names an unknown source " + str(s))
        pm = n.get("print_match")
        if isinstance(pm, dict) and "pattern" not in pm:
            problems.append(nid + ": print_match needs a pattern")
        if isinstance(pm, (str, dict)):
            import re
            try:
                re.compile(pm if isinstance(pm, str) else pm["pattern"])
            except (re.error, KeyError) as exc:
                problems.append(nid + ": print_match pattern does not compile (" + str(exc) + ")")
    return problems


def check_all(log):
    """Validate every manifest and the policy without running anything. Returns the problem count."""
    policy_doc = load_yaml(HERE / "policy.yml")
    policies = policy_doc.get("policies", {})
    total = 0
    for name, pol in policies.items():
        for kind, band in (pol.get("bands") or {}).items():
            if kind not in KINDS:
                log("policy " + name + ": unknown kind " + kind)
                total += 1
            for key in band or {}:
                if key not in ("direction", "points", "rel", "abs"):
                    log("policy " + name + ", kind " + kind + ": unknown band key " + key)
                    total += 1
    for path in sorted((HERE / "manifests").glob("*.yml")):
        manifest = load_yaml(path)
        problems = validate_manifest(manifest, policies)
        for p in problems:
            log(path.name + ": " + p)
        total += len(problems)
        fp = fingerprints_path(path.stem)
        log(path.name + ": " + str(len(manifest.get("numbers", []))) + " figures, " + str(len(manifest.get("sources", []))) +
            " sources, " + ("fingerprints recorded" if fp.exists() else "NO FINGERPRINTS RECORDED") +
            (", " + str(len(problems)) + " problems" if problems else ", valid"))
        if not fp.exists():
            total += 1
    return total


def run_project(project, root, out_dir, execute=True, run_date=None, log=None):
    manifest = load_yaml(HERE / "manifests" / (project + ".yml"))
    policy_doc = load_yaml(HERE / "policy.yml")
    policies = policy_doc.get("policies", {})
    project_dir = root / project
    run_date = run_date or utc_today()
    log = log or Log(out_dir / project / (run_date + ".log"))
    problems = validate_manifest(manifest, policies)
    if problems:
        raise ValueError("manifest " + project + " is not valid: " + "; ".join(problems))

    import duckdb
    env = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "duckdb": duckdb.__version__,
        "git_sha": git(root, "rev-parse", "HEAD"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
    }
    result = {
        "project": project,
        "label": manifest.get("label", project),
        "notebook_name": manifest["notebook"],
        "measured_on": str(manifest.get("measured_on", "")),
        "run_date": run_date,
        "run_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "environment": env,
        "sources": [],
        "notebook": {},
        "numbers": [],
    }
    log("project " + project + " in " + str(project_dir))

    # 1. sources the notebook cannot fetch for itself
    unavailable = None
    for s in manifest.get("sources", []):
        if s.get("kind") == "kaggle":
            try:
                ensure_kaggle_source(s, project_dir, log)
            except SourceUnavailable as exc:
                unavailable = str(exc)
                log("source " + s["id"] + ": " + unavailable)

    # 2. execute, with one more attempt when the network rather than the notebook stopped it
    notebook_error = None
    executed_copy = out_dir / project / (run_date + ".executed.ipynb")
    if not execute:
        result["notebook"] = {"skipped": True}
        log("notebook execution skipped")
    elif unavailable is not None:
        result["notebook"] = {"unavailable": unavailable}
    else:
        first_error = None
        for attempt in (1, 2):
            log("executing " + manifest["notebook"] + ("" if attempt == 1 else ", second attempt"))
            try:
                nbres = execute_notebook(project_dir, manifest["notebook"], log, out_path=executed_copy,
                                         cell_timeout=int(manifest.get("cell_timeout_s", 7200)))
            except Exception as exc:
                nbres = {"cells": 0, "code_cells": 0, "executed": 0, "elapsed_s": 0.0, "cell_times": [],
                         "error": {"position": 0, "opening": "", "ename": type(exc).__name__,
                                   "evalue": str(exc)[:2000], "elapsed_s": 0}}
                log("notebook runner error: " + str(exc)[:500])
            if nbres.get("error") is None or attempt == 2 or not is_transient(nbres["error"]):
                break
            first_error = nbres["error"]
            log("stopped with " + first_error["ename"] + " at cell " + str(first_error["position"]) +
                ", a network error rather than the notebook's own; waiting 60 s and executing once more")
            time.sleep(60)
        nbres["retried_after"] = first_error
        result["notebook"] = nbres
        notebook_error = nbres.get("error")
        log("notebook finished: " + str(nbres["executed"]) + " of " + str(nbres["code_cells"]) + " code cells in " +
            str(nbres["elapsed_s"]) + "s" + ("" if notebook_error is None else ", stopped with " + notebook_error["ename"]))

    # 3. fingerprint
    source_status = {}
    any_changed = False
    committed = committed_fingerprints(project, manifest)
    for s in manifest.get("sources", []):
        entry = {"id": s["id"], "refresh": s.get("refresh", ""), "policy": s.get("policy", "")}
        try:
            observed = fingerprint_source(s, project_dir)
            status, detail = compare_fingerprint(committed.get(s["id"], {}), observed)
            entry["observed"] = observed
        except (SourceUnavailable, ValueError, OSError, json.JSONDecodeError) as exc:
            status, detail = "missing", str(exc)[:300]
        expected_static = not policies.get(s.get("policy", ""), {}).get("change_expected", True)
        if status == "changed" and expected_static:
            detail += " (this source is not expected to change)"
        entry["status"] = status
        entry["detail"] = detail
        source_status[s["id"]] = entry
        result["sources"].append(entry)
        any_changed = any_changed or status == "changed"
        log("source " + s["id"] + ": " + status + ", " + detail)

    # 4. measure and classify; printed figures come from this run's executed copy when there is one
    if execute and executed_copy.exists():
        notebook_path, printed_from = executed_copy, "the executed copy of this run"
    elif execute:
        notebook_path, printed_from = project_dir / manifest["notebook"], "the committed notebook, because the executed copy was not written"
    else:
        notebook_path, printed_from = project_dir / manifest["notebook"], "the committed notebook's stored outputs (--no-execute)"
    result["printed_from"] = printed_from
    result["has_print_matches"] = any("print_match" in n for n in manifest.get("numbers", []))
    rows = measure_numbers(manifest, project_dir, source_status, policies, notebook_error, log,
                           notebook_path=notebook_path)
    for r, n in zip(rows, manifest.get("numbers", [])):
        r["round"] = n.get("round", decimals_of(n.get("expected")))
    result["numbers"] = rows
    counts = count_statuses(rows)
    result["counts"] = counts
    result["verdict"] = verdict_line(counts, run_date)

    blocked_rule = None
    if notebook_error is not None and notebook_error.get("ename") == "AssertionError":
        first = notebook_error.get("evalue", "").split()
        if first and first[0].rstrip(":").isalnum() and any(ch.isdigit() for ch in first[0]):
            blocked_rule = first[0].rstrip(":")
    result["blocked_rule"] = blocked_rule
    result["any_source_changed"] = any_changed

    # a stop is excused only by a source whose change the contract expects; a source that
    # is not supposed to change, or that could not be read after the stop, excuses nothing
    expected_change = any(
        source_status[s["id"]]["status"] == "changed" and policies.get(s.get("policy", ""), {}).get("change_expected", True)
        for s in manifest.get("sources", [])
    )
    result["expected_change"] = expected_change
    job_failed = counts["failed"] > 0
    failure_reason = ""
    if counts["failed"]:
        failure_reason = str(counts["failed"]) + " figure(s) differ on unchanged source bytes."
    if notebook_error is not None and not expected_change and result["notebook"].get("unavailable") is None:
        job_failed = True
        failure_reason += (" The notebook stopped, and no source changed in a way the contract expects, so the stop is the notebook's own."
                           if any_changed else " The notebook stopped on unchanged source bytes.")
    result["job_failed"] = job_failed
    result["failure_reason"] = failure_reason.strip()

    # 5. what the run rewrote
    porcelain = git(root, "status", "--porcelain", "--", project)
    result["working_tree"] = None if porcelain is None else [ln for ln in porcelain.splitlines() if ln.strip()]

    md = write_project_report(result, out_dir)
    log("report written: " + str(md))
    log(result["verdict"])
    return result


# %% aggregate across projects
# ----------------------------------------------------------------------------

def aggregate(out_dir, run_date=None):
    policy_doc = load_yaml(HERE / "policy.yml")
    run_date = run_date or utc_today()
    results = []
    for p in sorted(out_dir.iterdir()):
        latest = p / "latest.json"
        if p.is_dir() and latest.exists():
            results.append(json.loads(latest.read_text(encoding="utf-8")))
    totals = {s: 0 for s in STATUS_ORDER}
    for r in results:
        for s in STATUS_ORDER:
            totals[s] += r.get("counts", {}).get(s, 0)
    listed = sum(totals.values())
    any_failed = any(r.get("job_failed") for r in results)
    any_missing = any(s.get("status") == "missing" for r in results for s in r.get("sources", []))
    any_warn = (totals["drift_outside_band"] > 0 or totals["not_run"] > 0 or any_missing
                or any(r.get("blocked_rule") for r in results))
    color = "red" if any_failed else ("yellow" if any_warn else "brightgreen")
    latest_date = max((r["run_date"] for r in results), default=run_date)
    message = str(totals["reproduced"]) + " of " + str(listed) + " on " + latest_date
    if totals["drift"] + totals["drift_outside_band"]:
        message += ", " + str(totals["drift"] + totals["drift_outside_band"]) + " drifted"
    if totals["failed"]:
        message += ", " + str(totals["failed"]) + " failed"
    if not results:
        message, color = "no run yet", "lightgrey"
    badge = {"schemaVersion": 1, "label": "numbers reproduced", "message": message, "color": color}
    (out_dir / "badge.json").write_text(json.dumps(badge, indent=2), encoding="utf-8")

    lines = ["# Reproducibility summary, " + latest_date, ""]
    lines.append("Every figure quoted in a shipped project's README and findings memo, re-measured on a fresh pull "
                 "of its sources by the project's own notebook. Same bytes must give the same number; different bytes "
                 "are publisher drift and are read under the contract in `ci/policy.yml`.")
    lines.append("")
    lines.append("| Project | Listed | Reproduced | Drift | Outside band | Failed | Not run | Not reproducible | Sources | Report |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---|---|")
    for r in results:
        c = r.get("counts", {})
        src = "; ".join(s["id"] + " " + s["status"] for s in r.get("sources", []))
        lines.append("| " + r["label"] + " | " + str(sum(c.values())) + " | " + str(c.get("reproduced", 0)) + " | " +
                     str(c.get("drift", 0)) + " | " + str(c.get("drift_outside_band", 0)) + " | " + str(c.get("failed", 0)) +
                     " | " + str(c.get("not_run", 0)) + " | " + str(c.get("not_reproducible", 0)) + " | " + src +
                     " | [" + r["run_date"] + "](" + r["project"] + "/" + r["run_date"] + ".md) |")
    for ex in policy_doc.get("excluded", []):
        lines.append("| " + ex["project"] + " | excluded | | | | | | | " + ex["reason"] + " | |")
    lines.append("")
    lines.append("Badge: " + message + " (" + color + ").")
    for r in results:
        if r.get("job_failed"):
            lines.append("")
            lines.append("**" + r["label"] + " failed.** " + r.get("failure_reason", ""))
        if r.get("blocked_rule"):
            lines.append("")
            lines.append("**" + r["label"] + " was stopped by its own rule " + r["blocked_rule"] + ".** " +
                         (r["notebook"].get("error", {}) or {}).get("evalue", "")[:400])
    summary = "\n".join(lines) + "\n"
    (out_dir / "summary.md").write_text(summary, encoding="utf-8")
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as fh:
            fh.write(summary)
    print(summary)
    return badge, any_failed


# %% entry point
# ----------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", action="append", help="project folder name; repeatable")
    ap.add_argument("--all", action="store_true", help="every project with a manifest")
    ap.add_argument("--aggregate", action="store_true", help="build summary.md and badge.json from the reports present")
    ap.add_argument("--no-execute", action="store_true", help="measure against the existing DuckDB file, skip the notebook")
    ap.add_argument("--record-fingerprints", action="store_true",
                    help="save the source fingerprints as they stand in the project folder, after a hand run")
    ap.add_argument("--check", action="store_true",
                    help="validate every manifest and the policy without running anything; exit 1 on a problem")
    ap.add_argument("--root", default=str(DEFAULT_ROOT), help="repository root holding the project folders")
    ap.add_argument("--out", default=None, help="report folder (default <root>/ci/reports)")
    ap.add_argument("--date", default=None, help="report date, YYYY-MM-DD (default today)")
    args = ap.parse_args(argv)

    if args.check:
        problems = check_all(Log())
        print("manifests and policy: " + ("no problems" if problems == 0 else str(problems) + " problem(s)"))
        return 1 if problems else 0

    root = Path(args.root).resolve()
    out_dir = Path(args.out).resolve() if args.out else root / "ci" / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)

    projects = list(args.project or [])
    if args.all:
        projects = sorted(p.stem for p in (HERE / "manifests").glob("*.yml"))
    exit_code = 0
    if args.record_fingerprints:
        log = Log()
        for project in projects:
            record_fingerprints(project, root, log)
        return 0
    for project in projects:
        try:
            result = run_project(project, root, out_dir, execute=not args.no_execute, run_date=args.date)
            if result.get("job_failed"):
                exit_code = 1
        except Exception:
            traceback.print_exc()
            exit_code = 1
    if args.aggregate:
        _, any_failed = aggregate(out_dir, run_date=args.date)
        if any_failed:
            exit_code = 1
    if not projects and not args.aggregate:
        ap.print_help()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
