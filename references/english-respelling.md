# The English pronunciation line

It is written for anyone who reads English and has not studied Russian. The
conventions:

- **Hyphens separate syllables**: `ma-GOO`, `u-li-BA-tsa`.
- **The stressed syllable is in CAPITALS.** Words of one syllable are left alone - the
  stress is not in doubt.
- **Unstressed о is spelled `a`**, because that is the sound: `хорошо` → `kha-ra-SHO`,
  `молоко` → `ma-la-KO`.
- No diacritics, no IPA, no apostrophes.

## Spelling tables (`rules/ru-rules.json`)

Vowels, stressed / unstressed:

| | а | о | у | ы | и | э | е | ё | ю | я |
|---|---|---|---|---|---|---|---|---|---|---|
| stressed | a | o | oo | i | ee | e | ye | yo | yu | ya |
| unstressed | a | a | u | i | i | e | ye | yo | yu | ya |

Consonants:

| х | ц | ч | ш | щ | ж | й |
|---|---|---|---|---|---|---|
| kh | ts | ch | sh | shch | zh | y |

The rest map to the obvious Latin letter. `ь` and `ъ` produce nothing on their own: the
softness of `ь` is carried by the iotated vowel that follows (`семья` → `sye-MYA`), and
when no vowel follows it is English-invisible anyway (`забыть` → `za-BIT`).

Special spellings, all of which are exceptions to the tables above:

- **ж, ш + е** → `e` when stressed, `i` when not: `жена` → `zhi-NA`, `шесть` → `shest`.
- **ц + е** → `e` always: `солнце` → `SON-tse`. (`ц` is always hard, so no y-glide.)
- **ж, ш, ц + и** → `i`: `жизнь` → `zhizn`, `машина` → `ma-SHI-na`.

## The pronunciation rules applied before spelling

A word is first rewritten into the form it is spoken as; the spelling tables
then apply to that. This is where the difference between Russian spelling and Russian
speech lives:

| rule | example | why |
|---|---|---|
| final consonant devoices | `друг` → `drook`, `кровь` → `krof`, `мёд` → `myot` | Russian has no word-final voiced obstruents |
| obstruents agree in voicing | `вокзал` → `vag-ZAL`, `сделать` → `ZDYE-lat`, `ло́жка` → `LO-shka`, `дождь` → `dosht` | the second consonant decides |
| `-ться` / `-тся` → `-ца` | `улыбаться` → `u-li-BA-tsa` | the infinitive and 3rd-person endings |
| `-ого` / `-его` → `-ово` / `-ево` | `его` → `ye-VO`, `ничего` → `ni-chye-VO` | genitive ending; the adverbs много, строго, дорого keep [g] and are listed as exceptions |
| `чн` → `шн` in a closed word list | `конечно` → `ka-NYESH-na`, but `точно` keeps its ч | only some words shifted |
| `щн` → `шн` | `помощник` → `pa-MOSH-nik` | |
| silent letters, word by word | `солнце` → `SON-tse`, `сердце` → `SYER-tse`, `здравствуй` → `ZDRA-stvuy` | listed in `rules/ru-rules.json` rather than generalised, because the same clusters are pronounced in other words (`местность` keeps its т) |

Stress that the spelling guarantees is applied even with no stress mark: **ё** is always
stressed, and a word with a single vowel has nowhere else for the stress to go
(`кровь` is `krof`, not `kraf`).

## Known limitations - check these by hand

1. **Soft consonants are not marked** except through the following vowel. Say so if the
   user is learning the song from scratch.
2. **The [ə]/[ɐ] distinction is deliberately flattened** to `a`. Phonetically unstressed
   о in the syllable before the stress is [ɐ] and further away is [ə]; both are written
   `a` because that is what a singer can act on.
3. **Only listed words get silent letters and `-ого`.** A missed one shows up as an
   extra consonant (`stni` instead of `sni`) or a hard `g`. If a name or a rare word
   looks wrong, add it to `rules/ru-rules.json` -> `respelling.word_rules`.
4. **е written for ё.** Lyrics very often drop the diaeresis, and then the stressed
   vowel is wrong and the sound is wrong with it. Words where this matters (все/всё,
   ее/её, поем/поём) are worth checking explicitly: `stress.py --lookup все всё`.
5. **The dictionary's default reading can be the wrong one.** `страстные` comes back as
   `страстны́е` while the adjective is `стра́стные`. That is what the ambiguity report is
   for - see `homographs.md`.

## Changing the convention

Everything vowel- and consonant-shaped is data in `rules/ru-rules.json`
(`respelling.vowels_stressed`, `vowels_unstressed`, `consonants`), and the rule pipeline
is `respelling.word_rules`. Editing the JSON changes the script's output and the
documentation stays true, because this file describes the JSON rather than replacing it.
After any edit, run `python3 $SKILL_DIR/scripts/verify.py` - the golden set will tell
you which words you broke.
