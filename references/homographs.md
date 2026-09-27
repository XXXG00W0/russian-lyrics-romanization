# Choosing between readings

Russian stress distinguishes words, not just syllables: `за́мок` is a castle and `замо́к`
is a lock. The offline dictionary reports every form that has more than one reading, with
English glosses where the gloss table knows them:

```json
{"form": "замок", "status": "ambiguous", "accented": "за́мок",
 "candidates": [{"accented": "за́мок", "index": 1, "gloss": "castle"},
                {"accented": "замо́к", "index": 3, "gloss": "lock; keystone, clasp, fastener"}]}
```

`accented` on the word itself is the dictionary's default reading. Using it without
thinking is how you get a wrong line: the default is a frequency guess, not a reading of
this lyric.

## Procedure

1. Read the whole line, not the word. The reading is decided by the sentence's meaning.
2. Use the glosses. They are the fastest signal, and when one of them fits the line the
   question is answered.
3. If the glosses are missing, ask what part of speech and grammatical form the syntax
   requires. Many ambiguous pairs are two different words (за́мок/замо́к) and many others
   are two forms of one word (ру́ки "hands" nom. pl. / руки́ "of a hand" gen. sg.).
4. Apply the chosen reading by replacing the word's mark in the marked text, then render.
5. If both readings fit, take the dictionary default, and say so in the answer.

## Cases that turn up in songs

| form | readings | how to tell |
|---|---|---|
| за́мок / замо́к | castle / lock | a wall, a key, a door → lock; a palace, a hill → castle |
| пла́чу / плачу́ | I cry / I pay | tears vs. money; `плачу за` + accusative = pay |
| мо́ю / мою́ | I wash (from мыть) / my (from мой, accusative) | a following noun → my; a following object being washed → I wash |
| доро́га / дорога́ | road / dear (short adjective) | the adjective needs a subject it describes and is rare in lyrics |
| бе́лки / белки́ | squirrels / proteins | |
| му́ка / мука́ | torment / flour | |
| по́том / пото́м | with sweat / later | `потом` as a time adverb is far more common |
| се́ло / село́ | it sat down / village | |
| у́же / уже́ | narrower / already | |
| сто́ит / стои́т | is worth / stands, costs | |
| ве́сти / вести́ | news / to lead | |
| ру́ки / руки́ | hands (nom. pl.) / of a hand (gen. sg.) | |
| но́ги / ноги́ | legs (nom. pl.) / of a leg (gen. sg.) | |
| все / всё | all (unstressed) / everything (stressed, one syllable) | spelling, not stress: check for a flattened ё |

## When the source text is the problem

`страстные` comes back from the dictionary as `страстны́е`; the adjective is `стра́стные`.
The dictionary's `accents` table is optimised for homograph *resolution in text* and its
default is occasionally the other reading or a different paradigm. Anything the report
lists as ambiguous is worth a second of thought, and the golden set in
`tests/golden.tsv` exists so that a rule change cannot quietly make this worse.

Two more things the report cannot see:

- **Flattened ё** (see `stress-sources.md`). It looks like a stress error but it is a
  missing letter.
- **Loanwords and names.** `Битлз`, `Токио`, surnames, and recent borrowings resolve
  inconsistently or not at all. Mark them as inferred in the answer.

## Reporting

Say which words you chose between readings for, and why, in one short list under the
lyric sheet, with the two candidates.
