# Output formats and presentation

## The default: three-line blocks

```
о́чи чёрные, о́чи стра́стные,
ochi chyornyye, ochi strastnyye,
O-chi CHYOR-ni-ye, O-chi STRA-sni-ye,
```

Best for pasting into a chat, a lyric sheet, or notes. Blank lines from the source are
preserved, so stanzas stay stanzas.

## Table

```bash
python3 $SKILL_DIR/scripts/render.py marked.txt --format table
```

```markdown
| original | romanization | English pronunciation |
|---|---|---|
| о́чи чёрные, о́чи стра́стные, | ochi chyornyye, ochi strastnyye, | O-chi CHYOR-ni-ye, O-chi STRA-sni-ye, |
```

Use it when the user wants a document, a subtitle track source, or a spreadsheet.
`--lang en` (the default) writes English column headers; `--lang zh` writes
原文 / 罗马转写 / 英语发音.

## TSV and JSON

`--format tsv` is for spreadsheets and for pasting into a translation tool.
`--format json` gives `{"original", "romanization", "respelling"}` per line, for anything
that will be processed further.

## A full worked example

Input (`Очи чёрные`, a 19th-century romance - public domain):

```bash
python3 $SKILL_DIR/scripts/stress.py demo.txt --text \
  | python3 $SKILL_DIR/scripts/render.py --format blocks
```

```
о́чи чёрные, о́чи стра́стные,
ochi chyornyye, ochi strastnyye,
O-chi CHYOR-ni-ye, O-chi STRA-sni-ye,

о́чи жгу́чие и́ прекра́сные,
ochi zhguchiye i prekrasnyye,
O-chi ZHGOO-chi-ye ee prye-KRA-sni-ye,

ка́к люблю́ я́ ва́с, ка́к бою́сь я́ ва́с,
kak lyublyu ya vas, kak boyus ya vas,
kak lyu-BLYU ya vas, kak ba-YUS ya vas,

зна́ть, уви́дел ва́с я́ в недо́брый ча́с!
znat, uvidel vas ya v nedobry chas!
znat, u-VEE-dyel vas ya v nye-DO-briy chas!
```

What the pipeline did here, and what to mention to the user when it matters:

- `чё́рные` → `CHYOR-ni-ye`: ё is stressed and the dictionary's own mark would have been
  redundant, so no double accent.
- `прекра́сные` → `prye-KRA-sni-ye`: the unstressed `е` keeps its `y`, which is how the
  soft `п` and `р` reach a reader who does not know Russian.
- `страстны́е` → hand-corrected to `стра́стные` from the ambiguity report; the `т` in
  `-стн-` is silent, so the line reads `STRA-sni-ye`.
- `ча́с` → `chas` (not `chahs`): unstressed-vowel spelling and stress capitals are the
  only two things the reader has to act on.
- `в недо́брый` → `v nye-DO-briy`: a one-letter preposition keeps its `v`, because
  devoicing it out of context would be a lie about the next word.

## Presentation

Give the three lines, then a short list under them:

- words whose reading you chose between (from the ambiguity report),
- words whose stress you inferred because they were not in the dictionary,
- flattened `ё` you restored, if any.

Keep translation out of the answer unless it was asked for.

If the user wants a file, write one (markdown table for a document, blocks for a lyric
sheet) and tell them the path. Otherwise keep the output in the reply: a song is 30-60
lines, which is well within a message.
