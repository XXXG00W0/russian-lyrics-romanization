---
name: russian-lyrics-romanization
description: Romanize Russian lyrics and add an English pronunciation guide, syllable by syllable with the stress marked. Use for any request to romanize, transliterate, or pronounce Russian text or songs - 俄语歌词罗马音 / 罗马转写 / 拉丁转写 / 音译 / 俄语发音 / 英语发音, ударение, sing-along or cover lyrics, karaoke or lyric sheets, or reading Cyrillic aloud. Also covers stress lookup for individual Russian words and the BGN/PCGN, ISO 9, GOST and ALA-LC styles used for print and cataloguing.
---

# Russian lyrics → romanization + English pronunciation

Produce three aligned lines for each line of lyrics:

```
Я не могу́ забы́ть твои́ глаза́        original, with stress marks
Ya ne mogu zabyt tvoi glaza            romanization (letter-level transliteration)
ya nye ma-GOO za-BIT tva-EE gla-ZA     English pronunciation (stress in CAPITALS)
```

The romanization line is a letter-level transliteration. The pronunciation line is
phonetic: it applies the pronunciation rules (unstressed о is spoken "a", final
consonants devoice, -ться is "-tsa").

## Do not hand-write the output

The romanization and the pronunciation line are produced by the rule engine.
Write the text to a file (or pipe it) and run the scripts. Hand-transliterating a
song drifts from the rules between lines and can break the word-for-word alignment.

Stress in context is the part that needs a reader - see "Resolving stress" below.

## Workflow

```
1. save the lyrics       -> song.txt (strip LRC timestamps and metadata first)
2. stress.py             -> cached stress DB lookup; returns marked text + report
3. resolve the report    -> pick homograph readings, handle unknown words
4. render.py             -> the three lines
5. verify.py --check     -> sanity check (optional but cheap)
6. present               -> tell the user which words were inferred, not looked up
```

### 1. Get the text

Lyrics may arrive pasted, as a file, or as an `.lrc` with `[00:12.34]` timestamps and
`[ar:...]`/`[ti:...]` tags. Anything that is not Cyrillic passes through the scripts
untouched, so timestamps survive into the output rather than breaking it. Strip them
with your own edit tools when you want a clean sheet - the line breaks matter either way.

If the user gives a URL rather than text (Genius and similar lyric sites), fetch it
yourself first. Note that lyric sites are often reachable only through the system proxy:
if the fetch tool times out, pull the page with `curl -x <proxy>` and extract the text
from the page's lyrics container.

Text where `ё` was flattened to `е` is common in lyrics and changes the pronunciation
(все "all" vs всё "everything"). The scripts treat a written ё as stressed, so if you
suspect flattened ё in a word that matters, check it against the dictionary
(`stress.py --lookup все всё`).

### 2. Stress the text

`$SKILL_DIR` is this skill's own directory - the one containing this SKILL.md.

```bash
python3 "$SKILL_DIR/scripts/stress.py" song.txt            # JSON: text + report
python3 "$SKILL_DIR/scripts/stress.py" song.txt --text     # just the marked text
python3 "$SKILL_DIR/scripts/stress.py" song.txt --text > marked.txt   # to edit
python3 "$SKILL_DIR/scripts/stress.py" --lookup замок мою  # inspect single words
```

Write the marked text to a file whenever a word needs choosing between readings - that
file is what you edit and hand to `render.py`.

The lookup is offline against `~/.cache/ru-lyrics/stress.db` (3.2M word forms,
including inflected ones - `руку` resolves to `ру́ку` directly). The report marks
each word `ok`, `given` (already stressed by the caller), `implied` (one vowel or none,
so there is nothing to look up), `ambiguous`, or `unknown`.

### 3. Resolve stress - the part that needs judgement

**Ambiguous** words have two or more readings, and the report lists every candidate
reading with an English gloss where the dictionary has one:

```json
{"form": "замок", "status": "ambiguous", "accented": "за́мок",
 "candidates": [{"accented": "за́мок", "gloss": "castle"},
                {"accented": "замо́к", "gloss": "lock; keystone, clasp, fastener"}]}
```

Pick the reading the line's meaning requires, then apply it: take the marked text
from the report and replace that word's mark with the chosen reading. Read
`references/homographs.md` for the disambiguation procedure and the cases that come up
(мою, дорога, все/всё, остро́та/острота́).

**Unknown** words are absent from the dictionary - usually proper nouns, slang, or a
transliterated loan. Look them up online (`references/stress-sources.md` lists the
sites and the proxy note), or infer the stress from the language's patterns. Either
way these are the words you must report to the user as inferred. Do not silently
guess.

### 4. Render

```bash
python3 "$SKILL_DIR/scripts/render.py" marked.txt                 # blocks (default)
python3 "$SKILL_DIR/scripts/render.py" marked.txt --format table   # markdown table
python3 "$SKILL_DIR/scripts/render.py" marked.txt --format table --lang zh   # Chinese headers
python3 "$SKILL_DIR/scripts/render.py" marked.txt --format tsv     # for spreadsheets
python3 "$SKILL_DIR/scripts/render.py" marked.txt --system bgn     # other standards
```

Piping works too:

```bash
python3 "$SKILL_DIR/scripts/stress.py" song.txt \
  | python3 -c "import sys,json;sys.stdout.write(json.load(sys.stdin)['text'])" \
  | python3 "$SKILL_DIR/scripts/render.py" --format blocks
```

Systems: `lyrics` (default), `bgn`, `iso9`, `gost`, `alalc`. `--format table` writes
English column headers unless `--lang zh` is given. Add `--stress-marks` to
keep the acute on the romanization line, for correction passes. See
`references/romanization-standards.md` for what each system is for.

### 5. Check and present

```bash
python3 "$SKILL_DIR/scripts/verify.py"                  # the rule-engine test set
python3 "$SKILL_DIR/scripts/verify.py" --check song.txt # word counts, one stress per word
```

When presenting: give the three-line block, and say plainly which words were inferred
or left unstressed. Say that the output has not been reviewed by a Russian speaker and
that corrections are welcome. If the user asked for a file, write it (markdown table
for a document, blocks for a lyric sheet). Translation is a separate request unless the
user asks for it.

## Setup (once per machine)

```bash
python3 "$SKILL_DIR/scripts/fetch_data.py"     # ~31 MB, builds the cache
```

The cache holds the stress dictionaries (ruaccent, from HuggingFace) and English
glosses (OpenRussian, CC-BY-SA-4.0). It is downloaded, not bundled, so the skill
redistributes nothing. If the download is blocked or truncated (a sandboxed shell may
refuse writes outside the workspace), re-run it with the sandbox disabled; the script
verifies the row count and says so if the result is short. `--db path` points the other
scripts at a different cache.

The scripts use the standard library only, so any Python 3.9+ will do. The commands
below use `python3`; on Windows the interpreter may be `python`, `py` or a versioned
name such as `python3.12`, and `uv run --no-project python` also works.

HuggingFace and raw.githubusercontent.com are unreachable on some networks without the
system proxy. `fetch_data.py` reads it from the Windows registry
(`HKCU\...\Internet Settings`) automatically and prints what it used.

## Reference files

| file | read it when |
|---|---|
| `references/romanization-standards.md` | choosing or explaining an output standard, or answering "why is it written like that" |
| `references/english-respelling.md` | the pronunciation line looks wrong, or you need to explain a spelling to the user |
| `references/stress-sources.md` | a word is missing from the dictionary and you need to look it up online |
| `references/homographs.md` | the report lists candidates and you must choose |
| `references/output-formats.md` | deciding how to present the result, with a worked example |
