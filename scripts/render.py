#!/usr/bin/env python3
"""Render Russian lyrics as a romanization plus an English pronunciation.

Input is Cyrillic text. Stress may be marked with a combining acute (U+0301) or a
'+' before the stressed vowel - that is what scripts/stress.py produces. A word
with no mark is still rendered, it just gets no stress highlight.

The romanization line is letter-level transliteration (see rules/ru-rules.json for
the five profiles). The pronunciation line is phonetic: the word is first rewritten
into a "phonetic Cyrillic" form (word rules, voicing assimilation, final devoicing),
then split into syllables and mapped to English spellings, with the stressed syllable
in capitals.

Usage:
  python render.py lyrics.txt
  python render.py lyrics.txt --system bgn --format table
  python render.py lyrics.txt --format table --lang zh
  python render.py lyrics.txt --format tsv --stress-marks
  echo "Я не могу́ забы́ть" | python render.py
"""

import argparse
import json
import os
import re
import sys

# a Windows pipe defaults to the ANSI code page, which mangles Cyrillic the moment
# the output is redirected to a file
for _stream in (sys.stdin, sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
RULES_PATH = os.path.join(os.path.dirname(HERE), "rules", "ru-rules.json")

VOWELS = "аеёиоуыэюя"
CONSONANTS = "бвгджзйклмнпрстфхцчшщ"
SIGNS = "ьъ"
ACUTE = "\u0301"
GRAVE = "\u0300"
# a combining acute/grave belongs to the letter it marks, so a stressed word has
# to stay a single token
MARKS = "\u0300\u0301"
WORD_RE = re.compile(r"[А-Яа-яЁё\u0300\u0301]+(?:-[А-Яа-яЁё\u0300\u0301]+)*")

# Legal syllable onsets. Only used to decide where a hyphen goes, so a generous
# list is fine - the goal is hyphens a singer finds natural, not phonological truth.
ONSETS = {
    "бл", "бр", "вл", "вр", "вз", "вс", "гл", "гр", "дв", "др", "зв", "зд", "зл", "зм",
    "зн", "зр", "кл", "кр", "кв", "мн", "пл", "пр", "пс", "пт", "св", "ск", "сл", "см",
    "сн", "сп", "ст", "сх", "тр", "тв", "фл", "фр", "хл", "хр", "цв", "чв", "шл", "шп",
    "шк", "шт", "зг", "сб", "сд", "жд", "тк", "дн", "гн", "стр", "ств", "скр", "спр",
    "здр", "взг", "вск", "схв", "скл", "смр", "збр", "сдв", "сбл", "снт", "ткн",
}


def load_rules(path=RULES_PATH):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------- stress marks

def parse_stress(word):
    """Return (plain_word, index_of_stressed_char) for 'рук+а' or 'рука\\u0301'."""
    if "+" in word:
        index = word.index("+")
        return word.replace("+", ""), index
    out = []
    index = None
    for char in word:
        if char in (ACUTE, GRAVE):
            index = len(out) - 1
        else:
            out.append(char)
    return "".join(out), index


def vowel_ordinal(text, index):
    """Which vowel number (0-based) sits at `index`, or None."""
    if index is None or index < 0 or index >= len(text):
        return None
    if text[index].lower() not in VOWELS:
        return None
    return sum(1 for char in text[: index + 1] if char.lower() in VOWELS) - 1


def remap_stress(old_text, old_index, new_text):
    """Move a stress index across a rewrite by keeping the vowel ordinal.

    Every rewriting rule in this file either deletes consonants or swaps one vowel
    for another, so counting vowels is a reliable anchor.
    """
    ordinal = vowel_ordinal(old_text, old_index)
    if ordinal is None:
        return None
    seen = -1
    for i, char in enumerate(new_text):
        if char.lower() in VOWELS:
            seen += 1
            if seen == ordinal:
                return i
    return None


# ------------------------------------------------------------- romanization

def romanize_word(word, profile, mark_stress=False):
    """Letter-level transliteration of one word (punctuation is kept as-is)."""
    plain, stressed_at = parse_stress(word)
    letters = profile["letters"]
    iotated = profile.get("iotated") or {}
    endings = profile.get("ends") or {}

    stem, tail = plain, ""
    for ending in sorted(endings, key=len, reverse=True):
        if plain.lower().endswith(ending) and len(plain) > len(ending):
            stem, tail = plain[: -len(ending)], plain[-len(ending):]
            break

    out = []
    word_start = True
    for i, char in enumerate(stem):
        low = char.lower()
        if low in letters:
            value = letters[low]
            previous = stem[i - 1].lower() if i else ""
            if low in iotated and (word_start or previous in VOWELS + SIGNS + "й"):
                value = iotated[low]
            out.append(value)
            if mark_stress and stressed_at is not None and i == stressed_at:
                out.append(ACUTE)
        elif char == "-":
            out.append(char)
            word_start = True
            continue
        else:
            out.append(char)
        word_start = False
    out.append(endings.get(tail.lower(), tail))
    return "".join(out)


# ------------------------------------------------------- phonetic rewriting

def _next_consonant_after(chars, position):
    """Nearest consonant to the right, skipping ь/ъ; None past the end or at a vowel."""
    for j in range(position + 1, len(chars)):
        low = chars[j].lower()
        if low in SIGNS:
            continue
        return low if low in CONSONANTS else None
    return None


def _is_word_final(chars, position):
    return all(char.lower() in SIGNS for char in chars[position + 1:])


def _apply_rule(text, rule):
    """Apply one word rule (a character-level replacement) if the word qualifies."""
    low = text.lower()
    where = rule["where"]
    values = [v.lower() for v in rule["values"]]
    if where == "word" and low not in values:
        return text
    if where == "suffix" and not any(low.endswith(v) for v in values):
        return text
    if where == "prefix" and not any(low.startswith(v) for v in values):
        return text
    if where == "contains" and not any(v in low for v in values):
        return text
    if "unless" in rule and low in [u.lower() for u in rule["unless"]]:
        return text
    source, target = rule["from"], rule["to"]
    index = text.lower().find(source)
    while index != -1:
        text = text[:index] + target + text[index + len(source):]
        index = text.lower().find(source, index + len(target))
    return text


def phonetic_cyrillic(word, rules):
    """Rewrite a word into the form it is pronounced as.

    This is where the pronunciation rules that are not letter-mapping live:
    -ться is spoken -ца, -ого is spoken -ово, ч in что is spoken ш, final
    consonants devoice, and obstruents agree in voicing with the next one.
    """
    ruleset = rules["respelling"]
    plain, stressed_at = parse_stress(word)
    text = ruleset.get("word_map", {}).get(plain.lower(), plain)

    for rule in ruleset.get("word_rules", []):
        text = _apply_rule(text, rule)

    pairs = ruleset["voicing_pairs"]
    voiced = set("бвгджз")
    voiceless = set("пфктшсхцчщ")
    voiced_triggers = set(ruleset["voiced_triggers"])
    voiceless_triggers = set(ruleset["voiceless_triggers"])
    chars = list(text)
    # right to left so a chain of assimilations settles in one pass
    for i in range(len(chars) - 1, -1, -1):
        low = chars[i].lower()
        if low not in pairs:
            continue
        following = _next_consonant_after(chars, i)
        if following is None:
            # a lone letter is a preposition (в, с, к) - devoicing it in isolation
            # would tell the singer to say "f" where the next word decides
            if len(chars) > 1 and _is_word_final(chars, i) and low in ruleset["final_devoicing"]:
                chars[i] = ruleset["final_devoicing"][low]
            continue
        other = pairs[low]
        if following in voiced_triggers and other in voiced:
            chars[i] = other
        elif following in voiceless_triggers and other in voiceless:
            chars[i] = other
    text = "".join(chars)
    return text, remap_stress(plain, stressed_at, text)


# ---------------------------------------------------------- syllable split

def choose_onset(cluster):
    """Longest legal onset that is a suffix of `cluster` (ь/ъ ride with the consonant)."""
    if not cluster:
        return ""
    for size in (3, 2, 1):
        for start in range(len(cluster) - 1, -1, -1):
            candidate = cluster[start:].replace("ь", "").replace("ъ", "")
            if len(candidate) == size and (candidate in ONSETS or (size == 1 and candidate in CONSONANTS)):
                return cluster[start:]
    for start in range(len(cluster) - 1, -1, -1):
        if cluster[start] not in SIGNS:
            return cluster[start:]
    return cluster


def split_syllables(word):
    """Character ranges, one per syllable."""
    if not word:
        return []
    vowel_index = [i for i, char in enumerate(word) if char.lower() in VOWELS]
    if not vowel_index:
        return [(0, len(word))]
    cuts = []
    for left, right in zip(vowel_index, vowel_index[1:]):
        onset = choose_onset(word[left + 1:right])
        cuts.append(right - len(onset))
    ranges = []
    previous = 0
    for cut in cuts:
        ranges.append((previous, cut))
        previous = cut
    ranges.append((previous, len(word)))
    return [r for r in ranges if r[0] < r[1]]


def implied_stress(text, stressed_at):
    """Stress that the spelling itself guarantees.

    ё is always stressed in Russian, and a word with a single vowel has nowhere
    else for the stress to go - so кровь is KROF and мёд is MYOT even when the
    lyrics carry no stress marks.
    """
    if stressed_at is not None:
        return stressed_at
    lower = text.lower()
    if "ё" in lower:
        return lower.index("ё")
    vowels = [i for i, char in enumerate(lower) if char in VOWELS]
    if len(vowels) == 1:
        return vowels[0]
    return None


def render_syllable(chunk, state, rules):
    ruleset = rules["respelling"]
    table = ruleset["vowels_stressed"] if state == "stressed" else ruleset["vowels_unstressed"]
    hard = set(ruleset["hard_always"])
    out = []
    previous = ""
    for char in chunk:
        low = char.lower()
        if low in SIGNS:
            continue
        if low in VOWELS:
            if low == "и" and previous in hard:
                # жизнь, машина, цирк: и is spoken [ɨ] after ж, ш and ц
                out.append("i")
            elif low == "е" and previous == "ц":
                # ц is always hard, so е after it never carries a y-glide
                out.append("e")
            elif low == "е" and previous in ("ж", "ш"):
                # жена -> zhi-NA, шесть -> shest. ц is deliberately not in this
                # list: after ц the vowel keeps its own colour (солнце -> SON-tse)
                out.append("e" if state == "stressed" else "i")
            else:
                out.append(table.get(low, low))
        elif low in ruleset["consonants"]:
            out.append(ruleset["consonants"][low])
        else:
            out.append(char)
        previous = low
    return "".join(out)


def respell_word(word, rules):
    """English pronunciation: 'ма-ГУ' style syllables, stress in capitals."""
    phonetic, stressed_at = phonetic_cyrillic(word, rules)
    if not phonetic:
        return ""
    stressed_at = implied_stress(phonetic, stressed_at)
    ranges = split_syllables(phonetic)
    stress_syllable = None
    if stressed_at is not None:
        for number, (start, end) in enumerate(ranges):
            if start <= stressed_at < end:
                stress_syllable = number
                break
    parts = []
    for number, (start, end) in enumerate(ranges):
        state = "stressed" if number == stress_syllable else "unstressed"
        parts.append(render_syllable(phonetic[start:end], state, rules))
    # a one-syllable word needs no stress mark
    if stress_syllable is not None and len(parts) > 1:
        parts[stress_syllable] = parts[stress_syllable].upper()
    return "-".join(parts)


# --------------------------------------------------------------- line level

def render_line(line, profile, rules, mark_stress=False):
    original, roman, respell = [], [], []
    position = 0
    for match in WORD_RE.finditer(line):
        gap = line[position:match.start()]
        if gap:
            original.append(gap)
            roman.append(gap)
            respell.append(gap)
        word = match.group(0)
        original.append(word)
        transliterated = romanize_word(word, profile, mark_stress)
        if word[:1].isupper() and transliterated[:1].islower():
            transliterated = transliterated[0].upper() + transliterated[1:]
        roman.append(transliterated)
        respell.append(respell_word(word, rules))
        position = match.end()
    tail = line[position:]
    if tail:
        original.append(tail)
        roman.append(tail)
        respell.append(tail)
    return "".join(original), "".join(roman), "".join(respell)


def render_text(text, system, rules, mark_stress=False):
    profile = rules["profiles"][system]
    rows = []
    for line in text.splitlines():
        if not line.strip():
            rows.append((line, line, line))
        else:
            rows.append(render_line(line, profile, rules, mark_stress))
    return rows


TABLE_HEADERS = {
    "en": "| original | romanization | English pronunciation |",
    "zh": "| 原文 | 罗马转写 | 英语发音 |",
}


def format_rows(rows, fmt, lang="en"):
    if fmt == "tsv":
        return "\n".join("\t".join(row) for row in rows)
    if fmt == "table":
        out = [TABLE_HEADERS[lang], "|---|---|---|"]
        for original, roman, respell in rows:
            if not original.strip():
                continue
            out.append("| %s | %s | %s |" % (original, roman, respell))
        return "\n".join(out)
    if fmt == "json":
        payload = [{"original": o, "romanization": r, "respelling": p} for o, r, p in rows]
        return json.dumps(payload, ensure_ascii=False, indent=2)
    blocks = []
    for original, roman, respell in rows:
        if not original.strip():
            blocks.append("")
            continue
        blocks.extend([original, roman, respell])
    return "\n".join(blocks)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("file", nargs="?", help="lyrics file, or - for stdin (the default)")
    parser.add_argument("--system", default="lyrics", choices=["lyrics", "bgn", "iso9", "gost", "alalc"])
    parser.add_argument("--format", default="blocks", choices=["blocks", "table", "tsv", "json"])
    parser.add_argument("--lang", default="en", choices=["en", "zh"],
                        help="language of the table header row (--format table)")
    parser.add_argument("--stress-marks", action="store_true",
                        help="keep the acute accent on the romanization line")
    args = parser.parse_args()

    text = sys.stdin.read() if args.file in (None, "-") else open(args.file, encoding="utf-8").read()
    rules = load_rules()
    rows = render_text(text, args.system, rules, args.stress_marks)
    print(format_rows(rows, args.format, args.lang))
    return 0


if __name__ == "__main__":
    sys.exit(main())
