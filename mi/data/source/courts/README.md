# Michigan judges: what the two court cards' names are built from

`mi/scripts/build_mi_judges.py` reads these files and writes
`mi/data/app/mi-judges.json`. Nothing in the build fetches.

**Why a person's browser.** www.courts.michigan.gov publishes `User-agent: *` /
`Disallow: /` (measured 2026-10-01), so no script here reads it. On 2026-11-25
Adam ruled that a public page a site refuses to scripts may be read ONCE in his
own Chrome. These two court files were read that way the same day; no check page
appeared. There is no weekly job, and none may depend on that browser
(`mi/WATCH.md` has the re-read steps).

| file | what it is |
|---|---|
| `courts-mi-court-of-appeals-judges-2026-11-25.tsv` | The court's four district pages: 24 judges, each with the page's own "Term expires" date. |
| `courts-mi-circuit-judges-2026-11-25.tsv` | The trial court directory. Its page fills each county from `/api/directory/county/<1..83>`; all 83 were read from the page, 0.6 s apart, and the circuit court entries kept, merged across each circuit's counties. 240 names. |
| `michigan-manual-2025-2026-pp471-472.txt` | The Legislature's Michigan Manual 2025-2026, "Judges of the Circuit Court", as `pdftotext -layout` gives it. Source: `https://www.legislature.mi.gov/documents/2025-2026/michiganmanual/2025-MM-P0471-P0472.pdf`, 2 pages, PDF modified 2025-12-23, SHA-256 `eec0b121f59bd18c06a653159563ff87341d2efaa60dd2f1c703e6584ef7e480`, read 2026-11-25 with this project's own token. |
| `governor-court-notices-2026-11-25.tsv` | Court of Appeals and circuit appointments from the Governor's press releases, 2025 to 2026-11-25, and one from the Attorney General. |

## What the cross-check found

- **18 of the directory's circuit "Chief Judge" names are left out.** None is in
  the Manual's table for that circuit, and none was appointed to it in a notice
  found. The Supreme Court names each chief judge, and in a county that runs its
  courts together the chief can be a probate or district judge. Amy G. Gierhart,
  the 54th Circuit's judge, is also listed as the 52nd's chief. The names are in
  `NOT_CIRCUIT` in the builder.
- **The rest matched.** Every appointee in the notices is listed (Tremblay,
  Sabree, Castka, Grillo, Bates, Stempien, Bomia, Liddell, and Bazzi, Trebilcock,
  Korobkin and Lievense on the Court of Appeals), and no one a notice says left
  is still listed.
- **Two Wayne judges have no witness but the directory**: Rula Aoun and Robbie
  Gaines, Jr. The Governor's search feed does not return every release (paged in
  full it gave 2,926 of the 3,552 it counts; Robyn N. Liddell's appointment was
  found only in the Attorney General's release), so they are kept, by name, in
  `DIRECTORY_ONLY`.
- **Four of the Manual's judges are not in the directory** and no government
  notice of their leaving was found: Sara S. Lisznyai (1st Circuit, Hillsdale),
  and Kevin J. Cox, Muriel D. Hughes and Leslie Kim Smith (3rd, Wayne). The 1st
  Circuit card says the directory lists no judge there.
- **Two changes are pending and printed as notes, not made.** Dan Osher was named
  on 2026-11-09 to Judge Christopher Yates's Court of Appeals 3rd District seat
  (term to 2029-01-01) and is not yet on the court's page. Jevona Fudge takes
  Judge Tracey Yokich's 16th Circuit seat on 2026-12-14.
- **The November 3, 2026 winners are not carried.** Their terms begin
  2027-01-01. The state's results site, mielections.us, did not load on
  2026-11-25 for this project's client (connection reset) or in Adam's Chrome.
  Eleven Court of Appeals terms end 2027-01-01 (see the "Term expires" column),
  so re-read after that date.
- Two spellings follow the Manual where the feed puts an apostrophe for an
  accent: Kwamé LeRoy Rowe and André R. Borrello.
