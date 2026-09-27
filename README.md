# Russian Lyrics Romanization

An agent skill that converts Russian lyrics into three aligned lines: the original with
stress marks, a letter-level romanization, and an English pronunciation.

> **The output is not reviewed by a Russian speaker.** I do not read Russian myself.
> Stress marks come from a dictionary lookup and the rules are pinned by 51 test cases,
> but errors are possible. If a line is wrong, open an issue with the line and the
> correction.

## Output

```
Очи чёрные, очи стра́стные             original, stress marked
Ochi chyornyye, ochi strastnyye        romanization
a-chi CHYOR-ni-ye, a-chi STRA-sni-ye   English pronunciation, stressed syllable in CAPITALS
```

The romanization is a letter-level transliteration. The pronunciation line is phonetic:
each word is rewritten by pronunciation rules first (unstressed о as `a`, -ться as
`-tsa`, final devoicing, assimilation), then split into syllables and respelled in
English letters. The rules are in `rules/ru-rules.json`.

## Install

```bash
git clone https://github.com/XXXG00W0/russian-lyrics-romanization \
  ~/.agents/skills/russian-lyrics-romanization
```

`~/.agents/skills/` is shared by ZCode, Claude Code, Codex and Cursor. For a single
tool, use `~/.zcode/skills/` or `~/.claude/skills/`.

## Setup

```bash
python3 ~/.agents/skills/russian-lyrics-romanization/scripts/fetch_data.py
```

Downloads ~31 MB into `~/.cache/ru-lyrics/` and builds the stress database: ~3.2M word
forms including inflected ones, so `руку` resolves directly. The database is ~280 MB on
disk. The data is fetched from its original sources at setup time and is not
redistributed with this repo. The scripts use the standard library only, so Python 3.9
or newer (the commands here use `python3`; on Windows the interpreter may be `python`,
`py`, or a versioned name such as `python3.12`).

If the download fails the hosts are probably blocked on your network. `fetch_data.py`
reads `HTTPS_PROXY`/`HTTP_PROXY`, and on Windows the system proxy, then prints which one
it used.

## Use

### As an agent skill

Ask for it, in English or Chinese:

> Romanize this and give me a pronunciation line: Очи чёрные, очи страстные...
> 把这段俄语歌词转成罗马音和英文发音

The agent runs the scripts, resolves words that have more than one possible stress, and
reports which words were inferred.

### From the command line

```bash
S=~/.agents/skills/russian-lyrics-romanization

python3 $S/scripts/stress.py song.txt --text > marked.txt   # mark stress
python3 $S/scripts/render.py marked.txt                     # three lines
python3 $S/scripts/verify.py --check song.txt               # sanity checks
```

The same thing as one pipeline:

```bash
python3 $S/scripts/stress.py song.txt --text | python3 $S/scripts/render.py
```

`stress.py` prints JSON: the marked text and a report that labels each word `ok`,
`given`, `implied`, `ambiguous` or `unknown`. Ambiguous words are listed with their
readings, for example `замок` → `за́мок` (castle) / `замо́к` (lock). Choose one, edit the
marked text, and pass it to `render.py`.

## Output formats

`--format blocks` (default), `table` (markdown), `tsv` (spreadsheets), `json`.
`table` writes English column headers unless `--lang zh` is given.

## Romanization standards

`--system` selects the scheme used for the romanization line. Only that line changes;
the pronunciation line is the same in all five.

| `--system` | Очи чёрные, очи стра́стные | Notes |
|---|---|---|
| `lyrics` (default) | Ochi chyornyye, ochi strastnyye | for lyric sheets |
| `bgn` | Ochi chërnyye, ochi strastnyye | BGN/PCGN |
| `iso9` | Oči čërnye, oči strastnye | ISO 9 |
| `gost` | Ochi chyorny&#96;ye, ochi strastny&#96;ye | GOST 7.79 System B; &#96; marks the soft sign |
| `alalc` | Ochi chërnye, ochi strastnye | ALA-LC |

## Repository contents

| path | contents |
|---|---|
| `SKILL.md` | the workflow the agent follows |
| `rules/ru-rules.json` | letter maps and the five profiles |
| `scripts/stress.py` | dictionary lookup and homograph report |
| `scripts/render.py` | rules engine that produces the three lines |
| `scripts/verify.py` | golden-set tests and text checks |
| `scripts/fetch_data.py` | builds the cache (setup only) |
| `tests/golden.tsv` | 51 cases |
| `references/` | romanization standards, English respelling, homographs, stress sources, output formats |

## Tests

```bash
python3 scripts/verify.py
```

51 cases covering ё/е, unstressed о, ы, soft signs, чн/щн, -ться, -его/-ого, devoicing,
assimilation and homographs. The suite runs offline and does not need the 31 MB database.

`verify.py --check song.txt` also checks that word counts survive rendering and that
every multi-syllable word carries exactly one stress.

## Limitations

- Stress in context is chosen by the agent. `замок` has two readings and the tool lists
  both; which one is right depends on the line's meaning.
- Some homograph entries have no English gloss; the report shows `null` for those.
- Words absent from the dictionary (proper nouns, slang, recent loans) are inferred or
  looked up online, and the report labels them.
- A written `ё` is treated as stressed. Lyrics often write `е` for `ё`, which changes the
  pronunciation (все "all" vs всё "everything"); check suspect words with
  `stress.py --lookup все всё`.

## Attribution

Downloaded at setup time, not redistributed here:

- **ruaccent/accentuator** (HuggingFace) - stress dictionaries
- **Badestrand/russian-dictionary** - OpenRussian glosses, CC-BY-SA-4.0

## License

MIT - see [LICENSE](LICENSE).

## 中文说明

输入俄语歌词，输出三行对照：原文（带重音符号）、罗马转写、英文发音（重音音节大写）。
罗马转写是逐字母转写；英文发音先按发音规则处理，再按音节用英文字母拼写，规则在
`rules/ru-rules.json`。

**本Skill的输出未经俄语母语者校订。** 本人不是俄罗斯人，不会俄语，重音来自词典查询，规则由 51 条测试用例
决定，但可能有局限性。如发现错误请提issue，附上原句和正确读音。

安装：把仓库 clone 到 `~/.agents/skills/`（ZCode / Claude Code / Codex / Cursor 共用），
运行一次 `scripts/fetch_data.py` 建词库（约 31 MB，部分网络需要代理）。

一词多音的（замок 城堡／锁）由 agent 根据句意选择；词库里没有的词会在报告中标出。
