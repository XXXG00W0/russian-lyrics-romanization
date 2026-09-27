#!/usr/bin/env python3
"""Fetch and cache the offline data the romanization skill needs.

Builds <cache>/stress.db containing:
  accents(form, accented)        ~3.2M word forms -> stress marked with '+'
  omographs(form, variant)       ~79k forms that have two or more readings
  gloss(lemma, pos, en, accented)  English glosses (best effort, optional)

Data is downloaded on first run and never redistributed with the skill:
  ruaccent/accentuator (HuggingFace)   stress dictionaries
  Badestrand/russian-dictionary (GitHub, CC-BY-SA-4.0)  OpenRussian glosses

Usage:
  python fetch_data.py                 # build if missing
  python fetch_data.py --force         # rebuild
  python fetch_data.py --skip-glosses  # stress only, ~21 MB instead of ~31 MB
"""

import argparse
import gzip
import json
import os
import re
import sqlite3
import sys
import urllib.error
import urllib.request

# a Windows pipe defaults to the ANSI code page, which mangles non-ASCII output
for _stream in (sys.stdin, sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

HF_BASE = "https://huggingface.co/ruaccent/accentuator/resolve/main/dictionary/"
CSV_BASE = "https://raw.githubusercontent.com/Badestrand/russian-dictionary/master/"
UA = "ru-lyrics-romanization-skill/1.0 (+offline dictionary cache)"
ENTRY_RE = re.compile(r'^("(?:[^"\\]|\\.)*")\s*:\s*(.*)$')


def default_cache_dir():
    return os.path.join(os.path.expanduser("~"), ".cache", "ru-lyrics")


def detect_proxy():
    """Return a proxy URL, or None.

    Order: HTTPS_PROXY/HTTP_PROXY env vars, then the Windows system proxy
    (HKCU\\...\\Internet Settings). The system proxy matters because several
    upstream hosts (huggingface.co, raw.githubusercontent.com) are unreachable
    without it on some networks, and a subprocess does not inherit it.
    """
    for var in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"):
        val = os.environ.get(var)
        if val:
            return val if "://" in val else "http://" + val
    if sys.platform == "win32":
        try:
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
            )
            if winreg.QueryValueEx(key, "ProxyEnable")[0]:
                server = winreg.QueryValueEx(key, "ProxyServer")[0]
                if server and "=" not in server:
                    return "http://" + server
        except Exception:
            pass
    return None


def open_stream(url, proxy, timeout=600):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    handlers = [urllib.request.ProxyHandler({"http": proxy, "https": proxy})] if proxy else []
    opener = urllib.request.build_opener(*handlers)
    return opener.open(req, timeout=timeout)


def iter_json_entries(text_stream):
    """Stream (key, value) pairs out of a pretty-printed JSON object.

    Two shapes occur in the upstream files, and both are handled without
    loading the whole document (the accents file is ~175 MB decompressed):
        "form": "acc+ented",
        "form": [
          "read+ing1",
          "read+ing2"
        ],
    """
    key = None
    pending = None
    for raw_line in text_stream:
        line = raw_line.strip()
        if not line or line in "{}":
            continue
        if pending is not None:
            if line.startswith("]"):
                yield key, pending
                key, pending = None, None
                continue
            pending.append(json.loads(line.rstrip(",")))
            continue
        match = ENTRY_RE.match(line)
        if not match:
            continue
        k = json.loads(match.group(1))
        value = match.group(2).rstrip(",").strip()
        if value == "[":
            key, pending = k, []
        else:
            yield k, json.loads(value)


def download_jsongz(url, proxy, rows, batch=50000):
    """Stream a .gz JSON file and hand each (key, value) to rows()."""
    count = 0
    with open_stream(url, proxy) as response:
        with gzip.open(response, "rt", encoding="utf-8") as fh:
            batch_rows = []
            for key, value in iter_json_entries(fh):
                batch_rows.append((key, value))
                count += 1
                if len(batch_rows) >= batch:
                    rows(batch_rows)
                    batch_rows = []
            if batch_rows:
                rows(batch_rows)
    return count


def build_stress_tables(conn, proxy):
    print("[1/3] accents.json.gz ...", flush=True)
    buffer = []

    def write_accents(batch):
        conn.executemany("INSERT OR REPLACE INTO accents(form, accented) VALUES (?, ?)",
                         [(k, v) for k, v in batch if isinstance(v, str)])

    total = download_jsongz(HF_BASE + "accents.json.gz", proxy, write_accents)
    conn.commit()
    print("      %d word forms" % total)

    print("[2/3] omographs.json.gz ...", flush=True)

    def write_omographs(batch):
        flat = []
        for key, value in batch:
            if isinstance(value, list):
                for variant in value:
                    flat.append((key, variant))
        conn.executemany("INSERT INTO omographs(form, variant) VALUES (?, ?)", flat)

    total = download_jsongz(HF_BASE + "omographs.json.gz", proxy, write_omographs)
    conn.commit()
    multi = conn.execute("SELECT COUNT(DISTINCT form) FROM omographs").fetchone()[0]
    print("      %d forms in the file, %d ambiguous forms" % (total, multi))
    return None


