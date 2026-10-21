# North Carolina statute text, as published

These are plain-text conversions of four sections of the North Carolina General
Statutes as the General Assembly publishes them at
`https://www.ncleg.gov/EnactedLegislation/Statutes/HTML/BySection/Chapter_7A/<section>.html`,
fetched on 2026-10-20. They are kept here because the superior court and district
court layers are built from the TEXT of these sections rather than from any map:
each district is a list of whole counties written into the statute, and where a
county is divided, the statute lists the 2010 Census voting districts and blocks
of each part.

| file | what it settles |
|---|---|
| `GS_7A-41.txt` | the 73 superior court districts, their divisions, counties and resident judges (subsection (a), with the table already enacted for 1 January 2029), the voting districts and blocks of the nine divided counties (b), District 5's residence rule (b1), and that the 2010 Census lines govern (c), (c1) and (c2) |
| `GS_7A-41.1.txt` | that districts sharing counties form a "set of districts" with one senior resident superior court judge |
| `GS_7A-133.txt` | the 47 district court districts and their judges (a), the voting districts of Wake's six districts and Vance's two (b), and the residence rules of eight districts (b1) to (b8) |
| `GS_7A-140.txt` | that district judges are elected by the voters of their district, must live there, and serve four-year terms |

Each file is the page's text with its markup removed by `statute_text()` in
`nc/scripts/build_nc_court_districts.py`: a table cell ends in a tab and a row or
paragraph in a newline. The pages are served with Windows line endings, which the
conversion reads as plain newlines. Nothing else is changed, so a typo in the law
is a typo here: Cumberland County's block "510036004049" is printed with 12 digits
in G.S. 7A-41(b), and the builder reads it through a table that fails if the typo
is ever corrected.

**THE KEPT TEXT IS HELD TO THE LIVE PAGE.** Every build fetches all four pages,
converts them the same way and stops if any differs from the file here; a person
reads the change and then runs the builder with `--accept-statutes`, which
replaces the file. The builder's offline `--check` parses only these files and
fails if one has changed since the build record was written, so an edit here
without a rebuild is caught in CI.

`www.ncleg.gov` publishes a robots.txt of one `*` group that disallows `/WHPTest/`
and `/Ethics/` and asks for a 2-second crawl delay, which the builder honours; the
statute pages are allowed. Measured 2026-10-20 with this project's own client.
