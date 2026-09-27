#!/usr/bin/env python3
"""Check the renderer against the golden set, and sanity-check arbitrary text.

  python verify.py                     # run tests/golden.tsv
  python verify.py --system bgn        # run it against another profile
  python verify.py --check song.txt    # sanity checks on any lyrics file

The sanity checks cover what a rule engine can get wrong:
word counts must survive, every multi-syllable word must carry exactly one
stressed syllable, and no unstressed syllable may contain an 'o' (unstressed о
is always spoken 'a', so an 'o' there means a reduction rule was missed).
"""

import argparse
import os
import re
import sys

# a Windows pipe defaults to the ANSI code page, which mangles Cyrillic the moment
# the output is redirected to a file
for _stream in (sys.stdin, sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import render as R  # noqa: E402

DEFAULT_GOLDEN = os.path.join(os.path.dirname(HERE), "tests", "golden.tsv")


def run_golden(path, system):
    rules = R.load_rules()
    profile = rules["profiles"][system]
    passed = failed = 0
    failures = []
    with open(path, encoding="utf-8") as handle:
        for number, raw in enumerate(handle, 1):
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            fields = line.split("\t")
            if len(fields) != 3:
                failures.append((number, line, "expected 3 tab-separated fields", ""))
                failed += 1
                continue
            text, want_roman, want_respell = fields
            _, got_roman, got_respell = R.render_line(text, profile, rules)
            if got_roman == want_roman and got_respell == want_respell:
                passed += 1
                continue
            failed += 1
            detail = []
            if got_roman != want_roman:
                detail.append("  romanization  want %-28s got %s" % (want_roman, got_roman))
            if got_respell != want_respell:
                detail.append("  respelling     want %-28s got %s" % (want_respell, got_respell))
            failures.append((number, text, "", "\n".join(detail)))

    print("golden set [%s]: %d passed, %d failed" % (system, passed, failed))
    for number, text, note, detail in failures:
        print("\nline %d: %s" % (number, text))
        if note:
            print("  " + note)
        print(detail)
    return 1 if failed else 0


def run_checks(path, system):
    rules = R.load_rules()
    profile = rules["profiles"][system]
    text = sys.stdin.read() if path == "-" else open(path, encoding="utf-8").read()
    label = "stdin" if path == "-" else path
    marked = R.ACUTE in text or R.GRAVE in text
    notes = []
    problems = []
    if not marked:
        notes.append("this file carries no stress marks - run scripts/stress.py on it first, "
                     "or the stress checks have nothing to check")
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        _, roman, respell = R.render_line(line, profile, rules)
        if len(roman.split()) != len(line.split()):
            problems.append("line %d: romanization word count differs from the original" % number)
        if len(respell.split()) != len(line.split()):
            problems.append("line %d: respelling word count differs from the original" % number)
        if not marked:
            continue
        for word in respell.split():
            syllables = word.split("-")
            if len(syllables) > 1:
                stressed = [s for s in syllables if s.isupper() and any(c.isalpha() for c in s)]
                if len(stressed) != 1:
                    problems.append("line %d: %r has %d stressed syllables, want 1"
                                    % (number, word, len(stressed)))
                # unstressed о is always spoken 'a', so an 'o' in an unstressed
                # syllable means a reduction rule was missed - except in 'oo' and
                # 'yo', which are the spellings of a full у and ё.
                # Monosyllables are exempt: nothing reduces next to nothing.
                for syllable in syllables:
                    if syllable.isupper():
                        continue
                    for match in re.finditer("o", syllable):
                        at = match.start()
                        if syllable[at:at + 2] == "oo" or (at > 0 and syllable[at - 1] == "y"):
                            continue
                        problems.append("line %d: %r has an unreduced 'o' in the "
                                        "unstressed syllable %r" % (number, word, syllable))
                        break

    print("checks on %s: %d problem(s)" % (label, len(problems)))
    for note in notes:
        print("  note: " + note)
    for problem in problems:
        print("  " + problem)
    return 1 if problems else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--golden", default=DEFAULT_GOLDEN)
    parser.add_argument("--check", help="lyrics file to sanity-check")
    parser.add_argument("--system", default="lyrics",
                        choices=["lyrics", "bgn", "iso9", "gost", "alalc"])
    args = parser.parse_args()

    if args.check:
        return run_checks(args.check, args.system)
    return run_golden(args.golden, args.system)

if __name__ == "__main__":
    sys.exit(main())
