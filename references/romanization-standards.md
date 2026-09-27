# Romanization standards

Romanization here is **letter-level**: it transliterates what is written, not what is
spoken. `его` is `yego`, not `yevo` - the spoken form belongs to the pronunciation line.

## The five systems

| Cyrillic | `lyrics` (default) | `bgn` | `iso9` | `gost` | `alalc` |
|---|---|---|---|---|---|
| а | a | a | a | a | a |
| б | b | b | b | b | b |
| в | v | v | v | v | v |
| г | g | g | g | g | g |
| д | d | d | d | d | d |
| е | e | e | e | e | e |
| ё | yo | ë | ë | yo | ë |
| ж | zh | zh | ž | zh | zh |
| з | z | z | z | z | z |
| и | i | i | i | i | i |
| й | y | y | j | j | ĭ |
| к | k | k | k | k | k |
| л | l | l | l | l | l |
| м | m | m | m | m | m |
| н | n | n | n | n | n |
| о | o | o | o | o | o |
| п | p | p | p | p | p |
| р | r | r | r | r | r |
| с | s | s | s | s | s |
| т | t | t | t | t | t |
| у | u | u | u | u | u |
| ф | f | f | f | f | f |
| х | kh | kh | h | x | kh |
| ц | ts | ts | c | c | t͡s |
| ч | ch | ch | č | ch | ch |
| ш | sh | sh | š | sh | sh |
| щ | shch | shch | ŝ | shh | shch |
| ъ | *(dropped)* | ʺ | ʺ | `` | ʺ |
| ы | y | y | y | y\` | y |
| ь | *(dropped)* | ʹ | ʹ | \` | ʹ |
| э | e | e | è | e\` | ė |
| ю | yu | yu | û | yu | i͡u |
| я | ya | ya | â | ya | i͡a |

Context rules, only in the systems that have them:

- `lyrics` and `bgn`: **е** is `ye` at the start of a word or after a vowel, `ь`, `ъ` or
  `й`; otherwise `e`. BGN does the same for **ё** → `yë`.
- Adjective endings (`lyrics`: `ый`→`y`, `ий`→`iy`, `ой`→`oy`; `bgn`: `ый`→`yy`,
  `ий`→`iy`, `ой`→`oy`). So `добрый` is `dobry` and `синий` is `siniy`.
- `iso9`, `gost` and `alalc` are pure letter-for-letter tables. They are designed to be
  reversible, so they carry diacritics.

## Which one to use

| situation | use |
|---|---|
| lyric sheet, sing-along, anything read aloud | `lyrics` |
| English-language publication, map, press release, Wikipedia-style text | `bgn` |
| library catalogue record | `alalc` |
| corpus, round-tripping back to Cyrillic, academic transliteration | `iso9` |
| an official Russian document that requires the national standard | `gost` |

`lyrics` differs from `bgn` in exactly two ways, and both exist because BGN is built for
print rather than for reading aloud: BGN keeps `ë` for ё (a diaeresis English readers
skip) and keeps `ʹ`/`ʺ` for ь/ъ (which look like typos in a lyric sheet). If a user asks
for "the official transliteration", they usually mean BGN; if they ask for something
they can read, they mean `lyrics`.

## Where the tables come from

- `bgn` - ICU transliterator rules, `ru_ru_Latn_BGN.txt` (the machine-readable form of
  the BGN/PCGN agreement).
- `iso9` - ISO 9:1995.
- `gost` - GOST 7.79-2000 System B, Russian column (confirmed against the standard's
  table as reproduced in the Russian Wikipedia article on ISO 9; System B is the
  digraph variant, System A is ISO 9 with diacritics).
- `alalc` - the ALA-LC Russian table, cross-checked against the `ala_lc` schema in the
  `iuliia` library.
- `lyrics` - the informal convention used by lyric and fan-translation sites (the
  `wikipedia` schema in `iuliia`), i.e. what the user has already seen elsewhere.

If a user disputes a spelling, the answer is almost always "that is the other system",
not "the table is wrong". Show them the same line in two systems.

## Switching

```bash
python3 $SKILL_DIR/scripts/render.py marked.txt --system bgn
python3 $SKILL_DIR/scripts/render.py marked.txt --system iso9 --format tsv
```

The pronunciation line does **not** change with the system: it describes the sound of
the words, so it is the same whichever convention the romanization uses.
