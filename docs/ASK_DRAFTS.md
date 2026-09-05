# ASK_DRAFTS.md — outbound asks, drafted and awaiting a send

`docs/EXPANSION_GUIDE.md`: *"The ask is a route, not a last resort… Draft asks in
batches, send them, and **record the send date**; a silent ask is not a closed one."*
Until now the drafts themselves lived in the operator's mail client and only their
*existence* was recorded, in gap records reading `NOT YET ASKED — DRAFTED`. That made
the wording unreviewable and the batch uncountable. This file is the drafts.

## How this file is used

1. **The operator sends. Nothing here is sent automatically, and no draft is sent by
   the agent that wrote it.** An e-mail to a named public official is outward-facing and
   irreversible; it goes when a person decides it goes.
2. **Record the send date the day it goes, never before** — in the relevant gap record
   in `docs/DATA_LAYER_GUIDEBOOK.md`, changing `NOT YET ASKED — DRAFTED` to
   `ASKED <date>`. This is the Scott rule, and it exists because two ask ledgers in this
   repo once said "held" about e-mails that had already been sent.
3. **Follow up at ~3 weeks, again 2 weeks later, and only then record the route
   UNRESPONSIVE** — which is a different claim from "no source exists". A follow-up is a
   **recovery mechanism, not a nudge**: one county Clerk answered the question that
   unblocked a whole build only on the third attempt, because her spam folder ate the
   first two.
4. **A clean, citable NO is a good outcome.** It closes a question for good and is worth
   as much as a yes. Say so in the ask, so declining is easy.
5. Replace `<YOUR NAME>` / `<YOUR E-MAIL>` with the sender's own. They are deliberately
   not written into this file, which is public.

## What is NOT here, and why

**The Iowa county-officer tranche is withdrawn, not held.** Fifteen counties were drafted
and filled (19 questions across them) and **none was ever sent**. They are gone from this
file because the operator is reviewing Iowa's county sites **by hand**, the exercise that
worked for Wisconsin — and a hand review reaches precisely the pages that stopped the
probe. Six of the fifteen were blocked by a site that **refuses this client** or sits
**behind a challenge**, which is an access control this project does not route around and
a person opening the page in a browser closes for free. Sending the batch first would ask
fifteen county auditors for details the review is about to read off their own sites.

**The treasurer-address batch is not here because the route was built.** An earlier edition
of this section held a 48-county ask pending `iowatreasurers.org`, calling that route
"unbuilt". It was built on 2026-08-29 and it works, with two gates the sweep proved
necessary: the site serves **another county's complete, plausible page with no error and no
404** for eleven of its ninety-nine ids, so the page must identify as the county AND the
address's domain must fit it; and no NAME is ever read from it. Between that and the
counties' own sites, 346 officer e-mail addresses ship. The residue — 34 treasurers and 11
sheriffs — is the manual review's, not an ask's.

**What stays here is institutional.** Asks 3, 4 and 5 go to a state agency, not a county:
none is a question a county-site review can answer, and each is a single question with a
citable yes or no at the end of it.

---

## Ask 1 — Iowa county officers — **WITHDRAWN 2026-09-03, never sent**

Drafted 2026-08-29 as a template plus fifteen filled per-county e-mails: one to each
county auditor, asking for a single missing officer e-mail address or for which of two
published names currently holds an office. **It was never sent, and the ledger says so
rather than forgetting it existed** — a withdrawn ask and an unanswered one are different
claims, and only one of them means a source refused.

Withdrawn because the operator is reviewing Iowa's county sites by hand (see *What is NOT
here* above). The questions themselves are unchanged and are recorded where a person
doing that review will meet them: the per-county reasons in
`ia/scripts/.cache/ia_county_officer_emails.json` (site published none readable / refuses
this client / sits behind a challenge), and the five counties where two directories name
different people and the card therefore names **neither** — Davis (sheriff), Henry and
Keokuk (county attorney), Humboldt and Jasper (recorder).

**If the review does not close them, redraft from what it measured** rather than restoring
this text: a page that has been read by a person is a different starting point from one
that was only probed.

---

## Ask 2 — White County, Illinois: the one clerk address in 102 without one

`il-county-clerks.json` carries a name, address and phone for all 101 counties and an
e-mail for 100. White County (Clerk Kayci Heil) is the single gap.

