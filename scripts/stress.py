#!/usr/bin/env python3
"""Look up word stress from the offline dictionary and mark the lyrics.

Reads Cyrillic text and returns the same text with a combining acute (U+0301) after
every stressed vowel, plus a report: which words were resolved, which have two or
more possible readings (homographs - the caller must pick one from context), and
which are not in the dictionary at all.

The dictionary is built by scripts/fetch_data.py. It holds ~3.2M word forms
including inflected ones, so 'руку' is found directly instead of being reduced to
'рука' first.

Usage:
  python stress.py lyrics.txt                 # JSON report + marked text
  python stress.py lyrics.txt --text          # just the marked text
  python stress.py --lookup замок руку мою    # inspect single words
  python stress.py lyrics.txt --db other.db
"""

import argparse
import json
import os
import re
import sqlite3
import sys

# a Windows pipe defaults to the ANSI code page, which mangles Cyrillic the moment
# the output is redirected to a file
for _stream in (sys.stdin, sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

WORD_RE = re.compile(r"[А-Яа-яЁё\u0300\u0301]+(?:-[А-Яа-яЁё\u0300\u0301]+)*")
ACUTE = "\u0301"
GRAVE = "\u0300"
DEFAULT_DB = os.path.join(os.path.expanduser("~"), ".cache", "ru-lyrics", "stress.db")


def split_marks(word):
    """Separate a possibly pre-marked word into (plain, index_of_stressed_char)."""
    out = []
    index = None
    for char in word:
        if char in (ACUTE, GRAVE):
            index = len(out) - 1
        else:
            out.append(char)
    return "".join(out), index


def plus_to_acute(accented):
    """'рук+а' -> 'рука́'  (the '+' sits before the stressed vowel)."""
    index = accented.index("+")
    plain = accented.replace("+", "")
    if plain[index] == "ё":
        return plain  # ё is stressed by definition; an acute on top is just noise
    return plain[: index + 1] + ACUTE + plain[index + 1:]


def mark_only_vowel(form):
    """Mark the single vowel of a word that cannot be stressed any other way.

    Kept for callers that want the explicit position; stress.py itself leaves these
    words unmarked in the text.
    """
    for position, char in enumerate(form):
        if char.lower() in "аеёиоуыэюя":
            if char.lower() == "ё":
                return form
            return form[: position + 1] + ACUTE + form[position + 1:]
    return form  # no vowel at all (в, с, к): nothing to mark


def apostrophe_index(accented):
    """OpenRussian writes its mark after the vowel: 'рука'' -> 3."""
    if "'" not in accented:
        return None
    return accented.index("'") - 1


def connect(db_path):
    if not os.path.exists(db_path):
        raise SystemExit(
            "stress database not found at %s\n"
            "build it once with:  python %s/fetch_data.py"
            % (db_path, os.path.dirname(os.path.abspath(__file__)))
        )
    return sqlite3.connect(db_path)


def gloss_for(conn, lemma, stress_index):
    """The English gloss whose own stress position matches this reading."""
    if stress_index is None:
        return None
    for english, accented in conn.execute(
            "SELECT en, accented FROM gloss WHERE lemma = ?", (lemma.lower(),)).fetchall():
        if apostrophe_index(accented) == stress_index:
            return english
    return None


def all_glosses(conn, lemma):
    return sorted({row[0] for row in conn.execute(
        "SELECT en FROM gloss WHERE lemma = ?", (lemma.lower(),)).fetchall() if row[0]})


def lookup(conn, form):
    """Resolve one word form; returns a small dict describing what was found."""
    row = conn.execute("SELECT accented FROM accents WHERE form = ?", (form,)).fetchone()
    variants = [r[0] for r in conn.execute(
        "SELECT variant FROM omographs WHERE form = ?", (form,)).fetchall()]

    if not row and not variants:
        lowered = form.lower()
        if lowered != form:
            return lookup(conn, lowered)
        if "-" in form:
            parts = [lookup(conn, part) for part in form.split("-")]
            if all(part["status"] in ("ok", "implied") for part in parts):
                return {"status": "ok", "form": form, "accented":
                        "-".join(part["accented"] for part in parts)}
        if sum(1 for char in form if char.lower() in "аеёиоуыэюя") <= 1:
            # и, я, в, до, что ... the dictionary does not bother with them because
            # there is no choice to make. They are left unmarked: render.py infers
            # the stress for one-vowel words, and marking them would put an accent
            # on nearly every monosyllable in the song.
            return {"status": "implied", "form": form, "accented": form}
        return {"status": "unknown", "form": form}

    if len(variants) > 1:
        candidates = []
        for variant in variants:
            index = variant.index("+")
            accented = plus_to_acute(variant)
            candidates.append({
                "accented": accented,
                "index": index,
                "gloss": gloss_for(conn, form, index),
            })
        entry = {
            "status": "ambiguous",
            "form": form,
            # the dictionary still holds a default reading; offer it so the text can
            # be marked, but list the alternatives that context might prefer
            "accented": plus_to_acute(row[0]) if row else candidates[0]["accented"],
            "candidates": candidates,
        }
        if not any(candidate["gloss"] for candidate in candidates):
            entry["glosses"] = all_glosses(conn, form)
        return entry

    accented = row[0] if row else variants[0]
    index = accented.index("+")
    return {"status": "ok", "form": form, "accented": plus_to_acute(accented),
            "gloss": gloss_for(conn, form, index)}


def mark_text(conn, text):
    """Return (marked_text, per-word report)."""
    resolved = {}

    def resolve(match):
        word = match.group(0)
        if word not in resolved:
            plain, index = split_marks(word)
            if index is not None:
                # already stressed, by the caller or by an earlier run
                resolved[word] = {"status": "given", "form": plain, "accented": word}
            else:
                resolved[word] = lookup(conn, word)
        return resolved[word].get("accented", word)

    marked = WORD_RE.sub(resolve, text)
    return marked, list(resolved.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("file", nargs="?", help="lyrics file, or - for stdin (the default)")
    parser.add_argument("--db", default=DEFAULT_DB)
    parser.add_argument("--text", action="store_true", help="print only the marked text")
    parser.add_argument("--lookup", nargs="+", help="resolve these words and exit")
    args = parser.parse_args()

    conn = connect(args.db)

    if args.lookup:
        for word in args.lookup:
            print(json.dumps(lookup(conn, word), ensure_ascii=False))
        return 0

    text = sys.stdin.read() if args.file in (None, "-") else open(args.file, encoding="utf-8").read()
    marked, words = mark_text(conn, text)

    if args.text:
        print(marked)
        return 0

    ambiguous = [w for w in words if w["status"] == "ambiguous"]
    unknown = [w for w in words if w["status"] == "unknown"]
    ok = [w for w in words if w["status"] == "ok"]
    given = [w for w in words if w["status"] in ("given", "implied")]
    payload = {
        "text": marked,
        "words": ok + given + ambiguous + unknown,
        "stats": {
            "total": len(words),
            "resolved": len(ok),
            "given": len(given),
            "ambiguous": len(ambiguous),
            "unknown": len(unknown),
        },
    }
    if ambiguous:
        payload["note_ambiguous"] = (
            "each ambiguous word lists its candidate readings with English glosses "
            "where available; pick the reading the lyric's context requires, then "
            "adjust the mark in the text before rendering"
        )
    if unknown:
        payload["note_unknown"] = (
            "unknown words are absent from the offline dictionary (usually proper "
            "nouns or slang); look them up online or infer the stress, then mark them "
            "by hand and tell the user which ones were inferred"
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
