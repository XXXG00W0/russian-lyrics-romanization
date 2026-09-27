# Where stress comes from

## First choice: the offline cache

`~/.cache/ru-lyrics/stress.db` (SQLite, ~280 MB, built once by `scripts/fetch_data.py`):

| table | rows | contents |
|---|---|---|
| `accents` | 3,194,879 | word form → accented form, `+` before the stressed vowel (`руку` → `р+уку`) |
| `omographs` | 19,741 | forms with two or more readings (`замок` → `з+амок`, `зам+ок`) |
| `gloss` | 58,825 | English glosses from OpenRussian, each with its own accent mark |

The `accents` table is keyed on **word forms, not lemmas**: `руку`, `дошла`, `его`
resolve directly, with no need to guess a lemma and re-inflect. It covers inflected
forms of ~3.2M words.

Sources: `ruaccent/accentuator` on HuggingFace (stress dictionaries) and
`Badestrand/russian-dictionary` on GitHub (OpenRussian glosses, CC-BY-SA-4.0). Both are
downloaded at setup rather than bundled, so the skill ships no third-party data.

`stress.py --lookup <word>` is the fast way to inspect a single form. `--db path` points
at a different cache.

## Second choice: the web

Only needed for words the cache miss - proper nouns, slang, brand names, typos. Query in
this order, and stop at the first answer:

1. **gramota.ru** - `https://gramota.ru/poisk?query=<url-encoded word>`
   The official Russian reference portal, and the only one of these that answers for an
   *inflected form* directly (`руку` → "винительный ру́ку"). It also lists homographs with
   definitions. Note: it sits behind a WAF that returns **403 to plain curl**; the
   agent's own fetch tool passes, so use the fetch tool rather than a script here.
2. **en.openrussian.org** - `https://en.openrussian.org/ru/<word>`
   Per-form stress inside the declension tables, English glosses, homograph siblings with
   glosses, and audio. Lemma pages only (an inflected form 404s).
3. **accentonline.ru** - `https://accentonline.ru/<Capital first letter>/<word>`
   (e.g. `/З/замок`). Gives the syllable number and the accented vowel, both easy to read
   off. Lemma pages only; `/Р/руку` 404s.
4. **ru.wiktionary.org** - `https://ru.wiktionary.org/w/api.php?action=parse&page=<word>&prop=wikitext&format=json`
   Returns raw wikitext. Stress lives in `{{з|ударение=за́мок}}` section headers and in
   `{{transcriptions-ru|...}}`; the declension tables are generated with stress marks by
   Module:inflection, so `prop=text` also gets you stressed forms.
5. **udarenie.vip** - `https://udarenie.vip/slovo/<word>` (the old `udarenie-v-slove.ru`
   redirects here). Good display, but coverage has gaps - `рука` and `хорошо` 404 - so
   never rely on it alone.

Useful negative results, so nobody re-checks them: **wordhelp.org** has no stress feature
at all, **orf.textologia.ru** is a spelling dictionary with no per-word URL,
**wgramota.ru** no longer resolves, **my-dict.ru** and **razbiraem-slovo.ru** are not
reachable, and **context.reverso.net** returns 403 to automated fetches.

## Networks and the proxy

HuggingFace, `raw.githubusercontent.com`, Wikipedia/Wiktionary and loc.gov are
unreachable on some networks without the system proxy. `fetch_data.py` reads it from the
Windows registry (`HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings`,
`ProxyServer`, e.g. `127.0.0.1:17892`) and prints what it used; `HTTPS_PROXY` in the
environment overrides it, and `--no-proxy` disables it.

The agent's own fetch tool does not necessarily go through that proxy, which is why a
site can fail for a subagent while working for the human. If a lookup times out, check
the proxy before concluding the site is down.

## Etiquette and licensing

- These sites are dictionaries, not APIs. A song needs a handful of lookups, not a crawl;
  keep it that way. No bulk fetching.
- Wikipedia/Wiktionary content is CC-BY-SA-4.0; OpenRussian is CC-BY-SA-4.0. If you quote
  a definition back to the user, say where it came from.
- `gramota.ru` is the authoritative source; the others are convenient. When two disagree
  about a stress and it matters, trust gramota.ru, and tell the user there is a
  disagreement rather than silently picking one.

## The е/ё problem

Many lyrics write `е` where the word has `ё`, and that changes both the stress and the
vowel: `все` "all" is unstressed-ish `fsye`, `всё` "everything" is `fsyo`. The scripts
always treat a written `ё` as stressed, so the failure mode is a flattened `ё` in the
source, not a rule bug. When a line sounds wrong and contains a suspicious `е`, check
those words explicitly:

```bash
python3 $SKILL_DIR/scripts/stress.py --lookup все всё ее её поем поём
```

Report flattened-ё fixes to the user rather than making them silently: they may be
transcribing a specific recording.