> **Subject:** An e-mail address for the White County Clerk's office
>
> Dear Clerk Heil,
>
> I run districtry (https://districtry.com/il/), a free, non-commercial site that shows
> Illinoisans which civic districts cover any point in the state and who represents them
> there. It lists every Illinois county clerk's office, and White County's entry is the
> only one of 101 with no e-mail address — I have your office's name, address and phone
> from the published county-clerk directory, but no address to go with them.
>
> If your office has an address it is content to have listed publicly, a one-line reply
> is all I need. If you would rather it not be listed, please just say so and I will
> record that and stop asking.
>
> I never publish home addresses or personal contact details of any kind.
>
> Thank you for your time,
> <YOUR NAME>
> <YOUR E-MAIL>

---

## Ask 3 — Iowa HSEMD: statewide NG911 service boundaries

Iowa's Homeland Security & Emergency Management Department runs a 911 program that
requires counties to submit PSAP / Fire / Law / EMS service boundaries to a state GIS
standard. No open statewide aggregate was found on the state's ArcGIS organization in the
research pass — only county-local layers (Linn, Scott). Wisconsin's equivalent layer is
shipped; Iowa's is the fleet's largest missing safety fabric.

> **Subject:** Are Iowa's NG911 service boundaries available as a statewide layer?
>
> Dear HSEMD 911 Program,
>
> I run districtry (https://districtry.com/ia/), a free, non-commercial site that shows
> Iowans which civic districts cover any point in the state. It already carries the
> state's precincts, supervisor districts, school districts and judicial districts from
> the Legislature's and the Department of Education's own published services.
>
> I understand the NG911 program has counties submit PSAP, Law, Fire and EMS service
> boundaries to a state standard. I could not find a statewide aggregate of those
> published openly — only county-local layers such as Linn's and Scott's. Is there a
> statewide layer available for public reuse, and if so where?
>
> If it exists but is not public, or is public under terms that would not permit
> redistribution, that is a completely acceptable answer — I would simply record it and
> not use the data. I would rather know than guess.
>
> Thank you for your time,
> <YOUR NAME>
> <YOUR E-MAIL>

---

## Ask 4 — Iowa Secretary of State and HSEMD: the precinct column the current polling-place file dropped

**REWRITTEN 2026-09-05, and the rewrite is the point.** This ask used to be addressed to the
Secretary of State and to read "is there a current edition?" — measured against the published
files, that is the wrong question and would have spent the operator's credibility on something
already answered. HSEMD publishes a CURRENT edition openly and without a licence
(`PollingPlaces2026`, created 2026-05-21, 1,658 points). What it does not publish is the column
that made the previous edition usable: the **2024** file carried `Precinct_Name` and joins this
app's precinct fabric at **98.0%**, while the 2026 file dropped it and its `Pre_Code` joins at
**22.0%**, matching nothing at all in Polk, Linn, Scott and Black Hawk. So the ask is now for one
column, to BOTH offices that stand behind the file — the Secretary of State supplies it and
HSEMD hosts it, and the recipient line below says so — and the whole measurement is the
`ia-polling-places` gap record's blocker.

Recipient: **both offices**. The Legislature's own CC0 polling item credits "Iowa Secretary of
State, Iowa Legislative Services Agency" as its source, and HSEMD's layer is visibly geocoder
output over a supplied spreadsheet — so the **Secretary of State supplies** and **HSEMD hosts**.
An earlier version of this draft said the SoS "does not publish it" and re-addressed the ask to
HSEMD alone, which would have asked the wrong office to change a column it does not originate.

> **Subject:** Could the statewide polling-place layer carry the precinct name again?
>
> Dear Elections Division and HSEMD GIS team,
>
> I run districtry (https://districtry.com/ia/), a free, non-commercial site that shows
> Iowans which civic districts cover any point in the state. It already carries Iowa's
> precincts from the Legislature's own published service, and I would like to be able to
> tell a reader where their precinct votes.
>
> Your current polling-place layer (`PollingPlaces2026`) carries County_Name, Pre_Code and
> the polling place's name and address. The 2024 edition also carried a `Precinct_Name`
> column, and that column is what made it possible to match each polling place to the
> precinct it serves — it lines up with the Legislature's precinct names for about 98% of
> rows. `Pre_Code` does not: it appears to be each county's own internal code, and I can
> match only about a fifth of the rows with it, none at all in Polk, Linn, Scott or Black
> Hawk.
>
> Would it be possible for the current layer to carry the precinct name as the 2024 one
> did? A single column would be enough. I am not asking for anything not already public —
> the 2024 file has it today.
>
> If the pairing is deliberately not published, or if polling places are only authoritative
> on each county's own notice and a statewide file should not be relied on for a given
> election, please tell me that — it is exactly the caveat I would want on the page, and it
> would stop me shipping something misleading. A "no" is a genuinely useful answer and I
> will record it.
>
> Thank you for your time,
> <YOUR NAME>
> <YOUR E-MAIL>

---

## Ask 5 — Iowa Department of Education: the `CommColleges2020` licence

`CommColleges2020` carries `licenseInfo: "internal use only"`. **No geometry from it is
redistributed** — `build_ia_community_colleges.py` reads three aggregate columns
(`CCname`, `NumberofDirectorDistricts`, `SUM_TotalPop20`) at build time purely to gate
its own output against a second witness. That is defensible and it is exactly the kind of
thing this project resolves rather than assumes.

> **Subject:** Reading three columns from CommColleges2020 as a build-time check
>
> Dear GIS team,
>
> I run districtry (https://districtry.com/ia/), a free, non-commercial site that shows
> Iowans which civic districts cover any point in the state. It ships Iowa's 15 community
> college merged areas, using the geometry from your published `CC_2026update` service
> and the director districts from `CC_DirectorDistricts_FINAL`.
>
> To check that build against a second source, my script reads three aggregate values —
> college name, number of director districts, and 2020 population — from
> `CommColleges2020`, whose item is marked "internal use only". No geometry or row-level
> data from that layer is copied, stored or published; the values are compared and
> discarded, and the build refuses to write if they disagree.
>
> I would like to know whether that use is acceptable to you. If it is not, I will drop
> that check and find another witness — please just say so.
>
> Thank you for your time,
> <YOUR NAME>
> <YOUR E-MAIL>

---

## Ask 6 — Jo Daviess County, Illinois: display permission under the site's new domain

> **SENT 2026-08-29 — ANSWERED YES 2026-08-31. THIS ASK IS CLOSED.** Replied on the
> original thread (*"County board district boundaries — public release, or a digital data
> order?"*) to **jkratcha@**, cc **dlascala@**, **gis@** and **akaiser@** — the operator
> kept the County Administrator on, so the "and the county" half went with it.
>
> The IT/GIS Director answered two days later: *"I confirm you are authorized to use the
> Jo Daviess County Board district shapefiles provided under GIS Digital Data License
> Agreement #008328 on the new districtry.com website as noted below in your email."*
> The permission now names the domain the site actually uses. It is quoted in full, with
> the #008328/#008382 digit transposition explained rather than tidied away, in
> `LICENSE-DATA.md` §3 — **that file, not this one, is the record.** No follow-up is due;
> the 2026-09-19 and 2026-10-03 dates this block used to carry are retired.

**This is the only ask in this file that is not about getting data.** The data is already
here, lawfully: `il/data/app/jo-daviess-county-board-districts.json` is built from the
county's own board-district shapefile, purchased 2026-08-17 under Jo Daviess County GIS
Digital Data License Agreement **#008382** ($33.50, invoice 008382), and displayed under
a separate written authorization from IT/GIS Director **Joe Kratcha** the same day. That
authorization is what makes the file publishable, and it names one thing:

> "…granting you permission to display the requested Jo Daviess County Board District
> boundaries to be provided in shapefile format on your website: **chidistricts.com** for
> public viewing." — e-mail of 2026-08-17 13:49Z

**The site has since been renamed.** chidistricts.com is now districtry.com; the old
domain 301-redirects to the new one and it is the same site, same operator, same use.
Nothing about the display changed — but the permission names a domain, and the honest
reading is that a permission naming a domain says what it says. `LICENSE-DATA.md` records
exactly that and excludes this one file from the project's ODbL grant, so nothing sweeps
the county's data into an open licence. **This ask closes that gap** — and on the day it
was sent, `LICENSE-DATA.md` stopped saying the permission "has not been re-sought" and
started naming the date it was, because a published legal statement that is a day stale is
the kind of inaccuracy this project treats as a bug.

Nothing is blocked on the answer and the county is not being asked to reconsider anything
it already decided — which is worth saying plainly in the mail, because an office that
reads this as "re-litigate the licence" is more likely to say nothing at all than to say
no.

### Recipients

| WRITE TO                                   | WHO                                            | WHY THIS ADDRESS                                                                     |
|--------------------------------------------|------------------------------------------------|--------------------------------------------------------------------------------------|
| `jkratcha@jodaviesscountyil.gov`           | Joe Kratcha, IT/GIS Director                     | He wrote the 2026-08-17 authorization, so he is the person who can say whether it travelled. The county directory still lists him in post. |
| `dlascala@jodaviesscountyil.gov` (cc)      | Diane LaScala, GIS                               | Quoted, invoiced and delivered the shapefile; closed the original thread. |
| `gis@jodaviesscountyil.gov` (cc)           | GIS/IT department mailbox                        | The address the original ask went to, and the one the county publishes. Keeps the request in the office record rather than one inbox. |
| `akaiser@jodaviesscountyil.gov` (cc)       | Angela Kaiser, County Administrator               | The "and the county" half: a licence amendment is an administrative record, not only a GIS one. **Optional** — she was never on this thread, and adding an administrator to a routine confirmation can make it read as an escalation, which is the failure mode this ask is written to avoid. Drop her if a quiet yes is likelier without her. |

**The original 2026-08-17 thread exists and a reply on it is the route** — subject
*"County board district boundaries — public release, or a digital data order?"*, eleven
messages, ending 2026-08-17 18:43Z. Replying there carries the licence number, the
delivery and Kratcha's own wording as context, which is worth more than any restatement
below. The thread also supplies the personal addresses the county's public directory does
not: **jkratcha@jodaviesscountyil.gov** (Kratcha) and **dlascala@jodaviesscountyil.gov**
(Diane LaScala, who quoted, invoiced and delivered the files, and who closed the thread).

CORRECTION, 2026-08-29. An earlier version of this section said LaScala was "no longer
listed in the county directory" and warned against addressing her by name. **That was an
inference from an absence, and it was wrong.** The county's public directory lists 41
addresses and carries neither `dlascala@` nor `jkratcha@` — it publishes office mailboxes
and department heads, not GIS staff — so it is not evidence about anybody's employment,
and the thread shows her active in the role twelve days before that claim was written.
A directory that does not list someone has not said they left.

> **Subject:** Jo Daviess board districts — same site, new domain (licence #008382)
>
> Dear Joe Kratcha,
>
> Last August your office sold me a copy of the county's board-district shapefile under
> Digital Data License Agreement #008382, and you kindly followed it with written
> authorization to display those boundaries on my website, chidistricts.com, for public
> viewing. I have honoured both: the shapefile itself has never been republished or
> passed on, the site shows only a simplified display copy, and Jo Daviess County GIS is
> credited by name on the card every time a visitor lands in one of your districts.
>
> I am writing about one small thing. **The site has been renamed.** chidistricts.com is
> now **districtry.com** — the same site, run by the same person, doing the same thing;
> the old address redirects to the new one. Your authorization names chidistricts.com
> specifically, so rather than quietly assume it carries over, I would like to ask you to
> confirm it.
>
> **A one-line reply saying the 2026-08-17 authorization applies to districtry.com is all
> I need.** If your office would prefer to issue a fresh authorization naming the new
> domain, or to have me complete a form, I am glad to do whichever is easier for you.
>
> Nothing has changed about the use itself, and to be explicit about what it is and is
> not:
>
> - The boundaries are shown on a free public map. Nothing is sold, there is no
>   advertising, and there is no charge to anyone for anything.
> - **The shapefile is not redistributed.** It has never been committed to the project's
>   public code repository and is not downloadable from the site — only a simplified
>   version for on-screen display, as your authorization contemplates.
> - The county is credited as the source wherever those boundaries appear.
> - The project as a whole was recently given an open licence, and I specifically
>   **excluded** your county's data from it, so that nothing there can be read as
>   re-licensing material that belongs to Jo Daviess County. That exclusion names licence
>   #008382 and your authorization directly.
>
> If your office would rather the boundaries came down, please just say so and I will
> remove them — the page will point readers to the county's own board page instead. I
> would much rather have a clear no on record than leave an unanswered question sitting
> under a live map.
>
> Thank you again for the help last summer; it made Jo Daviess one of the few counties in
> this part of the state whose actual board districts a resident can look up.
>
> With thanks,
> <YOUR NAME>
> <YOUR E-MAIL>

### On a yes, or a no

* **Yes** → record the date and the wording in `docs/DATA_LAYER_GUIDEBOOK.md`'s Jo Daviess
  entry, and update every place that records the domain gap: the §3 note in
  `LICENSE-DATA.md`; the `license` string in the payload
  `scripts/build_jodaviess_board_districts.py` writes (the data file re-ships only when
  the operator re-runs the builder against the offline shapefile — never hand-edit the
  JSON); the data-file note in `metro-worksheet.json`, which regenerates the note in
  `scripts/validate_index.py` (run `python3 scripts/generate_metro_files.py`); the
  hand-kept manifest note in `scripts/validate_sources.py`; and the card's fixed credit
  literal in `il/index.html` if the wording changes. (Corrected 2026-09-02: this bullet
  used to name `SOURCE_LABEL` as the string that reaches the card; the card renders a
  fixed literal and reads nothing from the file, and the 2026-08-31 yes was written to
  the `license` string, not to `SOURCE_LABEL`.)
* **No, or take it down** → the file comes out of `il/data/app/`, the dispatch entry goes,
  and the gap record `jo-daviess-county-board-districts` reopens citing the withdrawal.
  That is a real outcome and the ask should not pretend otherwise.
* **Silence** → follow up at ~3 weeks and again 2 weeks later, per this file's cadence,
  before recording the route unresponsive. The display continues meanwhile: the existing
  authorization was given for this site and has not been withdrawn.

---

## Ask 7 — Wisconsin Legislative Reference Bureau: the Blue Book's reuse terms

> **SENT 2026-09-03.** Sent by the operator from his own mailbox to
> **lrb-reference-services@legis.wisconsin.gov**, the Bureau's published reference desk.
>
> **Follow up 2026-09-24**, and again **2026-10-08**, before recording the route
> unresponsive — which would be a claim about this ask, never about the terms. Silence is
> not permission any more than it is a refusal.
>
> **WHAT IT GATES IS NARROW.** Only the two builds already shipping off the Blue Book
> (`wi-county-officers.json`, `wi-county-clerks.json`) and whether section 190's
> county-seat and incorporation-year tables can be added. Nothing else in Wisconsin waits
> on it, and the existing use continues meanwhile — the ask exists because no reasoning
> for it was ever recorded, not because a problem was found.

**This ask is about a source already in production, which is why it is worth sending.**
`wi-county-officers.json` — 72 counties x 7 offices — and `wi-county-clerks.json` are
built weekly from the *Wisconsin Blue Book*'s own county-officer tables, fetched from
`docs.legis.wisconsin.gov/misc/lrb/blue_book/2025_2026/210_officials_and_employees.pdf`.
The Blue Book's front matter reads **"(c)2025 Joint Committee on Legislative
Organization, Wisconsin Legislature. All rights reserved."**, and the volume is sold
through the Legislature's Document Sales Unit.

Measured 2026-09-02, and this is the reason for the ask: **there is no recorded
reasoning anywhere in this repo for why that notice does not apply.** Zero mentions of
copyright, licence or attribution in `wi_county_clerk_scraper.py`,
`build_wi_county_clerk_roster.py` or `build_wi_county_officer_roster.py`; nothing in
`LICENSE-DATA.md`; and the worksheet's own source block calls it "a state publication",
which is an assumption rather than a finding. Under this project's own rules an "All
rights reserved" string is not automatically a refusal — it was the text of a REQUIRED
NOTICE for Des Moines's ward layer and a real block for Piatt County's GIS — so it has to
be established, not inferred. It has been shipping unestablished.

A second reason to ask now: section `190_population_and_political_divisions` carries
per-municipality data this project would use if the terms allow — year of incorporation
for every city and village, each municipality's county (multi-county memberships
included), county seats, and the Department of Administration's own current population
estimates. None of it is shipped today.

**Recipient:** `lrb-reference-services@legis.wisconsin.gov`, the Bureau's published
reference desk and the Blue Book's own service address. `lrb.legal@legis.wisconsin.gov`
is also published; it is deliberately NOT cc'd, because cc-ing legal staff who were
never on the thread reads as an escalation — the draft instead invites the Bureau to
route it there itself.

> **Subject:** Reuse terms for Blue Book reference tables
>
> Dear Reference Services,
>
> I run districtry (https://districtry.com/wi/), a free, non-commercial site that shows
> Wisconsinites which civic districts cover any point in the state and who represents
> them there.
>
> The site currently names each county's clerk, board chair, executive, sheriff,
> district attorney, treasurer, clerk of circuit court, coroner and register of deeds.
> Those names come from the 2025-2026 Blue Book's county-officer tables, refreshed
> weekly and shown with the date of the Blue Book's own April 2025 snapshot and a link
> back to the Bureau. Only the officeholder facts are used; no part of the volume is
> republished, and the PDF is not redistributed.
>
> I want to be sure that use is acceptable to you, and to ask about one extension. The
> Blue Book's population and political subdivisions section carries the year each city
> and village was incorporated, which counties each municipality lies in, and the county
> seats. I would like to show those on the corresponding cards, credited to the Blue
> Book in the same way.
>
> I am asking because the volume's front matter reserves all rights, and I would rather
> have your answer than my assumption. If either use needs a different form of credit,
> or a licence, or if the answer is simply no, please just tell me — a clear no is a
> genuinely useful answer, and I will record it and act on it.
>
> If this is really a question for the Bureau's legal staff, I am happy to be redirected
> rather than have you forward it.
>
> Thank you for your time,
> <YOUR NAME>
> <YOUR E-MAIL>

### What each answer means

* **Yes, both** → record `ANSWERED <date>` with the wording, note the credit form the
  Bureau asks for, and the section `190` fields become a build (the county card gains a
  county seat, the municipality card a year of incorporation).
* **Yes to what ships, no to the extension** → the existing use is settled and written
  down for the first time; the extension closes for good.
* **No** → this is a real outcome and the ask must not pretend otherwise: the county
  officers and clerks are the Blue Book's, so a no means finding another source for
  them or dropping them, and the county card's officer rows come out. Both roster files
  and the weekly workflow would be affected.
* **Silence** → follow up at ~3 weeks and again 2 weeks later, per this file's cadence,
  before recording the route unresponsive. The existing display continues meanwhile;
  nothing has been withdrawn.

---

## Ask 8 — Iowa Secretary of State: a statewide list of city clerks

**This is the ask Iowa never made, and Wisconsin's whole municipal tier rests on its
counterpart.** Wisconsin ships a clerk for all 608 of its cities and villages because ONE
publisher — the Wisconsin Elections Commission — holds all 1,848 municipalities in one file,
and it arrived in reply to a single e-mail, answered in 22 minutes. Iowa's structural
counterpart is the Secretary of State: city elections run under Iowa Code ch. 376 through the
county commissioners of elections, so a list of who to contact in each city has to exist
somewhere in that chain.

Measured first, 2026-09-03, so the ask is not for something already published: `sos.iowa.gov`
answers 200 to a browser request, and neither its **Schools & Cities** page (which explains
city and school elections to voters) nor its **Research & Data** page links a clerk directory
or any document of that kind. The Iowa League of Cities publishes every city's phone and
website and names no person. No county publishes its cities' officials as map data.

*Practical note for sending — CORRECTED 2026-09-04, and the correction is the useful part.*
This section previously read that the contact page "publishes a form and three phone numbers rather
than an e-mail address, so this may need to go through the form." **It publishes an address, and the
Elections Division has its own:** `elections@sos.iowa.gov`, alongside `sos@sos.iowa.gov` and
`business.services@sos.iowa.gov`. They were missed because they are **Cloudflare-obfuscated** —
rendered as `[email protected]` with the real value in a `data-cfemail` attribute — which is the same
trick `ia/scripts/ia_county_auditor_scraper.py` already decodes for the county auditors' addresses.
A plain read of the page finds no address; a decode finds three. The site had also been rebuilt since
the ask was written: the recorded `/about/contact.html` and `/elections/index.html` paths now answer
404, and the live page is `/contact-us`.

**DRAFTED IN THE OPERATOR'S MAILBOX 2026-09-04**, addressed to `elections@sos.iowa.gov`. Not sent —
rule 1 stands, and the ledger stays `NOT YET ASKED — DRAFTED` until the day it goes.

> **Subject:** Is there a statewide list of Iowa city clerks?
>
> Dear Elections Division,
>
> I run districtry (https://districtry.com/ia/), a free, non-commercial site that shows
> Iowans which civic districts cover any point in the state and who represents them there.
> It already carries Iowa's precincts, supervisor districts, school districts, community
> colleges and judicial districts from the Legislature's and the Department of Education's
> own published services, and all six elected county offices in all 99 counties.
>
> The one level it cannot answer for is the city. It knows all 939 of Iowa's incorporated
> places and carries an office phone and website for each, from the Iowa League of Cities'
> own directory — but outside Des Moines and Waterloo, which publish their council members
> themselves, it cannot name a single mayor, council member or clerk, because I can find no
> statewide source. Is there a list of Iowa's city clerks — names and
> office contact details — held anywhere in your office or by the county commissioners of
> elections, in any form you would be willing to share? A spreadsheet or a PDF is perfectly
> usable; it does not need to be a published dataset.
>
> If no such list exists, or exists but is not something you can share, that is a completely
> acceptable answer — I would record it and stop looking, and the site would keep pointing
> readers at the city's own website instead. I would rather know than guess, and I never
> publish a name I cannot source.
>
> Thank you for your time,
> <YOUR NAME>
> <YOUR E-MAIL>

### What each answer means

* **A list arrives** — Iowa's City card can name a clerk in every city that has one, the way
  Wisconsin's does, and the `ia-municipal-officeholders` gap record closes.
* **"We do not hold that"** — a clean, citable no. The gap record's blocker gains a fourth
  measured route and the remaining ones are the per-city ladder and the per-city GIS route
  (Des Moines and Waterloo both already publish their council members in band), plus the
  sixteen cities of 939 whose own pages a sweep found machine-readable on 2026-09-04.
* **"The county auditors would have it"** — that is a pointer, and a good one: it turns 99
  asks into a route this project already has the addresses for, since all 99 auditors ship in
  `ia/data/app/ia-county-auditors.json` with an e-mail apiece.

---

# Illinois — the asks that were drafted and never written down (added 2026-09-03)

This file's own opening says why this section exists: *"Until now the drafts themselves
lived in the operator's mail client and only their existence was recorded, in gap records
reading `NOT YET ASKED — DRAFTED`. That made the wording unreviewable and the batch
uncountable."* That is still true of four Illinois asks. Their gap records say a reply is
drafted; no draft exists anywhere a person can read. They are written out below.

**Addresses come from `data/app/il-county-clerks.json`**, refreshed weekly from ISBE and
re-run 2026-09-03, rather than from a list copied into this document.

**One correction that predates these drafts.** Fayette County's clerk changed while the
clerk refresh was frozen: the shipped card named Jessica Barker for eleven days after the
county swore in **Kara Dugan** (`kdugan@fayettecountyillinois.gov`). Any Illinois ask
addressed to Barker is addressed to someone who has left. Fayette has no open ask today,
but the same freeze covered every county, so check a recipient against the current roster
before sending rather than against a draft written in August.

**And one to verify before sending.** The Christian County gap record names the clerk
"Kandi Badman"; the ISBE roster names **Jodie Badman**. The roster is the fresher source
and is used below, but confirm the name before the envelope goes out — getting a public
official's name wrong is the cheapest possible way to lose a reader.

---

## Ask 9 — Bureau County: permission the licence does not grant, or the free route instead

> **NOT YET ASKED — DRAFTED.** GIS Technician Christine Anderson sent a signed-user
> agreement and a $150 invoice on **2026-08-12**; nothing has been sent back since, so this
> has been sitting for three weeks. The operator read both PDFs on 13 Aug: the invoice is
> honest cost recovery, and the agreement's *Protection of Proprietary Rights* clause
> forbids redistribution of the data "or products derived therefrom outside of licensee's
> organization" — which is exactly what a public `bureau-county-board-districts.json` is.
> Signing as written is off the table at any price. The clause's own tail ("without
> permission from Bureau County GIS") is a valve, and this asks for it.
>
> **Do not pay the invoice before the answer arrives.** The money is not the obstacle and
> paying first would buy a file this project could not then publish.

**To:** Christine Anderson, GIS Technician, Bureau County Assessor's Office —
`canderson@bureaucounty-il.gov`
**Cc:** `ccao@bureaucounty-il.gov`, and County Clerk Matthew Eggers
`countyclerk@bureaucounty-il.gov` (who opened the thread)
**Subject:** Re: Request: 2021 county board redistricting plan — one question about the licence

> Dear Ms. Anderson,
>
> Thank you for the user agreement and the invoice — and for finding the shapefile in the
> first place. I want to be straightforward about one clause before I sign anything,
> because I think the agreement was written for a different kind of user than me.
>
> I run districtry (https://districtry.com/il/), a free, non-commercial site that shows
> Illinois residents which civic districts contain any point they click, and who
> represents them there. It is not a data product and nothing on it is sold. But it does
> work by publishing simplified boundary outlines to each visitor's browser, and the
> agreement's Protection of Proprietary Rights clause forbids redistribution of the
> datasets "or products derived therefrom outside of licensee's organization". A public
> map of Bureau County's board districts is precisely such a derived product, so I cannot
> sign the agreement as written and then do the one thing I need the file for.
>
> The clause says "without permission from Bureau County GIS", so my question is simply
> whether the county is willing to give that permission for this use. Concretely, I would
> like to publish a simplified outline of the eighteen board districts, credited to Bureau
> County GIS, with a note that the boundaries are simplified for display and that your
> office is authoritative. Every obligation the agreement otherwise imposes — crediting
> the source, describing modifications — this site already does on every card.
>
> If that is not something the county wants to grant, that is a complete answer and I will
> stop asking. In that case there is a second route that costs your office almost nothing
> and needs no licence at all: a plain list of which voting precincts (or census blocks)
> make up each of the eighteen districts. That is a public record rather than a GIS
> product, and several Illinois counties have answered exactly that way — I rebuild the
> boundaries myself from published census geography and the county's file never leaves
> your office.
>
> Either answer closes the question, and I would rather have a clear no than leave it
> open. Thank you for your time.
>
> <YOUR NAME>
> <YOUR E-MAIL> · https://districtry.com/il/

---

## Ask 10 — Clark County: direct contact for the board, and which building serves each precinct

> **NOT YET ASKED — DRAFTED**, two questions on one thread. Clerk Lee already answered this
> project once, in a single sentence that unblocked the whole county ("The County Board is
> elected by districts. I do not have maps available"), so she is a proven responder and
> the ask should be correspondingly short. Both gap records — `clark-board-contact` and
> `clark-precinct-polling` — get their ASKED date when this goes, never before.

**To:** Laura H. Lee, County Clerk & Recorder, Clark County — `clerk@clarkcounty.illinois.gov`
**Subject:** Two small follow-ups now that Clark County is on the map

> Dear Clerk Lee,
>
> Thank you again for your reply in August. Knowing the board is elected by districts let
> me build Clark County's seven districts from your office's own certified canvasses, and
> the county has been live on districtry (https://districtry.com/il/) since then —
> a resident can click their address and see their board district, their member and their
> precinct.
>
> Two small things would finish it, and a one-line answer to either is plenty.
>
> First, the board members' cards currently show the courthouse switchboard, because that
> is the only number published. If the county has a direct phone number or e-mail for
> individual board members that it is content to see listed publicly, I would list it. If
> the switchboard genuinely is the route to a board member, that is a fine answer too and
> I will say so on the card instead of leaving it ambiguous.
>
> Second, the precinct cards name a resident's precinct but not where they vote. If your
> office has a list of polling places by precinct — a page, a PDF, a spreadsheet, anything
> already prepared — I would add it. I do not need anything made specially.
>
> No rush on either; both are improvements rather than corrections. Thank you.
>
> <YOUR NAME>
> <YOUR E-MAIL> · https://districtry.com/il/

---

## Ask 11 — CCGISC: the licence question behind two whole counties

> **NOT YET ASKED — DRAFTED.** Champaign and Piatt are the only two Illinois counties this
> project records as blocked for a LEGAL rather than a technical reason: the Champaign
> County GIS Consortium sells the data under terms that forbid copying, public display and
> rehosting, and Piatt additionally asserts "All Rights Reserved" over its GIS. Both
> clerks have been asked directly and neither route reached the data — this is the ask
> that goes to the party that can actually say yes.
>
> **The recipient is the one thing not settled here.** CCGISC's own current contact should
> be confirmed from ccgisc.org before sending; the clerks below are cc'd because both have
> corresponded with this project already and can vouch that the request is what it says.

**To:** the Champaign County GIS Consortium — *confirm the current address from ccgisc.org*
**Cc:** Aaron O. Ammons, Champaign County Clerk — `elections@champaigncountyclerkil.gov`;
Jennifer Harper, Piatt County Clerk — `countyclerk@piatt.gov`
**Subject:** Permission to display CCGISC county board and precinct boundaries on a free civic map

> Dear CCGISC,
>
> I run districtry (https://districtry.com/il/), a free, non-commercial site that lets an
> Illinois resident click their address and see every civic district that contains it and
> who represents them there. It covers 91 of Illinois's 102 counties. Champaign and Piatt
> are two of the eleven it cannot cover, and they are the only two held back by a licence
> rather than by missing data.
>
> Both counties' clerks have been helpful and both pointed here: the county board district
> and voting precinct boundaries are consortium data, and the terms I have seen permit
> personal, transitory viewing while prohibiting copying, public display and hosting on
> another server. I have not copied or republished anything, and I am not asking you to
> change your licence.
>
> What I am asking is narrower: permission to display a simplified outline of the county
> board districts and voting precincts of Champaign and Piatt counties on this site,
> credited to the Champaign County GIS Consortium, with a note that the boundaries are
> simplified for display and that CCGISC is authoritative. No parcel data, no attributes,
> no bulk download, and no redistribution of the consortium's files — the site publishes
> only the outline it draws.
>
> If the answer is no, that is genuinely useful and I will record it plainly: the two
> counties' cards will tell residents that the boundaries exist and are licensed, rather
> than implying nobody has them. If a narrower permission is easier to grant than the one
> I have described, I would rather have that than nothing.
>
> Thank you for considering it.
>
> <YOUR NAME>
> <YOUR E-MAIL> · https://districtry.com/il/

---

## Ask 12 — the four second follow-ups that are now due

> **This file's rule 3 is "follow up at ~3 weeks, again 2 weeks later, and only then record
> the route UNRESPONSIVE."** Four Illinois asks have had exactly ONE follow-up and are past
> the second interval. None of them may be called unresponsive yet, and the reason is
> written into that rule: a follow-up is a recovery mechanism, not a nudge — Clay County's
> clerk answered the question that unblocked a whole build only on the third attempt,
> because her spam folder had eaten the first two.
>
> Send these as replies on their existing threads, so the history travels with them.

| County | Recipient | Asked | 1st follow-up | Owed |
|---|---|---|---|---|
| Ford | Kelsie Vaughn, `clerk@fordcounty.illinois.gov` | 3 Aug | 16 Aug | 2nd follow-up |
| Christian | Jodie Badman, `elections@christiancountyil.com` | 5 Aug (+ the Taylorville 9 question 21 Aug) | 16 Aug | 2nd follow-up |
| Piatt | Jennifer Harper, `countyclerk@piatt.gov` | 3 Aug | 16 Aug | 2nd follow-up — **NARROWED 2026-09-04**, see below |
| Knox | Scott G. Erickson, `serickson@knoxcountyil.gov` | 5 Aug | 16 and 24 Aug | already two — record UNRESPONSIVE if this one is silent |

Each follow-up restates the ONE question and offers a no. The Ford one, as the shape:

> Dear Clerk Vaughn,
>
> I am following up once more on my notes of 3 and 16 August about Ford County's board
> districts — I know these land in a busy inbox, and I would rather ask again than assume
> an answer.
>
> There is only one thing I need, and either answer finishes it. The county's published
> district map is titled 2011 but was re-uploaded in November 2021, so I cannot tell which
> plan is currently in force. And Patton 3 appears under both District 1 and District 3,
> which reads as the precinct being split between them.
>
> If you can tell me which plan the county elects under today, and how Patton 3 divides, I
> can add Ford County to districtry (https://districtry.com/il/) — a free, non-commercial
> site that shows Illinois residents their districts and representatives. If the map is
> not something your office maintains, saying so is a complete answer and I will stop
> asking.
>
> Thank you for your time.
>
> <YOUR NAME>
> <YOUR E-MAIL> · https://districtry.com/il/

**Knox is the one to watch.** It has had two follow-ups already, so a third silence is the
point at which `knox-precinct-geometry` records the ROUTE as unresponsive — a claim about
this ask, never about the county. Note also that Knox's own board-members page turned out
to be readable after all (2026-09-03), so the county is less dark than its record implied;
the precinct question is the part still genuinely open.

**The two ledgers disagreed about the 24 August note, and the operator settled it.**
This row puts 24 Aug in the follow-up column, i.e. a note that WENT, while the
`knox-precinct-geometry` blocker said the opposite in as many words until 2026-09-05: "a
fourth note was drafted 24 Aug 2026 onto the same thread" and "its draft is unchanged".
Both could not be true, and the difference was not bookkeeping — it decides whether Clerk
Erickson has been written to three times or twice, and therefore whether the ask below is
his fourth note or his third. The gap record was corrected to match THIS file on a
tie-break (a dated entry in a follow-ups column is the stronger claim, "drafted" the
weaker), and a tie-break is not a measurement, so it was flagged rather than settled.

> **Operator confirmed 2026-09-05: the 24 Aug note was sent.**

So Knox's state is ASKED 5 Aug 2026, FOLLOWED UP 16 Aug and 24 Aug 2026, silent since —
two follow-ups spent, the third queued below as Ask 12 and NOT sent, and UNRESPONSIVE
recorded only if that one is silent too. What was never acceptable, and is the reason this
sat flagged for a day rather than being quietly reconciled, is two files in one repository
saying different things about whether a stranger has been written to.

---

## Ask 13 — Adams County: an answered question, and the roster that is still open

> **NOT YET ASKED — DRAFTED 2026-09-04**, as a reply on the clerk's own thread. This one is
> a REPLY OWED rather than a new ask: Clerk Ryan Niekamp answered on **2026-08-17** and
> nobody wrote back for eighteen days. His reply contained a correction — "Adams County has
> only 74 precincts" — and acting on it found a defect in this project rather than in his
> county (see the `adams-county-board-roster` blocker: 92 was the FEATURE count of the
> county's precinct layer, which stores 74 precincts multipart).
>
> **So the precinct half of the ask was deleted before sending.** The first draft asked him
> whether his 92-shape layer was superseded; by the time it was written, the answer was
> already known and the question would have implied his GIS was stale when it is fine.
> That is this file's rule 1 — an ask is the residue of a probe — catching a draft in
> flight. What remains is the roster, which is genuinely open.

**To:** Ryan Niekamp, County Clerk, Adams County — `countyclerk@adamscountyil.gov`
**Cc:** `elections@adamscountyil.gov`
**Subject:** Re: Request: county board members by district (and a question about Quincy's aldermen)

The draft opens by conceding the correction and saying what it turned up, then asks for one
of two things: the current board membership by district in any form, or the certified 2022
general canvass. Seven of the county's twenty-one seats ship today, each from the certified
November 2024 canvass; the other fourteen were seated in November 2022, and that canvass is
published nowhere this project can read.

**The tone matters here more than usual.** He has now twice said the members are on the
website, and he is right — the block is at this end, and the draft says so in those words
rather than implying the county publishes nothing. A "no" leaves the card exactly as it is,
naming which seats it knows and which it does not.

---

## Where these drafts actually are (2026-09-04)

All eight Illinois drafts below are queued **in Gmail, as replies on their existing
threads**, so the correspondence history travels with each one. None has been sent, and
none carries a send date. On send, change `NOT YET ASKED — DRAFTED` to `ASKED <date>` in
each county's gap-record `blocker` — Illinois has no `WATCH.md`, so that blocker is the
whole ledger.

| Ask | County / office | Thread it replies on |
|---|---|---|
| 9 | Bureau — Christine Anderson, cc Assessor + Clerk | the 2021-redistricting-plan thread |
| 10 | Clark — Clerk Lee | "How is the Clark County Board elected" |
| 11 | CCGISC, cc Champaign + Piatt clerks | "Permission request: showing CCGISC district boundaries" |
| 12 | Ford — Clerk Vaughn | "Two questions about Ford County's board districts" |
| 12 | Christian — Clerk Badman | "One question about Taylorville #9" |
| 12 | Piatt — Clerk Harper | "Request: county board district and precinct boundaries (GIS)" |
| 12 | Knox — Clerk Erickson | "Knox County Board Districts 4 and 5" |
| 13 | Adams — Clerk Niekamp, cc Elections | "Request: county board members by district" |

**Two sequencing notes for whoever sends them.** Piatt's clerk is cc'd on Ask 11 AND is the
recipient of one of Ask 12's follow-ups; sending both the same day puts two requests about
overlapping data in front of her, so Ask 11 should go first and Piatt's follow-up after, or
the follow-up should be held. And Ask 11's recipient address is inherited from the existing
thread (`ccgisc@co.champaign.il.us`) — confirm it against ccgisc.org before sending, which
this file has asked for since the ask was written.

---

## After the Illinois queue

**This file is chronological, not grouped by state** — Asks 1, 3, 4, 5 and 8 above are
Iowa, interleaved with the Illinois and Wisconsin ones. The "all eight Illinois drafts
below" line belongs to the table it introduces and covers Asks 9 through 13 only; what
follows here is outside it. Same rule either way: the operator sends, and the
`ASKED <date>` goes in on the day it goes, never before.

## Ask 14 — Jones County, Iowa: the GIS file behind a map the county already publishes

> **NOT YET ASKED — DRAFTED 2026-09-04.** Not queued in Gmail; there is no existing thread
> with this office, so it is a fresh message to the County Auditor. On send, change
> `NOT YET ASKED — DRAFTED` to `ASKED <date>` in the `jones-county-supervisor` blocker in
> `docs/DATA_LAYER_GUIDEBOOK.md` AND in the Jones row of `ia/WATCH.md` — Iowa keeps the
> ledger in both, unlike Illinois.

**This is the narrowest ask in this file, and the only one whose answer is a file the office
already has.** Jones County is the ONE Iowa county carrying no supervisor-district card at all:
the Iowa Legislature's own `CountySupervisorDistricts` layer — this app's only statewide source
— holds 266 rows across 98 counties, and Jones has zero, measured by name and by its own FIPS
(105), re-confirmed 2026-09-04. Every other Iowa county's reader is told which of five districts
they live in; a Jones reader is told nothing.

Measured first, so the ask is not for something already published or derivable:

* The county DOES publish its adopted plan — `bos_districts_final_23073.pdf`, linked from its
  own Board of Supervisors page — and that PDF names all five districts, their 2020 populations
  and their composition in a text layer. It is a map, not data.
* **The extraction route this project would normally take is closed, and was measured rather
  than assumed.** The PDF has 554 vector curves of which **zero are filled**; its map body is 22
  stacked raster image strips; the largest vector path on the page is an 18×14 pt road shield.
  Reading district shapes out of it would mean sampling raster pixels, which this project does
  not do — it produces a clean, confident, wrong answer.
* **No boundary fabric this app already ships can compose them.** All five districts take PART
  of at least one township, so townships are out; and the state's precinct layer gives Jones a
  single `Castle Grove/Lovell/Wayne` precinct while the county's own map puts Castle Grove in
  District 1, part of Lovell in District 2 and all of Wayne in District 3 — one precinct across
  three districts.

So the only thing that closes this is the file the county drew the map from.

### Recipient

Whitney Hein, Jones County Auditor — `auditor@jonescountyiowa.gov` (an office mailbox, published
by the county; the Auditor is Iowa's commissioner of elections under Iowa Code §47.2 and the
office whose page publishes the district map).

### Draft

> **Subject: Jones County supervisor district boundaries — GIS file request**
>
> Dear Ms Hein,
>
> I run districtry, a free, non-commercial civic site that shows people which districts they
> live in. Iowa is at districtry.com/ia/. For Jones County it already names your office and the
> other county officers, the county's precincts, school districts and legislative districts.
>
> The one thing it cannot show is the Board of Supervisors district. The Iowa Legislature
> publishes a statewide supervisor-district map layer that covers 98 of the 99 counties, and
> Jones is the county that is absent from it — so a Jones resident is the only one in the state
> whose card cannot say which of the five districts they are in.
>
> Your office does publish the adopted plan, as the Board of Supervisors district map PDF, and I
> can read the five districts' populations and their township and city composition from it. What
> I cannot do is turn a PDF map into boundaries accurately enough to tell a specific address
> which district it falls in — and I would rather show nothing than show a line I traced.
>
> If the map was drawn in GIS software, would you be able to share the underlying file — a
> shapefile, a geodatabase, a KML, or whatever form it exists in? If it is easier, a link to a
> published service would be just as good.
>
> If the answer is that no such file exists, or that it is not something the county shares, that
> is a genuinely useful answer and I will record it as the reason the district is not shown,
> rather than keep asking. A one-line reply either way is all I need.
>
> With thanks for your time,
>
> `<YOUR NAME>`
> `<YOUR E-MAIL>`
> districtry.com

### What each answer means

* **A file, or a link to one** → build it, gate it against the county's own five published
  populations (4,128 / 4,120 / 4,137 / 4,132 / 4,129, summing to the county's 2020 total), close
  `jones-county-supervisor`, and credit the county in `docs/SOURCE_CREDITS.md`.
* **"There is no GIS file — the map was drawn by hand"** → `ANSWERED <date>`, the record narrows
  to the state aggregate as the only remaining route, and the question is closed for good.
* **"Not something we share"** → `ANSWERED <date>` with the substance. A clean no is a good
  outcome; it retires a route rather than leaving it open forever.
* **No reply** → follow up once at ~3 weeks and once at ~2 more, then `UNRESPONSIVE` — which is a
  claim about the ask, never about the county.

---

## Ask 15 — City of Marion, Iowa: four names and the ward each holds

> **NOT YET ASKED — DRAFTED 2026-09-05.** Not queued in Gmail; there is no existing thread
> with this office. On send, change `NOT YET ASKED — DRAFTED` to `ASKED <date>` in the
> `marion-council-roster` blocker in `docs/DATA_LAYER_GUIDEBOOK.md` AND in the Marion row
> of `ia/WATCH.md` — Iowa keeps the ledger in both, unlike Illinois.

**This is the shortest ask in this file, and the only one whose subject is four names.**
Marion's ward boundaries are already built and gated: Linn County publishes them, they tile
the city on the same test Cedar Rapids's five already ship on, and the map is ready to draw.
The card does not ship because a boundary that names nobody is half a card — and everything
that would name the four ward members is out of reach from this project's server.

**The recipient is an office mailbox, not a person.** `cityclerk@cityofmarion.org` is
published by the city itself on every page of its own agenda portal; no name is guessed here
because none is needed.

**One thing to be careful about in the wording, and it is the reason this ask exists.** The
city's website returns HTTP 403 to this project's server at the network edge, and its origin
answers one path with an explicit "IP … is not authorized". That is worth telling them
plainly — it is probably not deliberate, and they may want to know — but it must be said as
a fact about our server's access, never as a complaint or a request to change their security
posture. The ask is for the four names, not for an exemption.

> **Subject:** Marion's four ward council members — a quick question from a civic map
>
> Hello,
>
> I run districtry (https://districtry.com/ia/), a free, non-commercial map of Iowa's civic
> districts. You click a point and it tells you every district that covers it and who
> represents you there. There are no ads and nothing is sold.
>
> Marion already appears on it: the City card carries the city's own main number and website,
> from the Iowa League of Cities' municipal directory. Linn County publishes Marion's four
> council ward boundaries as open GIS data, and I have those loaded and checked — they cover
> the city cleanly.
>
> What I am missing is the people. I would like the map to tell a Marion resident which ward
> they live in AND who represents that ward, and I have not been able to find the council
> roster in a form I can read and keep current.
>
> I should be straightforward about why: requests from my server to cityofmarion.org are
> refused before they reach your site — I get an HTTP 403 from the site's content-delivery
> layer on every page, and one path reports that my server's IP address is not authorized. I
> mention it only so it is clear I am not asking you to do something I could look up myself;
> I am not asking for an exception or for anything to be changed on your end. Your agenda
> portal at cityofmarion.civicweb.net is reachable, which is how I found this address, but it
> does not appear to publish which ward each council member represents.
>
> So the question is simply: **who currently represents each of Marion's four wards?** Four
> names against Ward 1 to Ward 4 is all I need. If the council also has at-large members, I
> would show them on every ward's card, so knowing which seats are at-large would help too.
>
> A page I could read on a regular basis would be even better than a one-off list, since
> officeholders change — but a plain list in a reply is genuinely enough to get Marion on the
> map.
>
> If this is not something your office provides, that is a perfectly useful answer: I will
> record it as the reason Marion's ward map is not shown and stop asking. A one-line reply
> either way is all I need.
>
> With thanks for your time,
>
> `<YOUR NAME>`
> `<YOUR E-MAIL>`
> districtry.com

### What each answer means

* **Four names with their wards** → build `marion-council-members.json` with a count guard,
  add Marion as the fourth `city-ward` entry beside Des Moines, Waterloo and Cedar Rapids,
  ship the boundaries that are already measured, close `marion-council-roster`, and credit
  the city in `docs/SOURCE_CREDITS.md`.
* **A readable page** → the better outcome: a weekly workflow like the other three cities'
  rather than a list that goes stale the first time a seat turns over.
* **Names but no ward attribution** → NOT enough on its own, and the record should say so
  rather than shipping wards keyed by guess. It would still close half the gap: the names
  could ride the City card the way five other Iowa cities' officials already do.
* **"We do not provide that"** → `ANSWERED <date>` with the substance, the ward geometry
  stays unshipped for good, and the record retires the route rather than leaving it open.
* **No reply** → follow up once at ~3 weeks and once at ~2 more, then `UNRESPONSIVE` — a
  claim about the ask, never about the city.

---

## Ask 16 — five Illinois city clerks: has your ward map changed since it was drawn?

> **NOT YET ASKED — DRAFTED 2026-09-05.** Five separate notes, one per city clerk. They
> ask the same single question and are worth sending together, but they are NOT a batch:
> each city's own map is the subject, and a mail-merge that named the wrong city would be
> worse than no ask at all.

**Why these five and not six.** Eight cities name their council members by ward while the
map cannot say where those wards are (`pass9-ward-seats-without-maps`). Six have boundaries
in hand — Peoria County's own Wards layer for Chillicothe, Elmwood and West Peoria, and
Henry County's archived `Wards.shp` for Galva, Colona and Geneseo. Measured on 2026-09-05
against each city's own Census place polygon, the share of the CITY that no ward polygon
covers runs:

| City | Uncovered | Acres | Largest single piece |
|---|---:|---:|---:|
| West Peoria | 8.0% | 107 | 77 |
| Colona | 3.9% | 98 | 91 |
| Chillicothe | 3.3% | 116 | 101 |
| Galva | 2.9% | 52 | 21 (six pieces) |
| Geneseo | 1.7% | 52 | 37 |
| **Elmwood** | **0.4%** | **4** | **2** |

The ward layers this instance already ships leave Rockford 0.5% of itself uncovered,
Evanston 0.1% and Aurora 0.1%. **Elmwood is in that company and shipped on 2026-09-05; the
other five are an order of magnitude worse and are held.** Every source is 2006–2015
county-held linework, so the uncovered ground is most likely annexation the ward map never
grew to cover — which means a resident standing there HAS a ward and the layer would tell
them they have none. That is a wrong answer rather than a missing one, and it is what these
five notes exist to resolve.

### Recipients, and how each address was arrived at

| City | Recipient | Where the address comes from |
|---|---|---|
| Chillicothe | Clerk Jill Byrnes, `cityclerk@cityofchillicotheil.org` | the Peoria County Clerk's directory; an office-mailbox form, not a person's |
| West Peoria | Clerk Mary "Margie" Barnes, `city_clerk@cityofwestpeoria.com` | the Peoria County Clerk's directory — **see the domain note below** |
| Galva | Clerk Debbie VanWassenhove, `cityclerk@galvail.gov` | the city's own site |
| Colona | Clerk Charlotte Park, `office@colonail.com` | the city's own site |
| Geneseo | Clerk Paige Seibel — **no address; see below** | — |

All five domains were checked and all five route mail (MX present and resolving,
2026-09-05).

**West Peoria's two domains, for whoever sends.** The county clerk's directory gives
`city_clerk@cityofwestpeoria.com` while the city's website is `cityofwestpeoria.org`, and
**both domains accept mail** — `.com` through Outlook, `.org` through its own host. The
`.com` is what the county publishes, so that is what is drafted; nothing on the city's own
site names either address, so this is not settled here. If it bounces, `.org` is the obvious
retry.

**GENESEO HAS NO PUBLISHED ADDRESS AND NONE IS GUESSED.** Its city-clerk page carries no
e-mail at all, and every one of the five addresses on its contact page belongs to the POLICE
DEPARTMENT — the chief, the deputy chief, the FOIA officer, the department mailbox and the
community service officer. Sending a ward question to a police mailbox because it is the
only address on the page is exactly the inference this file forbids. The one published route
is the telephone the Henry County Clerk's directory gives, **309-944-6419**, so Geneseo's
note is drafted and waits on a route rather than on a send.

### The note, as sent to Chillicothe. The other four are this with the city, the clerk, the source and the measured figure changed.

> Subject: One question about Chillicothe's ward boundaries
>
> Dear Clerk Byrnes,
>
> I build districtry.com, a free, non-commercial site that shows people which civic
> districts they live in — wards, county board districts, school and fire districts, and so
> on. It carries no advertising and sells nothing.
>
> Chillicothe's four aldermanic wards are already named on the site, from the Peoria County
> Clerk's own directory of elected officials, so a resident can see who represents Ward 2.
> What the site cannot yet show is WHERE those wards are.
>
> Peoria County's GIS publishes a Wards layer that includes Chillicothe, and I have it. My
> hesitation is its age: it appears to be county-held linework drawn well before the 2020
> census, and when I compare it against the city's current limits about 3% of Chillicothe —
> roughly 116 acres, the largest single piece about 101 — falls inside no ward at all. My
> guess is that this is ground annexed since the map was drawn, which would mean those
> residents do have a ward and my map would wrongly tell them they have none. I would rather
> show nothing than show that.
>
> So one question, and either answer finishes it:
>
> Have Chillicothe's ward boundaries changed since that county map was made — and if so, is
> there a current map, shapefile, ordinance or written description I could use?
>
> If the wards have not been redrawn and the county's map is still correct, saying so in one
> line is a complete answer and I will publish it with that confirmation noted. If this is
> not something your office keeps, that is equally useful — I will record it as the reason
> Chillicothe's wards are not drawn and stop asking.
>
> With thanks for your time,
>
> `<YOUR NAME>`
> `<YOUR E-MAIL>`
> districtry.com

### The four variants, in one line each

* **West Peoria** — Clerk Barnes; Peoria County's Wards layer; **8.0%, about 107 acres,
  largest piece 77**. Highest percentage of the six.
* **Galva** — Clerk VanWassenhove; the Henry County Clerk's archived ward shapefile;
  **2.9%, about 52 acres across six separate pieces** (say "six separate pieces" — it reads
  as scattered annexation rather than one missing block, and that is what the measurement
  shows).
* **Colona** — Clerk Park; same Henry County source; **3.9%, about 98 acres, almost all of
  it one 91-acre piece**.
* **Geneseo** — Clerk Seibel; same Henry County source; **1.7%, about 52 acres, largest
  piece 37**. Held for want of an address (above).

### What each answer means

* **"They have not changed"** → the six ship exactly as Whiteside County's six did after its
  clerk confirmed the same thing on 2026-08-03, with the confirmation and its date on the
  record. This is the outcome the Rock Island precedent says is most likely.
* **A current map or shapefile** → better still: the boundary ships as the city draws it and
  the county-held linework is retired.
* **"They changed and we have no map"** → the honest close. That city stays unshipped, the
  gap narrows to name it, and nothing is drawn from a map known to be wrong.
* **No reply** → follow up once at ~3 weeks and once at ~2 more, then `UNRESPONSIVE` — a
  claim about the ask, never about the city.

---

## Ask 17 — League of Wisconsin Municipalities: terms, before any money changes hands

**NOT YET ASKED — DRAFTED 2026-09-05.** Nothing here has been bought, and nothing should
be until this is answered.

**The sweep this draft was waiting on has landed, and the draft names its figures.**
When Ask 17 was first written, a sweep of all 608 city and village websites was still
running, and the mail said "I have been through the cities' and villages' own websites"
without a count, because a count that is not finished is not a measurement. It finished
on 2026-09-05: **444 of the 608 readable, 238 pairing an executive title with a name, 206
naming none, 63 with no municipal website at all in the Commission's clerk file, 47
disallowing all crawling, 29 refusing with HTTP 403 and 25 failing the network.** The
figures are in the `municipal-officers` gap record and the mail below now states the two
that bear on the ask. **The 238 is triage and not a roster** — roughly sixteen of them are
page furniture and the sweep truncates candidate names at its own column width — which is
why the mail says "fewer than half" rather than quoting it as a result.

**This ask exists because its prerequisite is now met.** The `municipal-officers` gap
record has said since 2026-09-02 that the League route needed one thing established
first: *"What was measured is the sign-in, NOT that officer names sit behind it —
establish that before any purchase or permission ask, because the Jo Daviess route costs
money and a signature."* Measured 2026-09-05, from the League's own public pages, with no
sign-in and no account:

**THE RECORD WAS LOOKING AT THE WRONG PAGE.** `lwm-info.org/directory.aspx` — the URL the
record measured as "presenting a Sign In control" — is the League's **own staff
directory**: its employees, Executive Director through Government Affairs Director. It
answers 200 to an ordinary browser and gates nothing. (**A first version of this note said
*six employees*. That was a filter artefact** — it came from grepping the page for lines
matching `director|member|official`, which surfaces only the titles containing the word
*Director* — and an unfiltered read gives eighteen, sixteen League staff plus two League
Insurance. The six is retracted; the eighteen is not restated as a measurement of my own,
because the page could not be re-read on 2026-09-05, `/directory.aspx` now redirecting to
`/m/directory`, which timed out on every attempt. **The finding does not rest on the count either way**: what matters is that this
is the League's staff, not Wisconsin's municipal officials, and that nothing on it is
gated.) The "Sign In" seen there is the
site-wide CivicPlus header control that appears on every page of the site, including the
front page the record measured as 200 without noticing it there.

**THE MUNICIPAL PRODUCT IS A PUBLICATION, NOT A WEB DIRECTORY**, and the League describes
its contents itself, at `lwm-info.org/1236/Directory-of-Cities-Villages`:

> "The League's Annual Directory is *the* municipal phone book: well used by
> municipalities throughout Wisconsin. It lists all city and village elected officials,
> governing body meeting days… The Directory is no longer available for download from our
> website, but League members may request a free copy by emailing the League. Non-members
> may purchase a copy through our mailing lists page."

*All city and village elected officials* is both halves of this gap — the executive and
the governing body — in one document. That is the establishing measurement the record
asked for, and it did not cost anything.

**AND IT IS SOLD RATHER THAN MEMBER-GATED — THE PRICES ARE PUBLISHED.**
`lwm-info.org/713/Mailing-Lists` (which now redirects to `/713/Contact-and-Mailing-Lists`)
sells contact lists as Excel spreadsheets, and sells the Directory itself. Read
2026-09-05, with no account and no sign-in:

| Product | Contacts | Price |
|---|---|---|
| **Chief Executives** (Mayors, City and Village Managers, Village Presidents) | ~600 | **$30.00** |
| **Governing Bodies** — the other half of this gap | **~3,500** | **$180.00** |
| **Directory of Cities and Villages** — the annual publication described at `/1236/` | — | **$500.00** |
| Clerks (*the only list that contains e-mail addresses*) | ~600 | $50.00 |
| Administrators, Managers | ~230 | $10.00 |
| Finance Director, Treasurer, Comptroller, HR Director | ~670 | $35.00 |

So the whole gap has a price on it: $30 for the executive half, $180 for the governing
bodies, $500 for the Directory that carries both. **This is a decision about terms and
about money, and both numbers belong in front of whoever makes it** — which is why they
are here rather than left as "member-gated", which is what an earlier version of this
record called it and which was simply wrong.

**TWO THINGS ABOUT THE $500 DIRECTORY DO NOT MATCH ITS OTHER PAGE, AND THE NARROWER ONE
IS THE ONE ON THE ORDER FORM.** `/1236/` says the Directory "lists **all** city and
village elected officials"; the order page's own scope line says it *"Lists all **member**
city and village elected officials, governing body, and staff. Includes county and
population."* Membership is not universal, so those two sentences describe different
documents, and the second is the one attached to the price. **What the $500 actually
covers is therefore part of the ask rather than a detail to settle afterwards** — a
Directory of members only would leave every non-member municipality exactly where it is
today.

**AND THE $180 LIST CARRIES NO PHONE AND NO E-MAIL.** The same page: *"Included is mailing
information, population, and county location… Only list '#2. Clerks' contains phone
numbers, clerk email addresses, and the municipal webpage."* So Governing Bodies would
give ~3,500 names with a mailing address and nothing else — and this project already has
the one officer whose list carries contact detail, free, from the Elections Commission.
One more thing is worth saying plainly before anyone pays: **"mailing information" for a
village trustee is very often their house**, and this project never ships a home address,
so part of what the $180 buys would be dropped on arrival.

**The page also says what a buyer may do with any of it:** *"Mailing lists are emailed as
an Excel spreadsheet **for your exclusive use**."* It does not say what that excludes, and
**whether it leaves room for naming an officeholder on a free public map is exactly what
this ask is for** — the phrase is the reason to ask, not an answer to it. So **the purchase
does not settle the question — the terms do**, and paying first and asking afterwards is
how a project ends up with data it cannot use. That is the Jo Daviess lesson exactly: ask for written permission BEFORE
signing or paying.

### Recipients

| WRITE TO | WHO | WHY THIS ADDRESS |
|---|---|---|
| `league@lwm-info.org` | The League's general mailbox | The address the League's own Directory page gives for requesting the Directory, and the one on its Contact page. A terms question is an organisation's answer rather than one person's. |

### The draft

> **Subject:** Reuse terms for the Directory of City and Village Officials
>
> Dear League of Wisconsin Municipalities,
>
> I run districtry (https://districtry.com/wi/), a free, non-commercial site that shows
> Wisconsinites which civic districts cover any point in the state and who represents them
> there. It carries the Legislature's ward and district files, the Elections Commission's
> statewide municipal clerk directory, all 72 county boards, and the alderpersons and
> village trustees of eighteen cities and villages read from those municipalities' own
> pages. There are no adverts and nothing is sold.
>
> The one level it cannot answer for is the municipal governing body. Outside those
> eighteen municipalities it can name no mayor, no village president and no council or
> village board member, because I have found no source that publishes them together. I
> have been through all 608 city and village websites looking for one: I could read 444 of
> them, and fewer than half of those name an executive anywhere a program can find it, so
> reading them one at a time is not a route to a statewide answer. Your Annual Directory
> of City and Village Officials plainly does publish them together, your Governing Bodies
> list covers the same ground, and your Chief Executives list would cover the executive
> half.
>
> Before buying either I would rather ask what I may do with it, because the mailing-list
> page says the spreadsheet is "for your exclusive use", and what I would want to do is the
> opposite: show a reader the name of their own mayor or village president, or their own
> village board, on the page for their own municipality, with the League credited as the
> source and a link to you.
>
> So: would the League be willing to let a free public site display officeholder names
> from the Directory, or from the Chief Executives list, with attribution? If there is a
> licence, a fee, or a form for that, I will follow it. If the answer is simply no, that is
> a completely acceptable answer — I would record it and stop looking, and the site would
> keep pointing readers at each municipality's own website instead. I would rather know
> than guess, and I never publish a name I cannot source.
>
> Thank you for your time,
> <YOUR NAME>
> <YOUR E-MAIL>

### What each answer means

* **Yes, with attribution** — Wisconsin's municipality card names a mayor or village
  president in ~600 municipalities and the `municipal-officers` gap closes on its
  executive half; the Directory would close the governing-body half as well. The purchase
  becomes a decision about money rather than about permission, and it is the operator's.
* **No** — a clean, citable no. The gap record records the League route CLOSED rather than
  unexplored, and what remains is the per-municipality ladder, which the 2026-09-05 sweep
  has now measured and found poor: 444 of the 608 sites readable, 238 pairing an executive
  title with a name (a triage figure, not a roster), and no CMS platform covering even a
  fifth of the state, so there is no one parser to write.
* **"Members get it free"** — districtry is not a municipality and cannot join, so this
  is really the purchase route with a different price. Worth asking whether a
  non-commercial public-information use has any standing.

**Nothing is blocked on the answer.** The clerk ships statewide today, the eighteen
rostered municipalities need nothing from the League, and neither does the
per-municipality route — that route is simply a poor one, which the sweep measured rather
than assumed.

---

## Ask 19 — Whiteside County GIS: permission to display three derived boundaries

> **DRAFTED 2026-09-05, HELD. Not sent.** Ask 18 is Grundy's, on an unmerged
> branch; this takes 19 so the two cannot collide whichever lands first.

**To:** Whiteside County GIS, `llee@whiteside.org` (815-772-5185, 200 East Knox
Street, Morrison IL 61270) — the office that published both documents this ask
is about.

**Why this ask exists.** Whiteside's fire, park and library districts are
derivable today from two things the county already publishes: the `CVTTXCD` tax
code on its public `Tax Parcels` layer, and the County Clerk's `District Rates
by Taxcode Report`. Dissolved, they give 13 fire, 7 library and 5 park
districts, and the crosswalk checks out on the report's own arithmetic. Nothing
is missing.

What stops it is the county's own licence. Its GIS Data Fee Schedule says
"Whiteside County licenses our data. We require a signed license agreement
before the data will be released", and its License Agreement for Data Sharing
says "Reproduction or redistribution of the data or products derived therefrom
outside of licensee's organization or entity is expressly forbidden … None of
the data shall be electronically duplicated by any means for use by others, in
whole or in part, without express written permission of Whiteside County."

Three published boundary files are products derived from the parcel layer, so
this is not a question the fee schedule answers — buying the data would not make
displaying a derivative permitted. The clause's own tail is the route: express
written permission. **This is the Jo Daviess shape** (`LICENSE-DATA.md` §3),
where a county's GIS director authorized display in writing over a licence with
the same clause.

### Draft

> Subject: Permission to display three district boundaries derived from Whiteside County parcel data
>
> Dear Whiteside County GIS,
>
> I run districtry (https://districtry.com/il/), a free, non-commercial civic
> map. You click a point in Illinois and it tells you every district you are in
> and who represents you there. It carries no advertising and sells nothing.
>
> Whiteside County already appears on it: its county board districts, its
> precincts and its municipal officials, all from sources the county publishes.
>
> I would like to add its fire protection, park and library districts. Those are
> derivable from two things the county publishes — the `CVTTXCD` tax code on the
> public Tax Parcels layer, and the County Clerk's District Rates by Taxcode
> Report — and the result is 13 fire, 7 library and 5 park districts.
>
> I have read your GIS Data Fee Schedule and your License Agreement for Data
> Sharing, and I am writing rather than building because of the Protection of
> Proprietary Rights clause: what I would publish is a boundary derived from
> your parcel data, and the clause forbids redistributing a derived product
> without the county's express written permission.
>
> So my question is that permission, not the data — I already have everything I
> need from your public services and the Clerk's report. Concretely, I am asking
> whether Whiteside County will permit districtry to display three derived
> district boundaries publicly, on these conditions, which I will follow whether
> or not you require them:
>
> * every card naming a Whiteside district credits Whiteside County GIS as the
>   source of the underlying parcel data;
> * every card states that the boundary is DERIVED — dissolved from tax codes,
>   not surveyed — and is not for legal boundary determination;
> * no parcel data is republished: what is served is a dissolved district
>   outline, not the parcels, attributes or any part of the parcel file;
> * if the county later withdraws permission, the layers come down.
>
> If a signed agreement, a form or a fee is the right route for that permission
> rather than an e-mail, please tell me which and I will follow it.
>
> **A "no" is a genuinely useful answer** and I will record it as the county's
> decision and take the question no further. What I would rather not do is
> publish something your licence forbids because nobody asked.
>
> Thank you for your time,
> <YOUR NAME>
> <YOUR E-MAIL>

### What each answer means

* **Yes** — the three layers ship. `build_parcel_fabric_districts.py` already
  holds the sources, the code maps and the probe gates, guarded behind a
  `blocked` flag; permission retires the flag and the build runs. Record the
  permission in `LICENSE-DATA.md` beside Jo Daviess's, and put the wording on
  the cards.
* **No** — a clean, citable no. `whiteside-special-districts` stays `blocked`
  with the county's own decision recorded, and the builder's guard stays. The
  county keeps its precincts, board districts and municipal officials on the
  map, none of which are affected.
* **"Buy a licence"** — that is the fee schedule, and it does not answer this
  question: the signed agreement forbids the derived product at any price. Worth
  saying so plainly and asking again for permission specifically.

**Nothing currently shipped depends on this.** Whiteside's other layers are from
unaffected sources; the three district files are not in the tree.