def build_gloss_table(conn, proxy):
    print("[3/3] OpenRussian glosses (CC-BY-SA-4.0) ...", flush=True)
    import csv

    files = [("nouns.csv", "noun"), ("adjectives.csv", "adjective"),
             ("verbs.csv", "verb"), ("others.csv", "other")]
    total = 0
    for name, pos in files:
        try:
            with open_stream(CSV_BASE + name, proxy) as response:
                import io
                import itertools

                text_stream = io.TextIOWrapper(response, encoding="utf-8-sig", newline="")
                header = text_stream.readline()
                # the files are named .csv but are tab separated
                delimiter = "\t" if "\t" in header else ","
                reader = csv.DictReader(itertools.chain([header], text_stream), delimiter=delimiter)
                if not reader.fieldnames or "bare" not in reader.fieldnames:
                    print("      %-16s header not understood: %r" % (name, header[:80]))
                    continue
                batch = []
                for row in reader:
                    bare = (row.get("bare") or "").strip()
                    if not bare:
                        continue
                    en = (row.get("translations_en") or row.get("translations") or "").strip()
                    batch.append((bare, pos, en[:300], (row.get("accented") or "").strip()))
                    total += 1
                    if len(batch) >= 20000:
                        conn.executemany(
                            "INSERT INTO gloss(lemma, pos, en, accented) VALUES (?, ?, ?, ?)", batch)
                        batch = []
                if batch:
                    conn.executemany(
                        "INSERT INTO gloss(lemma, pos, en, accented) VALUES (?, ?, ?, ?)", batch)
                conn.commit()
                print("      %-16s %6d rows" % (name, total))
        except Exception as exc:  # glosses are a nicety, never fatal
            print("      %-16s skipped (%s)" % (name, exc))
    return total


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cache-dir", default=None)
    parser.add_argument("--force", action="store_true", help="rebuild even if the cache exists")
    parser.add_argument("--skip-glosses", action="store_true", help="stress data only")
    parser.add_argument("--only-glosses", action="store_true",
                        help="add or refresh just the English gloss table in an existing cache")
    parser.add_argument("--no-proxy", action="store_true", help="ignore proxy settings")
    args = parser.parse_args()

    cache_dir = args.cache_dir or default_cache_dir()
    db_path = os.path.join(cache_dir, "stress.db")
    os.makedirs(cache_dir, exist_ok=True)

    proxy = None if args.no_proxy else detect_proxy()

    if args.only_glosses:
        if not os.path.exists(db_path):
            print("no cache at %s - run without --only-glosses first" % db_path)
            return 1
        if proxy:
            print("using proxy %s" % proxy)
        conn = sqlite3.connect(db_path)
        try:
            conn.execute("CREATE TABLE IF NOT EXISTS gloss(lemma TEXT, pos TEXT, en TEXT, accented TEXT)")
            conn.execute("DELETE FROM gloss")
            total = build_gloss_table(conn, proxy)
            conn.execute("DROP INDEX IF EXISTS idx_gloss")
            conn.execute("CREATE INDEX idx_gloss ON gloss(lemma)")
            conn.commit()
        finally:
            conn.close()
        print("gloss rows: %d" % total)
        return 0 if total else 1

    if os.path.exists(db_path) and not args.force:
        conn = sqlite3.connect(db_path)
        forms = conn.execute("SELECT COUNT(*) FROM accents").fetchone()[0]
        ambig = conn.execute("SELECT COUNT(DISTINCT form) FROM omographs").fetchone()[0]
        print("cache already present: %s" % db_path)
        print("  %d word forms, %d ambiguous forms" % (forms, ambig))
        print("  rebuild with --force")
        return 0

    if proxy:
        print("using proxy %s" % proxy)
    else:
        print("no proxy configured (set HTTPS_PROXY if downloads fail)")

    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA journal_mode = OFF")
        conn.execute("PRAGMA synchronous = OFF")
        conn.execute("CREATE TABLE accents(form TEXT PRIMARY KEY, accented TEXT)")
        conn.execute("CREATE TABLE omographs(form TEXT, variant TEXT)")
        conn.execute("CREATE TABLE gloss(lemma TEXT, pos TEXT, en TEXT, accented TEXT)")

        build_stress_tables(conn, proxy)
        if not args.skip_glosses:
            build_gloss_table(conn, proxy)

        conn.execute("CREATE INDEX idx_omographs ON omographs(form)")
        conn.execute("CREATE INDEX idx_gloss ON gloss(lemma)")
        conn.commit()

        forms = conn.execute("SELECT COUNT(*) FROM accents").fetchone()[0]
        ambig = conn.execute("SELECT COUNT(DISTINCT form) FROM omographs").fetchone()[0]
        glosses = conn.execute("SELECT COUNT(*) FROM gloss").fetchone()[0]
    finally:
        conn.close()

    size_mb = os.path.getsize(db_path) / 1048576.0
    print("\nbuilt %s (%.1f MB)" % (db_path, size_mb))
    print("  accents   %8d forms" % forms)
    print("  omographs %8d ambiguous forms" % ambig)
    print("  gloss     %8d lemmas" % glosses)
    if forms < 2000000:
        print("\nWARNING: far fewer word forms than expected (~3.2M). The download was "
              "probably truncated; re-run with --force outside any file-write sandbox.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
