# Serbia — legislation as Markdown (LawCodex)

Legislation of the **Republic of Serbia** (Република Србија) as plain Markdown, generated from
the official consolidated texts ("Редакцијски пречишћен текст") of the **Pravno-informacioni
sistem Republike Srbije** (PIS, https://www.pravno-informacioni-sistem.rs), the free official
legal information system operated by JP Službeni glasnik for the Government of Serbia.
Language: Serbian (`sr`), Cyrillic script as published.

Part of [LawCodex](https://github.com/LawCodex): one repository per jurisdiction.

## Important: source access and coverage

The PIS servers (and www.slglasnik.com) **cannot be reached from outside Serbia** — TCP
connections time out (tested 2026-10-12 from a Japanese IP). Following the LawCodex rules,
the texts were therefore taken from **Internet Archive (Wayback Machine) copies of the official
PIS pages**. Each file records both the official URL (`source`) and the archived copy used
(`archived_url`, `snapshot_date`).

Consequences:

- Coverage is limited to the acts of which the Internet Archive holds a capture of the
  consolidated-text page (`…/eli/rep/sgrs/…/reg` or `…/reg/viewAct/<uuid>`). This is **not
  the complete body of Serbian law**: roughly 425 laws out of the ~1,000+ laws in force, plus
  some decrees and rulebooks.
- Each text is the consolidated version **as of the snapshot date** (mostly 2018–2024). Later
  amendments are not reflected. `status` is `in_force` only when the snapshot is from 2024 or
  later (in force at that date), otherwise `unknown`. Acts whose page carried the publisher's
  note that they had ceased to be valid ("НАПОМЕНА ИЗДАВАЧА: Закон је престао да важи") were
  excluded (7).
- When the PIS becomes reachable, `scripts/` can be pointed at the live site to rebuild a
  complete, current corpus.

## What is covered

| Directory | Content | Files |
|---|---|---|
| `ustav/` | Устав Републике Србије (2006, as amended 2022) and the constitutional laws for its implementation | 3 |
| `zakoni/<year>/` | Закони / законици (Acts of the National Assembly, incl. codes and laws ratifying treaties) | 425 |
| `uredbe/<year>/` | Уредбе (Government decrees) | 343 |
| `pravilnici/<year>/` | Правилници (ministerial rulebooks) — only those archived | 186 |
| `odluke/<year>/` | Одлуке (decisions) | 33 |
| `uputstva/<year>/` | Упутства (instructions) | 9 |
| `poslovnici/<year>/` | Пословници (rules of procedure) | 2 |
| `ostalo/<year>/` | Other acts present in the archive (strategies, collective agreements, tariffs, lists…) | 38 |

`<year>` is the year of original publication in the *Службени гласник РС*. File names are
`<year>-<issue>-<page/number>-<transliterated title>.md`, e.g.
`zakoni/2005/2005-079-74-zakon-o-zastitniku-gradjana.md`.

Front matter: `title` (native title), `identifier` (original *Službeni glasnik RS* issue),
`citation` (all gazette issues that make up the consolidated text, as listed by PIS),
`date` (original publication), `last_amended` (date of the last gazette issue in the
consolidated text), `status`, `source`, `archived_url`, `snapshot_date`, `retrieved`.

Structure: article labels (Члан N.) are `####` headings; parts/chapters (all-caps lines) are
`###`; article captions are **bold**; the publisher's editorial notes on amendments (e.g.
`*Службени гласник РС, број 115/2021`) are kept in italics; tables are Markdown tables or
simplified HTML.

## What is NOT covered

- Laws not captured by the Internet Archive (the majority of current Serbian legislation);
  the text of acts published after the snapshots.
- Official texts of the gazette itself (originals as published), international treaties as
  such, and most secondary legislation.
- English translations (PIS offers some, also unreachable).

## Licence

Under Article 6 of the Serbian Law on Copyright and Related Rights (Закон о ауторском и
сродним правима), laws, other regulations and official materials of state bodies are not
subject to copyright. The editorial consolidation is made by the official publisher.

## Regenerating

```
python scripts/rs_fetch.py  ../_raw/rs      # CDX query + download of archived pages
python scripts/rs_convert.py ../_raw/rs .    # HTML -> Markdown
```

Requirements: `scripts/requirements.txt`. Retrieval date: 2026-10-12.
