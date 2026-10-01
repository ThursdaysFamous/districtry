# Kentucky statute and constitution text, as published

These are plain-text extractions of the PDFs the Kentucky Legislative Research
Commission publishes at `apps.legislature.ky.gov`, fetched on 2026-10-01 and
converted with `pdftotext -layout`. They are retained here because the court
and school-board layers are built from the TEXT of these sections rather than
from any map: every judicial district in Kentucky is a list of whole counties
written into statute, and every county school board division is a union of whole
voting precincts, so the statute is the boundary source.

Kentucky Revised Statutes are public records of the Commonwealth. Each file is
the section exactly as published, including its own effective date and
amendment history, so a reader can see which version this was.

| file | what it settles |
|---|---|
| `const117.txt` | that justices and judges of all four court levels are elected from districts or circuits |
| `const112.txt`, `const113.txt` | the Circuit and District Court provisions behind those tiers |
| `krs21A.010.txt` | the 7 Supreme Court districts, county by county |
| `krs21A.020.txt` | Supreme Court justices, one per district |
| `krs22A.010.txt` | that the 7 Court of Appeals districts correspond in geographical dimensions to the Supreme Court's |
| `krs23A.020.txt` | the 57 judicial circuits, county by county |
| `krs23A.040-two-divisions.txt` | that a multi-judge circuit's numbered divisions are SEATS, elected circuit-wide, with no geometry of their own |
| `krs24A.030-until2031.txt` | the 59 District Court districts in force now |
| `krs24A.030-from2031.txt` | the 58 District Court districts already enacted for 2031-01-01 |
| `krs160.210.txt` | county school boards elected by division, independent boards at large; five divisions of whole precincts |
| `krs160.211.txt` | Jefferson County's five school board divisions as 643 precinct codes |

**ONE LIMITATION IS RECORDED RATHER THAN HIDDEN.** The exact PDF URL each of
these came from was not written down at the time, and the route was not
recovered afterwards: `statute.aspx?id=<section>` serves a shell page with no
statute text in it, and four plausible direct-PDF paths all answer 404
(measured 2026-10-01). So these files are retained as the record of what was
read, and a builder reads them from here rather than re-fetching. Anything that
needs to re-verify a section against the live site has to rediscover the route
first. `apps.legislature.ky.gov` publishes no robots.txt — HTTP 404, which is
allow-all under RFC 9309 §2.3.1.3 — measured with this project's own client.
