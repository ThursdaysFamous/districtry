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
   **Put it in the record's own `ask` block too, as `outcome: "pending"` with `who` and
   `asked`** (and `followedUp` once a follow-up goes), because the prose is for a reader
   and that block is the half a program has to agree with. A sent ask had nowhere to sit
   until 2026-10-01 — the three outcomes were all terminal — so send dates went into
   `blocker` prose, which is the free-text state those fields exist to end.
   `scripts/build_coverage_gaps.py` prints each pending ask's clock on every run: days
   since the ask, days since the follow-up, and whether either is ripe. Nothing is
   computed into a committed file, so **a pending ask never earns a level credit and
   never turns into one by the calendar** — only step 3's edit moves it.
3. **Follow up at ~3 weeks, again 2 weeks later, and only then record the route
   UNRESPONSIVE** — which is a different claim from "no source exists". A follow-up is a
   **recovery mechanism, not a nudge**: one county Clerk answered the question that
   unblocked a whole build only on the third attempt, because her spam folder ate the
   first two.
4. **A clean, citable NO is a good outcome.** It closes a question for good and is worth
   as much as a yes. Say so in the ask, so declining is easy.
5. Replace `<YOUR NAME>` / `<YOUR E-MAIL>` with the sender's own. They are deliberately
   not written into this file, which is public.
6. **A new ask takes an id that names its subject, not the next number** —
   `## Ask il-ford-board-map`, `## Ask wi-oshkosh-wards`. The numbered asks below keep
   their numbers: several have been sent and cited in letters, and renumbering a letter
   somebody has already received would be worse than the inconsistency. But the sequence
   cannot be extended safely. On 2026-10-01 three branches each drafted "the next ask"
   and two of them wrote **Ask 33**; git merges that without a conflict, because both
   headings land, and whoever renumbers one afterwards moves it out from under every gap
   record citing it. A subject id cannot collide and cannot be renumbered.
   `scripts/build_coverage_gaps.py` fails on a duplicate id and on a gap record citing an
   ask this file does not have.
7. **Before a letter says we cannot read a page, read the page's own feed.** A page
   that arrives empty and fills in its names from a feed carries that feed's address,
   its parameters and any key it gives every visitor; fetch it that way, with our own
   reader identity, and compare with what a browser shows. Open the documents the page
   links to as well, and read a scanned PDF with no text layer as an image (Clark
   County, Illinois publishes its board contacts that way). Two letters on 2026-10-06
   (Scott County, Illinois; Lansing, Michigan) told a clerk their page was unreadable
   when it was not. A real sign-in or a managed challenge is still never worked
   around. The full check is in `docs/DATA_LAYER_GUIDEBOOK.md` under "A page that
   fills itself in is read through its own feed".

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

## The mailbox record — what has been sent, what is drafted, what replied

**THE SENT FOLDER IS THE EVIDENCE OF WHAT WAS SENT. THIS FILE IS NOT.** That is the
lesson of 2026-10-01 and it is the reason this section exists in this shape. Rule 2
above — record the send date the day it goes — is a rule about writing the date down,
and for months nobody checked it the other way round: eleven letters in this file said
`NOT YET ASKED` or `DRAFTED … Not sent` about mail that had already gone, and two
letters were sent that afternoon that introduced the project to clerks who had already
been written to twice. **Before drafting to any office, search the sent folder for its
address and its domain.** A ledger entry is a hypothesis about the mailbox.

Every project letter is drafted in the operator's Gmail as well as written here, on his
instruction of 2026-10-01: *"All emails should be drafted in my mailbox along side the
repo."* **The operator sends. No agent sends.** The table below is the record of which
letters exist as drafts, which have gone, and what came back.

### Sent 2026-10-01

Thirty-six letters went out that afternoon. Counted from the sent folder, not from this
file. **Eight of them were answered within the hour**, which is worth recording as a fact
about the asks rather than about the offices: of the counties written to about which
supervisor represents which district, most answered the same afternoon and one refused.
Whatever makes that letter easy to answer — it names what the site already has, states
what it will not guess, and says a one-line no is a complete answer — is worth copying
into the asks that have been waiting for weeks.

**The New York state letter at the foot of the table went the same afternoon, at 16:09 UTC,
after that count was taken, and the count above is deliberately left at thirty-six.** That
figure is a measurement of which sent messages are project letters, and the sent folder holds
the operator's ordinary mail beside them, so adding one to it is arithmetic on somebody else's
reading rather than a reading of the folder — which is the correction this file already records
going wrong twice. The New York letter is in the table because its own message was read; the
total is not restated because it was not re-measured. It was also found by searching the sent
folder for its own address before a duplicate was drafted, which is the rule this section opens
with, working as intended.

| recipient | letter | prior contact | reply |
|---|---|---|---|
| Worth County Auditor (IA) | city officials page | none | — |
| Wisconsin Towns Association | town board members | none | — |
| City of Milwaukee GIS | permission to read Map Milwaukee | none | automatic acknowledgement only, saying the team is reviewing it. **An acknowledgement is not a permission** and the three builders stay on hold |
| Montgomery and Lee county auditors (IA) | which supervisor represents which district | none | — |
| Sioux County (IA) | the same | none | **ANSWERED same day**, in plain text under the heading "2026 Board of Supervisors": all five districts paired |
| Washington County Auditor (IA) | the same | none | **ANSWERED same day** by pointing at the county's OWN supervisors page, which states each district, plus a district map. Better than a list: a page the weekly reader can return to does not age the way an email does |
| Palo Alto County Auditor (IA) | the same | none | **ANSWERED same day** with two PDFs — a supervisor-district letter carrying the names, and a precinct letter nobody asked for — **both dated 2020**, so no name ships until she confirms the five are still serving |
| Ida County Auditor (IA) | the same | none | **ANSWERED same day**, in plain text: districts 1, 2 and 3 with their supervisors' names |
| Osceola County Auditor (IA) | the same | none | **ANSWERED same day**: all five districts paired with their supervisor |
| Dickinson County Auditor (IA) | the same | none | **ANSWERED same day**: a bare "no", which the letter itself had offered as a complete answer. It settles that the office will not supply the pairing; it says NOTHING about whether the board is elected by district, and must not be read as if it did |
| Black Hawk and Guthrie county auditors (IA) | the same | none | — |
| Calhoun County Auditor (IA) | the same | none | — |
| Pottawattamie and Wright county auditors (IA) | how many supervisors, and who | none | — |
| Tama County Auditor (IA) | the same | none | **ANSWERED same day**, in full: five supervisors with districts, and contact details that need care — District 1's address is a personal one and his telephone is outside the county's own number block, so neither ships until she says which lines are the county's |
| Franklin County Clerk (IL) | which Public Square address the board meets at | **asked 2026-08-05, followed up 2026-08-16, no reply** | — |
| Clinton County Clerk (IL) | the address where the board meets | **asked 2026-08-05, followed up 2026-08-16, no reply** | — |
| nine Michigan city and township clerks | may an automated reader see your board page | none | Ypsilanti Township **ANSWERED same day**: the clerk was passing the request to the township's technology staff, and the correction reached her at 15:23. Lansing acknowledged automatically, with no content |
| Cass County Auditor (IA) | which supervisor represents which district | none | **ANSWERED same day, USABLE 2026-10-07 and SHIPPED.** Her 2026-10-01 reply carried the pairing as an inline image that this project's mail tools could not open; the operator supplied the image on 2026-10-07 and it reads District 1 Stephen Green, 2 Mark O'Brien, 3 Wendy Richter, 4 Steve Baier, 5 Bernard Pettinger. The county's own Resolution 2022-12 names the precincts in each district, and every one of our twelve Cass precincts lies in the same-numbered district of our map, including Atlantic's five wards (1 in District 1, 2 and 3 in District 2, 4 and 5 in District 3), so the numbering is checked and the cards name the five. The reply asking her to type the list out is withdrawn and was never sent. |
| Calumet (Brillion), Pepin (Durand) county clerks (WI) | ward-to-district filing | none | — |
| Outagamie County Clerk (WI) | the New London filing | none | **ANSWERED same day**, settled: New London wards 10, 11 and 12 are all in Aldermanic District 5 |
| Brown County Clerk (WI) | how Bellevue elects its board | none | **ANSWERED same day, HEDGED**: "They appear to be at large", with the village clerk's address and a question back about whether the village had been asked. A hedge is not a statement the village has made, so it settles nothing by itself |
| Chillicothe, West Peoria, Galva city clerks (IL) | ward boundaries | none | — |
| Oklahoma State Election Board | precinct maps in the CSA Data Warehouse | none | — |
| Cherokee Nation Election Commission | council district maps | none | — |
| NYS Dept of State, Division of Local Government Services, cc the Comptroller's local-government division | is there a directory of local elected officials | none | — |

**Four of those were sent twice**, six or seven minutes apart, because two sessions
drafted the same letter from the same source and both copies went: Black Hawk, Cass,
Dickinson and Guthrie county auditors. An apology to each is drafted. **Calhoun was sent
once** and its second copy was caught as a draft before it went — the first write-up of
this said five counties and that was an overcount, read off the draft folder rather than
off the sent folder, which is the same error this section opens by naming.

**The ten Michigan clerk letters are nine.** Burton has no published clerk address
anywhere this project can find, so its letter is written and unsendable; the other nine
went between 14:48 and 14:51. Three of the nine should not have gone at all — Shelby
Township, Northville Township and Ypsilanti Township turn out to permit this project's
reader — and a correction to each is drafted as a reply on its own thread rather than as
a fresh letter, so the clerk reads it under the note it corrects. Ypsilanti's clerk had
already answered by the time the correction was written, which is the cost of the
mistake: an office did work on a request that was not needed. Michigan keeps its own
record of these asks, and the two records are to agree.

**The apologies are going out as fast as they are written**: Dickinson's and Cass's were
sent within minutes of being drafted. Cass answered the original question in between, so
her apology reached her after her own reply; that is harmless and is left as it was sent.

**Follow-up clocks start from the dates above**: a first follow-up at about three weeks
(2026-10-22) and a second about two weeks after that (2026-11-05), then `UNRESPONSIVE`,
which is a claim about the ask and never about the source.

### Drafted and waiting in the mailbox

| letter | prior contact | state of the draft |
|---|---|---|
| Bureau County GIS (Christine Anderson) | long thread; she sent a user agreement and a $150 invoice 2026-08-12 | correctly written as a reply on her own thread |
| Clark County Clerk | asked 2026-08-05, followed up 08-16, **ANSWERED 08-18** ("The County Board is elected by districts. I do not have maps available") | correctly written as a follow-up |
| Knox County GIS (Taiwo Agbaje) | long thread; he sent the precinct shapefile 2026-09-08 | correctly written as a continuation, opening with thanks for that file |
| Christian County Clerk | **asked 2026-08-05, followed up 08-16, 08-21 and 09-04 — four letters, no reply** | REWRITTEN 2026-10-01: cites all four, states that the question they asked is now closed from the county's own 2021 reapportionment plan, and asks only for the sixteen members. **ANSWERED 2026-10-07**: Clerk Jodie L. Badman sent two screenshots of the county's own board member list naming all sixteen by district; they ship on the board card, and the `christian-county-board-roster` gap record is retired |
| Henderson County Clerk | **asked 2026-07-21 (seal), 2026-08-05 and 08-16, no reply** | REWRITTEN 2026-10-01: cites them and says the August questions are answered |
| Logan County Clerk | **same mailbox written to 2026-07-21** about the county seal | REWRITTEN 2026-10-01: opens by naming that letter |
| Will County Clerk | none | first contact, correct |
| Grundy County GIS | the county CLERK was written 2026-07-21; this is a different mailbox | first contact to this office, correct |
| Whiteside County GIS (Lisa Lee) | the county CLERK answered three times in August 2026; this is a different mailbox | first contact to this office, correct |
| Hardin County Clerk (IL) | who holds the commissioner seats | **seal 2026-07-21; board 08-05, 08-16, 08-21; ANSWERED 08-24** — countywide board, and NO county website | **SENT 2026-10-01 and ANSWERED IN SEVEN MINUTES**: three commissioners, with Darrick Armstrong as chairman, Ricky Williams as vice-chairman and Michael Belford the third (she first wrote "Belfor" and corrected it herself at 19:27 the same day: "I left the d off"). That closes the county's roster gap, and it is the clearest argument this file has for the prior-contact check — the question was answered at the fourth attempt, by a clerk who had already told us twice what the county does not have. Illinois's wording said the county's web address "leads to a parked page"; the Clerk had already said there is no website, so that claim is gone |
| Johnson County Clerk (IL) | the same | **seal 07-21, ANSWERED twice that day** ("We don't have a website to point back to"); board 08-05 and 08-16, no reply | drafted 2026-10-01. Illinois's wording said the county's website "declines automated visits"; the Clerk had already said there is none **ANSWERED 2026-10-07**: Clerk Robin Harper-Whitehead named all three commissioners — Jason Taylor (Chairman), Matthew Hayden (Vice Chairman) and John McCuan — with one e-mail for the board and her own office's telephone. They ship on the County card and the `johnson-county-board` gap record is retired |
| Perry County Clerk (IL) | the same | seal 07-20; two questions 08-05; follow-up 08-16; no reply | drafted 2026-10-01 with an opening citing all three |
| Pope County Clerk (IL) | the board's form, then the names | seal 07-20; board 08-05; third note 08-16; no reply | drafted 2026-10-01, opening "This is my fourth note" |
| Scott County Clerk (IL) | the same | **NOT a first letter**: the Clerk was written to 07-19 about the seal and the State's Attorney's office answered 07-20 | drafted 2026-10-01 with both acknowledged. Illinois's note recorded Scott as having no prior contact |
| Ford County Clerk (IL) | a readable copy of the board list | **three letters: 08-03, 08-16 and 09-04**, none answered | drafted 2026-10-01. Illinois's note said two and the letter said "in August"; corrected to name September as well |
| Village of Bellevue Clerk (WI) | is the village board elected at large | none, checked rather than assumed | drafted 2026-10-01 from Wisconsin's own wording, after the county clerk endorsed asking the village ("Indeed. That's the place to start") |
| Colona, Marion (IA) city clerks; Jones County Auditor; League of Wisconsin Municipalities; Lafayette (Cuba City) and Ozaukee (Port Washington) county clerks; Kentucky Administrative Office of the Courts; Burton (MI) clerk; City of Beloit clerk; City of Oshkosh clerk; WinGIS | none for any | first contact, correct |
| *(the seven apologies, the three Michigan corrections, the nine replies and Hardin's follow-up were all SENT the same afternoon — see the section below)* | | |
| Calhoun County Auditor | sent 2026-10-01 | **was a duplicate of the sent letter**, marked do-not-send, and the operator deleted it on 2026-10-01. Nothing is waiting |

**Four Wisconsin city-clerk drafts were WITHDRAWN on 2026-10-01** — Janesville, Wausau,
Wauwatosa and Mequon — because those sites turn out to permit this project's reader and
no letter is owed. Withdrawn is not unanswered.

### Sent later on 2026-10-01 — every reply, apology and correction went the same afternoon

Read off the sent folder at 16:35, not off this file. **Seventy-three letters left the
mailbox over the whole day**, counted from the rows of
`/mnt/project-files/letters/sent-2026-10-01.md`, which lists every one with its office,
its address and its send time to the second. Of those, 68 were a first or follow-up letter
to an office, four were a second copy of a letter already sent, and one reached nobody —
so 68 is the figure a record should carry. **Thirty-one went after 15:18**: eight replies
to offices that had answered, six apologies, the three Michigan corrections, Hardin's
follow-up, and thirteen of the letters that had been sitting in the drafted-and-waiting
table — one of which, Grundy's, bounced. Nothing owed to an office that wrote to us is
still a draft. That figure was written as thirty-two and then counted, which is the right
order round only because the counting happened at all.

**TWO COUNTS IN AN EARLIER VERSION OF THIS SECTION WERE WRONG AND BOTH WERE WRONG IN THE
FLATTERING DIRECTION.** It said twenty letters, between 14:46 and 16:08, and that the nine
replies had all gone. Eight had: the ninth, the reply to Cass asking for her pairing as
text rather than as pictures, was still a draft while the sentence saying it had gone was
being written. And 14:46 is when the MORNING batch started, not the afternoon's — those
were the original asks, already recorded a section above, so the window swept in letters
it then counted twice. **A count of what went is a count off the sent folder, taken at a
stated minute, and never a count of what was drafted plus a belief that it went.** That is
the same error this whole section opens by naming, made inside the section that names it.

**What is waiting on the operator's hand is not a short list and should not be summarised
as one.** Counted from the draft folder at 16:35: twelve letters with an address — the
Ford, Johnson, Perry, Pope and Scott county clerks, the Henderson, Christian, Clark and
Bureau county offices, Knox County GIS, the reply to Cass, and Grundy's re-addressed
letter — plus three deliberately blank ones (Beloit, Oshkosh, Burton). **A FIRST VERSION
OF THIS LINE SAID FIFTEEN AND WAS WRONG IN BOTH DIRECTIONS AT ONCE**: it put Jones County
and Kentucky's court administrator among the waiting, and both had gone at 16:23 and
16:24, while it left out Knox County GIS, which this file had just counted as sent and
which is still a draft. **A LIST OF WHAT IS WAITING IS READ OFF THE DRAFT FOLDER AND A
LIST OF WHAT WENT IS READ OFF THE SENT FOLDER**, within the same minute; assembling either
from the other plus a belief is how all three of this section's wrong counts were made.

**Counted again from the draft folder at 16:36, after the seven Illinois letters and the two
replies were added: twenty-five drafts, twenty-one of them addressed and four with the address
field left empty.** The twelve-plus-three count above was correct when it was taken an hour
earlier and is left standing rather than edited, which is this file's practice everywhere. Two
things about the new count are worth stating rather than leaving to arithmetic. Twelve plus the
nine added here is twenty-one, so every addressed letter is accounted for and none has gone in
between. And the blank ones are FOUR rather than the three named above — Beloit, Oshkosh and
Burton plus one dating from 28 September — so the earlier line was a list of three, not a count
of all of them, and a reader should take the number from a count and the names from the list.

**THE GRUNDY LETTER WAS SENT AND REACHED NOBODY.** The county's own GIS Data Request page
publishes `gisdatarequest@grundycountyil.gov`, and the county's own mail server refused it
at 16:17 as an undeliverable address — a published contact point that reaches no one, which
is worth telling them. The letter already addressed the county's GIS officer by name, and
the county's staff directory publishes his own address, so it is redrafted to him, opening
by reporting the bounce. **A letter that bounced is not a letter that was sent**, and it
earns no follow-up clock until it lands.

**Four of the Iowa answers are complete, in plain text, and are buildable work rather
than a wait** — Ida (three districts), Osceola, Sioux and Tama (five each) each name
which supervisor holds which district, in prose an editor can read and cite. Washington
answered better than a list by naming the county's own supervisors page, which a weekly
reader can return to; an emailed list ages and a maintained page does not, so that is the
source to read. Three are still not usable and each for its own stated reason: Cass's
pairing arrived as pictures, Palo Alto's two documents are dated 2020, and Tama's
District 1 contact details look personal rather than official. Those three are waiting on
answers to questions already asked, not on anything further to draft.

**SEVEN MORE ILLINOIS LETTERS WERE DRAFTED AT 16:50 AND EVERY ONE OF THEM IS A THIRD
LETTER.** `il-seven-counties-board-districts` — Bond, Cumberland, Fayette, Jersey, Lawrence,
Macoupin and Marion — each about where that county's board district lines run. Before drafting,
every one of the seven was looked up in the sent folder, and the lookup confirms the ask rather
than merely agreeing with it: six show a first letter in early August and a follow-up on
16 August, every message in those threads is ours, and **not one of the six has a reply of any
kind**, so each letter's opening sentence names dates the clerk can check against their own
inbox. Jersey's thread also confirms the odd history its letter recounts — a letter on 9 August,
withdrawn the same morning, and two questions put again on 16 August.

**FAYETTE IS THE ONE THAT PROVES THE CHECK WAS WORTH RUNNING.** A search of its new recipient's
address returns NOTHING, which is correct: August's letters went to Clerk Barker and then, on the
office's own auto-reply, to Chief Deputy Clerk Cheryl Pollard. The clerk roster now names Kara
Dugan. So the letter that would have said "I wrote to you in August" would have been wrong about
the person reading it, and Fayette's opens by naming the OFFICE and the two people actually
written to. **Check who holds the office before writing "you"** — and the sent folder is what
settles who was written to, since the ledger records the county and not always the person.

**THE TWO MARION LETTERS ARE FIRST APPROACHES AND THE SEARCH IS WHAT ESTABLISHES THAT.**
`marion-wi-council-districts` asks the Waupaca and Shawano county clerks how many districts the
City of Marion's council has, the city straddling the county line and the two counties filing its
wards under two numbering schemes. Neither clerk's address appears anywhere in the sent folder or
the inbox — the only Wisconsin thread near it is New London's, a different county and a different
city — so both letters open as a first approach, correctly. **A first letter is a CLAIM about the
sent folder exactly as a follow-up is**, and it is the cheaper of the two to get wrong, because
nothing in it looks odd to a reader who has in fact heard from us before.

**The city itself is not written to, and the reason is an address rather than its robots.txt.**
Marion's site refuses automated clients, which this project obeys, and that governs what we fetch
and never who we may write to — but the Elections Commission's directory gives the city clerk a
telephone number and no e-mail, and Wisconsin's municipal clerks' addresses are withheld
statewide at their own request. So the city route is a telephone call, which is the operator's to
make, and the two county clerks both publish an address and each holds part of the answer.

**One thing was added to each letter that the ask's text did not carry**: the signature in
`docs/ASK_DRAFTS.md` ends at the site's address, and both drafts carry Adam's own e-mail above it,
as every other letter in the mailbox does. A letter asking a clerk for a one-line answer should
not make her hunt for where to send it.

**THE TAMA MAP ASK IS DRAFTED AS A REPLY RATHER THAN A LETTER, AND THAT IS THE WHOLE POINT
OF IT.** `ia-tama-supervisor-map` follows an answer, not a silence: the Auditor named all five
supervisors against districts 1 to 5 within the hour of being asked, and the obstacle is at this
end — the statewide supervisor-district layer this project draws from has three districts for
Tama where the county elects from five. So the draft sits as the third message in her own thread,
opens by saying the problem is ours, asks only what the five lines are today, and says plainly
that if the county holds no map of its own then the repair belongs with the state agency. It also
makes good a promise already made in her thread, where the reply sent that afternoon told her the
county's entry would name all five with their districts. **A letter that says the publisher we
read is wrong is a letter about the publisher**, so this one says in as many words that a map
dated January 2024 may simply predate a redistricting the county has since adopted, and blames
nobody.

**NO ATTACHMENT CAN BE READ FROM THIS SESSION, AND THAT IS MEASURED RATHER THAN ASSUMED.** The
mail tools here return an attachment's filename, MIME type, part id and attachment id and never
its content — `PLAIN_TEXT` and `FULL_CONTENT` both fill the attachment list with metadata alone,
and the attachment id's own description says the file needs a separate request this session has no
tool for. Two Iowa answers arrived that way and the inventory is written to
`/mnt/project-files/letters/iowa-palo-alto-cass.md` with no name and no district number
transcribed, because taking one out of a file nobody read is the error this project refuses
everywhere else. Two things in those messages matter anyway, and both came out of the mail BODY
rather than the files: Palo Alto's second reply settles in plain text that her 2020-labelled
documents are the plan in force, and Cass states in her own words that the pairing exists and
what each picture is. **Neither county is waiting on us to ask it anything** — both are a reading
problem now rather than a correspondence one, which is a different kind of blocker and should not
be recorded as an open ask.

**TWO REPLIES WERE OWED AND ARE DRAFTED.** Hardin County's Clerk named the county's three
commissioners seven minutes after being asked, and Palo Alto County's Auditor answered a second
time within the hour to confirm that her 2020-labelled documents are the plan in force. Both are
answers to direct questions, so both get a short thank-you naming what will ship and who it is
credited to. Hardin's also says we will not keep writing to check, because the county publishes
no website and her note is the only source there is.

**Brown County answered a second time and it is the answer that matters**: asked whether
the village had been written to, the Clerk replied "Indeed. That's the place to start."
So the Village of Bellevue letter is not merely allowed but endorsed by the county officer
who hedged, which is why it sits in the mailbox rather than being withdrawn. **A hedge
plus a pointer is a route, not a fact** — the village still has to say it.

**The duplicate sends are closed out.** All four double-sent Iowa auditors have their
apology, and so do Clinton and Franklin, whose letters had ignored two earlier ones.
Counted at 16:15: six apologies sent, none waiting. What is NOT closed is the cause — two
sessions drafting the same letter from the same source is what produced the duplicates,
and no amount of apologising prevents the next one. **One thread creates the Gmail
drafts; the state threads write the wording.**

### A prior-contact check is a FACT check on the letter, not a politeness check

The rule above says to search the sent folder before drafting. Illinois's six letters of
2026-10-01 show what that search is actually for, and it is not only the opening line.

**Two of the six were about to tell a clerk something she had already corrected us
about.** Hardin's letter explained the missing roster by saying the county's web address
"leads to a parked page"; Clerk Cowsert had written on 2026-08-24, "Our county board is
elected countywide. And we do not have a website in Hardin County." Johnson's said the
county's website "declines automated visits"; Clerk Harper-Whitehead had written on
2026-07-21, "We don't have a website to point back to." Both explanations were drawn from
this project's own probe records, which describe what a request to a published address
returns, and neither was checked against what the office had said. **A measurement of a
host is not a statement about a county**, and when the county has already made the
statement, the measurement is the weaker source.

**And two counts were wrong in the direction that reads as careful.** Scott was recorded
as having no prior contact and has two threads; Ford was recorded as having had two
letters and has had three, the most recent on 2026-09-04, so a letter saying "I wrote to
you in August" would have understated how often that office has been written to.

So the check has three parts, and the first is the one that matters most: does anything
the letter ASSERTS contradict what this office has already told us; how many letters has
it actually had, and when; and does the opening say so.

### Replies are read for what they refuse, not for what they seem to settle

Three of 2026-10-01's answers had to be read twice, and each one would have been
mis-recorded on a first reading.

- **Dickinson County's whole reply is the word "no".** The letter it answers had offered
  a one-line no as a complete answer and had already said the map draws the county's
  supervisor districts, so the refusal is of the district-to-supervisor pairing and says
  NOTHING about whether the board is elected by district. A bare no takes its meaning
  from the question.
- **Cass County's answer arrived as a picture.** The Auditor states the office keeps the
  pairing, which is the substantive answer, but the list itself is two inline images with
  a 2022 map attached, so nothing can ship until a person reads the names off it. An
  answer in hand is not a fact in the file.
- **Brown County's answer is hedged.** "They appear to be at large" is a county officer's
  impression of a village's own arrangement, offered with the village clerk's address and
  a question back about whether we had asked her. Recording it as settled would publish an
  inference as a statement.

### Eight Illinois counties owe no board-membership letter

Illinois re-read the county websites on 2026-10-01 and found that Bond, Bureau,
Cumberland, Jasper, Lawrence and Piatt publish their board members themselves, so no
letter about membership is owed to any of them; Scott and Macoupin publish too and are
being checked again, so letters to those two are held rather than cleared. **The mailbox
was searched and holds no board-membership draft to any of the eight**, so there was
nothing to mark do-not-send — the Bureau draft in the table above asks about the licence
and the invoice, which is a different question and still open. This is the sent-folder
rule pointing the other way: a letter the repository thinks is owed can be owed to
nobody, and the county's own page is the evidence.

### Still with no letter to draft

A letter cannot be put in the mailbox until somebody writes it. These have a recipient
and an argument here and no wording: Asks 13, 25, 33, `wi-oshkosh-council` and
`ia-pottawattamie-tama-wright-boards`. Ask 11 (CCGISC) has wording and no recipient
address. The thirteen Illinois county letters that exist only in state notes are being
rewritten as follow-ups, because every one of them bar Scott was asked in early August
and followed up on 2026-08-16, and Jasper (2026-08-17) and Hardin (2026-08-24) answered.

### Two earlier disagreements, kept because they are the reason for this section

- **Ask 8** reads `DRAFTED IN THE OPERATOR'S MAILBOX 2026-09-04 … Not sent`, and the
  sent folder carries *"Is there a statewide list of Iowa city clerks?"* to
  `elections@sos.iowa.gov` on **2026-09-04**.
- **Ask 12's follow-ups** to Ford, Christian and Knox counties are likewise recorded as
  held, and all three went on **2026-09-04**.

### Six more replies landed on the afternoon of 2026-10-01, and two of them answer an ask outright

Read at 18:00 UTC. Every one of these arrived **after** the letters recorded above went out, so
this is the first pass over them.

| Who answered | What they said | Whose question it was |
|---|---|---|
| Ozaukee County Clerk (WI), 17:33 | Port Washington Ward 9 is in aldermanic district 1 and county supervisor district 4 | the six-county ward-to-district ask |
| Calumet County Clerk (WI), 16:56 | Brillion elects its council **at large**, and the two wards its filing omits are **bare land** rather than missing data | the same ask |
| Kentucky AOC, 17:16 | the join **is** published, two ways: a page per county, and a directory search that returns a table | the Kentucky judges ask, answered |
| Hardin County Clerk (IL), 16:15 | three commissioners, named, elected countywide | an eight-week-old thread, now closed |
| Oklahoma State Election Board, 16:52 | the warehouse is downloadable, and permission and modification questions **belong to the OU Center for Spatial Analysis**, not to the board | the Oklahoma precinct ask, redirected |
| NY Department of State, 17:26 | the Department takes its municipal contact information **from the Comptroller**, and is not sure the Comptroller can release it | the New York local-roster ask, redirected |

**TWO OF THE SIX ARE REDIRECTIONS AND A REDIRECTION IS NOT A REFUSAL.** Both name the office
that actually holds the thing, which is more than silence gives and more than a no gives. The
Oklahoma board's answer also settles a question the fleet's own rule would otherwise have to
argue: the mapping centre is the **state's contracted mapping provider** rather than an
independent university dataset, which is why its warehouse is where the board's own maps page
sends a reader.

**AN ACKNOWLEDGEMENT IS NOT SENT WHERE A FOLLOW-UP MIGHT BE NEEDED IN THE SAME BREATH.**
Ozaukee, Calumet and Hardin each answered completely, so each has a short reply drafted saying
what will be published and crediting the office — which is a correction opportunity, and the
reason these are worth sending at all. Kentucky and Oklahoma have none yet: until somebody
reads the two pages the AOC named and confirms they carry the circuit **number** rather than
only the county, a thank-you would be claiming an answer that has not been checked, and a
second message a day later is a worse use of the correspondent than one message that waits.

**NEW YORK'S REDIRECTION LEAVES A QUESTION ONLY THE PERSON WHO ANSWERED CAN SETTLE**, and it is
drafted: does the information the Department holds **name the people in office**, or is it
office contact details without names? Municipal contact information and a roster of
officeholders are not the same thing, and the answer decides whether the Comptroller is worth
writing to at all. Asking him costs one line; asking the Comptroller for the wrong dataset
costs that office real work.

### A DUPLICATE ACKNOWLEDGEMENT WAS DRAFTED AND WITHDRAWN, AND THE CAUSE IS A SWEEP THAT DID NOT READ THE DRAFT FOLDER FIRST

Hardin County's reply already had an acknowledgement waiting in the mailbox, written half an
hour earlier. A second one was drafted anyway, because the sweep read the **inbox** for new
replies and did not check the **draft** folder for answers already written to them — so a reply
that had been handled looked exactly like a reply that had not. The duplicate was deleted
minutes after being created, which is a withdrawal of this session's own mistake rather than a
judgement about a draft the operator was waiting on; those are still his to delete.

**SWEEP THE INBOX AND THE DRAFT FOLDER IN THE SAME PASS.** A reply is outstanding only if
nothing is drafted to it, and the draft folder is the only place that says so.

### A COUNT CARRIES THE MINUTE IT WAS READ, OR IT CARRIES NO MINUTE AT ALL

Twice on 2026-10-01 a draft-folder figure was reported with a reading time attached when it had
been reached by adding to the previous figure instead. Both times the numbers happened to be
right, which is the dangerous part: the figures survived and the method did not exist. The
second instance was the worse one, because the first had already been corrected an hour before
and the correction asserted a method that was then not used.

**The folder at 18:00 UTC held 32 drafts, 28 of them addressed and 4 blank.** One of the 28 was
then deleted as the duplicate described above, so 31 and 27 is arithmetic and is labelled as
arithmetic — the mailbox was not re-read after the deletion, and no time is attached to those
two numbers.

### A FOURTH LETTER ANSWERED IN THIRTY-NINE MINUTES, AFTER THREE WENT UNANSWERED

Three letters went to the Ford County Clerk and none was answered — 3 August,
16 August and 4 September — and the status table above records that run. A fourth
went at 18:12 UTC on 2026-10-01 and Clerk Kelsie Vaughn replied at 18:51 with the
whole board: twelve members under three numbered districts, four to a district,
with Chase McCall named Chairman and Carson Vaughn Vice Chairman, over the Clerk &
Recorder's own office address and telephone number.

**Three letters unanswered is not a closed door**, and reading it as one would have
cost this roster. Nothing about the county changed between September and tonight;
the fourth letter arrived on a day somebody read it. That is the case for sending
the fourth letter rather than recording the county as unresponsive and moving on —
and it is the counterpart to the correction above, which says silence earns a
project nothing. Silence earns nothing AND proves nothing.

What it answers is bounded and the thank-you says so to the Clerk rather than
leaving her to guess: it names the twelve PEOPLE, from the office that maintains
them, and says nothing about the three district BOUNDARIES, which are Ford's actual
blocker, its maps being scans with no map file behind them. No geometry ask was
reopened with her in the same breath.

Two traps for whoever ships it. The Clerk and the Vice Chairman are both named
Vaughn, so a surname is not a key here. And the roster arrived by letter rather
than off a page, so nothing re-reads it weekly — it is a dated snapshot from the
county and has to be labelled as one, the way the two document-sourced rosters
already are.

### AN ANSWERED REFUSAL IS NOT SILENCE, AND MUST NOT BE LEFT READING LIKE IT — WRONG, SEE THE CORRECTION BELOW

Ypsilanti Township's Clerk answered three times on 2026-10-01 and the third answer
was no. At 15:13 UTC Debbie Swanson referred the request to the township's
technical staff; at 15:23 this project corrected its own claim, having rechecked
and found the board page readable after all; at 18:23 she wrote, in full: "Our
system will not allow this request at this time."

So the outcome is **asked-and-refused**, which is a different thing from
asked-and-waiting and wants recording as its own state. No thirty-day clock
applies to it, there is nothing to follow up, and a record that left it looking
like an unanswered letter would misdescribe a correspondent who answered promptly
three times. Under the project's coverage standard a published record substitutes
for a source that has been asked and has refused, which is exactly what this is.

The reply this thread drafted to that refusal was removed from the draft folder
unsent. **Deleting a draft is the operator's call**, so it has not been recreated,
and the removal is recorded here rather than quietly undone.

**CORRECTED 2026-10-01, WITHIN THE HOUR: SHE REFUSED NOTHING, AND THIS WHOLE SECTION
IS WRONG ABOUT WHAT HER THIRD ANSWER WAS.** The wording above is left standing under
this correction rather than edited away. The request Debbie Swanson answered at 18:23
had already been **withdrawn** at 15:23, when this project rechecked the township's
board page, found it served to our own reader, and wrote to say so. Her "our system
will not allow this request at this time" is therefore an answer to a question nobody
was still asking, and reading it as a refusal invented a blocker. Ypsilanti Township's
whole seven-member Board of Trustees has been on the map since 18:43 UTC, read from the
township's own board page and dated, so nothing about this level is unanswered and no
refusal record is wanted. The outcome is **a reply to a withdrawn request**, which earns
nothing and blocks nothing.

The reading that went wrong is worth naming, because it is not carelessness about the
facts: every sentence above about who wrote what and when is accurate. What it got wrong
is which question the last letter answered. **A LATE REPLY IS A REPLY TO THE LETTER IT
QUOTES, NOT TO THE STATE OF THE WORK TODAY** — when a request has been corrected or
withdrawn in between, check which version the correspondent was holding before filing
their answer as a verdict on anything.

### TAMA'S MAP ARRIVED, AND THE THANK-YOU ASKS NOTHING

Auditor Karen Rohrs answered `ia-tama-supervisor-map` at 18:24 UTC on 2026-10-01 with
the county's own supervisor district map attached — a drawn map of all five districts,
which is the whole of what was asked. The Iowa work has read it and it settles the
blocker: the five lines can be drawn as the county draws them rather than as the
statewide layer carries them, which had three. She has now answered three times in one
afternoon, and the reply drafted to her asks for nothing further and says so in as many
words. Both the five supervisors and the five lines are credited to her office and
dated 1 October 2026.

That is four Iowa counties answered from one afternoon's letters, and the shape worth
keeping is the one `ia-tama-supervisor-map` already recorded: the ask opened by saying
the problem was at this end, and the county answered it by sending the thing it holds.

### WHERE THE MAILBOX STANDS AT THE PAUSE, 2026-10-01 19:31 UTC

The project pauses until Tuesday 6 October. Inbox monitoring stops, nothing is
scheduled, and the drafts are left exactly as they are. This is the state to pick
up from.

**THIRTY-SEVEN DRAFTS WAIT IN THE OPERATOR'S FOLDER AND NOT ONE HAS BEEN SENT.**
Nothing here sends; the operator sends. The five where somebody is actively
waiting on an answer from us are the four Iowa replies (Ida, Osceola, Sioux,
Washington) and Cumberland's one yes-or-no question. The rest are first
approaches, thank-yous and follow-ups that can go whenever he gets to them.

What was added on 1 October, by county: Ford's thank-you; Tama's map thank-you;
Kentucky's Jefferson reply; Cumberland's 500E question; Iowa's twenty — four
replies and sixteen first letters, counting Linn's.

Four drafts remain deliberately blank in the `To` field and are listed for the
operator rather than guessed at: Oshkosh, Beloit, Burton and the wingis host.

**WHAT ARRIVES BEFORE TUESDAY IS NOT LOST AND IS NOT ROUTED EITHER.** Replies will
land in the inbox unread by this project. The first action on Tuesday is a sweep
of the inbox and the draft folder in one pass, because a draft missing from the
folder is ambiguous until the sent folder is checked — it may have gone or it may
have been deleted, and only the sent folder tells the two apart.

**ONE CLOCK IS RUNNING AND IS RECORDED RATHER THAN REMEMBERED**: Tama's
precinct-list follow-up is held for around 8 October, which falls after the pause
ends.

Two findings from the evening belong with the pause because they will be needed on
Tuesday. Gmail's `update_draft` detaches a reply from its thread, so a reply draft
is rebuilt with `create_draft` and never edited in place. And a changed ask record
is not automatically a changed letter: the nineteen Iowa drafts were diffed rather
than rewritten, because the correction was to the record's own prose.

**A FOLLOW-UP IS HELD FOR AROUND 8 OCTOBER, AND DELIBERATELY KEPT OUT OF THE THANK-YOU.**
The Iowa work found that the five-district plan she sent is NEWER than the precinct data
this project holds, so the next thing Tama needs is the county's current precinct list.
That is a second ask, and putting it in a letter whose whole point is that nothing further
is being asked would have made the thank-you untrue in its own closing line. It waits
about a week, as its own letter, and it is recorded here rather than left to be
remembered. **A THANK-YOU THAT SAYS IT ASKS NOTHING MUST ASK NOTHING**, even when the next
question is already known.

### A KENTUCKY REPLY ASKS WHY A POLICY ABOUT OUR READER STOPS A PERSON READING A PAGE

The Court of Justice's Data Officer answered `ky-judges-by-district` twice. The first
answer solved it — the county pages on the Court's own site pair each sitting judge
with a circuit and district number, which covered 119 of the 120 counties. The second,
at 18:56 UTC on 2026-10-01, is the interesting one. Jefferson County's page names no
judges, he could not find the page that does, and he asks, reasonably: the directory
asks automated clients not to read it, but why would that stop a person reading it by
hand today? He adds that his division cannot produce reports identifying individuals,
and that anything static he sent would say exactly what the directory already shows.

**THE ANSWER IS NOT ABOUT PERMISSION, IT IS ABOUT WHAT HAPPENS AFTERWARDS**, and the
drafted reply says so plainly: a page our weekly reader may not visit cannot be
re-read, so anything taken from it by hand becomes a snapshot that ages while still
looking current, which is the one thing this project will not publish. A static list
from his office is a different thing — dated, citable, and labelled as supplied rather
than as checked weekly — so the reply accepts that offer, says it will ask for no
routine, and says that a no is an acceptable answer that will be recorded as one.

**IT IS WORTH NOTING THAT HE IS RIGHT THAT NOTHING FORBIDS THE MANUAL READ.** The rule
in this project is about the crawler, not about a person, and a reply that implied
otherwise would be overstating a policy in order to sound careful. What the reply
claims instead is a standard this project actually holds itself to.

### THE AFTERNOON'S SENDS, AND WHAT A FIRST LETTER DOES NOT EARN

Between 18:02 and 18:15 UTC on 2026-10-01 the operator sent fifteen letters: five replies this
thread had drafted to answers that arrived during the afternoon (Tama, Hardin, Calumet, Ozaukee
and the one-line question to the New York Department of State), follow-ups in the Palo Alto and
Tama threads, and thirteen first approaches — Shawano in Wisconsin; Marion, Macoupin, Lawrence,
Jersey, Fayette, Cumberland, Bond, Ford and Scott in Illinois; the Grundy County GIS officer on
the redrafted letter; and the OU Center for Spatial Analysis.

**A FIRST RECORD OF THAT BATCH SAID THEIR "THIRTY-DAY CLOCKS START TODAY", AND THAT IS WRONG IN
THE DIRECTION THAT WOULD HAVE EARNED CREDIT THIS PROJECT HAD NOT EARNED.** A first letter starts
no clock that counts for anything. Silence substitutes for an answer only after a follow-up **and
then** thirty days, and only once a person records the outcome as unresponsive. So a first
approach is `pending` and nothing more: it records that we asked, never that we were refused.
Keeping a follow-up due date is useful; calling it "the clock" invites a later reader to take
thirty days of quiet as a measured no.

**The Oklahoma letter went fifteen minutes after it was drafted.** That is the argument against
drafting with a blank `To` field and a note explaining why: there was no window in which anybody
would have gone looking for the address. Its recipient was verified first — see below.

### A RECIPIENT CAN BE UNREACHABLE AT THE HOST A RECORD NAMES AND PUBLISHED SOMEWHERE ELSE

`ok-csa-precinct-terms` recorded that `csa.ou.edu` does not resolve from this project's network
and concluded that the centre's address "must be read off the centre's own contact page in a
browser". The first half is still true and the conclusion was wrong: **the centre's site is not
at that host any more.** It is at `www.ou.edu/ags/csa`, which answers normally, and whose robots
policy permits this project (93 bytes, one binding group, no rule matching any path read). Nobody
needed a browser; the host had moved.

Read off the centre's own Faculty & Staff page: Chengbin Deng, PhD, **Director**
(`cdeng@ou.edu`); Todd Fagin, PhD, **Executive Associate Director** (`tfagin@ou.edu`); Zakary
Gipson, Senior GIS Analyst (`zakarygipson@ou.edu`), also named on the centre's own GIS Data
Warehouse page. The letter went to the Director with the Executive Associate Director copied.
**This project's preference for an office mailbox over a person's desk could not be honoured
here, and that is a measurement**: the centre's Contact Us page offers a web form and no address
at all, and the only general address it publishes anywhere is a footer maintenance byline on a
domain with no address record, so whether mail to it is delivered could not be tested. Gipson
was considered and not used — the warehouse page names him for help navigating that site, which
is a different question from what may be done with the files.

**A SEARCH ENGINE'S SUMMARY IS NOT A SOURCE, AND IT ANSWERED THIS ONE CONFIDENTLY.** A first pass
produced all three names, all three titles, a street address and a telephone number out of a
search result's own summary text. Every one was re-read on the centre's own pages before any of
it was used, and the telephone number was not used at all.

### TWO BOUNCES IN ONE DAY, BOTH ON AN ADDRESS SOMEBODY HAD PUBLISHED

`gisdatarequest@grundycountyil.gov`, printed on Grundy County's own GIS Data Request page, was
refused as undeliverable at 16:17. `kristy.opperman@co.waupaca.wi.us` was refused at 18:09 with
`550 permanent failure ... (kristy.opperman@co.waupaca.wi.us:blocked)`.

**"BLOCKED" IS NOT "NO SUCH USER", AND READING IT AS A STALE ADDRESS WOULD BE A GUESS.** The
mailbox may well exist and the county's mail server may be refusing this sender. Waupaca was
redrafted to the Chief Deputy County Clerk, whose address the county's own department page
publishes, opening by saying the earlier copy was refused — and if that bounces the same way the
cause is the county's filtering rather than the address, and a third address will not fix it.

**A LETTER THAT BOUNCED IS NOT A LETTER THAT WAS SENT.** Neither county is awaiting a reply and
neither has a follow-up due. Recording either as silence would be wrong in a way nothing else
would later catch.

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

> **SENT 2026-09-03. ANSWERED 2026-09-10. CLOSED.** Sent by the operator from his own
> mailbox to **lrb-reference-services@legis.wisconsin.gov**, the Bureau's published
> reference desk.
>
> **THE REPLY, IN FULL**, from **Madeline Kasper, Managing Legislative Analyst**,
> Wisconsin Legislative Reference Bureau:
>
> > Hello Adam,
> >
> > These uses seem acceptable to us. Thanks for checking in.
> >
> > Madeline
>
> **QUOTE IT; DO NOT PARAPHRASE IT AS "APPROVED" OR "LICENSED".** It is an informal
> permission from a named officer of the Bureau — the Jo Daviess shape — so the record
> carries her words, her name, her title and the date, and a reader judges. "Seem
> acceptable to us" is what she wrote.
>
> **THE SCOPE IS THIS ASK'S, NOT THE REPLY'S.** One plural answers what was put to her,
> so what "these uses" covers is read off the outgoing message below:
>
> 1. **The use already shipping**, now confirmed rather than assumed —
>    `wi-county-officers.json` exactly as it ships: county officials from the 2025-26
>    volume's county-officer tables, refreshed weekly, the April 2025 snapshot date
>    attributed, linking back to the Bureau. The front matter's reservation of rights is
>    what this answers.
> 2. **The section 190 extension**, which was closed the day before and is open now:
>    incorporation year, county and county seat for cities and villages, under the same
>    attribution.
>
> **THREE LIMITS RIDE WITH IT**, because the permission rests on what the ask
> represented. No part of the volume is republished and the PDF is not redistributed —
> this does not authorise shipping it, mirroring it, or publishing bulk tables. Only the
> specific facts named. A different Blue Book table is outside this answer and needs its
> own ask rather than a citation of this one.
>
> **NO CREDIT FORMAT WAS IMPOSED**, and that is an answered question rather than an
> unanswered one: the ask asked directly whether either use "requires a specific form of
> credit, a license, or is not permitted", and she named none. She also did not route the
> inquiry to the Bureau's legal staff, which the ask had offered.
>
> **THE 2026-09-24 AND 2026-10-08 FOLLOW-UPS ARE RETIRED.** They were scheduled for a
> question that now has an answer. Nobody writes to Kasper about this again.
>
> **THE EXTENSION IS UNBLOCKED, NOT DECIDED.** Permission to use those facts is not a
> decision to ship them; whether a Wisconsin card should carry municipal incorporation
> facts goes through the normal new-row route with its own review.

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

> **SENT 2026-09-04 to `elections@sos.iowa.gov`**, subject "Is there a statewide list of Iowa
> city clerks?". No reply on that thread as of 2026-10-01, so one follow-up is due and the
> thirty-day silence mark falls on 2026-10-04.
>
> **THE SEND WAS RECORDED NOWHERE FOR TWENTY-SEVEN DAYS**, and it is worth saying how that
> happened, because the failure is invisible from inside the repository. This file and the
> `ia-municipal-officeholders` blocker both read `NOT YET ASKED — DRAFTED` until 2026-10-01,
> when the operator's own sent folder was read and the message was sitting in it. Nothing was
> wrong with the letter and nothing was wrong with the ledger's rules; what was missing is
> that the rule says the send date is written on the day it goes, and the only person who can
> write it is the one who sends. **A ledger entry that is wrong in the "still to do"
> direction looks like pending work rather than an error**, so nobody counts the days, no
> follow-up falls due, and the gap record goes on telling readers the office was never asked.
> When an ask's clock matters, read the sent folder and not the ledger.

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

*RE-MEASURED 2026-09-25, and the letter was corrected rather than the record above.* An
unsent draft is not history: it is a statement that will be made to a public official on
the day it goes, so its claims have to be true then. Two of them had stopped being true.

**"carries an office phone and website for each" was never right, and the gap record
says so one sentence after contradicting itself.** `ia-city-contact.json` ships 939
cities with **927** telephones and **531** websites — the League's own table gives 935
and 536, so the join drops a few more. The blocker in `docs/DATA_LAYER_GUIDEBOOK.md`
states 935 and 536 and then says "all 939 cities now carry their own office phone and
website", in consecutive sentences. That is the third figure this month whose own
supporting numbers sat beside it, unread.

**"outside Des Moines and Waterloo … it cannot name a single mayor, council member or
clerk" is now false, and correcting it makes the ask stronger.** Counted as a union
across the three rosters rather than by arithmetic: 102 cities from the ten counties
that publish, 4 that publish their own, and Des Moines, Cedar Rapids and Waterloo —
**109**, with no city counted twice, leaving **830**. Cedar Rapids was missing from the
sentence as well. And the 99-county sweep of 2026-09-25 is evidence the draft could not
have had: every county's own site was asked once, and ten publish a page of this kind,
which is what makes the Secretary of State the right recipient rather than the next
ninety.

**The site was re-probed before the draft was touched, per the rule that a redesigned
site often starts publishing the thing.** Four pages — `/`, `/voters/schools-and-cities`,
`/contact-us` and `/city-elections` — read 2026-09-25 with the **districtry token**, no
browser string needed, all 200, robots.txt allowing each with no crawl delay and no
Content-Signal. **Zero occurrences of "clerk" across all four.** `/city-elections` is
linked from the Schools & Cities page and was not named in the 2026-09-03 measurement;
it carries none either, so the ask is still warranted and now rests on four pages rather
than two. `elections@sos.iowa.gov` is still live on the contact page, still
Cloudflare-obfuscated, so the recipient stands.

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
> The one level it can barely answer for is the city. It knows all 939 of Iowa's
> incorporated places and carries an office telephone for 927 of them and a website for
> 531, from the Iowa League of Cities' own directory. It can name a mayor, council member
> or clerk in 109 of those cities: Des Moines, Cedar Rapids and Waterloo publish their own
> council members, and ten counties publish the officials of every city inside them. That
> leaves 830 cities where the site can give a reader their city hall's telephone number
> and cannot tell them who answers it.
>
> I checked all 99 counties' own sites this month, and ten publish a page of that kind, so
> that route is close to exhausted. Is there a list of Iowa's city clerks — names and
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
> First, the county's board page links a "County Board Member 2022-2024" list that gives a
> phone number and e-mail for each member, and all seven names on it are still the members
> your certified canvasses show today. Are those numbers and addresses still right, and is
> the county content for them to appear on each member's card? If you would rather residents
> used the courthouse number, that is a fine answer too and I will leave the cards as they
> are.
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
| Knox | Scott G. Erickson, `serickson@knoxcountyil.gov` | 5 Aug | 16 and 24 Aug | **OVERTAKEN 2026-09-08 — do not send**, see below |

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

**Knox was the one to watch, and on 2026-09-08 it answered — from an office this file had
never written to.** GIS Coordinator Taiwo Agbaje sent a county-authored precinct shapefile
in reply to a separate GIS thread. So Knox's row above is **overtaken, not owed**: the
third note to Clerk Erickson should NOT be sent, because the office that actually holds
precinct data has now identified itself and is corresponding. Knox cannot be recorded
UNRESPONSIVE either — that is a claim about an ask, and this county replied.

The remaining question moved with it, and is narrower than anything asked so far: the file
Agbaje sent is the JULY 2020 fabric, and the one fact `knox-precinct-geometry` turns on —
what became of Knox Township's seventh precinct — is still unpublished. That goes to
**Agbaje on his own thread as Ask 21**, not to the Clerk. Note also that Knox's own
board-members page turned out to be readable after all (2026-09-03), so the county is less
dark than its record implied.

**The lesson is the one this file keeps re-learning at a different address.** Three notes
to a county clerk went unanswered while a different desk in the same county was willing to
send a shapefile. A clerk's silence is a fact about the clerk. Before recording any county
UNRESPONSIVE, check whether its GIS, assessor or election-authority desk is a separate
publisher — it usually is, and it is often the one that answers.

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

> **ASKED 2026-10-01** (sent 16:23:59 UTC to auditor@jonescountyiowa.gov, per
> `/mnt/project-files/letters/sent-2026-10-01.md`). **ANSWERED 2026-10-05 WITH A FILE THAT IS
> NOT THE PLAN IN FORCE**: GIS Coordinator Kristi Aitchison, via Auditor Whitney Hein, sent a
> shapefile named `JonesCo_IA_BOS_2012`. Measured 2026-10-06 against the gate below, its five
> districts sum the county's Census 2020 blocks to 3,945 / 4,388 / 3,988 / 4,105 / 4,220 where
> the county's own adopted plan publishes 4,128 / 4,120 / 4,137 / 4,132 / 4,129 — a plan drawn
> on 2020 blocks would match to the person, so this is an earlier plan and nothing ships from
> it. The follow-up below is **NOT YET SENT — DRAFTED 2026-10-06**; the Letters thread puts it
> in Adam's mailbox as a reply on the same thread, and Adam sends.
>
> **ANSWERED AGAIN 2026-10-06, 17:01 UTC, WITH THE PLAN IN FORCE — THE ASK IS CLOSED.** Ms
> Aitchison replied on the same thread ("This SHOULD work better!") with `BOS.zip`, holding a
> shapefile named `BOS_2022` (five districts `DIST_ID` 1-5, plus one empty record labelled
> `Unassigned` carrying no shape). Run through the same gate: the county's 1,460 Census 2020
> blocks, assigned by each block's internal point, sum to **4,128 / 4,120 / 4,137 / 4,132 /
> 4,129 — every district equal to the county's published figure to the person**, 20,646 in
> all, with no block outside every district and none inside two. That is the plan in force, and
> it lets Jones carry a supervisor-district card for the first time; that is a reader-visible
> change and goes in its own pull request.

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

### Follow-up, drafted 2026-10-06 — a reply on Ms Aitchison's own message

**SENT 2026-10-06 16:40:45 UTC AND ANSWERED THE SAME DAY — CLOSED, AND BUILT 2026-10-07.** Verified in
the operator's sent folder. Ms Aitchison replied at 16:44 that she had sent the previous plan's
file, and at 17:00:59 sent `BOS.zip`, the shapefile `BOS_2022`. Its five districts sum over Census
2020 blocks to 4,128 / 4,120 / 4,137 / 4,132 / 4,129, the county's own published figures exactly,
so the gate under *What each answer means* passed and `jones-county-supervisor` is closed (its
history is a closed record in `docs/DATA_LAYER_GUIDEBOOK.md`). The county is credited in
`docs/SOURCE_CREDITS.md`. No further letter is owed; a thank-you is the operator's choice.

**To:** Kristi Aitchison, at the address her 2026-10-05 message came from, copying the Auditor's
office mailbox it was forwarded through. The Letters thread reads both addresses off that
message; none is written here, because a guessed address on an outbound ask is worse than none.

> **Subject:** Re: Jones County supervisor district boundaries — GIS file request
>
> Dear Ms Aitchison,
>
> Thank you for sending the supervisor district shapefile, and to Ms Hein for passing my
> request along.
>
> Before using it I checked it against the population figures on the county's current
> district map, the one adopted after the 2020 census. The file's districts come out
> noticeably different from those figures (one district by about 270 people), and its name
> includes 2012, so I think it may be the plan from the previous redistricting.
>
> Is there a version of the file for the current plan, the one shown on the county's
> Board of Supervisors district map? If the current lines exist only on the printed map,
> that is a useful answer too, and I will record it rather than ask again.
>
> With thanks,
>
> `<YOUR NAME>`
> districtry.com

**What each answer means.** A file → gate it against the five published populations again, and
build only if it matches. "Only the printed map" → `ANSWERED`, and the record says the county's
file route is closed. No reply → one follow-up at about three weeks.

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
accepted on its FORM — an office mailbox, which is this file's own test — and no name is
guessed here because none is needed. Its recorded provenance was the city's agenda portal,
and that citation is withdrawn below.

**One thing to be careful about in the wording, and it is the reason this ask exists.** The
city's website returns HTTP 403 to this project's server at the network edge, and its origin
answers one path with an explicit "IP … is not authorized". That is worth telling them
plainly — it is probably not deliberate, and they may want to know — but it must be said as
a fact about our server's access, never as a complaint or a request to change their security
posture. The ask is for the four names, not for an exemption.

*RE-PROBED 2026-09-25, and one sentence was withdrawn from the letter.* The 403 half
verifies exactly as written: `www.cityofmarion.org/` and `/government/city_council` both
answer **403 from AkamaiGHost** to the districtry token, 412 and 441 bytes. The half that did
not is the agenda portal. **`cityofmarion.civicweb.net` SERVES A 24,999-BYTE robots.txt WHOSE
BINDING `*` GROUP IS `Disallow: /`**, matched on every path tried — so the letter's "your
agenda portal is reachable, which is how I found this address" told a public office that this
project had read a host that refuses automated clients. Reachable and permitted are different
questions, and only the first was ever asked here. The sentence is gone, and with it the
claim that the portal "does not appear to publish which ward each council member represents",
which rested on the same read.

The `/api` sub-claim — that one path names this server's IP as not authorized — is NOT
restated to the city either. It is recorded in the gap blocker with its date and its exact
`ErrorCode 900` body, which is where a measurement belongs; it did not reproduce on the two
paths probed today, and a specific technical assertion about someone else's infrastructure
should not go out on a measurement nobody re-ran.

**This project also breached its own rule while finding that out**, and it is recorded rather
than quietly fixed: the probe read robots.txt and fetched the portal root in one pass without
gating the fetch on the answer, so one GET went to a host the gate had already refused. One
request, nothing extracted, and no further fetch of that host. Read the verdict BEFORE the
fetch in the same script, not beside it.

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
> layer on every page I have tried. I mention it only so it is clear I am not asking you to
> do something I could look up myself; I am not asking for an exception or for anything to be
> changed on your end.
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
## Ask 18 — Grundy County GIS: does your fee schedule cover the public map service too?

**NOT YET ASKED — DRAFTED 2026-09-05. HELD.** The operator sends; nothing here
is sent by the agent that wrote it.

**Why this exists, and it is a question I should have asked before building.**
`docs/EXPANSION_GUIDE.md` §3.5.1 makes reading the publisher's terms *step zero*
of county research, ahead of every technical probe, and Grundy's fire, park and
library districts were built without it. Asked afterwards, the answer is
genuinely ambiguous rather than obviously fine:

- The county **sells both of the things this build produced**.
  `services/gis/gis_data_request.php` publishes a Data Request form and a fee
  schedule with a **Tax Parcel Data** line — Parcel Data Package **$0.35 per
  parcel** (real-estate information built into the price at $0.10 of it), plus a
  **$100.00 processing and handling fee**, requested by section, township, full
  county or custom area — **and a Government Boundary Data line reading
  "Individual Boundary Data of Taxing Bodies $100.00"**. This build bulk-read
  27,661 parcels and dissolved taxing-body boundaries: the two priced products.
  Cheques are payable to the **Grundy County GIS Automation Fund**.
- The county **also runs an open public ArcGIS Server** at
  `maps.grundyco.org/arcgis/rest/services/…`, backing the "GIS Interactive Map"
  property viewer it links from its own home page. **No token, no referer check,
  no authentication**, and the service's `copyrightText` is **empty**.
- The county's site-wide **Terms of Use carry no data clause at all** — it is a
  boilerplate website agreement about user submissions and acceptable use, with
  no redistribution, reuse or copyright assertion over GIS data.

So this is NOT the Champaign/Piatt case, whose terms expressly forbid copying,
public display and transfer, and NOT WinGIS's, whose data is sold under a signed
Data License Agreement. It is a county that sells a bulk product and separately
publishes a resident-facing service that says nothing. **Whether the fee
schedule is meant to reach a derived layer built from that public service is the
county's to say, not this project's to assume in either direction.**

**Recipient:** the Data Request page names the office mailbox for exactly this
question — **`gisdatarequest@grundycountyil.gov`** — and the county's GIS staff
page (`services/gis/gis_database.php`) names Dave Ostrander, GIS Staff,
(815) 941-6778. Send to the office mailbox and name him; both are
county-published.

---

**Subject:** Using Grundy County's public GIS map service on a free civic site

To the Grundy County GIS office (for the attention of Dave Ostrander),

I run districtry, a free, non-commercial civic site that tells an Illinois
resident which districts contain a point they click — https://districtry.com/il/

Grundy County is already on it: your board districts and precincts, and your
County Clerk's roster. I have also built fire protection, park and library
district boundaries for the county, and I would like to check with you before
they go live.

They are not a copy of a dataset. Your public parcel map service at
maps.grundyco.org publishes a `Districts` column naming every taxing body a
parcel pays into; I read that column and merged the parcels into one shape per
district, so what the site would draw is 13 fire, 6 library and 2 park district
outlines and nothing else — no parcel numbers, no owner names, no assessment or
billing information. The district names come from the county's own 2025 Tax
Distribution List.

What I want to be sure of is this. Your GIS Data Request page sets a fee
schedule that covers both halves of what I have done — "Parcel Data Package"
per parcel, and "Government Boundary Data — Individual Boundary Data of Taxing
Bodies" at $100.00 — and I do not want to have taken through the public map
service something the county intends to sell. Two questions, and a one-line
answer to each is plenty:

1. Does that fee schedule apply to data read from the public map service at
   maps.grundyco.org, or only to files ordered through the Data Request form?
2. Either way, may the county permit the district outlines described above to be
   displayed on this site? I am glad to pay the boundary-data fee, to sign
   whatever agreement the county uses, and to credit Grundy County GIS on every
   card.

**A "no" is a genuinely useful answer** and I will record it and remove the
layers; I would rather have the county's word than my own reading of a terms
page.

Many thanks,

<YOUR NAME>
<YOUR E-MAIL>

---

## Ask 19 — Whiteside County GIS: permission to display three derived boundaries

> **DRAFTED 2026-09-05, HELD. Not sent.** Ask 18 is Grundy's; this takes 19 so
> the two cannot collide whichever lands first. Revised 2026-09-05 on review to
> put the question the record already carried — whether the agreement binds a
> user of the county's public service at all — to the county rather than
> answering it here.

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
> need from your public services and the Clerk's report. I am asking whether or
> not the agreement binds someone who has only used your public map service: I
> have not signed it, and I would rather have your answer than my own reading of
> it. Concretely, I am asking whether Whiteside County will permit districtry to
> display three derived district boundaries publicly, on these conditions, which
> I will follow whether or not you require them:
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

---

## Ask 20 — six Wisconsin county clerks: the city wards your filing leaves without a district

> **ASKED 2026-10-01 — ALL SIX SENT, FIVE ANSWERED THE SAME DAY.** Six separate notes, one per
> county clerk. Four ask the same question about a different city; two ask a different question.
> They are not a batch: each note names one county's own filing, and one that named the wrong
> city or the wrong ward would be worse than not writing.
>
> Send times, read off the sent folder (`/mnt/project-files/letters/sent-2026-10-01.md`, which is
> the only record of what actually went, as against what a thread drafted): Calumet 14:52:02,
> Brown 14:52:11, Outagamie 14:52:19, Pepin 14:52:38, Lafayette 16:14:29, Ozaukee 16:14:42 UTC.
>
> **OUTAGAMIE ANSWERED AND SETTLED NEW LONDON.** Clerk Kelly Gerrits wrote that City of New
> London wards 10, 11 and 12 are all in New London Aldermanic District 5 — exactly the three
> uncoded wards this note asked about, so that city's composition is now completely known. It is
> written down in `wi/scripts/build_wi_aldermanic_districts.py`'s `EXCLUDED` table and in
> `wi/WATCH.md` and is not yet built, because composing a city from the county's coded wards plus
> three sentences from a clerk is a different shape from the city-publishes-its-own-composition
> route `LOCAL_COMPOSITION` holds, and wants its own gate and its own operator rebuild.
>
> **BROWN HEDGED AND THEN POINTED SOMEWHERE BETTER.** Clerk Patrick Moynihan wrote that the
> Village of Bellevue's board "appear to be at large", which is a qualified guess and not the
> village's own statement, and then endorsed asking the village itself. That is why ask
> `wi-bellevue-board-form` exists and went the same day; see the "Why the county clerk and not
> the city clerk" section below, whose rule this does not break — the village clerk's address
> came from the county clerk in writing, so none had to be sourced against the clerks' own
> withholding.
>
> **CALUMET ANSWERED AND SETTLED BRILLION, WHICH RETIRES IT FROM THE GAP RATHER THAN FILLING IT
> IN.** Clerk Beth Leary wrote that the City of Brillion elects its council AT LARGE, not by
> district, and that wards 5 and 6 — the two her county's filing leaves with no district code —
> are bare land with nobody living on them. So the uncoded wards are not missing data: there is no
> district for them to be in. Brillion therefore leaves the `aldermanic-incomplete-filings` gap
> record, which goes from six municipalities to five, and `calumet` leaves its county list. The
> city's council members are a separate, still-open question and want the at-large municipality
> card rather than this layer. A second reading is consistent with her answer and is not proof of
> it: the state's own 2024 election file carries a population for Brillion's wards 1-4 and leaves
> wards 5 and 6 empty.
>
> **OZAUKEE ANSWERED AND COMPLETED PORT WASHINGTON.** Clerk Kellie Kretlow wrote that City of Port
> Washington ward 9 — the one ward her county's filing leaves uncoded — is in aldermanic district 1
> and county supervisor district 4. The supervisor half is independently corroborated: the state's
> own ward file already codes that ward into supervisor district 4, so the one claim that could be
> checked against another publisher checks out, which is what makes the aldermanic half worth
> relying on. That city's composition is now completely known and, like New London's, is written
> down and not yet built, because it is the same county-coded-wards-plus-a-clerk's-sentence shape
> that wants its own gate and an operator rebuild.
>
> **LAFAYETTE ANSWERED AND COMPLETED CUBA CITY, AND THE CITY CONFIRMED IT.** Clerk Carla
> Jacobson wrote that City of Cuba City ward 5, the one ward her county files with no district
> code, is in Aldermanic District 3, and City Clerk-Treasurer Jill Hill confirmed the same that
> evening (replies 19:12 and 19:49 UTC, read off the Letters thread's ledger in
> `/mnt/project-files/letters/sent-2026-10-01.md`). The county files the city's other four wards
> 01-04, so ward 5 joining 03 completes a four-district plan with nothing left over. Like New
> London and Port Washington it is written down and not yet built, waiting on the same gate. No
> reply is owed; a thank-you note is optional and the Letters thread drafts it.
>
> Pepin has not replied. Follow up once at about 2026-10-21.

**What this is about.** Wisconsin's aldermanic districts are drawn as groups of wards, and
the ward file the Legislative Technology Services Bureau publishes is the only statewide
source for which ward is in which district. Counties file it. Where a county files a ward
with no district code, nothing published says which district that ward votes in, so the
map cannot draw that city's districts without either leaving a hole or guessing.

Six municipalities are excluded for this reason (gap `aldermanic-incomplete-filings`).
Three others left the list on 2026-09-06 when their own cities turned out to publish the
composition — Kaukauna in a district map, Berlin on its council page, Edgerton in its own
GIS — so the remaining six have been checked against their cities' sites, their cities' and
counties' GIS, and the state's polling-place file first. This is what is left.

### Why the county clerk and not the city clerk

The city clerk holds the answer more directly. This project does not write to them, and the
reason is on the record rather than a preference: the Elections Commission's municipal
clerk file carries no e-mail address for any of Wisconsin's 1,848 municipal clerks — 0
records contain `@`, the PDF's own `/Subject` metadata reads
`WI Municipal Clerks PDF - no emails:`, and the Commission said the omission was "at their
request". That is a withholding by the people named. `build_wi_municipal_clerks.py` already
refuses to source those addresses elsewhere in order to display them, and the same refusal
applies with more force to using one to send mail.

County clerks are a different case: they publish their own addresses through their own
association directory, and they are also the office that files the ward data. Every address
below is from `wisconsinvcountyclerks.org` by way of `wi-county-clerks.json`, and all six
domains resolve with a live MX (checked 2026-09-08).

### Recipients, and which ward each note is about

| County | Clerk | Address | City | Wards filed with no district |
|---|---|---|---|---|
| Brown | Patrick W. Moynihan, Jr. | `patrick.moynihan@browncountywi.gov` | Village of Bellevue | 1–11 of 12 |
| Calumet | Beth Leary | `beth.leary@calumetcounty.gov` | City of Brillion | 5, 6 of 6 |
| Lafayette | Carla Jacobson | `carla.jacobson@lafayettecountywi.org` | City of Cuba City | 5 of 5 |
| Pepin | Audrey Bauer | `countyclerk@co.pepin.wi.us` | City of Durand | 3 of 3 |
| Outagamie | Kelly Gerrits | `Kelly.Gerrits@outagamie.org` | City of New London | 10, 11, 12 of 12 |
| Ozaukee | Kellie Kretlow | `kkretlow@ozaukeecounty.gov` | City of Port Washington | 9 of 9 |

**Two of these are not the county the city sits in, and that is deliberate.** Cuba City is
usually listed under Grant County and its clerk is in Grant, but ward 5 — the only uncoded
one — is on the LAFAYETTE side, so Lafayette files it and Lafayette is asked. New London
spans Waupaca and Outagamie; all three of its uncoded wards are Outagamie's. Outagamie is
also the county that files every one of Appleton's 50 wards without a district code, which
is not raised in the note but is worth knowing before a reply comes back.

### Two questions, not one

**Four cities are one filing detail short.** Cuba City, Durand, New London and Port
Washington each have a working district plan in the file with one or three wards left out:
Cuba City's wards 1–4 carry districts 01–04 and ward 5 carries none; Durand's 1–2 carry
01–02 and ward 3 carries none; Port Washington's 1–8 carry 01–07 and ward 9 carries none;
New London's 1–9 carry four districts and 10–12 carry none. The wards left out are not
empty: Cuba City's ward 5 holds 248 people and Durand's ward 3 holds 624, more than either
of Durand's two coded wards. So this cannot be handled by leaving a small hole.

**Two cities raise a prior question: whether there are districts at all.** Bellevue is a
village whose board page names no districts, and 11 of its 12 wards carry no code while
ward 12 carries `03`. Brillion's council page lists a Mayor and At-Large Representatives
and uses the words "alder", "district" and "ward" nowhere, while the county files districts
01–04 on its wards 1–4. In both cases the county's filing and the municipality's own page
disagree about the form of the body. This project does not choose between two publishers,
so neither city is drawn.

### The note, for the four one-ward cases. This is Port Washington's; the others change the city, the clerk, the ward numbers and the district numbers.

> Subject: One question about Port Washington's ward-to-district filing
>
> Dear Clerk Kretlow,
>
> I build districtry.com, a free, non-commercial site that shows people which civic
> districts they live in — wards and aldermanic districts, county board districts, school,
> fire and library districts, and so on. It carries no advertising and sells nothing.
>
> I have one small question about Ozaukee County's ward filing in the state's municipal
> ward layer.
>
> For the City of Port Washington, wards 1 through 8 carry aldermanic district codes
> (districts 01 through 07, with ward 8 in district 04). Ward 9 carries no district code.
> Because the site builds each city's aldermanic districts by grouping the wards the state
> file assigns to them, one ward without a code means Port Washington's districts cannot be
> drawn at all — so the city currently shows no aldermanic districts, rather than showing
> eight of nine.
>
> Which aldermanic district does ward 9 vote in?
>
> If ward 9 is new since the districts were last drawn, or if the answer is that it has not
> been assigned yet, that is a useful answer too and I will record it as such rather than
> guessing.
>
> Thank you for your time.

### The note, for Bellevue and Brillion.

> Subject: One question about how the Village of Bellevue elects its board
>
> Dear Clerk Moynihan,
>
> I build districtry.com, a free, non-commercial site that shows people which civic
> districts they live in. It carries no advertising and sells nothing.
>
> I have one question about Brown County's ward filing in the state's municipal ward layer,
> and it is a question about the Village of Bellevue's form of government rather than about
> a mistake.
>
> Of Bellevue's twelve wards, eleven carry no trustee-district code and ward 12 carries
> district 03. The Village's own website lists a Village Board without naming districts. I
> can read those two together in more than one way, and I would rather ask than assume.
>
> Does the Village of Bellevue elect its trustees by district, or at large?
>
> If at large, the single code on ward 12 is presumably left over from something, and I will
> record Bellevue as an at-large village and stop treating its filing as incomplete. If by
> district, I would be grateful to know which wards make up each district.
>
> Thank you for your time.

**What a reply changes.** For the four one-ward cases, a district number ships that city's
aldermanic districts. For Bellevue and Brillion, either answer settles the record: at large
means the gap entry is wrong to call them incomplete filings and they should be recorded as
having no districts to draw, and by district means the composition can be built. A clean
"we don't know" or no reply at all leaves each city where it is, recorded as measured
rather than unexamined.

---

## Ask 21 — Knox County GIS: which precinct absorbed Knox Seven?

> **NOT YET ASKED — DRAFTED 2026-09-09.** A reply on the existing thread with Taiwo
> Agbaje, GIS Coordinator, who sent `Precincts_20200717.zip` on 2026-09-08. **This is not
> the queued Ask 12 note**, which goes to Clerk Erickson and is now overtaken: different
> office, different thread, and this one replies to somebody who has just written to us.

**What this is about.** The file that arrived is a county-authored precinct layer carrying
a `District` column — the thing Knox's certified canvasses withhold, since they count each
district's precincts and never name one. It has already earned its keep: overlaid on the
board districts this project drew from the county's own 2022 district map, it confirms
districts 1, 3, 4 and 5 to within 0.6-1.2% of area, and the one difference in district 2 is
explained to 95% by the city of Galesburg's corporate limits reaching into Galesburg
Township and Henderson-2.

**It is the 2020 fabric, and that is measured rather than read off the filename.** Every
member of the archive is stamped 2020-07-17, and its 31 county precincts match the Illinois
State Board of Elections' certified precinct-level results for the November 2020 general
one for one, by name, with nothing left over on either side.

**Three precincts went away between then and the June 2022 primary**, and ISBE's certified
returns name two of the three changes outright:

- HENDERSON FIRST and HENDERSON SECOND are replaced by a single HENDERSON
- INDIAN POINT FIRST and INDIAN POINT SECOND are replaced by a single INDIAN POINT
- KNOX SEVEN disappears, and **no new precinct name appears in its place** — the other six
  Knox Township precincts keep their names, and all six are still reporting in the
  certified 2026 general primary.

That third one is the whole gap. The two merges are visible because each produced a
precinct named after its township; Knox Seven was absorbed into neighbours that kept their
old names, so nothing published records where its territory went. All three changes sit
inside a single board district, so the board map is unaffected — this is only about drawing
the precincts.

### The draft

> Subject: Knox County precincts — which precinct took in Knox Seven?
>
> Dear Mr Agbaje,
>
> Thank you for sending the voting precincts shapefile. It has already been useful:
> overlaid on the board district boundaries we drew from the county's own 2022 district
> map, it confirms districts 1, 3, 4 and 5 almost exactly, and the one difference in
> district 2 turns out to be the city of Galesburg's corporate limits extending into
> Galesburg Township.
>
> One question left, and I think it is a short one.
>
> The file is stamped July 2020, and its 31 county precincts match the State Board of
> Elections' certified results for the November 2020 general exactly. Comparing those
> against the certified results for the June 2022 primary, three precincts went away. Two
> of them are clear from the returns themselves: Henderson First and Henderson Second
> became a single Henderson precinct, and Indian Point First and Indian Point Second became
> a single Indian Point.
>
> The third is not. Knox Seven stops appearing after 2020, and no new precinct name takes
> its place — Knox First through Knox Six are still reporting today. So Knox Seven's
> territory went into one or more of the existing six, and nothing published says which.
>
> Is there a precinct layer from after the 2021-22 redistricting? That would answer it and
> I would be grateful for it.
>
> If there isn't one, then this would do just as well: which of the six Knox Township
> precincts took in Knox Seven's territory — or was the whole township redrawn rather than
> one precinct being folded into another?
>
> And if the answer is that there's no newer file and the change isn't recorded anywhere
> you can point me to, that is genuinely useful too. I will record that the precinct map
> can't be drawn rather than guess at it, and I won't ask again.
>
> districtry is a free, non-commercial civic map. Knox County's five board districts and
> its board members are already on it, credited to the county.
>
> With thanks,
> <YOUR NAME>
> <YOUR E-MAIL> · https://districtry.com/il/

### What each answer means

- **A newer layer** — Knox's precincts ship and `knox-precinct-geometry` retires.
- **"Precinct N took it in"** — the six are drawable from the 2020 geometry by dissolving
  Knox Seven into the named neighbour, with the county's own statement as the source.
- **"The township was redrawn"** — the 2020 geometry cannot be adapted and the gap stays
  open, but for a stated reason rather than an unanswered question.
- **"No newer file and it isn't written down"** — measured, permanent shut. The note says
  this is a useful answer so that declining is easy.
- **No reply** — this thread's first follow-up would be its own, on the usual cadence. The
  Clerk's thread is separate and is not revived by it.

### Two things deliberately left out

**The seal.** Knox has a separate open question about use of the county seal (asked of the
Clerk, 21 Jul 2026). Folding a licensing question into a note that otherwise has a one-line
answer would make it harder to reply to, and it is a different office. If the operator
prefers to raise both at once, that is a judgement about the threads rather than the data.

**The `COPLLEY` spelling.** The layer's `Precinct` field reads COPLLEY where its own
`Township` field on the same row, and ISBE's certified returns, both read COPLEY. It is a
typo in one column of one export, it costs this project nothing, and it is not worth a line
of this note.

---

## Ask 22 — Clay County Clerk: one Clay City precinct, or two?

> **WITHDRAWN UNSENT 2026-09-12 — the county already publishes the answer.** Never
> sent, and it must not be: the rule is that this project does not ask an office for
> something already published. The County Clerk's own elections page carries "a list of
> all current polling locations in Clay County" — eighteen rows, one of them Clay City —
> and it can be read as a precinct list rather than a building list because it does not
> group. Three of its buildings serve several precincts and every precinct still has its
> own row: 202 N. Olive St. serves Harter 1, 3, 4 and 5; 435 Chestnut St. serves
> Louisville 1 and 2; 4722 Cherrybark Ln. serves Harter 6 and 7. So a second Clay City at
> 237 S. 2nd St. SE would have had a row of its own, and it has none. The list also
> reproduces the county's own gap at Harter 2, which a list of buildings would not.
> Clay's eighteen precincts shipped on 2026-09-12 and clay-precinct-geometry is retired.
>
> WITHDRAWN IS NOT UNANSWERED, and the distinction is the point: nobody declined and
> nobody failed to reply. The page had been there the whole time and this project had
> read the board page and the returns without reading the Clerk's own polling list.
>
> It was DRAFTED 2026-09-11 as a reply on the existing thread with County Clerk Amy
> Britton, who has answered this project twice — 2026-08-24 on where the Clay City
> district line falls, and 2026-08-26 confirming the board plan is current. The draft is
> kept below as written, because a withdrawn ask is worth being able to read.

**What this is about, and why it is one sentence long.** Clay's fourteen board districts
ship. Its eighteen voting precincts do not, and exactly one fact is in the way.

The county's two surfaces disagree on how many precincts it runs. Its County Board page
states the board's composition letter by letter and names **Clay City I** in District A and
**Clay City II** in District B. Its own certified returns — in the State Board of Elections'
statewide precinct-level archive — report **one** precinct named Clay City, at one reporting
id, in the November 2024 general and again in the March 2026 primary. Census 2020 likewise
drew one Clay City voting district, of 1,166 people.

Clerk Britton's 2026-08-24 reply settled where the **district** line falls: District A is
"within the Village limits of Clay City", District B "the unincorporated area of Clay
City/Stanford". That is what the board build needed and it is what shipped. It does not say
whether the county runs one polling precinct there or two, and that is the remaining
question.

**Everything else about the county's precincts is already measured.** The census fabric
carries all eighteen of the county's precinct names after eleven renames (roman ordinals,
plus a vestigial trailing I on Clay City I, Larkinsburg I and Pixley I) and sums to the
county's exact 2020 population of 13,288. The raw-canvass check that kept Washington County
from shipping the same week was run here and Clay passes it: eighteen names in both
elections, none reported at two ids.

### The draft

> Subject: Clay County precincts — one Clay City precinct, or two?
>
> Dear Ms Britton,
>
> Thank you again for the two answers in August. Both were used exactly as you gave them:
> Clay County's fourteen board districts are on the map, with the Clay City line drawn at
> the village's corporate limits as you described, and the plan credited to the county.
>
> One short question left, and it is the only thing standing between the county's voting
> precincts and the map.
>
> The county's board page names Clay City I in District A and Clay City II in District B.
> The county's certified election results, as the State Board of Elections publishes them,
> report a single Clay City precinct — in November 2024 and again in March 2026.
>
> So: does the county run one Clay City voting precinct that the district line divides, or
> two separate precincts?
>
> If it is one, the precincts can be drawn today and I will not need to trouble you again.
> If it is two, I would be grateful for anything that shows where they divide — a precinct
> map, a list of streets, or your own description would all work.
>
> And if the honest answer is that it is not written down anywhere you can point me to,
> that is genuinely useful too. I will record that the precincts cannot be drawn rather
> than guess at them.
>
> districtry is a free, non-commercial civic map. Clay County's fourteen board districts
> and all fourteen members are already on it, credited to the county.
>
> With thanks,
> <YOUR NAME>
> <YOUR E-MAIL> · https://districtry.com/il/

### What each answer means

- **"One precinct"** — the eighteen precincts ship from the census fabric that same day and
  `clay-precinct-geometry` retires. Nothing else is needed; the names, the count and the
  population identity are already checked.
- **"Two precincts"**, with a line — they ship as nineteen, with the Clay City split drawn
  where she describes it, the same way District A and B already are.
- **"Two precincts"**, without a line — the gap stays open and narrows to that one boundary,
  which is a better record than the count question.
- **"It isn't written down"** — measured, permanent shut, and the note says so plainly so
  that declining is easy.
- **No reply** — one follow-up on the usual cadence, then unresponsive. The board districts
  are unaffected either way: they ship on her existing answers and nothing here revisits
  them.

### One thing deliberately left out

**The population deviation.** Clay carries the fleet's largest accepted deviation —
District J at +39.8% and District L at +33.3% against the ideal — and she has already been
asked about it and answered ("These are the current maps"). Re-raising a question she has
answered, inside a note that otherwise has a one-line answer, would make it harder to reply
to and would read as doubting the first answer. It is recorded, not re-asked.

## Ask 23 — Logan County Clerk: may an automated client read the yearbook?

> **NOT YET ASKED — DRAFTED 2026-09-12.** A first approach to this office. It asks for
> permission, not for data: the county already publishes the file and it already serves
> normally to a browser. Nothing is blocked and nothing is being worked around.

**What changed.** `scripts/logan_municipal_officials_scraper.py` read the County Clerk's
*Reference and Yearbook* every Wednesday for its eleven municipalities' governing bodies —
65 officials, with a phone on 51 and an e-mail on 41. On 2026-09-12 a fleet-wide sweep
(`scripts/probe_user_agents.py`) read the site's `robots.txt` and found, in the group that
binds this project's clients:

    User-agent: *
    Disallow: /images/

The yearbook lives at `/images/Reference_and_Yearbook_2025-2026_updated.pdf`. So the weekly
fetch stopped the same day. The clerk's own `/index.php` article page is permitted and is
still read; the county board roster, which comes from that page, is unaffected.

**What ships now.** The eleven municipalities and all 65 officials still ship, carried
forward from the last read rather than re-fetched, because `robots.txt` governs retrieval and
not what already-public information may be shown. What is lost is the weekly re-verification:
an official who leaves office will sit on the card until the file can be read again or the
data arrives another way.

**The ask, in one sentence.** Would the Clerk's office be willing either to say that an
automated weekly read of that one PDF is acceptable, or to place the yearbook at a path the
`*` group permits?

Draft:

> Subject: districtry.com — permission to read the Reference & Yearbook automatically
>
> Dear Logan County Clerk's office,
>
> I run districtry.com, a free public map that shows anyone which civic districts cover a
> given address in Illinois and who represents them there. For Logan County it lists the
> mayors, clerks, treasurers and trustees of all eleven municipalities, taken from your
> office's Reference and Yearbook, as read from your 2025-2026 edition.
>
> Until this week a script re-read that PDF once a week so the names stayed current. I have
> stopped it, because your site's robots.txt asks automated clients not to read anything
> under /images/, which is where the yearbook is filed. The file itself serves perfectly
> well — this is me following the request, not a problem with your website.
>
> Two ways forward, whichever suits you better, and a plain "no" is a fine answer:
>
> 1. If an automated read of that one PDF, once a week, is acceptable to you, a short note
>    saying so is all I need.
> 2. If the /images/ rule is there for a reason, could the yearbook be linked from a path
>    outside it — or could your office e-mail me each new edition when it is published?
>
> Either way the officials already published stay on the map, marked as read from the
> 2025-2026 edition, so nobody is told a name is current when it has not been re-checked.
>
> Thank you for publishing the yearbook at all — a directory with a phone number for most of
> the people it names is not something every county publishes.

**If there is no reply.** Follow up at about three weeks and again about two weeks after
that, then record the office as unresponsive — which is a different claim from "the county
refused", and neither is the same as "no source exists". The scraper re-reads the policy every
week regardless, so a rule change or a moved file restores the weekly read with no edit and no
correspondence.

---


## Ask 24 — Waukesha Clerk of Circuit Court: not asked, because the county publishes it

> **NOT ASKED — UNNECESSARY, 2026-09-12.** Nothing was drafted and nothing must be. The
> question was going to be which of two spellings is current for Waukesha's Branch 5, and
> the pre-send check found the county answering it on its own website — twice. Rule 4 of
> this file's protocol is that a clean, citable NO is a good outcome; the better one is
> discovering the office has already published the answer, which is what happened to Ask 22
> a day earlier. **This project does not ask a public office for something it publishes.**

**What the question was going to be.** The app's Circuit Court card for Waukesha names
twelve judges and, before this change, gave eight of them a branch and a phone. Four carried
neither — Domina, Melvin, Bugenhagen and Ramirez — and one of the four was a spelling problem
rather than a missing source: the state bench table at
`wicourts.gov/courts/circuit/judges.htm` writes `J. Arthur Melvin III` where
the state contact page at `wicourts.gov/contact/Circuit_Courts.html` gives Branch 5 to
`Jack A. Melvin`. Two differences at once — a generational suffix and a given name — so the
builder withheld rather than assert that two differently-written names are one judge.

**What the county publishes.** `waukeshacounty.gov/circuit-courts/court-officials/court-official-directory/`
prints the full pairing, Branch 1 through Branch 12, each row reading
`Branch N, Courtroom … Judge--Honorable …`. Branch 5 is **J. Arthur Melvin III**. The county's
`court-reporter-directory/` prints it independently — a reporter, a judge and a branch per
row — and agrees on all twelve. So the two spellings are one judge, on the county's own
authority, and no clerk needs to be written to.

**The check turned up something larger, and it is recorded rather than acted on.** Those two
county directories list the same twelve judges as the state's CONTACT page — including
**Jeremy Guza** (Branch 3) and **Michael Schindhelm** (Branch 11). The state's BENCH TABLE
lists neither, and instead names **William Domina** and **Ralph M. Ramirez**. Three surfaces
agree with each other and the fourth is the one this builder treats as authoritative for who
sits, across all 69 circuits. Preferring a different surface for one county is a decision
about the whole join rather than a Waukesha repair, so nothing here changes it. The
measurement is in `wi/WATCH.md`; the decision is a person's.

**If it ever is asked**, the recipient is the office rather than a named holder: the county's
Clerk of Courts page publishes one address, `Monica.Paz@wicourts.gov`, and the Blue Book
2025-26 (April 2025) names Monica Paz as Clerk of Circuit Court "appointed to fill a
vacancy" — a dated source, corroborated by that live page but worth confirming on the day.

---

## Ask 25 — Adams County, Wisconsin: two details the county's own pages do not carry

> **NOT YET ASKED — DRAFTED 2026-09-13.** Nothing here is sent by the agent that wrote
> it. Note this is Adams County, **Wisconsin** — Ask 13 is Adams County, **Illinois**, a
> different county with the same name and a different clerk. Do not merge the threads.

**To:** Liana Glavin, County Clerk, Adams County — `liana.glavin@co.adams.wi.us`
**Subject:** Two details about the county board that your website does not carry

### Why this ask exists

This is the residue of a measurement, which is this file's rule 1. Until 2026-09-13 this
project read Adams's twenty supervisors from the Clerk's own "2026 Public Directory" —
the Drive PDF linked from the county board page as "County Directory". That document is
excellent: a text layer, a district heading per seat, a county mailbox and a phone for
every supervisor.

It is no longer read, and **not because of anything the county did.** Google's
`drive.google.com/robots.txt` disallows `/uc`, the download endpoint, and
`drive.usercontent.google.com` — the only download host Drive's own viewer names — serves
26 bytes of `Disallow: /`. This project reads robots.txt before it fetches and does not
look for a way around a publisher's answer, so there is no permitted route to that file's
bytes. The viewer page is permitted and returns the page furniture, not the document.

So the roster now comes from the county's own site, which publishes it well:
`/government/county-board/supervisory-districts` lists all twenty seats, and each links a
page carrying that supervisor's name and their `district<n>@co.adams.wi.us` address. That
is a better source in every respect but two, and those two are the ask.

### What is asked

**1. The supervisors' phone numbers.** The directory printed one for each of the twenty;
the district pages print none. If those numbers are ones the county is content to publish
— they are already in the directory — adding them to each district page would put them
back in front of a reader, and would not depend on any document being fetchable.

**2. Who chairs the board.** The word "chair" does not appear on the county board page,
the districts listing, or any district page. The directory named Rick Pease as chair; the
Wisconsin Blue Book's April 2025 snapshot names John West, who is no longer a supervisor.
Rather than print a name two publishers disagree about, the card now says the chair is not
named and why. **One line on the board page saying who chairs it would settle that**, and
would keep settling it after each April organizational meeting.

### What a "no" costs, said plainly

Nothing that matters to the county. Twenty supervisors, their districts and their county
mailboxes ship either way, refreshed weekly from the county's own pages. A "no" leaves the
card naming what it knows: the supervisors, and — for the chair — that it does not know.
A clean no is a good outcome and the draft says so.

**Home addresses are not asked for and would not be used.** The directory prints one per
supervisor and this project has never carried them.

## Ask 26 — Henderson County Clerk: who is on the county board, and how are they elected?

**Status: NOT YET ASKED — DRAFTED (2026-09-14).** Gap `henderson-county-website`.

**To:** Amanda Van Arsdale, Henderson County Clerk & Recorder —
`avanarsdale.coclerk@hendersoncountyil.gov`
(307 Warren Street, PO Box 308, Oquawka, IL 61469 · (309) 867-2911)

**Why this one is asked at all.** Henderson's thirteen precincts now ship, built without
reading anything the county publishes: ISBE's certified per-precinct results name them and
the Census 2020 voting districts draw them. The board is the one thing left, and every
non-ask route to it is measured shut — `hendersoncountyil.gov` is a parked domain, no
election-results publisher carries the county's canvasses, and ISBE's downloadable archive
covers federal and statewide offices only, with no county board contest at any election.
So this is not a question the county could have answered by publishing better; nothing
reachable holds it.

**A second recipient, if this one goes unanswered.** The WIU GIS Center
(`wiu.edu/cas/gis_center`) hosts Henderson's county GIS and publishes McDonough's precincts
AND board districts. It is a different office from the Clerk and worth trying for board
DISTRICT geometry — but only if the answer below is "by district". It cannot answer who
sits on the board, so it is not the first ask.

---

**Subject:** Henderson County Board — members, and whether they are elected county-wide

Dear Ms Van Arsdale,

I run districtry (https://districtry.com/il/), a free, non-commercial civic map. You click
a point in Illinois and it tells you every district that covers it and who represents you
there. It covers 92 counties, and Henderson joined this week.

Henderson's thirteen precincts are now on the map — Bald Bluff, Biggsville, Carman,
Gladstone 1 and 2, Lomax, Media, Oquawka 1 and 2, Raritan, Rozetta, Stronghurst and Terre
Haute — drawn from the State Board of Elections' certified precinct-level results and the
Census Bureau's 2020 voting districts.

The county board is the one thing I cannot show, and I would rather leave it blank than
guess. Two questions, and a one-line reply to each would be plenty:

1. **Are your board members elected county-wide, or by district?**
2. **Who currently sits on the board?** A list of names is all I need. If there is a
   district or seat attached to each, that helps; if not, the names alone are useful.

I have not been able to answer either from anything published. The address listed for the
county in the state's clerk directory, hendersoncountyil.gov, leads to a holding page
rather than a county site, and I could find no published election results for Henderson
that include a county board contest.

I am not asking for anything the county does not already have to hand, and **a reply
saying the county would rather not provide this is a genuinely useful answer** — I will
record it and stop asking. Nothing about how districtry works depends on my getting a yes.

Anything you send is credited to the county on the page that shows it, and I do not
publish home addresses or personal contact details for officeholders — office contact
only, or nothing.

With thanks for your time,

<YOUR NAME>
<YOUR E-MAIL>
https://districtry.com/il/

---

## Ask 27 — Christian County Clerk: who sits on the county board?

**Status: ANSWERED 2026-10-07.** Gap `christian-county-board-roster`, retired that day. Clerk
Jodie L. Badman replied with two screenshots of the county's County Board Members list, which
name all sixteen members by district, and they ship from
`scripts/build_christian_county_board.py`. The Clerk's first name is settled as Jodie by her
own reply. The list marks no chair, and it prints each member's home city and ZIP, which do
not ship. The record below is kept as it was written.

**Recipient:** Christian County Clerk & Recorder, `elections@christiancountyil.com` —
the address the 5 August and 21 August 2026 inquiries used. **Two of this project's own
records disagree on the clerk's first name** (the old gap blocker wrote Kandi Badman,
this file's tranche table wrote Jodie Badman), so the draft below addresses the office
rather than a person until that is settled from the county's own page.

**Why this is worth sending, and what has changed since the last one.** The August asks
were about Taylorville precinct 9, and that question is closed — the county's own
certified canvasses answered it. Christian's four board districts now ship. What does
not ship is the sixteen members: the county's board page named only its Chairman and
Vice Chairman when it was last readable, and `christiancountyil.gov` has answered every
automated client with a challenge page since 2026-09-15, so there is nothing left to
read. This is the only districted county board in the Illinois instance whose card names
nobody.

**Draft:**

> Subject: Christian County Board — a list of the sixteen members
>
> Dear Christian County Clerk & Recorder,
>
> I run districtry (https://districtry.com/il/), a free, non-commercial site that shows
> anyone which civic districts cover a point they click on, and who represents them
> there. It is not a campaign or a commercial product and it carries no advertising.
>
> Christian County's four board districts are now on it, drawn from the county's own 2021
> County Board District and Precinct Map and checked against the certified results your
> office publishes for the 2022 and 2024 General Elections and the 2026 General Primary.
> Both are credited to the county on the page that shows them.
>
> The one thing I have not been able to find is a list of the board's sixteen members. When
> I was last able to read the county's board page, it named the Chairman and the Vice
> Chairman, and I could find no page that named the other members or said which district
> each represents.
>
> Is there a current list of the sixteen members with their districts that I could link to
> or be sent? If the district is not attached to each name, the names alone are useful.
>
> **A reply saying the county would rather not provide this is a genuinely useful answer** —
> I will record it and stop asking. Nothing about how the site works depends on a yes.
>
> I do not publish home addresses or personal contact details for officeholders: office
> contact only, or nothing.
>
> With thanks for your time,
>
> <YOUR NAME>
> <YOUR E-MAIL>
> https://districtry.com/il/

---

## Ask 28 — Will County Clerk: the 2025 directory as a document

> **NOT YET ASKED — DRAFTED 2026-09-18.** One note to the Will County Clerk. Adam sends;
> nothing here sends mail.

**Why this one is worth sending.** Will's 31 municipalities name their whole village board
or city council, and those names stopped being rechecked on 8 Sep 2026. The directory is
the only source that carries them, so nothing else can confirm a trustee who has since
changed.

**NARROWED 2026-09-19, and the ask is smaller than it was.** Until that date Will sat in
`REQUIRED_COUNTIES` alongside Cook, so a failed Will scrape skipped the rebuild and every
other county's turnover with it — 629 municipalities across 34 counties frozen behind one
vendor's challenge. Will now preserves like any other blocked source, so the other counties
refresh weekly and this ask no longer unblocks anybody else's data. What it still buys is
Will's own: 31 towns whose councils are carried forward indefinitely, with no count floor
able to notice a name going stale, because the number of towns and seats never changes.

**What is actually blocking it, and what is not.** The Clerk publishes the directory
through FlipHTML5, a third-party flipbook viewer, and that viewer has switched on a
Cloudflare managed challenge: measured 2026-09-17, `https://fliphtml5.com/hbvu/bbmp/basic`
answers HTTP 403 to four different clients, each with `Cf-Mitigated: challenge` and the
"Just a moment…" body. **The county is not blocking us — a vendor is**, the county's own
`willcountyclerk.gov` is perfectly reachable, and the flipbook's robots.txt allows the
path. A challenge is an access control and is never solved or worked around here, so the
only routes left are a document from the Clerk or another full-governing-body source, and
the Clerk's page offers none today. The ISBE handbook linked from that page is procedural
guidance and names nobody.

**Do not mention the vendor's block as a complaint.** The office chose a viewer that works
fine for people with browsers, which is most of its readers. The ask is for a second form
of the same document, not a change to how they publish.

### Recipient

Annette Parker, Will County Clerk — `electionsmgmt@willcounty.gov` · (815) 740-4615 ·
302 North Chicago Street, Joliet, IL 60432. (Taken from this project's own
`il-county-clerks.json`; re-check it against the county's page on the day it is sent.)

### Draft

> Subject: Will County municipal officials directory — a machine-readable copy?
>
> Dear Ms Parker,
>
> I run districtry, a free public map that shows anyone in Illinois which civic districts
> cover an address and who represents them there. It is not commercial and carries no
> advertising. Every boundary and every name comes from a government publisher and is cited
> back to it.
>
> Your office's 2025 Will County Directory is the source I use for the mayors, presidents,
> trustees and council members of Will County's cities and villages. Until recently I could
> read it automatically once a week, so the names stayed current without anyone re-typing
> them.
>
> That stopped working this month. The directory is published through FlipHTML5, and the
> viewer now asks every visitor to pass a browser check before serving the page. It opens
> normally for a person in a browser; an automated reader cannot get past it, and I do not
> attempt to work around checks of that kind.
>
> **Would your office be willing to send or publish the same directory as a document — a
> PDF, a spreadsheet or a plain web page?** Anything that lists each municipality with its
> current officials would do. A one-off copy is genuinely useful; a stable link I could
> re-read each week is better still, and I would cite the county as the source either way.
>
> If there is another county source that names each municipality's full governing body, I
> would be glad to be pointed at it instead.
>
> **A reply saying the county would rather not is a genuinely useful answer** — I will
> record it and stop asking.
>
> I do not publish home addresses or personal contact details for officeholders: office
> contact only, or nothing.
>
> With thanks for your time,
>
> <YOUR NAME>
> <YOUR E-MAIL>
> https://districtry.com/il/

### What each answer means

- **A document or a link** — the Will scraper reads that instead of the flipbook, the
  builder's required-county gate is satisfied again, and all 34 counties resume refreshing.
  Retire `will-municipal-directory-freeze` and record the source in the scraper's header.
- **Another county source** — same outcome, measure it the usual way before wiring it.
- **No, or no reply after the follow-up cadence** — the freeze stands and the gap record is
  already honest about it. The next question then becomes whether Will should stay a
  REQUIRED county or whether the builder should ship the other 33 with Will's own
  municipalities explicitly marked as not refreshing, which is a design decision for Adam,
  not a threshold to quietly relax.

---

## Ask 29 — Clinton and Franklin County Clerks: where does the county board sit?

**Status: NOT YET ASKED — DRAFTED.** Gap `county-board-office-addresses` — the last two
of Illinois's 64 districted board cards that name no office at all, down from 50 on
2026-09-06.

**Two counties, two e-mails, and deliberately different questions.** Clinton publishes no
street address anywhere on its board page, so its question is open. Franklin's own site
footer and the state's directory disagree about the number on the same street, so its
question is narrow — which is the smaller and more answerable ask of the two.

**What was measured first, 2026-09-21**, because an ask is the residue of a probe and
neither ledger had a prior ask to either office:

| source | Clinton | Franklin |
|---|---|---|
| the county's own board page | HTTP 200, 74,904 bytes, **no street address anywhere** | the only non-residential address is `100 Public Square, Benton, IL 62812`, in the **site-wide footer** beside `618-435-9800` |
| ISBE County Officers Book | no address in the record at all | no address in the record at all |
| the county's 2024 AFR filing | `PO Box 308, Carlyle, IL 62231` | `PO Box 967, Benton, IL 62812` |
| this project's clerk roster | `850 Fairfax Street, Carlyle` — but that is stated as the **Clerk's** office | `901 Public Square, P.O. Box 607, Benton` |

**Why none of that ships.** A post-office box is not a place a reader can go. The clerk's
own street address is the CLERK's office and no source says the board sits there, and
inferring it would be this project guessing on a card that tells people where to turn up.
For Franklin the two street sources disagree on the number — `100` in the county's footer
against `901` in the state's directory — and a disagreement between two publishers is
exactly what the board-office builder's two-witness rule exists to catch, so it correctly
declines to write either.

**Recipients**, each the office that keeps the board's record, and each an address this
project already holds and did not guess:

### Clinton County Clerk — `ccclerk@clintonco.illinois.gov`

An office mailbox rather than a person, which is what this file prefers.

> Subject: Clinton County Board — the address where the board meets
>
> Dear Clinton County Clerk,
>
> I run districtry (https://districtry.com/il/), a free, non-commercial site that shows
> anyone which civic districts cover a point they click on, and who represents them there.
> It carries no advertising and is not a campaign or a commercial product.
>
> Clinton County's five board districts are on it, drawn from the county's own certified
> election returns, and each card names the district's members. The one thing the card
> cannot tell a reader is where to go: I can find no street address for the County Board.
> The county's board page gives none, the State Board of Elections' County Officers Book
> carries none for Clinton, and the county's Annual Financial Report gives a post-office
> box, which is not somewhere a person can turn up.
>
> Could you tell me, in one line, the street address of the building where the County
> Board meets or holds office hours? I would publish that and nothing else from this
> question.
>
> **A reply saying the county would rather not is a genuinely useful answer** — I will
> record it and stop asking.
>
> I do not publish home addresses or personal contact details for officeholders: office
> contact only, or nothing.
>
> With thanks for your time,
>
> <YOUR NAME>
> <YOUR E-MAIL>
> https://districtry.com/il/

### Franklin County Clerk — `paris.dunk@franklincountyil.gov`

The Clerk's own named county address, so the name vouches for it.

> Subject: Franklin County Board — 100 or 901 Public Square?
>
> Dear Franklin County Clerk,
>
> I run districtry (https://districtry.com/il/), a free, non-commercial site that shows
> anyone which civic districts cover a point they click on, and who represents them there.
> It carries no advertising and is not a campaign or a commercial product.
>
> Franklin County's three board districts are on it, and the nine members' names come from
> the county's own County Board Members page. I have one small question before I add the
> address to that card, because two sources disagree and I would rather ask than pick one.
>
> The county website's footer gives `100 Public Square, Benton, IL 62812`. The State Board
> of Elections' directory records the Clerk's office as `901 Public Square`. Which of those
> is the building where the County Board meets — and is the board's address the same as the
> Clerk's, or a different room or entrance?
>
> One line is plenty. **A reply saying the county would rather not is a genuinely useful
> answer** — I will record it and stop asking.
>
> I do not publish home addresses or personal contact details for officeholders: office
> contact only, or nothing. Your County Board Members page lists each member's home
> address; those are not read and are never published by this project.
>
> With thanks for your time,
>
> <YOUR NAME>
> <YOUR E-MAIL>
> https://districtry.com/il/

### What each answer means

- **A street address** — it ships on that county's board card labelled as coming from the
  county itself, the card-order gap closes for that county, and `county-board-office-addresses`
  is retired once both have answered.
- **"The board meets at the Clerk's office"** — the same, and it settles that the clerk
  street already in this repo may be used for the board, which it may not today.
- **A post-office box again, or no** — the gap record stays as it is and becomes final
  rather than open: it already says plainly that the card names no office and why. A clean
  no is a good outcome here.
- **No reply after the follow-up cadence** — record UNRESPONSIVE against the ask, not
  against the county. Nothing about the boundary or the members is blocked on this; it is
  one row on two cards.

## Ask 30 — twelve Iowa counties: which supervisor holds which district

> **ASKED 2026-10-01 — ALL TWELVE. SEVEN ANSWERED THE SAME AFTERNOON, FOUR OF THEM WITHIN AN
> HOUR, AND THREE OF THOSE SEVEN SHIP.**
> Twelve separate messages, one per county, each to that county's Auditor, every one confirmed
> in the operator's own sent folder: **Black Hawk, Calhoun, Cass, Dickinson, Guthrie, Ida, Lee,
> Montgomery, Osceola, Palo Alto, Sioux and Washington**. A follow-up falls due for the five
> still silent at about three weeks (2026-10-22) and the thirty-day silence mark at 2026-10-31:
> **Black Hawk, Calhoun, Guthrie, Lee and Montgomery**. Cass and Palo Alto are
> answered-and-pending and are not among them.
>
> **SEVEN REPLIES IN ONE AFTERNOON IS THE FINDING, not the three counties that shipped.** This
> project spent weeks measuring the same two statewide files and then re-measuring county pages
> that do not carry the join; one letter per auditor, sent once, answered more of this gap in
> four hours than any sweep had. Use the same letter for the counties that remain and for the
> other Iowa asks.
>
> * **Osceola — ANSWERED, and it ships.** Auditor Rochelle Van Tilburg, 2026-10-01, gave all
>   five pairings in plain text. The county has left the gap record.
> * **Dickinson — REFUSED, and only of the pairing.** Auditor Lori Pedersen, 2026-10-01, in
>   full: `no`. That is the answer this letter asks for in as many words, so no follow-up goes
>   out and the county stays in the gap record for a stated reason. It refuses the one question
>   the letter put — which supervisor holds which district — and says nothing about whether the
>   board is elected by district, which the state's own plan type already settles, or about any
>   other question this project might put to the county. Reading a one-word refusal as wider
>   than the question it answers is how a county comes to be written off for things it never
>   declined.
> * **Cass — ANSWERED, and waiting on one more exchange.** Auditor Kathy Somers, 2026-10-01,
>   sent the district numbers with names as INLINE IMAGES plus a district-map PDF; the message's
>   plain text carries none of it, and the Gmail connector available to these sessions lists an
>   attachment and cannot fetch its bytes. Nothing is guessed from a filename. She has been asked
>   to type the names out or confirm a reading of the image, so the county is
>   **answered-and-pending**: the thirty-day clock does not apply to it and nothing ships until
>   that answer is in.
> * **Ida — ANSWERED, and it ships.** Auditor Kristy Gilbert, 2026-10-01, gave all three
>   pairings in plain text. The county has left the gap record. It is also the reply that turned
>   the name join into a gate: the county wrote `Devlun Whiteing` where the gated roster spells
>   it `Devlun P. Whiteing`, so the table now holds each letter VERBATIM and the builder joins an
>   unmatched name on a unique surname, prints every such join, and stops on an ambiguous one.
>> * **Sioux — ANSWERED, and it ships.** The Auditor's office, 2026-10-01, sent a table headed
>   `2026 Board of Supervisors` pairing all five names with their districts, in plain text. The
>   county has left the gap record, and it is the one county where a letter is the only route
>   there will ever be: its own host fronts robots.txt with a managed challenge, so no weekly run
>   reads a page of that site. It exercises the name join a second time — the office wrote
>   `Carl Vande Weerd` where the gated roster spells it `Carl L. Vande Weerd`.
> * **Washington — ANSWERED by pointing at the county's own page, and it ships from that page
>   rather than from the letter.** Auditor Tamera Stewart, 2026-10-01, gave the url of the board
>   page that states each supervisor's district, plus a district-map PDF. So the weekly scraper
>   reads it like any other county and the card cites the page. It took two fixes on this side,
>   each of which had this project saying something false about the county: its menu is built by
>   script, so the home page carries the word `supervisor` zero times and the board's link could
>   never be found — now reached through the sitemap the host's own robots.txt declares — and the
>   roster spells its chair `Jack Seward Jr.`, whose last token is the suffix, which the name
>   reader took for a surname and then reported as the county naming no district.
> * **Palo Alto — ANSWERED TWICE, and still held, on a DIFFERENT question from the one it
>   started on.** Auditor Carmen Moser, 2026-10-01 at 15:38 UTC, sent two PDFs, both dated
>   **2020**: a precinct letter and a supervisor-district letter. Asked whether a six-year-old
>   letter still describes the board, she answered at 16:24 UTC, in full: `Yes. the 5
>   supervisors are current. The documents are labeled 2020 due to redistricting, but both are
>   current.` **THAT CLOSES THE CURRENCY QUESTION AND IS NOT THE THING THAT WAS BLOCKING.** The
>   pairing itself is inside the PDF, and the Gmail connector available to these sessions lists
>   an attachment and cannot fetch its bytes — so this project has still never read which
>   supervisor holds which district here. The county's own host answers 202, an access control,
>   so there is no page to read it off either. **NOTHING IS TAKEN FROM A FILENAME**, and the
>   file is called `PaloAltoCoIA_SupDist_Letter_2020_SupNames.pdf`, which is exactly the
>   temptation that rule exists for: an earlier version of this bullet said the letter named
>   five people, which was read off its name rather than its contents. So the county is
>   **answered-and-pending** alongside Cass, for the same mechanical reason and not for want of
>   an answer: the five pairings have to reach this project as text, either typed out by the
>   office or read out of the attachment by the operator, who can open it. The thirty-day clock
>   does not apply.
>
> **ONE REPLY CAME IN ON A DIFFERENT ASK AND IS WORTH READING HERE.** Tama County Auditor Karen
> Rohrs, 2026-10-01, named five supervisors with their districts 1 to 5 in plain text, answering
> Ask `ia-pottawattamie-tama-wright-boards`. Nothing ships from it yet and the reason is the map
> rather than the names: the shipped district layer draws THREE districts for Tama against the
> five she names, so two supervisors would be placed in districts the map does not draw. It
> settles the board's size and members and opens a narrower follow-up to the same auditor — the
> county's current five-district map. **The reply sent in the operator's name says the entry
> `will list all five supervisors along with their respective districts`, which the shipped map
> cannot yet support**, so that follow-up matters to a promise already made.
>
> **THE FIRST WRITE-UP OF THIS SAID SEVEN SENT AND FIVE DRAFTED, AND IT WENT STALE INSIDE THE
> HOUR.** The sent folder was read at 14:42–14:46 UTC and the other five went at 14:47, so a
> reading taken minutes earlier was written down as the state of the mailbox. It cost more than
> a wrong sentence: five counties were written to TWICE, at 14:47 and again at 14:53–14:54,
> because this thread drafted letters the Letters thread had already prepared and both sets went
> out. A sent-folder read is a snapshot, and in this project another session may be sending in
> the same minutes — re-read it immediately before writing a ledger line, and check for an
> existing draft before creating one.
>
> The ledger lives in the `ia-supervisor-district-seats` blocker in
> `docs/DATA_LAYER_GUIDEBOOK.md` AND in `ia/WATCH.md` — Iowa keeps it in both, unlike Illinois.

**This ask is twelve counties and not eighteen, and the narrowing is the point.** Of the
eighteen in this record on 2026-09-24, six publish the supervisor-to-district join on their
own board page. Four of those shipped that day — Butler, Chickasaw, Howard and Winnebago —
and **Kossuth and Worth are refused by this project's own 1..N gate**, which is a question
about their page rather than their records: Kossuth prints its districts rotated with each
heading before the name it belongs to, Worth renders its roster twice, and a flat-text parse
cannot settle either safely. Writing to those two to ask for something they already publish
would be the wrong letter. **The twelve below publish it nowhere this project could find.**

### What the app already has, and what it is missing

The ask is for one fact, and it is worth saying plainly that it is the only one missing:

* **The districts are drawn and they ship.** The Iowa Legislature's own
  `CountySupervisorDistricts` layer gives every one of these twelve its 3 to 5 districts, and
  a reader clicking inside one is correctly told which district they live in.
* **The supervisors are named and they ship.** `ia-county-officers.json` carries each county's
  three or five supervisors.
* **Nothing published says which of those people holds which district.** So the card names the
  board and cannot place any of them, and it says so in its own words rather than guessing.

### The twelve, and what this client can and cannot read

Measured 2026-09-24, re-measured at 23:45 UTC for the three this record had called
unreachable. **Six serve this client and six do not**, and the six that do not are a fact
about this client rather than about the county:

| county | this client's access |
|---|---|
| Black Hawk, Calhoun, Cass, Ida, Washington | serves — fetched, and the page carries no join |
| Sioux | **serves** — re-measured 2026-09-24, 200 with no crawl-delay and no Content-Signal |
| Guthrie, Lee, Montgomery | 403 to this client |
| Dickinson, Osceola, Palo Alto | HTTP 202, the captcha shape — an access control, never worked around |

**A blocked page is not a blocked county.** All twelve can be written to, and the ask route is
intact for every one of them; the table is here so the next reader knows which pages a machine
could re-check and which only a person can.

### Recipients — compiled at send, deliberately not here

The recipient is each county's **Auditor**, Iowa's commissioner of elections under Iowa Code
§47.2 and the office whose page publishes the district map — the same reasoning as Ask 14.

**CORRECTED 2026-10-01 — THE ADDRESSES ARE IN THIS REPOSITORY AND WERE WHEN THE SEVEN WENT
OUT.** This section used to read "No auditor address exists anywhere in this repository, and
the addresses that do exist are the wrong offices", and then set out, correctly for what it
believed, why the twelve addresses had to be read off each county's site by a person at send.
That was true of the two files it named — `ia-county-board-directory.json` carries county,
plan, seats and a URL and no contact at all, and `ia-county-officers.json`'s keys are
`countyAttorney`, `recorder`, `sheriff` and `treasurer`, so asking a Sheriff which supervisor
holds District 3 is the wrong office. It was never true of the file that actually answers:
**`ia/data/app/ia-county-auditors.json` carries a name, an office, a telephone and an e-mail
for the auditor of all 99 counties**, and it is what `ia/scripts/ia_county_auditor_scraper.py`
builds weekly.

**The seven addresses the operator sent to on 2026-10-01 match that file exactly, all seven**,
which is what establishes it as the right source rather than an assumption about it. So the
remaining five were drafted straight from it — Black Hawk (Karen Showalter), Calhoun (Jena
Patzner), Cass (Kathy Somers), Dickinson (Lori Pedersen) and Guthrie (Dani Fink) — with no
address guessed and none read off a page this client cannot reach. **The rule against guessing
an address stands unchanged**; what was wrong here was a claim about this repository's own
contents, which is the kind a search settles in one command and nobody ran. A sentence saying
a fact is absent from the tree is a claim about the tree, and it goes stale the day a scraper
ships the fact.

### Draft

> **Subject: <County> County supervisor districts — which supervisor represents which district?**
>
> Dear <name>,
>
> I run districtry, a free, non-commercial civic site that shows people which districts cover
> the place they live and who represents them there. It covers all 99 Iowa counties.
>
> For <County> County the site already draws your supervisor districts, from the Legislature's
> own published district layer, and it already names your supervisors. The one thing it cannot
> tell a reader is which of those supervisors represents the district they are standing in, so
> the page names the board and stops there rather than guessing.
>
> If your office has that pairing written down anywhere — a district number beside each
> supervisor's name, in any form at all, including a sentence in a reply — I would be glad to
> use it, with the county credited as the source. If the board is elected by district but your
> office does not keep that list, that is a useful answer too and I will record it rather than
> keep asking.
>
> I am not asking for anything that is not already public, and there is no cost or obligation
> of any kind. If you would rather not, a one-line no is a complete answer.
>
> With thanks,
> Adam Overberg
> districtry — https://districtry.com/ia/

### What each answer means

- **A district beside each name** — the join ships for that county, the card places every
  supervisor, and the county leaves this record. Four counties left it this way on 2026-09-24
  by publishing it; this is the same outcome by a different route.
- **"We elect by district but do not keep that list"** — a real answer and a closing one for
  that county. Record it in the blocker and stop asking; the districts and the names still
  ship, and the card's own wording is already correct.
- **"We are not elected by district"** — then the record is wrong about that county and the
  Legislature's own plan type is wrong with it, which is worth chasing on its own.
- **No reply after the follow-up cadence** — record UNRESPONSIVE against the ask, per county,
  never against the county. Nothing on the card is blocked on this; one row is.

## Ask 31 — Worth County Auditor: the city-officials page is published and empty

> **ASKED 2026-10-01**, to `auditor@worthcounty.org` under the subject "Your city officials
> page" — confirmed in the operator's own sent folder on the day it went. One follow-up falls
> due at about three weeks (2026-10-22) and the thirty-day silence mark at 2026-10-31. The
> ledger lives in the `ia-municipal-officeholders` blocker in `docs/DATA_LAYER_GUIDEBOOK.md`
> AND in `ia/WATCH.md` — Iowa keeps it in both, unlike Illinois.

**This is a better-founded ask than the usual one, and the difference is worth stating.** The
standard ask puts a question to a county that publishes nothing: would you send us a list. This
one puts a question to a county that has already built the page. Measured 2026-09-25 by
`ia/scripts/probe_ia_city_officials_pages.py`, Worth's city-officials page answers with **seven
per-city blocks and seven role headings and not one name** — the same content-management module
the ten counties that do publish use, with nobody filled in. So the question is about the page
rather than about the county's records, and the answer may be as short as "it is not finished".

**It is not a request to build anything.** Ten Iowa counties publish exactly this page for every
city inside them, and Worth has the same page. If it is unfinished, saying so is a complete
answer and closes the question; if it is finished and simply renders empty to us, that is a fault
worth their knowing about.

### The draft

> Subject: Your city officials page
>
> Hello,
>
> I run districtry, a free, non-commercial civic map that shows people which districts they live
> in and who represents them there. Iowa's counties are the only place that publishes city
> officials in any consistent form, and ten of them do — Adams, Boone, Cerro Gordo, Crawford,
> Iowa, Jackson, Jasper, Keokuk, Marion and Muscatine each list the mayor, clerk and council for
> every city inside the county, and the site shows those names on the map for the cities they
> cover.
>
> Worth County has that same page, and when I load it I see the layout for seven cities with the
> headings for each role, and no names in it. I wanted to ask rather than assume: is that page
> still being filled in, or is it finished and not displaying correctly?
>
> If it is unfinished, that is a complete answer and I will leave it alone. If it should be
> showing names, the empty result is something you would probably want to know about.
>
> I am not asking you to compile anything for me — only whether that page is meant to have
> content in it yet.
>
> Thank you for your time.
>
> Adam Overberg
> districtry.com

### What each answer means

| answer | what it settles |
|---|---|
| "still being filled in" | The route stays open and this county is a re-check rather than an ask. Record it and re-probe on a later sweep. |
| "it is finished" | A real display fault on their side, and worth one reply saying what we see. Their fix ships to a reader by itself on the next weekly run. |
| no reply after the follow-up cadence | `UNRESPONSIVE` in the ledger, and the county stays in the sweep artifact as a scaffold. |

**Worth is the only county in the sweep with this shape**, so this ask does not generalise to a
tranche. If a later sweep finds more, they can go together.

---


## Ask 32 — City of Milwaukee GIS: permission to read the Map Milwaukee services automatically

> **NOT YET ASKED — DRAFTED 2026-09-30.** A first approach to this office. It asks for
> permission, not for data: the city already publishes every one of these layers, and every
> one of them already ships on the map. Nothing is blocked, nothing is being worked around,
> and nothing is currently being fetched from the host — the monthly provenance probe
> declines it and the three builders that read it are run by hand and are on hold.

**What changed.** `milwaukeemaps.milwaukee.gov` publishes, in the group that binds every one
of this project's clients:

    User-agent: *
    Disallow: /

with an exception for Google's crawlers. Measured 2026-09-05 and re-measured 2026-09-30
through `scripts/robots_policy.py` with the exact client the builders send
(`districtry/1.0 (+https://districtry.com/wi/)`). Six shipped layers were built from that
host, all six of them the city's own:

| layer | service read |
|---|---|
| Aldermanic districts (the roster attribute) | `election/alderman/MapServer/0` |
| MPS school board districts | `AGO/MPS_School_Districts/MapServer/1` |
| Police districts | `MPD/MPD_geography/MapServer/2` |
| Police squad areas | `MPD/MPD_geography/MapServer/1` |
| Neighbourhoods (the 190-area planning fabric) | `planning/special_districts/MapServer/4` |
| Tax incremental districts | `planning/special_districts/MapServer/8` |

**What ships now.** All six, exactly as they were last read, carried forward rather than
re-fetched, because `robots.txt` governs retrieval and not what already-public information may
be shown (the operator's ruling of 2026-09-19: *"Preserve data we have already fetched."*).
What is lost is re-verification: a redrawn district or a new alderperson will sit on the card
until the layer can be read again or the data arrives another way.

**Why this ask is worth sending rather than simply substituting.** The permitted substitutes
are measured and recorded in `wi/WATCH.md`, and they cover four of the six: the city's own
open-data portal allows every shapefile these builders already download as their area
witness, and the city's own hosted feature services on `services1.arcgis.com/5ly0cVV70qsN8Soc`
permit us and answer in WGS84. **Three layers have no substitute at all** — police districts,
police squad areas and the 190-neighbourhood fabric — and for those the only permitted route
is the portal's static shapefiles, which are filed in a 1927 state-plane projection that would
need a datum shift this project has never performed. So the ask is not a shortcut around work
that could be done anyway; for three layers it is the difference between a layer that stays
current and one that quietly ages.

**One thing worth naming, and not as a complaint.** The city's own GIS Web Services page at
`city.milwaukee.gov/mapmilwaukee/services` publishes `https://milwaukeemaps.milwaukee.gov/arcgis/rest/`
as a service "to be used in desktop software or web mapping applications", while the same
host's `robots.txt` asks automated clients not to read anything. Both are the city's, and the
likeliest explanation is a blanket default on a web server rather than a decision about map
services. That is exactly the kind of thing one short reply settles.

**The ask, in one sentence.** Would the GIS office be willing either to say that an automated
read of those six services is acceptable, or to point at the route it would rather we used?

**Recipient.** `gis@milwaukee.gov` — the office mailbox the city's own GIS Web Services page
publishes, on the page that documents this very service. Not a named individual: two of the
datasets carry a named maintainer on the open-data portal, but the question is about the
mapping server's policy rather than any one dataset, and writing to an office avoids putting a
policy question on one person's desk.

Draft:

> Subject: districtry.com — permission to read the Map Milwaukee services automatically
>
> Dear City of Milwaukee GIS office,
>
> I run districtry.com, a free, non-commercial public map that shows anyone which civic
> districts cover a given address and who represents them there. Wisconsin's instance is at
> districtry.com/wi/. For the City of Milwaukee it shows your aldermanic districts with each
> alderperson named, Milwaukee Public Schools' board districts, police districts and squad
> areas, the neighbourhood planning areas, and the tax incremental districts — all six of
> them read from your Map Milwaukee ArcGIS services, and each one credited to its publisher on
> the map's sources page — the City for five of them, Milwaukee Public Schools for the sixth.
>
> I have stopped reading those services. Your robots.txt at milwaukeemaps.milwaukee.gov asks
> automated clients not to read anything on that host, so I am following the request. The
> services themselves work perfectly well — this is not a problem with your website, and I am
> not asking you to change a policy you meant.
>
> The reason I am writing rather than simply stopping is that four of those six layers I can
> get elsewhere from the City — your open-data portal allows the shapefiles, and your hosted
> feature services on ArcGIS Online allow automated reads — but police districts, squad areas
> and the neighbourhood areas I cannot. For those three, the Map Milwaukee services are the
> only current source I am permitted to read, so without them those boundaries will slowly
> age on the map while the rest stay current.
>
> Three ways forward, whichever suits you best, and a plain "no" is a genuinely useful answer:
>
> 1. If an automated read of those services — a handful of requests, no more often than once
>    a month — is acceptable to you, a short note saying so is all I need.
> 2. If the blanket rule is deliberate but some paths are fine, naming them would be just as
>    good.
> 3. If you would rather I used a different route altogether, telling me which one closes the
>    question for good, and I will use it.
>
> One small thing you may want to know either way: the copy of the tax incremental districts
> published on your ArcGIS Online account was last updated in October 2025 and returns 73
> active districts, where the shapefile on data.milwaukee.gov returns 79. The shapefile looks
> like the current one.
>
> Whatever you decide, the boundaries already published stay on the map, marked as last read
> on the date they were read, so nobody is told a boundary is current when it has not been
> re-checked. If you would prefer they came down instead, say so and they will.
>
> Thank you for publishing this at all — a city that puts its police districts, its
> neighbourhood areas and its TIDs out as open data is not the norm.
>
> <YOUR NAME>
> districtry.com
> <YOUR E-MAIL>

**What each answer means.**

| answer | what it settles |
|---|---|
| "yes, that is fine" | The six layers go back on a schedule with the permission recorded beside each provenance row and cited in `wi/WATCH.md`. Nothing else changes. |
| "these paths are fine" | The same, narrowed to the named paths; anything outside them moves to the substitutes already measured. |
| "use the portal / ArcGIS Online instead" | The question closes for good. The four substitutable layers move; the three that cannot are recorded as a re-verification gap with the city's own answer as its reason, which is a far better record than silence. |
| "please take them down" | A real outcome and the ask should not pretend otherwise: the six files leave `wi/data/app/`, their dispatch entries and worksheet rows go, and the gap record reopens citing the withdrawal. |
| no reply after the follow-up cadence | `UNRESPONSIVE` in the ledger — a claim about the ask, never about the policy. The disallow still binds, the shipped data still stands, and the substitutes are built instead. |

**Two things deliberately left out.** No named individual, for the reason above. And no request
for anything the city does not already publish: every layer named in the note is already public
on at least one City surface, so the question is purely about how it may be read.

---

## Ask il-gurnee-board-names — Village of Gurnee: your board page names nobody

> **NAMED RATHER THAN NUMBERED, and this ask is why the convention changed.** It was
> drafted as the next number after 33, and on the same evening the Wisconsin, Michigan and
> Iowa branches each drafted their own next-number-after-33. Git merges two identical
> headings without a conflict, and
> renumbering one afterwards moves it out from under every record that cites it, so a new
> ask takes a name from now on. The numbered asks above keep their numbers; several have
> been sent and their numbers travel with the thread.

> **NOT YET ASKED — DRAFTED 2026-10-01.** One message, to the Village Clerk. On send, change
> `NOT YET ASKED — DRAFTED` to `ASKED <date>` in the `gurnee-village-board-names` blocker in
> `docs/DATA_LAYER_GUIDEBOOK.md` — Illinois has no `WATCH.md`, so that blocker is the whole
> ledger.

**This is the Worth County shape rather than the usual ask**, and the difference matters the
same way: this is not a request that a village compile anything. Gurnee has built the page. Its
board page describes the body in full — "The Village President, also known as the Mayor, and six
Village Trustees are elected to four-year terms" — and then says "Current Village Board members
are listed below:" with nothing below it. Measured 2026-10-01: 189,943 bytes of served HTML
containing the word Trustee exactly once, in that sentence about the terms. So the question is
about the page, not about the village's records, and the answer may be one line.

**Nothing about Gurnee is blocking us.** The site serves this project's own client a full page
and publishes no robots.txt at all, so there is no refusal anywhere in this; the names simply are
not in what a visitor is sent. Its six neighbours above 25,000 people in Lake County — Highland
Park, Mundelein, North Chicago, Round Lake Beach, Vernon Hills and Waukegan — were all read from
their own pages on the same day, which is why Gurnee stands out rather than fitting a pattern.

### Recipient

The Village Clerk, through the village's own published board mailbox,
`villageboard@village.gurnee.il.us`. Confirm against the village's contact page before sending;
that address and `Mayor@village.gurnee.il.us` are the only two the board page publishes, and
neither names a person.

### The draft

> Subject: Your Village Board page
>
> Hello,
>
> I run districtry, a free, non-commercial civic map that shows people which districts they live
> in and who represents them there. It covers Illinois, and it already shows Gurnee's village
> hall address and telephone.
>
> I wanted to ask about one thing rather than assume. Your Village Board page explains that the
> Village President and six Trustees are elected to four-year terms, and then says "Current
> Village Board members are listed below:" — and when I load the page, nothing appears below it.
> I see the same empty result every time, and I have not been able to find the names anywhere
> else on the site.
>
> Is that list meant to be there? If it is, the empty result is probably something you would want
> to know about. If the page is being rebuilt, that is a complete answer and I will leave it
> alone and check again later.
>
> I am not asking anyone to compile anything for me. If the names are published somewhere else on
> the site and I have simply missed them, a link is all I need.
>
> Thank you for your time.
>
> Adam Overberg
> districtry.com

### What each answer means

| answer | what it settles |
|---|---|
| a link, or the names | Gurnee joins the six siblings on the next weekly run and the gap record closes. |
| "the page is being rebuilt" | The route stays open. Record it and re-read the page on a later sweep rather than asking again. |
| "we do not publish them" | A refusal, which counts at once towards the done standard's fourth test. Record it with the date and tag the gap record. |
| no reply after the follow-up cadence | `UNRESPONSIVE` after one follow-up and thirty days, recorded with both dates, and the record is tagged then and not before. |

**Urbana is deliberately NOT here.** It is the other Illinois city above 25,000 that names
nobody, and its site resets every connection from this project's sandbox — which is a measurement
of this vantage and not of the city. Writing to a city to ask for data it may already publish is
a question we would be asking of ourselves. That one waits on a reading from a build machine.

---


## Ask il-urbana-site-unreachable — City of Urbana: your website does not answer us from anywhere

> **NAMED RATHER THAN NUMBERED**, for the reason `il-gurnee-board-names` above gives.

> **NOT YET ASKED — DRAFTED 2026-10-01.** One message, to the City Clerk. On send, change
> `NOT YET ASKED — DRAFTED` to `ASKED <date>` in the `urbana-city-council-names` blocker in
> `docs/DATA_LAYER_GUIDEBOOK.md`.

**This ask waited on a measurement and the measurement came back.** Until 2026-10-01 the only
reading of urbanaillinois.us was from a Claude Code sandbox, where every connection is reset —
and this project's own record says reachability moves with the address it is measured from, so
writing to a city on the strength of that would have been reporting our own network as their
problem. `scripts/probe_robots_verdicts.py` was dispatched on a GitHub runner the same day, which
is the vantage the weekly jobs actually crawl from, and read the host's robots.txt THREE times
fifteen seconds apart: every one timed out.

**So the two addresses fail differently — a reset from one, a timeout from the other — and
neither gets a byte.** That is the shape of a host that does not serve automated clients rather
than one that is merely slow. It is worth saying plainly what this does NOT establish: nobody
here has seen a single page of the city's site, so this project cannot say whether Urbana
publishes its council or not, and the ask must not imply otherwise.

**Urbana is the last Illinois city above 25,000 people whose governing body this site cannot
name**, and it is the only one of the eleven read this week that could not be reached at all.
Champaign, next door, was read from its own site on the same day without difficulty.

### Recipient

The Urbana City Clerk. The address must be confirmed before sending, and confirming it is itself
the problem: the city's own contact page cannot be read from here. Find it from a source that
does answer — a printed directory, the county clerk, or simply a browser — and record where it
came from, rather than composing an address from the city's domain.

### The draft

> Subject: Your website does not respond to automated requests
>
> Hello,
>
> I run districtry, a free, non-commercial civic map that shows people which districts they live
> in and who represents them there. It covers Illinois, and it names the mayor and council for
> every city of Urbana's size in the state except Urbana.
>
> The reason is unusual and I thought you would want to know. When my software tries to read
> anything from urbanaillinois.us, including the small rules file that tells visiting software
> what it may and may not read, the connection is refused or times out. I have now tried from two
> completely different networks, several days apart, and neither gets a response of any kind.
> Your site presumably loads normally in a browser; something in front of it appears to be
> turning away everything else.
>
> I am not asking anyone to compile anything. I would only like to know whether that is
> deliberate. If the city blocks automated visitors on purpose, that is a complete answer and I
> will record it and stop. If it is not deliberate, whoever runs the site would probably want to
> know, because search engines and screen readers reach a site the same way my software does.
>
> If it is easier, a link to wherever the council members are listed would also settle it, and I
> will check that address instead.
>
> Thank you for your time.
>
> Adam Overberg
> districtry.com

### What each answer means

| answer | what it settles |
|---|---|
| "it is deliberate" | A refusal, which counts at once towards the done standard's fourth test. Record it with the date and tag the gap record. The city's own choice, and nothing here works around it. |
| "it is not deliberate" and it is fixed | The city joins on the next weekly run once a scraper is written, and the candidate host becomes an ordinary one. |
| a link to the council page | Read that address and nothing else; it may well be on a host that answers. |
| no reply after the follow-up cadence | `UNRESPONSIVE` after one follow-up and thirty days, recorded with both dates, and the record is tagged then and not before. |

**Why this is not phrased as a data request.** Every other ask in this file asks a government for
something it has. This one asks whether a door is locked on purpose, because until that is
answered there is no way to find out what is behind it — and a note asking for a roster the city
may already publish would be asking them to do work this project should be doing itself.

---


## Ask 33 — New York State: is there a directory of local elected officials?

> **ASKED 2026-10-01 at 16:09 UTC AND ANSWERED AT 17:26 THE SAME DAY — and the answer is a
> REDIRECTION, which earns the three New York levels nothing.** John Fatato, Administrative
> Specialist 2 in the Department's Local Government Services, replied in two sentences: "The
> Department of State receives our municipal contact information from OSC. I'm not sure if
> they're able to provide it to you for these purposes." That names the holder and settles
> nothing else. It is not one of the five answers tabled below, so a sixth row is added for
> it; and it is **not a refusal**, so it starts no clock and the levels stay as they are.
>
> **The operator asked the follow-up himself at 18:04**, on the same thread, and it is the
> right one: does the contact information the Department holds NAME the people in office, or
> is it office details without names? A dataset of town-hall telephone numbers closes none of
> these levels, so that answer decides whether writing to the Comptroller is worth doing at
> all. He also said in that message that he will write to the Comptroller directly.
>
> **A LETTER TO THE COMPTROLLER WOULD NOT BE A FIRST APPROACH, and that is easy to get wrong
> here**: `localgov@osc.ny.gov` was copied in on the original at 16:09, so that office has
> already had the question in full and has not answered it. Any letter there cites the cc and
> reads as a follow-up, never as an opening. **Nothing goes to the Comptroller until Mr.
> Fatato answers**, because his answer may make the letter unnecessary.
>
> **ANSWERED AGAIN AT 18:20, AND THIS ONE IS SUBSTANTIVE: THE NAMES EXIST.** Mr. Fatato:
> "We do receive names, but as I understand it the municipalities are responsible for
> updating their own information so the information may not be as up-to-date as you're
> looking for." So a statewide collection naming the people in local office DOES exist, held
> by the Comptroller, and its currency is each municipality's own to maintain. **That settles
> the question this ask was written to answer** — the state does hold such a thing — and it
> does NOT close any level, because nothing has been obtained and nothing is dated.
>
> It also changes what is worth asking the Comptroller, which is why the letter was not
> written before this reply came: the question is no longer whether names exist but whether
> each record carries a DATE. This project's honesty rule is that a card never presents a
> name as current without a verifiable source, so an undated self-reported roster cannot ship
> as a roster. It would still be worth having as a STARTING LIST to check against each
> municipality's own page, which is how this project works everywhere else. That letter is
> `Ask ny-comptroller-local-officials` below.
>
> **Prior contact: none, and that was measured rather than assumed.** All of the operator's
> mail was searched on 2026-10-01 for both domains and for the two offices by name, not just
> the sent folder, and this thread is the only one. So the letter was correctly written as a
> first approach.
>
> **Every date and address above is read off the sent folder, not off this file.**
>
> This is the one ask that belongs to the STATE rather than to 57
> county clerks and a hundred town clerks, which is why it went first: if the answer is
> yes, a single file closes most of New York's county and local tiers, and a hundred and
> sixty separate asks were never the right opening move. It is also the cheapest possible
> ask — one question, one reply, and a clean no is worth as much as a yes because it
> settles the route for good.
>
> **The operator shortened the letter before sending it, and the sent wording is what was
> asked.** It keeps the three things a reply has to be read against: the question itself,
> naming the same four kinds of officeholder; the statement that the catalogue, the
> Comptroller's pages and the county sites were all looked at first; and all three
> acceptable answers — it exists, it exists and cannot be released, it does not exist. It
> drops the specific measurements (the five-way catalogue search, 43 of 57 county sites
> answering) and the sentence saying nothing is being asked about reuse terms. That second
> omission is the one to watch: a reply that raises licensing is answering a question the
> sent letter did not disclaim, so it is new ground rather than a refusal.

**To:** New York State Department of State, Division of Local Government Services —
`localgov@dos.ny.gov`
**Cc:** Office of the State Comptroller, Division of Local Government and School
Accountability — `localgov@osc.ny.gov`
**Subject:** Is there a published directory of local elected officials in New York?

**What the ask says.** We publish a free, non-commercial map that tells a reader which
civic districts cover a point and who represents them there, and New York is one of eight
states it answers for. The state's own open-data portal publishes the official website of
every county, city, town and village, which is how this project reaches them, and we can
find no published list of the PEOPLE holding local elective office — county legislators
and supervisors, town and village board members, city council members. The question is
simply whether such a directory exists anywhere in the Department's or the Comptroller's
hands, in any form, including one not on the open-data portal.

**What was measured first, and is said in the ask so it does not read as a question
somebody could have answered by searching.** The open-data catalogue was searched five
ways on 2026-10-01 and returns code-enforcement officials, grant awards, lobbying filings
and four website directories, and no roster of officeholders. The Comptroller's
local-government pages publish financial filings and a guide for new officials. All 57
county websites outside the city were read, and 43 answered.

**Why a no is useful and is said so plainly.** A no closes the statewide route for good and
sends this project to the counties and towns one at a time, which is the work it is already
doing in Illinois; it also means the gap records that tell our readers what is missing can
say the state does not publish it rather than that we did not find it.

**What is deliberately not asked.** Nothing is asked about reuse terms or licensing, because
there is nothing yet to license. No individual is named. And no county or town is named,
because this is a question about whether a statewide product exists, not a complaint about
any local government's website.

**The letter as drafted.** The operator shortened it before sending; the status note
above says what the sent version keeps and drops, and the sent folder carries its words.

> Subject: Is there a published directory of local elected officials in New York?
>
> Dear Division of Local Government Services,
>
> I run districtry.com, a free, non-commercial public map that shows anyone which civic
> districts cover a given address and who represents them there. New York is one of eight
> states it answers for, at districtry.com/ny/.
>
> Inside New York City it names the Council Member, the borough officials and the community
> education council for a point. Outside the city it draws the county, the city, town or
> village, the school district and the legislative districts, and for almost all of that
> ground it can name nobody, so a reader is told which county and town they live in and not
> who governs either.
>
> My question is simply whether the Department, or the Comptroller's office, holds a
> directory of the people currently holding local elective office — county legislators and
> supervisors, city council members, town board members and village trustees — in any form,
> including one that is not on the open-data portal.
>
> I looked before writing, so this is not a question you could answer by pointing me at a
> search. The state open-data catalogue returns code-enforcement officials, grant awards,
> lobbying filings and four directories of local government WEBSITES, and no list of
> officeholders. The Comptroller's local-government pages publish financial filings and a
> guide for newly elected officials. I have read the website your own county table publishes
> for each of the 57 counties outside the city, and 43 of them answered.
>
> A no is as useful to me as a yes, and I would rather have it than keep looking. It means
> the route is each county and each town one at a time, which is the work this project is
> already doing in Illinois, and it lets the notes that tell our readers what is missing say
> that the state does not publish it rather than that we did not find it.
>
> If a directory exists but is not something you can share, that is an answer too and I will
> record it as such and not ask again.
>
> I am not asking about reuse terms or licensing, because there is nothing yet to license. If
> there is a directory, I will come back about that separately.
>
> Thank you,
>
> <YOUR NAME>
> districtry.com
> <YOUR E-MAIL>

**What each answer means.**

| answer | what it settles |
|---|---|
| "yes, here it is" | The statewide route opens and most of New York's county, local and sub-county tiers close from one file. The three gap records come down to whatever the file does not carry. |
| "it exists and we cannot share it" | `REFUSED` in the ledger, which counts straight away: the three gap records stand with the state's own answer as the reason, and the route goes county by county. |
| "no such directory exists" | The best possible no. The statewide route closes for good, the records say the state does not publish it rather than that we did not find it, and nobody re-asks this in a year. |
| "ask the counties and towns" | The same as the above in practice, and it also tells us which desk each one is, which is worth having before 160 letters. |
| no reply after the follow-up cadence | `UNRESPONSIVE` in the ledger, thirty days after one follow-up — a claim about the ask and never about the state. |
| "we get it from the Comptroller and may not be able to share it" | **What actually came back, at 17:26 on the day it was asked.** It names the holder and answers neither question: not whether a directory of PEOPLE exists, and not whether it can be released. It earns nothing, starts no clock, and what it waits on is the follow-up already sent — does the Department's data name the people in office, or is it office details without names? |

**Three things deliberately left out.** No individual is named, at either office. No county or
town is named, because this is a question about whether a statewide product exists and not a
complaint about any local government's website. And nothing is asked about the fourteen county
sites that would not answer this project: those readings were taken in a sandbox whose own
network accounts for most of them, and the fleet's rule is to re-measure from the build machine
before writing any publisher off.

## Ask ny-comptroller-local-officials — New York's Comptroller: how current are the names, and are they dated?

**Status: NOT YET ASKED — DRAFTED 2026-10-01.** Named rather than numbered. **This is a
FOLLOW-UP, not an opening**: `localgov@osc.ny.gov` was copied in on Ask 33 at 16:09 on
2026-10-01 and has not replied, so the letter cites that message rather than introducing the
project from scratch.

Gaps `ny-county-governing-body`, `ny-local-governing-body`.

**What is already settled, and why this is a narrow letter.** Ask 33 went to the Department
of State with the Comptroller copied in. The Department answered twice the same day: it gets
its municipal contact information from the Comptroller, and that information **does include
names**, with each municipality responsible for keeping its own entry up to date. So the
existence question is closed and only two things are left to ask — whether the collection can
be shared, and whether each record carries a date.

**The date is the whole question, and that is this project's own rule rather than
fussiness.** A card here never shows a person's name as current without a source that can be
checked. A self-reported list with no date per record cannot be published as a roster, because
there would be no way to tell a name that is right from one that is four years stale. The same
list WITH a date per record can be published, each row carrying its own date exactly as the
county cards already do. And even undated it is worth having, as a starting list to check
against each municipality's own page — which is how every other state in this project is
built.

**It is kept short deliberately.** The operator shortened Ask 33 before sending it, which is
the clearest signal available that these drafts run long. This one asks three things and
stops.

> Subject: Re: Is there a published directory of local elected officials in New York?
>
> Dear Division of Local Government and School Accountability,
>
> You were copied last week on a question I sent to the Department of State, asking whether
> anyone at the state holds a directory of local elected officials. Mr. Fatato there has since
> told me the Department gets its municipal contact information from your office, that it does
> include names, and that each municipality is responsible for keeping its own entry current.
>
> I run districtry.com, a free, non-commercial map that shows anyone which civic districts
> cover their address and who represents them there. Outside New York City it can draw every
> county, city, town and village in the state and name almost nobody.
>
> Three questions, and I expect the answer to the first may settle the others:
>
> 1. Can that information be shared with me, in any form?
> 2. Does each record carry a date — when the municipality last updated it?
> 3. If not, is there anything in it that indicates how current an entry is?
>
> The date matters more than it might sound. I never show someone's name as current unless I
> can point to a source for it, so an undated list is not something I could publish as a
> roster. The same list with a date on each row I could publish, showing that date beside each
> name. And even without dates it would be valuable to me as a starting point to check against
> each municipality's own website, which is how I build this everywhere else.
>
> If it is not something you can share, that is a complete answer and I will record it as such
> and not ask again. Whatever you are able to send, your office would be credited and linked on
> every page that used it.
>
> Thank you,
>
> Adam Overberg
> adam@overberg.co
> districtry.com

**What each answer means.**

| answer | what it settles |
|---|---|
| shared, with a date per record | The strongest possible outcome: New York's county, local and sub-county levels close from one file, each row publishable with its own date. |
| shared, undated | Not publishable as a roster on its own, and still a large gain: a starting list of names to check against each municipality's own page, which turns an open-ended search into a verification pass. |
| cannot be shared | `REFUSED`, which counts immediately. The three gap records stand with the state's own answer as the reason, and the route is each county and town one at a time. |
| no reply | `UNRESPONSIVE` thirty days after one follow-up — a claim about the ask and never about the office. |

**One thing deliberately not asked.** Nothing about reuse terms or licensing, for the reason
Ask 33 gives: there is nothing yet to license. If a file arrives, that is a separate letter.

## Ask il-five-counties-commissioner-roster — five Illinois county clerks: who holds the commissioner seats?

**Status: HARDIN SENT 2026-10-01 AND ANSWERED THE SAME DAY; JOHNSON ANSWERED 2026-10-07;
THE OTHER THREE DRAFTED 2026-10-01.** Named rather than numbered, for the reason `il-gurnee-board-names` above gives.

Gaps `johnson-county-board` (retired 2026-10-07, below), `perry-county-website-blocked`, `pope-county-board`,
`scott-county-commissioners`. **Hardin's gap record is gone**: Clerk Jill Cowsert answered
within seven minutes of the letter, naming all three commissioners, and they ship — so the
record that said they were unnamed no longer describes the county. This is the first of these
five to close, and it closed on a reply rather than on anything found. **Johnson's is gone too**:
Clerk Robin Harper-Whitehead replied on 7 October naming Jason Taylor (Chairman), Matthew
Hayden (Vice Chairman) and John McCuan, with the board's e-mail and her office's telephone,
and they ship the same way. Like Hardin it is a letter-only county for good, because its Clerk
had already told us there is no website.

**THREE OF THESE FIVE LETTERS WERE WRITTEN AS FIRST APPROACHES AND THREE OF THESE COUNTIES
HAD ALREADY WRITTEN BACK.** Corrected 2026-10-01, after the operator asked whether we were
writing to people as though we had never met them. Two of the three were worse than merely
repetitive: each told a clerk something about their own county that the clerk had already
told us was not so.

- **HARDIN.** The draft said the county's published web address "serves a parked page".
  Clerk Jill Cowsert had answered on 24 August 2026, after three letters and a back
  operation: *"Our county board is elected countywide. And we do not have a website in
  Hardin County."* So there is no county website to be parked, and we were about to describe
  a site the clerk had told us does not exist. The letter sent on 1 October thanks her for
  that answer and asks only for the names.
- **JOHNSON.** The draft said the county's site "refuses every automated visit at the host".
  Clerk Robin Harper-Whitehead had answered on 21 July 2026, in reply to an unrelated
  question: *"We don't have a website to point back to."* Same error, same shape: a block
  described where there is nothing to block.
- **SCOTT.** The draft recorded no prior contact. The Clerk's office was written to on
  19 July 2026 and answered on 20 July by Bobbie Jo McKee in the State's Attorney's office:
  *"I have asked around the courthouse and, to my knowledge, Scott County does not have its
  own seal. We use the State of Illinois Seal only."* That answers a different question and
  it is still a reply, so the new letter opens by referring to it. Scott's own members page
  does exist and does come back empty, so that part of the draft stood.

**THE LESSON IS THE SAME ONE THE EIGHT-COUNTY ASK BELOW RECORDS, POINTING THE OTHER WAY.**
There, two letters claimed the site already named members it did not. Here, two letters
claimed a county has a website when its clerk had said it has none. Both come of writing a
letter from this project's own gap records rather than from the correspondence and the
county. **Read the sent folder before writing to anybody, and check every claim a letter
makes about the county against the county.**

| county | seats | what blocks the roster | prior contact |
|---|---|---|---|
| Hardin — **CLOSED** | 3 commissioners | nothing now: all three are named and shipped | 21 July, 5, 16 and 21 August 2026; answered 24 August; asked again 1 October and answered the same day |
| Johnson | 3 commissioners | the county has no website at all, as its Clerk stated on 21 July 2026 | 21 July 2026, answered the same day; 5 and 16 August, unanswered |
| Perry | 3 commissioners | the county's site turns away automated visits | none |
| Pope | unknown | the web address serves a template page carrying no county information, and the clerk's domain is mail-only with no website behind it | none |
| Scott | 3 commissioners | the county's own page renders its member list through a widget that returns nothing | 19 July 2026, answered 20 July by the State's Attorney's office about the county seal |

**Why certified returns are not the answer, which is worth saying because this project
builds a great deal from them.** Every one of these five has readable certified canvasses —
that is how their boards were proven county-wide in the first place. A canvass names who
WON a contest, not who holds the seat today: a member can resign, die or be appointed
between elections, and Edgar County settled the rule when its canvasses elected a District
6 member who has since left and only the county's own page named the appointee. Geometry
comes from whatever proves the lines; people come from whatever the county maintains as
people.

**Pope is asked a second question and it is the first one.** Nothing published anywhere
says whether Pope's board is elected by district or county-wide — it is the one Illinois
county whose board FORM is unknown, and the ArcGIS Online catalogue was asked on 2026-10-01
under six terms and returns no board district or precinct layer for it. So Pope's letter
asks the form before the names, because the answer decides whether a map is wanted at all.

**What was measured first**, so none of these reads as a question somebody could have
answered by searching: each county's own website was probed, each clerk domain in this
project's clerk roster was probed, and the three election-results vendors that carry
Illinois counties were swept across several election slugs — a vendor's carriage is
per-election, which is how Pulaski and Hardin were found after being recorded as uncarried.
What those sweeps produced is the certified returns above, which answer the form and not the
roster.

**Recipients**, each the Clerk's own office address already held in
`il/data/app/il-county-clerks.json` and not guessed.

### Hardin County Clerk — `countyclerk@hardincountyil.gov` — SENT 2026-10-01

Clerk Jill Cowsert has already answered once, on 24 August 2026, after three letters and
while recovering from surgery. She settled the board's form and told us the county has no
website at all. So this letter thanks her for that answer, re-asks neither question, and
says nothing whatever about a website.

> Subject: Re: How is the Hardin County Board elected — and do district maps exist as data?
>
> Dear Clerk Cowsert,
>
> Thank you again for your reply of 24 August, and I hope your recovery has gone well. Both
> of the things you told me are now on the site: Hardin County's board shows as elected
> county-wide, and I am no longer looking for a county website.
>
> One thing is still missing, and it is the last one. Hardin County's voting precincts are on
> the map, drawn from Census boundaries and named from your office's own certified returns,
> and the county's card cannot say who sits on the board. Certified results tell me who won a
> race rather than who holds a seat today, so I would rather ask you than infer it.
>
> Could you send me the names of the commissioners now serving, and which of them chairs
> the board? A list in the body of a reply is ideal — I do not need a document.
>
> **A reply saying the county would rather not is a genuinely useful answer** — I will
> record it and stop asking.
>
> I do not publish home addresses or personal contact details for officeholders: office
> contact only, or nothing.
>
> With thanks for your time,
>
> <YOUR NAME>
> <YOUR E-MAIL>
> https://districtry.com/il/

### Johnson County Clerk — `CountyClerk@johnsonco.illinois.gov`

> Subject: Johnson County Board — who is serving now?
>
> Dear Clerk Harper-Whitehead,
>
> I run districtry (https://districtry.com/il/), a free, non-commercial site that shows
> anyone which civic districts cover a point they click on, and who represents them there.
> It carries no advertising and is not a campaign or a commercial product.
>
> You wrote to me on 21 July, when I had asked about the county seal, to say that Johnson
> County has no website to point back to. That is recorded here and the site claims nothing
> else. I also wrote twice in August to ask how the board is elected; please disregard both,
> because the county's own certified 2026 primary canvass has since answered it — the board
> is elected county-wide rather than by district.
>
> So one thing is left. Johnson County's sixteen voting precincts are on the map, named from
> that same canvass, and the county's card cannot say who sits on the board. Certified
> returns name who won a race rather than who holds a seat today, and with no county website
> there is nowhere else for me to look, so I would rather ask than infer.
>
> Could you send me the names of the commissioners now serving, and which of them chairs
> the board? A list in the body of a reply is ideal.
>
> **A reply saying the county would rather not is a genuinely useful answer** — I will
> record it and stop asking.
>
> I do not publish home addresses or personal contact details for officeholders: office
> contact only, or nothing.
>
> With thanks for your time,
>
> <YOUR NAME>
> <YOUR E-MAIL>
> https://districtry.com/il/

### Perry County Clerk — `countyclerk@perrycountyil.gov`

> Subject: Perry County Board — who is serving now?
>
> Dear Perry County Clerk,
>
> I run districtry (https://districtry.com/il/), a free, non-commercial site that shows
> anyone which civic districts cover a point they click on, and who represents them there.
> It carries no advertising and is not a campaign or a commercial product.
>
> Perry County's twenty-seven voting precincts are on it, named from the county's own
> certified 2026 primary canvass, which is also what told me the board is elected
> county-wide. What the card cannot say is who holds the three seats. The county's website
> is the only source that names them and it turns away automated visits, and certified
> returns name who won a race rather than who is serving now.
>
> Could you send me the names of the commissioners now serving, and which of them chairs
> the board? A list in the body of a reply is ideal.
>
> There is a second thing you may be able to settle in the same line, and it is entirely
> optional: if the county would be willing for its website to answer automated clients, that
> would keep the roster current here every week without anybody having to write again. If
> turning them away is deliberate, that is a perfectly good answer and I will record it and
> leave the site alone.
>
> **A reply saying the county would rather not is a genuinely useful answer** — I will
> record it and stop asking.
>
> I do not publish home addresses or personal contact details for officeholders: office
> contact only, or nothing.
>
> With thanks for your time,
>
> <YOUR NAME>
> <YOUR E-MAIL>
> https://districtry.com/il/

### Pope County Clerk — `countyclerk@popeco.illinois.gov`

The one mail-only address in this group: the domain carries mail and no website, which is a
documented pattern among Illinois clerks and is why no site could be read.

> Subject: Pope County Board — elected by district or county-wide, and who is serving?
>
> Dear Pope County Clerk,
>
> I run districtry (https://districtry.com/il/), a free, non-commercial site that shows
> anyone which civic districts cover a point they click on, and who represents them there.
> It carries no advertising and is not a campaign or a commercial product.
>
> Pope County is the one Illinois county where I cannot answer even the first question about
> the county board, and I would rather ask you than publish a guess. Every other county in
> the state is on the site with at least its board's form settled.
>
> Two questions, in order:
>
> 1. Is the Pope County Board elected by district, or county-wide?
> 2. If by district, could you point me to the district boundaries — a map file, a map, or a
>    list of which precincts make up each district would all work. If county-wide, could you
>    send the names of the commissioners now serving and which of them chairs the board?
>
> I have found no county source that answers either, and I can find no board district or
> precinct map for Pope anywhere public.
>
> **A reply saying the county would rather not is a genuinely useful answer** — I will
> record it and stop asking.
>
> I do not publish home addresses or personal contact details for officeholders: office
> contact only, or nothing.
>
> With thanks for your time,
>
> <YOUR NAME>
> <YOUR E-MAIL>
> https://districtry.com/il/

### Scott County Clerk — `countyclerk@scottcoil.gov`

The narrowest of the five: the county has a page for this and it comes back empty. This
office was written to on 19 July 2026 about the county seal and answered the next day by
Bobbie Jo McKee in the State's Attorney's office, so the letter opens by saying so rather
than introducing the project from scratch. Brooke Smith is the current clerk and Ms. McKee
answered from a different office, so the letter names both correctly.

> Subject: Scott County commissioners — your members page comes back empty
>
> Dear Clerk Smith,
>
> I wrote to this office on 19 July to ask whether Scott County has a seal of its own, and
> Ms. McKee kindly answered the next day that the county uses the State of Illinois seal.
> Thank you again for that. This is a different and smaller question.
>
> I run districtry (https://districtry.com/il/), a free, non-commercial site that shows
> anyone which civic districts cover a point they click on, and who represents them there.
> It carries no advertising and is not a campaign or a commercial product.
>
> Scott County's ten voting precincts are on it, named from the county's own certified 2026
> primary canvass. The card cannot name the three commissioners, and the reason is worth
> passing on whether or not you can help with the roster: the county's own page for the
> board renders its member list through a widget that returns nothing, so the names are not
> in the page a visitor downloads. A person using a screen reader, or anyone whose browser
> blocks that widget, would see the same empty list I do.
>
> Could you confirm which three commissioners are serving now, and which of them chairs the
> board? One line is plenty.
>
> **A reply saying the county would rather not is a genuinely useful answer** — I will
> record it and stop asking.
>
> I do not publish home addresses or personal contact details for officeholders: office
> contact only, or nothing.
>
> With thanks for your time,
>
> <YOUR NAME>
> <YOUR E-MAIL>
> https://districtry.com/il/

### What each answer means

- **A roster** — it ships on that county's board card, sourced to the county, and the card
  stops saying nothing where it should name three or six people. **Hardin is the proof and it
  took seven minutes**: Clerk Cowsert's reply of 1 October named all three commissioners, they
  ship, and the gap record is gone. Johnson, Perry and Scott each close the same way, on one
  reply. For Johnson that reply is the only route there will ever be — as it was for Hardin —
  because each county's own Clerk has told us the county publishes no website, so no amount of
  further looking could ever have closed either one.
- **And a county with no website is a document roster permanently.** Hardin joins Edwards and
  Wabash in the small table of counties whose members are carried from a letter rather than
  re-read from a page, so every weekly run prints which document those three names came from
  and how old it is. Nothing re-verifies itself here; the only refresh is another letter.
- **Pope answering "county-wide"** — its commissioners ride the County card like nineteen
  other Illinois counties, with no district geometry and no toggle, and the county joins the
  tier it belongs to. Answering "by district" opens a map question instead, which is a
  bigger piece of work but a known one.
- **A refusal** — the gap record stays and becomes final rather than open, and under the
  done standard a refusal counts straight away, so the county is covered by record. A clean
  no is a good outcome here.
- **No reply** — record UNRESPONSIVE against the ask after one follow-up and thirty days,
  not against the county. Nothing about the precincts, which are already on the map, is
  blocked on this.

## Ask il-seven-counties-board-districts — seven Illinois county clerks: following up on August

**Status: NOT YET SENT — REWRITTEN 2026-10-01.** Named rather than numbered, for the reason
`il-gurnee-board-names` above gives. **It was drafted as an EIGHT-county first approach and it
is a SEVEN-county follow-up**, which is the whole of what this rewrite changed.

Gaps `bond-county-board-districts`, `cumberland-county-board`,
`fayette-county-board-geometry`, `jersey-county-board-districts`, `lawrence-county-board`,
`macoupin-county-board-districts`, `marion-county-board-districts`.

**EVERY ONE OF THESE COUNTIES HAD ALREADY BEEN WRITTEN TO TWICE, AND THE DRAFT INTRODUCED THE
PROJECT TO ALL EIGHT AS THOUGH FOR THE FIRST TIME.** The operator asked on 2026-10-01 whether
we were doing that, and the sent folder says we were about to. Each of these counties got a
first letter in early August and a follow-up on 16 August, every one about this same question —
where the board district lines run. Not one has replied. So a letter that opened "I run
districtry, a free, non-commercial site…" would have been the third letter to each clerk and
the first to pretend there had been none.

**AND ONE OF THE EIGHT HAD ANSWERED.** Jasper County's Clerk, Amy Tarr, replied on **17 August
2026**: *"The board members are elected from districts. Please see the attached map."* She
attached the map. Jasper is removed from this ask entirely — writing to her again would ask for
something she has already sent. Its gap record keeps the ask with an `answered` outcome, and the
remaining work on Jasper is to read the map she sent, which is a job in this project and not a
question for her.

| county | districts | first letter | follow-up | why nothing published draws the lines |
|---|---|---|---|---|
| Bond | 5 | 8 Aug 2026 | 16 Aug 2026 | no district map, and the returns show four precincts split between two districts |
| Cumberland | 3 | 5 Aug 2026 | 16 Aug 2026 | no district boundary, and the certified returns count fourteen precincts across a county of twelve, so two are split |
| Fayette | 7 | 5 Aug 2026 | 16 Aug 2026 | the county's own printed map divides one precinct between two districts and leaves one line undrawn |
| Jersey | 4 | 9 Aug 2026 | 16 Aug 2026 | the only map published is dated 2016, before the 2021 redraw, with no data behind it |
| Lawrence | 7 | 5 Aug 2026 | 16 Aug 2026 | the county's mapping carries taxing districts only — no board districts and no precincts |
| Macoupin | 9 | 1 Aug 2026 | 16 Aug 2026 | readable district maps with no data behind them, and the precinct data does not say which district each precinct is in |
| Marion | 5 | 5 Aug 2026 | 16 Aug 2026 | no district map, and Centralia and Salem are each split across three districts |

**FAYETTE'S LETTER GOES TO A DIFFERENT PERSON FROM THE AUGUST ONES, AND SO MUST NOT SAY
"YOU".** August's first letter went to Clerk Barker and the follow-up to Ms. Pollard, whom the
office's own auto-reply named; the clerk roster now names **Kara Dugan**. A follow-up addressed
to a new officeholder that says "I wrote to you in August" is wrong about that person, so
Fayette's opens by referring to the OFFICE. Check who holds the office before writing "you".

**EACH LETTER NOW OPENS BY NAMING ITS OWN COUNTY'S DATES** rather than carrying one shared
sentence. A clerk can tell at once whether the letter was written for them or run off a list,
and the dates are the cheapest possible proof that it was the former.

**TWO OF THESE LETTERS WERE ALSO ABOUT TO TELL A CLERK SOMETHING UNTRUE, AND CHECKING THEM IS
WHAT FOUND IT.** The Fayette letter opened "Fayette County's fourteen board members are named
on the site" and the Jersey letter "Jersey County's twelve board members are named on the site,
each with their district". Neither was true when written: both counties sat among the thirteen
Illinois counties naming nobody. Reading each county's own board page on the afternoon of
2026-10-01 showed that both publish every member with a district — Fayette with party and term
besides — so the two sentences are true now, and the honest fix was to make the claim true
rather than to soften it (`scripts/il_county_board_pages_scraper.py`). **THE CAUSE IS THE SAME
ONE THIS WHOLE PASS TURNED UP**: these counties had been written to about their GEOMETRY, and
nobody went back to ask whether they publish their MEMBERS, so what the site named and what the
counties published had drifted apart with every check green. Read a letter's claims about what
the site already has against the site, not against the record.

**What was measured first, on 2026-10-01**, so none of these reads as a question somebody
could have answered by searching: each county was asked of the ArcGIS Online catalogue under
six terms — board district, county board, voting precinct, precinct, supervisor district,
commissioner district — the unauthenticated query that found another county's twenty-six
public services with no county page read at all. **All seven return nothing.** That is the
route that most often turns up a layer a county's own website never mentions, so its coming
back empty is what makes these letters the remaining route rather than a shortcut past one.

**Each letter asks for the smallest thing that would close its county**, not for a dataset in
general. Three of the seven could be closed by a few lines of prose rather than any file:
Bond needs to know how four split precincts divide, Fayette needs one line's position and two
precincts' district numbers, Jersey needs to know whether its 2016 map is still in force.

**Recipients**, each the Clerk's own office address already held in
`il/data/app/il-county-clerks.json`. Fayette's is Kara Dugan's, which is the current holder
rather than either August recipient.

### Bond County Clerk — `brooke.weathers@bondcountyil.gov`

> Subject: Bond County board districts — how do four precincts divide?
>
> Dear Ms. Weathers,
>
> I wrote to you on 8 August about Bond County's five board district boundaries and followed
> up on 16 August. I am sorry to come back a third time, and I have narrowed the question down
> to one thing since then, which I hope makes it easier to answer.
>
> For context again: I run districtry (https://districtry.com/il/), a free, non-commercial
> site that shows anyone which civic districts cover a point they click on, and who represents
> them there. It carries no advertising and is not a campaign or a commercial product.
>
> Bond County's five board members are named on the site from the county's own pages. What I
> cannot do is draw the five districts, so a reader clicking inside the county is not told
> which district they are in. I can usually build a county's districts out of whole voting
> precincts, but the county's own certified returns show four precincts each voting in two
> different board districts, so no arrangement of whole precincts will do it.
>
> Either of these would close it: the county's 2021 board redistricting map or ordinance, in
> whatever form you hold it, or — just as good — a sentence or two saying how those four
> split precincts divide between the districts.
>
> **A reply saying the county would rather not is a genuinely useful answer** — I will
> record it and stop asking.
>
> With thanks for your time,
>
> <YOUR NAME>
> <YOUR E-MAIL>
> https://districtry.com/il/

### Cumberland County Clerk — `bhoward@cumberlandcoil.gov`

> Subject: Cumberland County's three board districts
>
> Dear Clerk Howard,
>
> I wrote to you on 5 August asking how the Cumberland County Board is elected and whether its
> district boundaries exist as map data, and followed up on 16 August. The first half of that
> has since answered itself from your office's own certified returns — the board is elected from
> three districts — so this letter asks only the second half, and asks it more narrowly.
>
> For context again: I run districtry (https://districtry.com/il/), a free, non-commercial
> site that shows anyone which civic districts cover a point they click on, and who represents
> them there. It carries no advertising and is not a campaign or a commercial product.
>
> Cumberland County's twelve voting precincts are already on the site, named from the
> county's own certified returns, and all six board members are named from the county's
> site. The three board districts are the only thing missing, so a reader is not told whether
> they are in Central, Eastern or Western.
>
> I would normally assemble the districts from whole precincts, but the county's own
> certified primary canvass counts six, five and three precincts in the three districts —
> fourteen across a county of twelve — so at least two precincts are divided between
> districts, and I cannot tell where.
>
> Could you send the three district boundaries in whatever form you have them: a map file, a
> map, or a description of where the lines run through the divided precincts? Nothing else
> about this county is missing.
>
> **A reply saying the county would rather not is a genuinely useful answer** — I will
> record it and stop asking.
>
> With thanks for your time,
>
> <YOUR NAME>
> <YOUR E-MAIL>
> https://districtry.com/il/

### Fayette County Clerk — `kdugan@fayettecountyillinois.gov`

> Subject: Fayette County board districts — two questions about your district map
>
> Dear Clerk Dugan,
>
> I wrote to this office twice in August about Fayette County's board district and precinct
> boundaries — to Clerk Barker on 5 August and to Ms. Pollard on 16 August. I gather the office
> has changed hands since, so I am not holding you to either letter; I am writing once more
> because the question is still open and I have narrowed it to two specific points.
>
> I run districtry (https://districtry.com/il/), a free, non-commercial site that shows
> anyone which civic districts cover a point they click on, and who represents them there.
> It carries no advertising and is not a campaign or a commercial product.
>
> Fayette County's fourteen board members are named on the site from the county's own pages,
> with party and term. I cannot draw the seven districts yet, and the reason is two specific
> places on the county's own published district map rather than anything missing from it
> generally.
>
> Two questions, and either an answer in words or the map file behind the printed map would
> settle both:
>
> 1. The map appears to divide Avena precinct between two districts. Where does that line
>    run?
> 2. The line between two of the western districts is not drawn on the copy I can read.
>    Which of the western precincts sit in District 2 and which in District 6?
>
> If the file behind that map exists in any form — a shapefile, a GIS export, a CAD drawing —
> that would answer both at once and I would be glad of it.
>
> **A reply saying the county would rather not is a genuinely useful answer** — I will
> record it and stop asking.
>
> With thanks for your time,
>
> <YOUR NAME>
> <YOUR E-MAIL>
> https://districtry.com/il/

### Jasper County Clerk — NO LETTER. SHE ANSWERED ON 17 AUGUST 2026.

The draft that stood here asked Clerk Amy Tarr for Wade township's four precinct boundaries,
opening as a first approach. She had already answered the August letters, on 17 August, with
*"The board members are elected from districts. Please see the attached map."* and the map
attached. Two further letters went back to her the same day thanking her.

So there is nothing to ask. **Jasper's remaining work is ours**: read the map she sent and
draw the districts from it. The gap record keeps the ask with an `answered` outcome so nobody
re-drafts this letter, and the narrow Wade township question — if it survives reading her map
at all — is a question to ask only once the map has been read and found not to answer it.

### Jersey County Clerk — `pwarford@jerseycounty-il.gov`

> Subject: Jersey County board districts — is the 2016 map still the plan in force?
>
> Dear Ms. Warford,
>
> I wrote to you on 9 August about the board district map, withdrew that letter the same
> morning when I found the map on the Clerk's website, and then wrote again on 16 August with
> two questions the map itself had raised. Those two are still the whole of what I need, so
> rather than start over I am simply putting them to you once more.
>
> For context again: I run districtry (https://districtry.com/il/), a free, non-commercial
> site that shows anyone which civic districts cover a point they click on, and who represents
> them there. It carries no advertising and is not a campaign or a commercial product.
>
> Jersey County's twelve board members are named on the site, each with their district. I
> have not drawn the four districts, for one reason I would rather have you settle than
> assume: the only district map the county publishes is dated 2016, which is before the
> redraw every Illinois county did in 2021, and there is no data file behind it.
>
> So, the same two questions:
>
> 1. Is that 2016 map still the plan in force, or was a new one adopted after the 2020
>    census?
> 2. Either way, is there a map file behind the current map? A list of which precincts make
>    up each of the four districts would work just as well.
>
> I will not publish a boundary I am not confident is current, which is why I am asking
> rather than drawing what I can see.
>
> **A reply saying the county would rather not is a genuinely useful answer** — I will
> record it and stop asking.
>
> With thanks for your time,
>
> <YOUR NAME>
> <YOUR E-MAIL>
> https://districtry.com/il/

### Lawrence County Clerk — `WGibson@lawrencecounty.illinois.gov`

> Subject: Lawrence County's seven board districts
>
> Dear Clerk Gibson,
>
> I wrote to you on 5 August asking how the Lawrence County Board is elected and whether its
> district boundaries exist as map data, and followed up on 16 August. The first half has since
> answered itself — the board is elected from seven districts — so this letter asks only the
> second, and tells you exactly where I have already looked so you need not repeat it.
>
> For context again: I run districtry (https://districtry.com/il/), a free, non-commercial
> site that shows anyone which civic districts cover a point they click on, and who represents
> them there. It carries no advertising and is not a campaign or a commercial product.
>
> Lawrence County's seven board members are named on the site from the county's own pages.
> The seven districts are not drawn, so a reader is not told which one covers them.
>
> I have looked in the places that usually answer. The county's mapping carries taxing
> districts only — no board districts and no voting precincts — and I can find no published
> election results that describe the districts either, so I cannot assemble them from
> precincts the way I do in most counties.
>
> Any one of these would close it: the seven districts as a map file, a description of which
> townships and part-townships make up each district, or a precinct map for the county.
>
> **A reply saying the county would rather not is a genuinely useful answer** — I will
> record it and stop asking.
>
> With thanks for your time,
>
> <YOUR NAME>
> <YOUR E-MAIL>
> https://districtry.com/il/

### Macoupin County Clerk — `pete.duncan@macoupincountyil.gov`

> Subject: Macoupin County — which precinct is in which board district?
>
> Dear Mr. Duncan,
>
> I wrote to you on 1 August asking whether the county's elected-officials directory exists in
> a form a program can read, and followed up on 16 August. This is the same project and a
> narrower question: of everything I asked for then, one piece is now all that is missing.
>
> For context again: I run districtry (https://districtry.com/il/), a free, non-commercial
> site that shows anyone which civic districts cover a point they click on, and who represents
> them there. It carries no advertising and is not a campaign or a commercial product.
>
> Macoupin County's voting precincts are already on the site, and the board members are in
> hand. The nine board districts are the only piece missing, so a reader clicking in the
> county is not told which district they are in.
>
> The county publishes district maps a person can read, and I can see them, but there is no
> data behind them and the county's precinct data does not say which district each precinct
> belongs to. Either of these would close it:
>
> 1. The nine district boundaries as a map file, in whatever format you hold.
> 2. A plain table pairing each voting precinct with its board district. If every district is
>    made of whole precincts, that table is all I need — I already have the precinct
>    boundaries.
>
> **A reply saying the county would rather not is a genuinely useful answer** — I will
> record it and stop asking.
>
> With thanks for your time,
>
> <YOUR NAME>
> <YOUR E-MAIL>
> https://districtry.com/il/

### Marion County Clerk — `CountyClerk@MarionCo.Illinois.gov`

> Subject: Marion County board districts — Centralia and Salem
>
> Dear Clerk Fox,
>
> I wrote to you on 5 August with two questions about Marion County's election maps, following
> an earlier note in July about the county seal, and followed up on 16 August. One of the two
> is now settled from your office's own certified returns. The other is not, and it has come
> down to one specific thing, which is why I am writing a third time.
>
> For context again: I run districtry (https://districtry.com/il/), a free, non-commercial
> site that shows anyone which civic districts cover a point they click on, and who represents
> them there. It carries no advertising and is not a campaign or a commercial product.
>
> Marion County's five board districts are not on the site, so a reader clicking in the
> county is not told which district covers them. The county's own certified returns describe
> the five districts completely — that part is settled — and I still cannot draw them, for one
> reason.
>
> The boundaries I would use to stand in for the county's precincts come from the Census, and
> five of those carry the base names Centralia and Salem while each of those two spans three
> different board districts. So I cannot tell which Census area belongs with which of the
> county's current Centralia and Salem precincts, and any guess would put a reader in the
> wrong district.
>
> Either of these would close it: the county's five board districts as a map file, or a note
> saying which Census areas make up each of the current Centralia and Salem precincts. A
> county precinct map would also do.
>
> **A reply saying the county would rather not is a genuinely useful answer** — I will
> record it and stop asking.
>
> With thanks for your time,
>
> <YOUR NAME>
> <YOUR E-MAIL>
> https://districtry.com/il/

### What each answer means

- **Map data** — that county's districts are drawn as the county drew them, with no
  derivation and nothing traced, which is the best outcome available and is how two other
  Illinois counties shipped.
- **A written answer to the narrow question** — Bond, Fayette, Jersey, Macoupin and Marion
  each become buildable from boundaries this project already holds, with the county's answer
  recorded as the source for the one thing it settled. This is the likeliest good outcome and
  it costs the clerk a paragraph.
- **A refusal** — the gap record stays and becomes final rather than open; under the done
  standard a refusal counts straight away, so the county is covered by record.
- **No reply** — the August letters are already past one follow-up and thirty days, so each of
  the seven gap records carries its ask as UNRESPONSIVE from the August dates. A third letter
  going unanswered changes nothing in the ledger; it is sent because the question is narrower
  now, not because the record needs it.

**What is deliberately not asked.** Nothing about reuse terms, because none of these
counties has offered anything to license yet and a licence question turns a simple request
into a legal one. No fee is offered or asked about. And no individual board member is named in
any of the seven letters, because the question is about boundaries.

**WHAT A THIRD LETTER MUST NOT DO.** It must not re-send the August text, and it must not
reproach anybody for not replying: a clerk's office is not obliged to answer, two unanswered
letters are not a grievance, and a county that has said nothing has refused nothing. Each of
these opens by owning the repetition ("I am sorry to come back a third time"), says what has
been narrowed since, and asks one thing. If a third goes unanswered, the next step is to record
the silence and stop — not a fourth.
---

## Ask il-ford-board-members — Ford County Clerk: who sits on the board?

**Status: NOT YET ASKED — DRAFTED 2026-10-01.** Named rather than numbered, for the reason
`il-gurnee-board-names` above gives.

Gap `ford-county-board-vintage`.

**THIS IS A FOURTH LETTER TO A CLERK WHO HAS ALREADY HAD THREE, AND A FIRST DRAFT OF THIS
PARAGRAPH SAID TWO.** Corrected 2026-10-01 against the sent folder. Ford County was written to
on **3 August 2026**, followed up on **16 August**, and followed up again on **4 September** —
every time about its district MAP: which plan is in force, and how the Patton 3 precinct
divides between districts 1 and 3. None of the three has been answered. The 4 September letter
called itself a final follow-up, which makes the tone of this one matter more rather than less:
it does not re-ask the map question, it asks a different and smaller one, and it says in its
first line that we have written before and are not asking that again.

**A LETTER'S COUNT OF ITS OWN PREDECESSORS IS A CLAIM, AND IT IS ONE ONLY THE SENT FOLDER CAN
SETTLE.** Writing "I wrote to you in August" to somebody who has had three letters, the last of
them calling itself final, reads as not having kept track — which is exactly the impression a
fourth letter can least afford.

**AND THE GAP RECORD WAS CLAIMING SILENCE IT HAD NOT MEASURED.** It carried the 16 August
follow-up and read UNRESPONSIVE, which was true of that letter and stopped being the whole truth
when the 4 September one went: the record now names 4 September and reads PENDING, because the
standard counts thirty days from the LAST time the county had a chance to answer and that is
twenty-seven days ago. It turns back to unresponsive on 4 October without anybody editing
anything, and the build prints the countdown on every run. **A later follow-up makes a silence
claim younger, not older**, so the field has to hold the most recent letter rather than the
first.

**Why it is needed when the county publishes the answer.** Ford's own board page lists its
members with their districts, and that page's record in this project has said so since
2 August. It says it of a person with a browser, which is true, and it was read as saying it
of this project, which is not. Measured 2026-10-01: `fordcounty.illinois.gov` serves its
robots.txt cleanly and permits every path, its front page answers HTTP 200 at 124 KB, and its
two board paths answer NON-DETERMINISTICALLY — six reads of `/ford-county-board/` and
`/county-board/`, spaced sixteen seconds apart, returned the page three times and an HTTP 307
to a "Javascript is required. Please enable javascript before you are allowed to see this
page." interstitial three times, with BOTH paths giving both answers. That is an access control
stating its condition, so nothing here satisfies it another way: taking the readings where the
control happens to be off is working around it.

**So the ask is for the list in any form that is not that page**, which is the smallest thing
that would close it. A county that has not answered two letters about a map may well answer one
that asks for a page it already maintains.

**What the letter must NOT say**, and this is the reason it is drafted separately rather than
added to one of the two asks above. It must not imply the county is hiding anything or that its
site is broken: the interstitial is a bot protection that a human visitor never sees, the
county is publishing the list perfectly well, and the problem is on our side of the exchange.
And it must not ask about the map again, because that question is already outstanding and
asking it a third time in a letter whose subject is something else is how a clerk stops reading.

**Recipient**, the Clerk's own office address already held in
`il/data/app/il-county-clerks.json` and not guessed.

### Ford County Clerk — `clerk@fordcounty.illinois.gov`

> Subject: Ford County Board members — a list I can read automatically
>
> Dear Clerk Vaughn,
>
> I have written to you three times about Ford County's board district map — on 3 August,
> 16 August and 4 September — and have not heard back. I said last time that it would be my
> final letter on that, and I am keeping to it: I am not asking about the map again here.
> This is a different and much smaller question, and it should be an easier one.
>
> I run districtry (https://districtry.com/il/), a free, non-commercial site that shows anyone
> which civic districts cover a point they click on, and who represents them there. It carries
> no advertising and is not a campaign or a commercial product.
>
> Ford County's board page lists every member with their district, and it reads perfectly well
> in a browser. My difficulty is that the page is protected against automated visitors, so the
> program that keeps my site's pages current cannot read it — it is turned away about half the
> time with a notice asking it to enable JavaScript. That protection is doing its job and I
> have no wish to get around it.
>
> So: is there any other form of that same list I could read — a PDF, a spreadsheet, a plain
> page, or simply the names and districts pasted into a reply? Anything would do. I would
> refresh it from whatever you point me at and cite the county as the source.
>
> **A reply saying the county would rather not is a genuinely useful answer** — I will record
> it and stop asking.
>
> With thanks for your time,
>
> <YOUR NAME>
> <YOUR E-MAIL>
> https://districtry.com/il/

### What each answer means

- **A readable copy, in any form** — Ford's eleven or twelve members are named on the site and
  on its own county page, and Illinois reaches 92 of its 102 counties.
- **The names pasted into a reply** — just as good, and the reply itself becomes the source,
  cited and dated, the way Wabash County's roster already ships.
- **A refusal** — the gap record gains an ask about MEMBERS rather than about geometry, which
  is the ask the fourth test actually wants, and the county is covered by record.
- **No reply** — record it against this ask after one follow-up and thirty days. The three
  outstanding map letters are a separate ledger entry and are not closed by this one.

**What is deliberately not asked.** Nothing about the map, nothing about reuse terms, and no
fee. And the letter does not ask the county to change its site, which would be asking a
government to weaken a protection for one visitor's convenience.
---

## Ask wi-town-boards — Wisconsin Towns Association: is there a list of town board members?

> **NOT YET ASKED — DRAFTED 2026-10-01.** A first approach to this organisation. It asks
> whether a list exists and on what terms, not for anything free: the association is a
> membership body, not a government, and a list it compiles from its members is its own work
> to price as it likes.

**Why this ask exists.** The fourth test asks whether the app answers every expected level of
government. Wisconsin's towns are a level: outside a city or village a TOWN is the
general-purpose government, the app draws every one of them, and what it names there is the
town CLERK, who administers rather than governs. The town BOARD — a chairperson and two or four
supervisors — is named for no town in the state.

**What was measured first, on 2026-10-01, before writing anything.** The state aggregates
exactly one municipal officer, the clerk, through the Elections Commission, and that file is
what the app already ships for all 1,847 municipalities. Nothing public pairs a town with its
board. The League of Wisconsin Municipalities, which Ask 17 is drafted to, is the wrong body
for this question: its membership is cities and villages, not towns. The Wisconsin Towns
Association is the towns' own body, and `wisctowns.com` publishes no officer roster — a vendor
directory and the association's own board of directors, and nothing naming any town's officers.

**Why it is nevertheless likely to hold one.** The association's front page links a **Member
Update Form**, which is how a membership body keeps a current contact for each member town. A
body that collects officer updates from 1,250-odd towns almost certainly holds, somewhere, the
very pairing this level needs. Whether it will share it, sell it, or decline is exactly what one
reply settles.

**Recipient.** `wtowns@wisctowns.com`, telephone (715) 526-3157 — the office mailbox the
association's own Contact Us page publishes. Not a named individual: the question is about
whether an organisation holds a dataset and on what terms, which belongs on a desk rather than
on a person.

**Measured before fetching.** `www.wisctowns.com` serves a 1,248-byte `robots.txt` and its
binding group permits the pages read here, read with the same client that would crawl it. Note
the host: `wisconsintowns.org` has no DNS record at all, which is the wrong spelling and was
tried first.

Draft:

> Subject: districtry.com — is there a list of town board members?
>
> Dear Wisconsin Towns Association,
>
> I run districtry.com, a free, non-commercial public map that shows anyone which units of
> government cover a given address and who represents them there. Wisconsin's part of it is at
> districtry.com/wi/, and it already draws every town, village and city in the state and names
> each one's clerk, from the Elections Commission's own file.
>
> What it cannot do is name a town board. Click inside a town and the map tells a reader who the
> clerk is, which is useful, but the clerk is not who governs — the chairperson and supervisors
> are, and the map names them nowhere in Wisconsin. As far as I can tell nothing public pairs a
> town with its board: the state aggregates only the clerk, and the League of Wisconsin
> Municipalities covers cities and villages rather than towns.
>
> So my question is simply whether the Association holds such a list — each town with its
> chairperson and supervisors — and if so, on what terms it could be used. I ask because your
> site publishes a Member Update Form, which suggests you keep a current record for each member
> town, and you are the towns' own organisation rather than a third party guessing at it.
>
> I should be plain about three things:
>
> 1. I am not asking for it free. Compiling and maintaining 1,200-odd records is real work and
>    yours to price. If there is a licence fee or a members-only restriction, tell me what it is
>    and I will either pay it or record that the data exists and is not available to me, which
>    is a far more honest thing to tell a reader than silence.
> 2. I would publish each board member's name and the town they serve, each credited to the
>    Association as its source, with a link back to you. Nothing else — no personal addresses,
>    no telephone numbers unless they are the town's own office line.
> 3. A plain "no" is a genuinely useful answer and I will not follow it up. What I would do
>    instead is record on the map that Wisconsin's town boards are not named, and why.
>
> If the answer is that no such list exists in one place, that is worth knowing too, and I would
> be glad of a pointer to whoever would be closest — a county towns association, or a particular
> county's clerk who keeps one for their own towns.
>
> Thank you for the work the Association does; a state where 1,200 small governments have a
> common voice is better served than one where they do not.
>
> <YOUR NAME>
> districtry.com
> <YOUR E-MAIL>

**What each answer means.**

| answer | what it settles |
|---|---|
| "yes, here it is" / "yes, for a fee" | The level closes properly: a roster file, a weekly or annual refresh, and the Association credited on the card and the sources page. A fee is the operator's call. |
| "members only" | The level closes with a RECORD rather than a layer, and a good one: the data exists, is held by a named body, and is not available on terms this project can meet. That is the measured absence the fourth test asks for. |
| "no such list exists" | Also a record, and a stronger one than the measurement alone, because the towns' own organisation is the best-placed witness there could be. The pointer to a county-level keeper, if one comes, is the next ask. |
| no reply after the follow-up cadence | `UNRESPONSIVE` in the ledger — a claim about the ask and never about the data. Follow up once at about three weeks, then once more, then record it. |

**One thing deliberately not done.** No town was written to directly. There are roughly 1,250
of them, most with a part-time clerk, and 1,250 letters to close one level is a cost borne by
other people for this project's convenience. The Association is one letter to the body that
exists precisely to answer for all of them, and if it says no then a sample of counties is the
next step rather than a mailing.

---

## Ask wi-city-council-pages — Beloit: may we read your council page?

> **RE-CHECKED 2026-10-06 UNDER THE READ-THE-PAGE-FIRST RULE. THE REFUSAL STANDS AND ONE
> SENTENCE OF THE LETTER WAS FALSE FOR BELOIT, NOW CORRECTED.** The rule asks whether a page we
> called unreadable actually loads its names from a feed we could read. For Beloit that question
> cannot be asked: `www.beloitwi.gov/robots.txt` was re-read with the same token as before and is
> unchanged (HTTP 200, 573 bytes, six named crawlers with narrow rules, then `User-agent: *` /
> `Disallow: /`). That refuses the council page AND everything a feed hunt would need, the page
> source included, so nothing on that host was fetched. The file names the same six crawlers as
> the seven Wisconsin county hosts `validate_card_links.py` records as one CMS vendor's default,
> though it is not byte-identical to them (Beloit's Googlebot and bingbot groups carry two extra
> rules); the letter already allows that the block may be a default rather than a decision.
> **THE FALSE SENTENCE:** the shared template says the map "draws every aldermanic district in
> <CITY> and names nobody in them". The state's ward file (`WI_Municipal_Wards_Current`, read
> 2026-10-06) codes all 32 of Beloit's city wards `ALDERID 00`, so the map draws no Beloit
> district at all. Beloit may elect its council at large, which would explain it, but that is not
> measured here and the letter does not claim it. Its paragraph now reads as the Beloit variant
> below.

> **WITHDRAWN FOR FOUR OF THE FIVE CITIES, 2026-10-01, later the same day. JANESVILLE,
> WAUSAU, WAUWATOSA AND MEQUON DO NOT BLOCK THIS PROJECT AND NEVER NEEDED A LETTER.** All four
> serve their robots.txt with HTTP 200 and PERMIT `/`, and all four serve their home and council
> pages — 146,771, 96,666, 111,716 and 57,621 bytes, Mequon's through Cloudflare. Their Gmail
> drafts were deleted rather than held, because a letter telling a city it turns us away when it
> does not is worse than no letter.
>
> **THE CAUSE WAS READING THE POLICY WITH A THINNER CLIENT THAN THE ONE THAT CRAWLS**, which is
> the one defect CLAUDE.md names for this exact pair of hosts and which this ask reproduced
> anyway. The measurement above was taken with `UA_HEADERS_ROSTER_BOT`, which carries no
> `sec-ch-ua` client hints. `wi/scripts/wi_municipal_executive_scraper.py` had already settled
> on 2026-09-29, leave-one-out and two reads per rung, that **those three headers are the whole
> difference** on `www.milwaukee.gov` and `www.wauwatosa.net` — 403 without them, a policy that
> permits us with them. Asked with `UA_HINTS_CHROME_126`, the client the Wisconsin scrapers
> actually send, all four answer 200.
>
> **THIS IS NOT AN ESCALATION AND THE DISTINCTION IS THE WHOLE RULE.** The fleet does not try a
> richer client to get a better verdict; it reads the policy with the client that will crawl.
> For a Wisconsin municipal host that client is Chrome plus the pinned hints, so the token read
> was the WRONG measurement rather than the cautious one. Beloit was deliberately **not**
> re-probed: its robots.txt is served to the token and says `Disallow: /`, which is a published
> refusal, and re-asking a host that already answered in order to get a different answer is
> exactly the escalation the rule forbids.
>
> **WHAT REPLACES THE FOUR LETTERS IS WORK, NOT AN ASK.** Four readable councils now want a
> scraper and a builder. Wausau's alderpersons page already shows 11 districts and 29
> alderperson mentions in its served bytes; Janesville says "council member" rather than
> "alderperson" and Mequon's list is not linked from its home page, so each needs its own look.
> That is Wisconsin's level 6 moving from waiting-on-a-reply to buildable.
>
> **AND THE GENERAL LESSON IS THE ONE THAT KEEPS COSTING THIS PROJECT.** A refusal is a dated
> measurement taken with a named client. Re-measure it with the client that crawls before
> writing to anyone about it, and above all before recording it as the reason a city names
> nobody — because a wrong refusal reads exactly like a right one, and it stops the work rather
> than prompting it.


> **NOT YET ASKED — DRAFTED 2026-10-01.** Five near-identical letters, one per city. Each asks
> permission to read a page the city already publishes to the public. Nothing is blocked that
> this project is working around, nothing is currently being fetched from any of the five, and
> no agent is renamed to get past anything.

**Why these five and not the other sixteen.** Of Wisconsin's 21 general-purpose governments
above 25,000 people that named no governing body on 2026-10-01: four were built the same day
(Franklin, Greenfield, Muskego, West Bend), Oshkosh turned out to be open and elects at large,
and eleven are readable and simply need their own small piece of work. These five are the only
ones where the obstacle is the city's own answer to an automated reader, so they are the only
ones where a record can substitute for a layer — and under the fourth test a record counts only
after an ask has been refused, or sent with one follow-up and thirty days' silence.

**What was measured, 2026-10-01, with the exact client that would crawl.**

| city | 2020 population | what it answers |
|---|---|---|
| Beloit | 36,657 | `robots.txt` publishes `User-agent: * / Disallow: /` under six named crawlers that get narrow rules. The city's own file on the city's own host, so it binds fully. |
| Janesville | 65,615 | HTTP 403 at the HOME page, not merely on `robots.txt`. **AkamaiGHost** answers it, with an `Access Denied` body |
| Wausau | 39,994 | HTTP 403 at the HOME page, **AkamaiGHost**, same body |
| Wauwatosa | 48,387 | HTTP 403 at the HOME page, **AkamaiGHost**, same body |
| Mequon | 25,129 | **CORRECTED 2026-10-01, later the same day.** `robots.txt` is SERVED — HTTP 200, 2,005 bytes, deterministic over three reads fifteen seconds apart — and no rule in its one binding group matches `/`, so Mequon's published policy PERMITS this project. What stops the read is a **Cloudflare managed challenge** on the content pages: the home page's 403 carries the `Just a moment...` interstitial, which is an access control and is never solved or worked around |

**WHO ANSWERED THE 403 WAS CHECKED, AND THAT IS NOT A FORMALITY.** CLAUDE.md records that a 403
from an egress proxy is not a 403 from a site — in this sandbox `github.com` itself 403s with the
proxy's own JSON body — so a refusal recorded without reading the responder is a guess. All four
came from the cities' own edge (`Server: AkamaiGHost` on three, `Server: cloudflare` on Mequon),
so the measurement holds.

**THE MEQUON CORRECTION DID NOT CHANGE WHAT WE MAY DO AND DID CHANGE WHAT WE MAY SAY.** A city
whose rules file turns us away has decided something; a city whose rules file welcomes us while a
security product turns us away probably has not, and its letter says so and asks for the hand-off
on that basis. It is also NOT a `CHALLENGE_FRONTED_HOSTS` entry: that table is for a host whose
answers are non-deterministic, and Mequon's are not — the robots read is stable and the page
challenge is consistent.

**The four 403s are a site-wide block that enforces itself**, which is #1271's own reading of why
a 403 on `robots.txt` needed no strict treatment: a server refusing every path needs no policy
rule to be effective. **None of the five was probed with a second client.** A host that refuses
the first is not an invitation to try a richer one, and escalating to get a better answer is
working around an access control rather than measuring one.

**Recipients.** Each city's Clerk, from the Wisconsin Elections Commission's own directory,
which this project already ships — so no refused site was read to find them:

| city | clerk | telephone |
|---|---|---|
| Beloit | Rebecca Wallendal | 608-364-6682 |
| Janesville | Lori Stottler | 608-755-3070 |
| Mequon | Caroline Fochs | 262-236-2912 |
| Wausau | Rachel Brown | 715-261-6622 |
| Wauwatosa | Deyanira Nevarez | 414-479-8917 |

**THERE IS NO E-MAIL ADDRESS TO FIND, AND THAT IS A WITHHOLDING BY THE PEOPLE NAMED RATHER THAN
A GAP IN OUR READING** (settled 2026-10-01, when the six letters were drafted into the operator's
mailbox). The Commission's directory carries no e-mail address for any of the five — 0 of 1,848
records in the shipped file contain an `@`, the source PDF's own `/Subject` metadata reads
`WI Municipal Clerks PDF - no emails:`, and the Commission said why: *"that was at their
request"*. `wi/scripts/build_wi_municipal_clerks.py` already rules on what follows from that, and
the rule covers this ask exactly: **nothing here goes looking for those addresses elsewhere to
backfill them.** The cities' own contact pages are behind the very block this ask is about, so
there was nowhere permitted to look even if the rule allowed it.

**SO FIVE OF THE SIX DRAFTS CARRY NO RECIPIENT**, and the empty address field is the safeguard —
a mail client will not send without one. Each opens with a bracketed note naming the clerk and
their telephone number, saying why the address is blank, and asking the operator to supply it. The
operator browses as a person, which all five sites serve perfectly well; that lookup is
deliberately not automated, and it is the operator's to make rather than ours to route around.

**WAUWATOSA IS THE ONE EXCEPTION AND IT IS A PUBLISHED OFFICE ADDRESS, NOT A PERSON'S.**
`wi/data/app/wi-municipal-executives.json` already ships `mayor@wauwatosa.net`, from Milwaukee
County GIS — a government publisher, fetched legitimately, and an address belonging to an office
rather than to anyone the Commission's withholding protects. That draft is addressed to the Clerk
and routed through the Mayor's office, and it says in its first line that it is being routed and
why, so nobody is left guessing how the letter arrived.

Draft (one per city; `<CITY>`, `<CLERK>` and the bracketed clause are the only parts that change):

> Subject: districtry.com — may we read the Common Council page automatically?
>
> Dear <CLERK>,
>
> I run districtry.com, a free, non-commercial public map that shows anyone which units of
> government cover a given address and who represents them there. Wisconsin's part of it is at
> districtry.com/wi/. It draws every aldermanic district in <CITY> and, at the moment, names
> nobody in them, which is the thing I am writing about.
>
> [For Beloit, in place of the sentence above: It shows which city covers an address in Beloit
> but, at the moment, names nobody on your City Council, which is the thing I am writing about.
> And in the next paragraph, "the one that lists each alderperson and their district" becomes
> "the one that lists each council member".]
>
> [For Beloit: Your website's robots.txt asks automated readers to stay off the whole site, and
> I am following that request — this letter is not a complaint about it and I have not tried to
> get around it.]
> [For the other four: Your website turns away the sort of automated reader I use, on every
> page rather than only on the rules file, and I have taken that as an answer rather than trying
> a different disguise.]
>
> The page I would like to read is your Common Council page — the one that lists each
> alderperson and their district. It is already public, and anyone with a browser can read it; I
> am asking only whether a small program may read the same page about once a week so the names
> on the map stay current when your council changes.
>
> Concretely, what that means: one request a week to one page, identifying itself plainly as
> districtry, honouring whatever rules you publish. Nothing else on your site, no bulk download,
> no attempt to reach anything that is not already public. The names appear on the map credited
> to the City of <CITY> with a link back to your page.
>
> Three answers, any of which is genuinely useful:
>
> 1. **Yes.** A short note is all I need, and I will record it with the page.
> 2. **Yes for that page only**, or by a different route — your open-data portal, a file you
>    e-mail, whatever is least trouble for you. Naming it closes the question for good.
> 3. **No.** Then I will record on the map that <CITY> does not name its council members here,
>    and that the reason is a decision of the City's, which is a far more honest thing to tell a
>    reader than silence. I will not ask again.
>
> If the block is not deliberate — some of these are a default setting on a web server rather
> than anyone's decision — then whoever looks after the website would be the person to ask, and
> I would be glad of the hand-off.
>
> Thank you for your time. Publishing a council list at all is more than some cities manage.
>
> <YOUR NAME>
> districtry.com
> <YOUR E-MAIL>

**What each answer means.**

| answer | what it settles |
|---|---|
| "yes" / "yes, this route" | That city joins the aldermanic roster on its next weekly run, with the permission recorded beside its scraper and the date it was given. |
| "no" | The city tier closes for that unit with a RECORD, and a properly earned one: a measured block, a named ask, a dated refusal. That is exactly what the fourth test asks for. |
| "that was not deliberate, talk to IT" | The best outcome, and likelier than it sounds for the four 403s. The hand-off becomes the ask. |
| no reply | Follow up once at about three weeks. Thirty days of silence after that follow-up makes the record count, per the standard. A claim about the ask, never about the city. |

**Two things deliberately not done.** No second client was tried against any of the five, for the
reason above. And no third-party copy was sought — an archived or mirrored council page would
answer the data question and sidestep the permission question entirely, which is the wrong way
round.

---

## Ask wi-oshkosh-council — City of Oshkosh Clerk: our reader cannot reach your robots.txt

> **RE-CHECKED 2026-10-06 UNDER THE READ-THE-PAGE-FIRST RULE. THE LETTER STANDS AS WRITTEN.**
> The rule asks whether names we called unreadable sit in a feed we could read. Oshkosh's do
> not need one: its council page carries the seven names in its own HTML, which is why the
> scraper is already written. What stops it is the robots read, and that is unchanged from both
> places that matter. From this sandbox, the scraper's own client fails the handshake
> (`UNEXPECTED_EOF_WHILE_READING`) while `curl` gets the 331-byte file. From a GitHub runner, the
> weekly Oshkosh job on 2026-10-01 at 23:04 UTC failed with `Connection reset by peer`, three
> attempts, and fetched nothing (run 36938706422). The next weekly run is 2026-10-08. No other
> client was tried.

> **NOT YET ASKED — DRAFTED 2026-10-01.** The only one of the 21 unnamed Wisconsin cities where
> the obstacle is neither a refusal nor a page that needs a browser, but a connection this
> project cannot complete and cannot explain. It asks one question and offers the city
> something useful in return: the symptom, from two independent addresses, which a city's own
> IT staff can act on and nobody outside the city can.

**To:** City of Oshkosh, City Clerk's Office — Darla Salinas, City Clerk; (920) 236-5013
**Subject:** Our automated reader cannot reach https://www.ci.oshkosh.wi.us/robots.txt

> **NO E-MAIL ADDRESS, FOR THE SAME REASON AS THE FIVE ABOVE** (2026-10-01). The Elections
> Commission's clerk directory withholds every municipal clerk's address at the clerks' own
> request, and this project's standing rule is not to go looking for those addresses elsewhere
> to backfill them. Oshkosh's own site cannot be reached by this client at all, so there was
> nowhere permitted to look in any case. The draft sits in the operator's mailbox with the
> address field empty — which is what stops it being sent by accident — and opens with a
> bracketed note naming the clerk, her telephone number and the reason.

**Why this ask exists.** Oshkosh publishes its Common Council on a public page and we would
like to name those seven officials on a free, non-commercial map. Before reading any page on a
site, this project reads that site's `robots.txt` and obeys it, and where that file cannot be
read at all the rule we follow (RFC 9309 §2.3.1.4) says to treat the site as closed. So
Oshkosh is the one city of the 21 that is not shut by anybody's decision and is not shipped
either — and the ask is simply whether the city intends that, and whether it is something the
city can see from its side.

**What was measured first, and is stated in the ask so it does not read as a question somebody
could have answered by searching.** Measured 2026-10-01 from two independent addresses with
the same client that would do the reading:

| Where | What happened |
| --- | --- |
| A sandboxed build environment | the TLS handshake fails with `UNEXPECTED_EOF_WHILE_READING`, unchanged over three attempts |
| A GitHub Actions runner, which is where our weekly jobs run | `Connection reset by peer`, three reads fifteen seconds apart, every one |
| `curl` from the same sandbox | completes, and returns the file |

**The two symptoms are different and we do not claim to know what they share.** One fails
inside the TLS handshake and the other at the socket; both sit below HTTP. What makes it worth
writing about is the third row: a plain `curl` reaches the same server from the same address
that the Python client cannot, so the server is not down and something about the connection is
the variable. That is a difference the city's own staff or its hosting provider can see in a
log and we cannot.

**What is deliberately NOT asked and not done.** We do not ask for a rule to be changed in our
favour, and we are not asking to be allowed past anything: if Oshkosh intends automated readers
to be turned away, that is a complete answer and the city tells us so in one line. We did not
try a different client, a browser user-agent, or a lowered TLS security level to get through —
the first is not what this project does, and the last would be reading a site's permissions
with a client we do not crawl with, which defeats the point of reading them. We did not take
the council names from an archived or mirrored copy, which would answer the data question while
sidestepping the permission question. And no named official is asked for anything personally;
this is a question for whoever looks after the city's website.

**Why even a no is useful and is said so plainly.** A no closes this for good and lets the
record we show readers say that the city asked not to be read, rather than that we could not
work out how. A yes costs the city nothing it has not already published.

**What each answer means**

| Answer | What happens |
| --- | --- |
| "Yes, read it" plus a fix or an explanation of the connection failure | the council page is read weekly and the seven officials are named on the card, exactly as five other Wisconsin municipalities already are |
| "We do not want automated readers" | the city is recorded as having declined, with the date, and nothing is fetched from it again; under the fourth test that record stands in for the layer |
| "We do not know why" | the symptom is recorded as measured from both addresses and unexplained, which is the honest state, and the city is not asked again |
| No reply | followed up once after about three weeks, and once more after another two; thirty days' silence after that is recorded as the answer |

---

## Ask mi-city-township-boards — Michigan cities and townships whose board pages this app cannot read

> **ASKED 2026-10-01 FOR NINE OF THE TEN — the operator sent them from his own mailbox between
> 14:48 and 14:51 UTC. BURTON IS NOT YET ASKED**, because its clerk's address has not been read
> (see the recipients table). THREE OF THE NINE GAVE A WRONG REASON and the operator sent a
> correction to each, in the same thread, at 15:21-15:23 UTC; see "Three letters went out on a
> wrong reason" below. One message per unit, to its clerk. Each unit has its
> own gap record in `docs/DATA_LAYER_GUIDEBOOK.md` (named in the table below), already carrying
> `"covers": ["local-government:<its geoid>"]`. On send, add `"ask": {"who": "<clerk, by name>", "asked":
> "<date>"}` to that unit's record and change its `NOT YET ASKED — DRAFTED` to `ASKED <date>`;
> add `followedUp` on the follow-up, and `outcome` (`refused`, or `unresponsive` once thirty days
> have passed from the follow-up) when it is true. A reply that sends the list is `answered`,
> and the work is then to read it, not to record the level.
>
> **The six letters still waiting carry an `ask` field with `outcome: "pending"`** (Rochester
> Hills, Norton Shores, West Bloomfield, Bedford, Lansing, Wyoming), `asked: 2026-10-01` and
> the clerk's name; the send times stay in the table above. The other three records were
> retired when their boards shipped. Lansing's 14:51 reply was an automatic acknowledgement,
> which is not an answer, so its ask stays pending.

**Why these letters exist.** The done standard asks that a reader in any Michigan city or
township over 25,000 people be told who governs it. Of the 82 such units, most publish their
board on a page this project reads every week. The ones below do not, for one of three reasons,
and the standard counts a unit as recorded rather than missing only once it has been asked and
has said no, or has been asked, followed up once and given 30 days.

| unit | record | what stops us | measured |
|---|---|---|---|
| Rochester Hills (city) | `rochester-hills-council-roster` | its robots.txt asks every automated client to stay out | 2026-09-06 |
| Norton Shores (city) | `norton-shores-council-roster` | its robots.txt asks every automated client to stay out | 2026-10-01 |
| West Bloomfield (charter township) | `west-bloomfield-township-board` | its website vendor's robots.txt, served for the township's own address, asks every automated client to stay out | 2026-10-01 |
| Bedford (township) | `bedford-township-board` | the same vendor default as West Bloomfield | 2026-10-01 |
| Shelby (charter township) | `shelby-township-board` | ~~the site answers this client "Access Denied"~~ **wrong: one client was tried; the fleet's browser-class client is served the page** | 2026-10-01 |
| Northville (township) | `northville-township-board` | ~~the site answers this client "Access Denied"~~ **wrong: one client was tried; the fleet's browser-class client is served the page** | 2026-10-01 |
| Ypsilanti (charter township) | `ypsilanti-township-board` | ~~a Cloudflare challenge page, which is an access control and is never worked around~~ **no longer true: re-read the same day, the page is served to our own token** | 2026-10-01 |
| Burton (city) | `burton-council-roster` | a Cloudflare challenge page | 2026-10-01 |
| Lansing (city) | `lansing-council-roster` (retired 2026-10-06) | ~~the page answers, but the names are loaded by a script after the page arrives, so the page itself carries none~~ **closed: the page hands every visitor a read-only key for the service the names come from, and the weekly reader now reads them the way the page does** | 2026-10-01 |
| Wyoming (city) | `wyoming-mi-council-roster` | **the operator's own ruling keeps this project off the city's site entirely.** Whether to write at all is Adam's decision; the draft is here so the decision is the only thing left. | ruling |

**Recipients, recorded 2026-10-01 on the operator's instruction that every letter also goes
into his mailbox.** This section used to say the addresses would be read off each unit's own
site at send, because most of these sites refuse this client. They were found instead through a
web search engine's listings of each unit's own clerk page, without fetching any of the ten
sites: reading a site that asks us not to, or that challenges us, would be the thing these
letters are asking permission for. A search listing is one step removed from the page, so
**open each unit's clerk page in a browser before sending and check the address and the name**.
Two are known to need it: the search listings name two different people as Ypsilanti
Township's clerk, so that letter is addressed to the office; and Burton's clerk page hides its
e-mail addresses from automated readers, so its draft has no recipient yet.

| unit | addressed to | address | where the address came from |
|---|---|---|---|
| Rochester Hills | Leanne Scott, City Clerk | `clerksoffice@rochesterhills.org` | the Clerk's Office address the city publishes on its clerk and election pages |
| Norton Shores | Rachel Pavlich, City Clerk | `rpavlich@nortonshores.org` | the city's clerk page |
| West Bloomfield Township | Debbie Binder, Township Clerk | `dbinder@wbtownship.org` | the township clerk's directory page |
| Bedford Township | Trudy L. Hershberger, Township Clerk | `thershberger@bedfordmi.org` | the township clerk's page |
| Shelby Township | Stanley Grot, Township Clerk | `sgrot@shelbytwp.org` | the township clerk's office page |
| Northville Township | Cynthia L. Jankowski, Township Clerk | `cjankowski@twp.northville.mi.us` | the township clerk's office page (the office's shared address is Clerk@twp.northville.mi.us) |
| Ypsilanti Township | the Township Clerk's office | `clerk@ypsitownship.org` | the township clerk's office page; the clerk is named differently by two search listings, so the letter is addressed to the office. Township Clerk Debbie Swanson (`dswanson@ypsitownship.org`) answered it herself |
| Burton | Racheal Boggs, City Clerk | **none recorded** | NOT FOUND: the city's clerk page hides its e-mail addresses from automated readers, so the address must be read in a browser |
| Lansing | Chris Swope, City Clerk | `city.clerk@lansingmi.gov` | the Clerk's Office address printed on the city's own published notices |
| Wyoming | Kelli VandenBerg, City Clerk | `clerk_info@wyomingmi.gov` | a search listing of the city's clerk page; this project does not read the city's site |

**Three letters went out on a wrong reason, and the check that would have caught it ran after
they were sent.** Before the operator sent anything, each unit's site was meant to be re-read
with exactly the client that would crawl it; that re-read happened at 15:09 UTC, after the
send. It held for six (Rochester Hills, Norton Shores, West Bloomfield and Bedford refuse us in
robots.txt; Burton serves a Cloudflare challenge; Lansing's page names nobody without its
scripts) and Wyoming was not fetched, by ruling. It failed for three:

- **Shelby and Northville** were recorded "Access Denied, no other client tried", and the letter
  repeated it. Through the fleet's four-rung probe both serve the board page to the browser
  string with Chrome client hints on the stdlib stack, the Kendall and McHenry shape. A site
  that needs a browser-class client has not refused automation, and this project's rule allows
  that client where the token is measurably refused, so these two need a reader, not a letter.
- **Ypsilanti** answered with a Cloudflare challenge in the morning and served the scraper's own
  token in the afternoon. The clerk replied at 15:13 UTC that she has forwarded the request to
  the township's technology staff.

Each of the three got a short correction, as a reply in the same thread, saying the site can be
read after all and nothing needs changing; Ypsilanti's also thanks the clerk. The operator sent
them at 15:21 (Northville), 15:22 (Shelby) and 15:23 UTC (Ypsilanti). **Ypsilanti's office had
already done work on a request we then withdrew**: the clerk passed it to the township's
technology staff at 15:13, ten minutes before the correction reached her. That is the cost of
the wrong order, and it fell on somebody else. The three gap records now say the page is readable and the
reader is not yet written. **Later the same day the readers were written** and the three
records retired: Shelby and Northville are read with the browser string their sites serve
(the measurement is in `mi/scripts/mi_municipal_parsers_browser.py`), Ypsilanti with the roster
token. The rows below for those three are kept as the record of what the letters said.
**The order is the lesson: re-read the premise with the crawling
client before a letter is drafted, not after it is sent.** A record that says "no other client
was tried" is a record that has not yet been measured.

**Two versions of one letter**, because the ask differs: the robots.txt units are asked for
permission; the other units are asked whether the refusal is meant for a site like this one.

### Draft A — the unit's robots.txt asks automated clients to stay out

> **Subject: <Unit> board members on districtry.com — may an automated reader see your board page?**
>
> Dear <Clerk's name>,
>
> I run districtry.com, a free, non-commercial public map that shows anyone which governments
> cover their address and who represents them there. Michigan's map is at districtry.com/mi/.
>
> For most large Michigan cities and townships, the map names the council or board, read once a
> week from the government's own website so it stays current. For <Unit> it names nobody,
> because your website's robots.txt file asks automated tools not to read any of it, and this
> project follows that request.
>
> Three answers would each settle it, and a plain "no" is a useful one:
>
> 1. If one automated read of your board members page a week is acceptable, a short note saying
>    so is all I need.
> 2. If you would rather send the list yourself whenever it changes, that works too, and the map
>    will say the list came from your office and when.
> 3. If you would rather the map named nobody, say so and it will keep linking to your own site
>    instead.
>
> There is no cost or obligation of any kind.
>
> <YOUR NAME>
> districtry.com
> <YOUR E-MAIL>

### Draft B — the unit's site refuses or challenges this client

> **Subject: <Unit> board members on districtry.com — your website blocks our weekly reader**
>
> Dear <Clerk's name>,
>
> I run districtry.com, a free, non-commercial public map that shows anyone which governments
> cover their address and who represents them there. Michigan's map is at districtry.com/mi/.
>
> For most large Michigan cities and townships, the map names the council or board, read once a
> week from the government's own website so it stays current. For <Unit> it names nobody,
> because your website turns away our reader before any page loads. That is very likely a
> general security setting rather than a decision about us, and I do not try to get around it.
>
> Any one of these would settle it, and a plain "no" is a useful answer too:
>
> 1. If whoever runs the site can let one automated read of the board page a week through, it
>    identifies itself as "districtry.com roster bot".
> 2. If you would rather send the list yourself whenever it changes, the map will say the list
>    came from your office and when.
> 3. If you would rather the map named nobody, say so and it will keep linking to your own site.
>
> There is no cost or obligation of any kind.
>
> <YOUR NAME>
> districtry.com
> <YOUR E-MAIL>

For **Lansing**, replace the second paragraph's reason with: "because the council page builds
its list of members in the browser after the page loads, so the page an automated reader
receives has no names in it", and ask whether the same list is published anywhere as plain text
or a file.

### The ten letters, as drafted in the operator's mailbox

Draft A and Draft B above are the templates. These are the filled letters, word for word as
they sit in Gmail, so the mailbox and this file cannot drift. Lansing takes the variant noted
above, and Wyoming has its own second paragraph because this project does not read its site
at all. **Whether to send Wyoming's is still the operator's decision.**

#### Rochester Hills

To: clerksoffice@rochesterhills.org  
Subject: Rochester Hills City Council members on districtry.com: may an automated reader see your council page?

> Dear Ms. Scott,
>
> I run districtry.com, a free, non-commercial public map that shows anyone which governments cover their address and who represents them there. Michigan's map is at https://districtry.com/mi/.
>
> For most large Michigan cities and townships, the map names the council or board, read once a week from the government's own website so it stays current. For Rochester Hills it names nobody, because your website's robots.txt file asks automated tools not to read any of it, and this project follows that request.
>
> Three answers would each settle it, and a plain "no" is a useful one:
>
> 1. If one automated read of your council members page a week is acceptable, a short note saying so is all I need.
> 2. If you would rather send the list yourself whenever it changes, that works too, and the map will say the list came from your office and when.
> 3. If you would rather the map named nobody, say so and it will keep linking to your own site instead.
>
> There is no cost or obligation of any kind.
>
> With thanks,
> Adam Overberg
> adam@overberg.co
> districtry: https://districtry.com/mi/

#### Norton Shores

To: rpavlich@nortonshores.org  
Subject: Norton Shores City Council members on districtry.com: may an automated reader see your council page?

> Dear Ms. Pavlich,
>
> I run districtry.com, a free, non-commercial public map that shows anyone which governments cover their address and who represents them there. Michigan's map is at https://districtry.com/mi/.
>
> For most large Michigan cities and townships, the map names the council or board, read once a week from the government's own website so it stays current. For Norton Shores it names nobody, because your website's robots.txt file asks automated tools not to read any of it, and this project follows that request.
>
> Three answers would each settle it, and a plain "no" is a useful one:
>
> 1. If one automated read of your council members page a week is acceptable, a short note saying so is all I need.
> 2. If you would rather send the list yourself whenever it changes, that works too, and the map will say the list came from your office and when.
> 3. If you would rather the map named nobody, say so and it will keep linking to your own site instead.
>
> There is no cost or obligation of any kind.
>
> With thanks,
> Adam Overberg
> adam@overberg.co
> districtry: https://districtry.com/mi/

#### West Bloomfield Township

To: dbinder@wbtownship.org  
Subject: West Bloomfield Township board members on districtry.com: may an automated reader see your board page?

> Dear Ms. Binder,
>
> I run districtry.com, a free, non-commercial public map that shows anyone which governments cover their address and who represents them there. Michigan's map is at https://districtry.com/mi/.
>
> For most large Michigan cities and townships, the map names the council or board, read once a week from the government's own website so it stays current. For West Bloomfield Township it names nobody, because your website's robots.txt file asks automated tools not to read any of it, and this project follows that request.
>
> Three answers would each settle it, and a plain "no" is a useful one:
>
> 1. If one automated read of your board members page a week is acceptable, a short note saying so is all I need.
> 2. If you would rather send the list yourself whenever it changes, that works too, and the map will say the list came from your office and when.
> 3. If you would rather the map named nobody, say so and it will keep linking to your own site instead.
>
> There is no cost or obligation of any kind.
>
> With thanks,
> Adam Overberg
> adam@overberg.co
> districtry: https://districtry.com/mi/

#### Bedford Township

To: thershberger@bedfordmi.org  
Subject: Bedford Township board members on districtry.com: may an automated reader see your board page?

> Dear Ms. Hershberger,
>
> I run districtry.com, a free, non-commercial public map that shows anyone which governments cover their address and who represents them there. Michigan's map is at https://districtry.com/mi/.
>
> For most large Michigan cities and townships, the map names the council or board, read once a week from the government's own website so it stays current. For Bedford Township it names nobody, because your website's robots.txt file asks automated tools not to read any of it, and this project follows that request.
>
> Three answers would each settle it, and a plain "no" is a useful one:
>
> 1. If one automated read of your board members page a week is acceptable, a short note saying so is all I need.
> 2. If you would rather send the list yourself whenever it changes, that works too, and the map will say the list came from your office and when.
> 3. If you would rather the map named nobody, say so and it will keep linking to your own site instead.
>
> There is no cost or obligation of any kind.
>
> With thanks,
> Adam Overberg
> adam@overberg.co
> districtry: https://districtry.com/mi/

#### Shelby Township

To: sgrot@shelbytwp.org  
Subject: Shelby Township board members on districtry.com: your website blocks our weekly reader

> Dear Mr. Grot,
>
> I run districtry.com, a free, non-commercial public map that shows anyone which governments cover their address and who represents them there. Michigan's map is at https://districtry.com/mi/.
>
> For most large Michigan cities and townships, the map names the council or board, read once a week from the government's own website so it stays current. For Shelby Township it names nobody, because your website turns away our reader before any page loads. That is very likely a general security setting rather than a decision about us, and I do not try to get around it.
>
> Any one of these would settle it, and a plain "no" is a useful answer too:
>
> 1. If whoever runs the site can let one automated read of the board page a week through, it identifies itself as "districtry.com roster bot".
> 2. If you would rather send the list yourself whenever it changes, the map will say the list came from your office and when.
> 3. If you would rather the map named nobody, say so and it will keep linking to your own site.
>
> There is no cost or obligation of any kind.
>
> With thanks,
> Adam Overberg
> adam@overberg.co
> districtry: https://districtry.com/mi/

#### Northville Township

To: cjankowski@twp.northville.mi.us  
Subject: Northville Township board members on districtry.com: your website blocks our weekly reader

> Dear Ms. Jankowski,
>
> I run districtry.com, a free, non-commercial public map that shows anyone which governments cover their address and who represents them there. Michigan's map is at https://districtry.com/mi/.
>
> For most large Michigan cities and townships, the map names the council or board, read once a week from the government's own website so it stays current. For Northville Township it names nobody, because your website turns away our reader before any page loads. That is very likely a general security setting rather than a decision about us, and I do not try to get around it.
>
> Any one of these would settle it, and a plain "no" is a useful answer too:
>
> 1. If whoever runs the site can let one automated read of the board page a week through, it identifies itself as "districtry.com roster bot".
> 2. If you would rather send the list yourself whenever it changes, the map will say the list came from your office and when.
> 3. If you would rather the map named nobody, say so and it will keep linking to your own site.
>
> There is no cost or obligation of any kind.
>
> With thanks,
> Adam Overberg
> adam@overberg.co
> districtry: https://districtry.com/mi/

#### Ypsilanti Township

To: clerk@ypsitownship.org  
Subject: Ypsilanti Township board members on districtry.com: your website blocks our weekly reader

> Dear Township Clerk,
>
> I run districtry.com, a free, non-commercial public map that shows anyone which governments cover their address and who represents them there. Michigan's map is at https://districtry.com/mi/.
>
> For most large Michigan cities and townships, the map names the council or board, read once a week from the government's own website so it stays current. For Ypsilanti Township it names nobody, because your website turns away our reader before any page loads. That is very likely a general security setting rather than a decision about us, and I do not try to get around it.
>
> Any one of these would settle it, and a plain "no" is a useful answer too:
>
> 1. If whoever runs the site can let one automated read of the board page a week through, it identifies itself as "districtry.com roster bot".
> 2. If you would rather send the list yourself whenever it changes, the map will say the list came from your office and when.
> 3. If you would rather the map named nobody, say so and it will keep linking to your own site.
>
> There is no cost or obligation of any kind.
>
> With thanks,
> Adam Overberg
> adam@overberg.co
> districtry: https://districtry.com/mi/

#### Burton

To: (no address yet: read it off the city clerk page in a browser)  
Subject: Burton City Council members on districtry.com: your website blocks our weekly reader

> Dear Ms. Boggs,
>
> I run districtry.com, a free, non-commercial public map that shows anyone which governments cover their address and who represents them there. Michigan's map is at https://districtry.com/mi/.
>
> For most large Michigan cities and townships, the map names the council or board, read once a week from the government's own website so it stays current. For Burton it names nobody, because your website turns away our reader before any page loads. That is very likely a general security setting rather than a decision about us, and I do not try to get around it.
>
> Any one of these would settle it, and a plain "no" is a useful answer too:
>
> 1. If whoever runs the site can let one automated read of the council page a week through, it identifies itself as "districtry.com roster bot".
> 2. If you would rather send the list yourself whenever it changes, the map will say the list came from your office and when.
> 3. If you would rather the map named nobody, say so and it will keep linking to your own site.
>
> There is no cost or obligation of any kind.
>
> With thanks,
> Adam Overberg
> adam@overberg.co
> districtry: https://districtry.com/mi/

#### Lansing

To: city.clerk@lansingmi.gov  
Subject: Lansing City Council members on districtry.com: is the member list published as plain text?

> Dear Mr. Swope,
>
> I run districtry.com, a free, non-commercial public map that shows anyone which governments cover their address and who represents them there. Michigan's map is at https://districtry.com/mi/.
>
> For most large Michigan cities and townships, the map names the council or board, read once a week from the government's own website so it stays current. For Lansing it names nobody, because the council page builds its list of members in the browser after the page loads, so the page an automated reader receives has no names in it.
>
> Any one of these would settle it, and a plain "no" is a useful answer too:
>
> 1. If the same list of council members is published anywhere as plain text or as a file, a link to it is all I need.
> 2. If you would rather send the list yourself whenever it changes, the map will say the list came from your office and when.
> 3. If you would rather the map named nobody, say so and it will keep linking to your own site.
>
> There is no cost or obligation of any kind.
>
> With thanks,
> Adam Overberg
> adam@overberg.co
> districtry: https://districtry.com/mi/

#### Lansing, reply of 2026-10-06 (WITHDRAWN, NOT SENT)

**Withdrawn the same day, before it went.** The paragraph and the letter below rest on a wrong
reading. The page that names nobody also carries, for every visitor who has not signed in, the
content service's address and a read-only key for it (client `mi-lansing:default`, read scopes
only); the 401 came from calling the service without the settings the page supplies, the
mistake already made with Scott County, Illinois. Read with that key, on the operator's word of
2026-10-06, the service returns all eight members, so the page the Clerk pointed at does meet
the need. The weekly reader now reads Lansing that way, the `lansing-council-roster` record is
retired, and the ask closes `answered`. The thank-you below replaces this letter. The withdrawn
letter is kept under this note so that the mistake can be found later.

The Clerk answered on 2026-10-03, asking whether https://www.lansingmi.gov/council-members
meets our needs. It was re-read on 2026-10-06 with the client the weekly reader uses: the page
and its robots.txt permit us, and the page as served still names nobody. The names are added
afterwards by the website vendor's script, from the vendor's content service, which turns away
any request without a sign-in, and getting past a sign-in is not something this project does.
The measurement is in the `lansing-council-roster` record. The ask stays `pending`: a reply
that points at a page is not yet an answer the map can use.

To: city.clerk@lansingmi.gov  
Subject: Re: Lansing City Council members on districtry.com

> Dear Mr. Swope,
>
> Thank you for writing back, and for pointing me to the council members page. I checked it again today. The page loads, and the city's site settings allow it to be read. But the members' names are not in the page as it arrives. They are added a moment later by a program that runs in the visitor's browser and fetches them from your website company's content service, and that service turns away any request that has not signed in. So a reader that collects the page once a week receives the heading "Council Members" and no names.
>
> Any one of these would let the map name your council:
>
> 1. The members' names, with the ward or at-large seat each holds, typed into the text of that page or another city page, the way most Michigan cities publish theirs.
> 2. The same list as a file on the city's site, such as a PDF your office already keeps.
> 3. If it is easier, a reply listing the eight members and their seats. The map will say the list came from your office and on what date.
>
> If none of these suits the city, that is a fine answer, and the map will keep linking to your council page.
>
> With thanks,
> Adam Overberg
> adam@overberg.co
> districtry: https://districtry.com/mi/

#### Lansing, thank-you of 2026-10-06

Replaces the withdrawn reply above. It says the map names the council, so it should go only once
the change that adds Lansing's council to the map has been published.

To: city.clerk@lansingmi.gov  
Subject: Re: Lansing City Council members on districtry.com

> Dear Mr. Swope,
>
> Thank you for pointing me to the council members page. It does meet our needs. The names are loaded onto the page a moment after it opens, and once I read the page the same way a visitor's browser does, all eight members came through, with their seats, phone numbers and e-mail addresses.
>
> The map now names Lansing's City Council, says the list comes from the city's own council page, and reads that page again each week, so changes there will reach the map on their own. There is nothing more you need to do.
>
> With thanks,
> Adam Overberg
> adam@overberg.co
> districtry: https://districtry.com/mi/

#### Wyoming

To: clerk_info@wyomingmi.gov  
Subject: Wyoming City Council members on districtry.com: how would you like them listed?

> Dear Ms. VandenBerg,
>
> I run districtry.com, a free, non-commercial public map that shows anyone which governments cover their address and who represents them there. Michigan's map is at https://districtry.com/mi/.
>
> For most large Michigan cities and townships, the map names the council or board, read once a week from the government's own website so it stays current. For Wyoming it names nobody, because this project has chosen not to read your city's website at all, out of respect for the limits the site sets on automated tools.
>
> Any one of these would settle it, and a plain "no" is a useful answer too:
>
> 1. If you would be glad for an automated reader to look at the council members page once a week, a short note saying so is all I need.
> 2. If you would rather send the list yourself whenever it changes, the map will say the list came from your office and when.
> 3. If you would rather the map named nobody, say so and it will keep linking to your own site.
>
> There is no cost or obligation of any kind.
>
> With thanks,
> Adam Overberg
> adam@overberg.co
> districtry: https://districtry.com/mi/

### What each answer means

| answer | what it settles |
|---|---|
| "yes, that is fine" / "we've allowed it" | The unit gets a parser in `mi/scripts/mi_municipal_parsers_*.py` and its board ships the next week, with the permission recorded in `mi/WATCH.md`. |
| "here is the list" | The list ships as a dated document roster, never re-read, and the card says so. A follow-up ask goes out when the unit's next election seats new members. |
| "please name nobody" | A closing answer. The card keeps its link to the unit's own site and the gap record cites the reply. |
| no reply after one follow-up and 30 days | `UNRESPONSIVE` against the ask, never against the unit, and the unit counts as recorded for the done standard. |

---

## Ask ia-pottawattamie-tama-wright-boards — three Iowa counties: how many supervisors sit on the board, and who are they?

> **ASKED 2026-10-01 — ALL THREE, AND TAMA ANSWERED THE SAME AFTERNOON.** Three separate
> messages, one per county, each to that county's Auditor at the address
> `ia/data/app/ia-county-auditors.json` carries, every one confirmed in the operator's own sent
> folder: Tama (Karen Rohrs, 14:53:51 UTC), Wright (Amanda Meyer, 14:53:56) and Pottawattamie
> (Mary Ann Hanusa, 14:54:03). The ledger is updated in the
> `ia-supervisor-count-impossible` and `ia-supervisor-count-disagrees` blockers in
> `docs/DATA_LAYER_GUIDEBOOK.md` and in `ia/WATCH.md`, and both records now carry an `ask` block
> reading `pending`. A follow-up falls due for the two still silent at about three weeks
> (2026-10-22) and the thirty-day silence mark at 2026-10-31.
>
> **TAMA'S REPLY SPLIT THE RECORD IT CAME FROM.** Auditor Rohrs named five supervisors against
> districts 1 to 5, which settles the board's size and its members and makes the statewide
> directory's four the stale half — so Tama's question is answered and its card still names
> nobody, because the map this project ships draws three districts for the county. That is a
> different blocker from Pottawattamie's, which is a publisher's error plus a site this project
> may not read, so Tama left `ia-supervisor-count-impossible` for a record of its own,
> `ia-tama-supervisor-map`, and its follow-up is the ask of that name below. **A RECORD THAT
> HOLDS TWO COUNTIES CANNOT STATE EITHER ONE'S STATE ONCE THEY DIVERGE**, and it cannot carry an
> `ask` block at all, because that block names one desk.
>
> **THE NUMBER 34 IS CONTESTED AND MAY NOT BE THIS ASK'S.** Measured 2026-10-01: main's last
> ask is 33, and three open branches each number their next one 34 — this one (#1331),
> Wisconsin's (#1330) and Michigan's (#1333). Only the first to merge keeps it. Whoever merges
> after renumbers against main's last heading and updates every record that points at its own
> ask: for this one that is the heading below, the `ASK:` lines in the
> `ia-supervisor-count-impossible` and `ia-supervisor-count-disagrees` blockers in
> `docs/DATA_LAYER_GUIDEBOOK.md`, the row in `ia/WATCH.md`, and #1331's own description. Check
> main immediately before merging, not when the draft was written.
>
> **This ask is three counties and not eight, and the narrowing is what makes it worth
> sending.** On 2026-09-22 eight Iowa counties named no supervisor at all. Five closed without
> writing to anybody: Warren's was a defect in this repo, and Adair, Floyd, Humboldt and Lucas
> each publish their own board page. Pottawattamie, Tama and Wright are what is left, and each
> of them has a route that only a person can open.

### What the app already has, and what it is missing

* **The districts are drawn and they ship.** A reader clicking inside any of these three
  counties is correctly told which supervisor district they live in.
* **Every other county office ships.** Treasurer, recorder, sheriff, county attorney and
  auditor are all named in all three counties, from the same sources that fail on the board.
* **The board is the one row the card leaves blank**, and it says so in its own words rather
  than naming a board this project cannot confirm.

### The three, and why each is stuck

| county | what two publishers say | why it cannot be settled here |
|---|---|---|
| **Pottawattamie** | the county directory lists **six** supervisors | Iowa Code 331.201 allows three or five, so six cannot describe a lawful board. The county's own site answers HTTP 403 to every client this project will send, while publishing no robots.txt — so the refusal is at the edge rather than from the county, and reading past it would be defeating an access control. |
| **Tama** | the county directory lists **four** | Four is not a lawful board size either, so one row is spurious or one is missing, and nothing published says which. |
| **Wright** | the directory lists **five**, in districts 1 to 5; the state's own district map draws **three** | Five is lawful and the county naming districts 1 to 5 is strong evidence it elects from five, so the names are not in doubt — the MAP is. Publishing five names against a three-district map would seat a supervisor in a district no reader can be shown. |

**What the ask says.** We publish a free, non-commercial map that tells a reader which civic
districts cover a point and who represents them there, and Iowa is one of eight states it
answers for. We carry every other elected county office for your county and we are missing the
board of supervisors, because the two statewide sources we read disagree with each other. For
Pottawattamie and Tama: how many members does the board seat today, and who are they? For
Wright: how many districts does the board elect from today, and which supervisor holds each?

**What is deliberately not asked.** Nothing about reuse terms, because county officeholders are
public record. No request to change any website, and for Pottawattamie no mention of the 403 at
all — that is this project's problem to work around by asking a person, which is what this
letter is. And nothing is implied about either statewide source being at fault; the question is
what the county itself reports.

**Why a no is still useful.** A refusal, or thirty days of silence after one follow-up, lets
the record that tells our readers what is missing say that the county was asked, which is the
difference between a gap we have measured and a gap we have merely noticed.


## Ask ia-tama-supervisor-map — Tama County Auditor: your county's current five-district map

> **BUILT 2026-10-07 — CLOSED.** The five districts ship, drawn from the 2025 map she sent and
> gated on the Legislative Services Agency's published plan populations (four exact, one
> seven-person block declared, because her map draws the detached parcel in District 2). The
> county's own board page prints each supervisor's district, so the card now names all five,
> which keeps the promise in the reply sent in the operator's name. The record's history is a
> closed record in `docs/DATA_LAYER_GUIDEBOOK.md`; the county is credited in
> `docs/SOURCE_CREDITS.md`. The one open question is unchanged: which of the five telephone
> numbers are county lines, and until she says, none ships.
>

> **ASKED 2026-10-01** (sent 18:07:32 UTC as a reply on the existing thread, per
> `/mnt/project-files/letters/sent-2026-10-01.md`) and **ANSWERED 2026-10-01 18:24 UTC**:
> Auditor Rohrs attached the county's own five-district map, a vector PDF. Its measurement is
> in the numbering row of `ia/WATCH.md`. Building it needs the county's current precinct list,
> which is the follow-up at the end of this section, drafted 2026-10-06 and due about
> 8 October. It is a separate letter on purpose: the thank-you told her nothing more was being
> asked that day.
>
> **THIS IS A FOLLOW-UP TO AN ANSWER, NOT TO SILENCE.** Auditor Rohrs answered
> `ia-pottawattamie-tama-wright-boards` within the hour, in plain text, naming five supervisors
> against districts 1 to 5. Nothing is wrong with that reply and nothing more is wanted from it.
> The one thing between it and a card naming all five is a map: the statewide
> supervisor-district layer this project ships draws **three** districts for Tama, so publishing
> the five would seat two supervisors in districts no reader can be shown.
>
> **IT MATTERS TO A PROMISE ALREADY MADE.** The reply sent in the operator's name told her the
> county's entry would list all five supervisors with their respective districts. The shipped
> map cannot support that yet, so this letter is what makes that sentence true rather than
> something that quietly went unkept.

### What the app already has, and what it is missing

* **Her five names and districts are in hand** and are not in doubt. This asks nothing about
  them.
* **Every other elected county office ships for Tama** — treasurer, recorder, sheriff, county
  attorney and auditor.
* **The supervisor card names the county and no supervisors**, and says in its own words that
  the map it draws has three districts where the county elects from five.

**What the ask says.** Thank you for the five names and districts, which answered the question
completely. One thing on our side is still in the way: the statewide supervisor-district map we
draw from, published by the Legislative Services Agency and dated January 2024, has three
districts for Tama County rather than the five you named, so we cannot yet show a reader which
of your five districts covers their address. Does the county have a current map of its five
supervisor districts — a PDF, an image, a shapefile, or a description by township or precinct,
whichever is easiest to send? Anything that says where the five district lines run would let us
finish the entry.

**What is deliberately not asked.** Nothing about reuse terms, because district boundaries are
public record. Nothing about the telephone numbers, which is a separate reply already sent.
Nothing is implied about the Legislative Services Agency being at fault — a map dated January
2024 may simply predate a redistricting the county has since adopted, and the question is only
what the lines are today.

**Why a no is still useful.** If the county has no map of its own, saying so closes the
question: it tells us the repair belongs with the state agency rather than with the county, and
it lets the record that tells our readers what is missing say the county was asked.

### Follow-up, drafted 2026-10-06 — the county's current precinct list (send about 8 October)

**SENT 2026-10-06 16:39 UTC AND ANSWERED THE SAME DAY, 17:55 UTC — CLOSED.** Auditor Rohrs
sent two files: the county's precinct list with each precinct's polling place and supervisor
district (an `.xls`, 12 precincts) and the 2025 general-precinct map (an ArcMap PDF, 12
precincts). Read against the five-district map she sent on 1 October, every district line
follows a precinct line, so each district is a whole set of current precincts: **District 1 =
Lincoln, Dysart and Clutier; 2 = Tama; 3 = Traer and Gladbrook; 4 = Garwin and Toledo; 5 =
Montour, Elberon, Chelsea and Indian Settlement.** The spreadsheet agrees on eleven of the
twelve and puts **Lincoln in District 3**, which is the earlier plan: it carries a note dated
April 2013, and her 2024 district map draws Lincoln and Grant townships in District 1.
**MEASURED, NOT READ OFF THE PICTURE**: the district map's five districts are each ONE filled
vector shape in the PDF, and placed on the ground by fitting the drawing's extent to the
county's Census outline (98.9% overlap), the county's Census 2020 blocks sum to 3,407 / 3,446
/ 3,395 / 3,420 / 3,449 against an ideal of 3,427 — every district within 1%, which a stale
or misread plan would not be. That fit is a check and not shipping geometry: the build places
the lines with proper control points before anything ships. Two side findings: this project's
shipped Tama precincts are the 13 Census 2020 voting districts, where the county now runs 12;
and the build for Tama's five-district card is reader-visible and goes in its own pull request.

**As drafted (kept for the record):** A reply on Auditor Rohrs's own
thread, after the thank-you for the map. The text below matches the mailbox draft, including the
sentence the Letters thread added: the thank-you had told her the map resolved everything, so
this letter says plainly that one more thing turned up. Adam sends.

**Why this question.** Her map gives five districts. To tell a reader at a given address which
of them they live in, the lines have to be placed on the ground exactly. Two of the districts
are drawn tightly around the cities of Tama and Toledo and cut through townships, so the
township lines this project already has cannot place them. The precinct list this project
holds is older than her plan and has a precinct (Buckingham/Perry) that her map puts in two
districts, so the county has probably re-drawn precincts since. Her current list, with the
district each precinct votes in, would settle most of the lines; where a district line runs
through a city, a sentence saying which streets it follows would settle the rest.

> **Subject:** Re: Tama County supervisor districts — one more question
>
> Dear Ms Rohrs,
>
> Thank you again for the district map. I said last week that it resolved everything, but
> working through it I found one more thing I need. The map shows the five districts clearly.
>
> To place each address in the right district I need to know where the lines run on the
> ground, and the precinct list I have is older than your current plan. Could you send the
> county's current list of precincts, with the supervisor district each one votes in? A
> list in an e-mail, a spreadsheet or a PDF would all be fine.
>
> If any precinct is split between two districts, a note saying where the line runs through
> it, for example which streets it follows in Tama or Toledo, would be very helpful too.
>
> If this is more work than it is worth, please say so and I will not ask again.
>
> With thanks,
>
> `<YOUR NAME>`
> districtry.com

**What each answer means.** A precinct list → compose the districts from it and check each
against the map's own district shapes before anything ships. A split described in words →
resolve it to whole census blocks, as was done for Jackson County, Illinois. No reply → nothing
changes; the Tama card keeps naming the county and no supervisors.

---

## Ask wi-bellevue-board-form — Village of Bellevue Clerk: is the village board elected at large?

> **ASKED 2026-10-01**, sent 16:10:19 UTC to mseidl@villageofbellevuewi.gov. One message, to
> the Village Clerk. Recorded from `/mnt/project-files/letters/sent-2026-10-01.md`, which is read
> off the sent folder — the only record of what actually went, as against what a thread drafted.
> The matching Bellevue note in `wi/scripts/build_wi_aldermanic_districts.py`'s `EXCLUDED` table
> and the `aldermanic-incomplete-filings` gap blocker were updated the same day. Follow up once
> at about 2026-10-21; thirty days of silence after that follow-up is what would let a gap record
> say the village was asked.
>
> **NO `ask` BLOCK GOES WITH IT, AND THAT IS THE STANDARD RATHER THAN AN OMISSION.** An `ask`
> block can only ever matter on a record that declares `covers`, and
> `aldermanic-incomplete-filings` declares none — Bellevue is a village of about 15,000 people,
> under the 25,000 the local tier counts, so no level is waiting on this answer. The reply is
> wanted for the map, not for the scorecard.
>
> **AND `pending` WOULD EARN NOTHING EVEN THERE, WHICH IS WORTH SAYING SO NOBODY READS IT AS A
> HALF-CREDIT.** `pending` records only that a letter went; it earns nothing however old it gets.
> Credit comes two ways and neither is automatic: a refusal counts straight away, and silence
> counts only after a follow-up and thirty days, and only once a person reads the silence and
> writes the outcome as `unresponsive`. The clock is printed on stdout and no committed byte
> depends on it, so no record ever starts counting on its own.
>
> **NO PRIOR CONTACT, CHECKED RATHER THAN ASSUMED.** Searched Adam's mail on 2026-10-01 for
> Bellevue, `bellevuewi.gov` and Seidl across every folder including trash: the only thread is
> the Brown County one below, and nobody has written to the village. So this is a first letter
> and is written as one.
>
> **WHY IT IS BEING SENT AT ALL, WHEN A COUNTY CLERK HAS ALREADY ANSWERED.** Brown County
> Clerk Patrick Moynihan replied on 2026-10-01: "They appear to be at large. Have you contacted
> Bellevue for any clarifying statements? The Municipal Clerk Michelle Seidl's email is
> mseidl@villageofbellevuewi.gov". **"Appear to be" is a hedge and not the village's own
> statement**, and the thing being decided is whether a card tells a reader their village board
> is elected by the whole village. This project does not print a governing body's form on
> somebody's qualified guess, however well informed — so Bellevue is not recorded as at-large on
> that reply, and the county clerk himself pointed at the person who can say. He also gave the
> address, which is why no address had to be hunted for.
>
> **WHAT IS AT STAKE IS WHICH CARD BELLEVUE'S BOARD RIDES.** Brown County files all eleven of
> Bellevue's wards with no aldermanic district code, which is why the village has no district
> geometry in the shipped map. If the board is elected at large that is the correct and complete
> answer and the trustees belong on the village's own card beside its clerk; if it is elected by
> district, the eleven wards need an assignment and the county's filing is incomplete. One
> sentence from the clerk settles which of those two pieces of work is the right one.

**Subject:** One question about how the Village of Bellevue elects its board

Dear Clerk Seidl,

I maintain districtry.com/wi/, a free, non-commercial website that helps people in Wisconsin
find out which civic districts they live in and who represents them there. It is not funded by
anyone and carries no advertising.

I have one question about the Village of Bellevue.

Are the members of the Village Board elected at large, by the whole village, or does each
trustee represent a district or ward?

I ask because Brown County files all eleven of Bellevue's wards without an aldermanic district
code, which is what the county does for a municipality that has no districts to report. Clerk
Patrick Moynihan at the county kindly suggested I check with you directly, and gave me your
address.

If the board is elected at large, I will list Bellevue's trustees on the village's own page
alongside the village clerk, and the site will say plainly that every seat is elected by the
whole village. If each trustee does represent a ward or a group of wards, I would be grateful
to know which wards go with which seat, and I will draw it that way instead.

Either answer is useful, and a one-line reply is plenty. If the answer is already on a page of
the village's website, a link to it is just as good and I will not trouble you further.

Thank you for your time.

Adam Overberg
districtry.com/wi/

**What is deliberately not asked.** Nothing about reuse terms, because the names of elected
village officers are public record. No request to change the village's website or the county's
filing. And no suggestion that the county got anything wrong — the county clerk's reply is what
prompted this letter and said so.

**Why a no is still useful.** If the village does not answer, the record that tells our readers
what is missing can say Bellevue was asked, which is the difference between a gap this project
has measured and one it has merely noticed.

---

## Ask ky-judge-district-join — Kentucky Administrative Office of the Courts: which district was each judge elected from?

> **ANSWERED 2026-10-01.** Sent 16:24:34 UTC by the operator from his own address; Daniel
> Sturtevant replied at 17:16:25 UTC, 52 minutes later, naming two published surfaces. Both
> were read the same day, and the measurement is in the `ky-judges` record in
> `docs/DATA_LAYER_GUIDEBOOK.md`. In short: **he answered the question.** The Court of
> Justice does print the numbered unit beside each judge, not only a county. The directory
> search he named second (`kcoj.kycourts.net`) is **not a route for this project** — its
> robots.txt is 25 bytes refusing every client, so nothing is fetched from it. The first,
> `kycourts.gov`, answers in full: the Supreme Court's own page names all seven justices
> against their districts, the Court of Appeals' own page all fourteen judges against the
> seven appellate districts, and 119 of the 120 county pages name each trial judge's
> judicial circuit or judicial district number — 818 numbered rows in all.
>
> **The one follow-up, and it is one line.** Jefferson County's page ships its judge list
> commented out in its own HTML, and Jefferson is the only county in circuit 30 and in
> district 30, so Louisville's circuit and district judges are named on no page of that
> source while every other county's are. Follow-up to send, to the same desk, on the same
> thread: *"Jefferson County's page at kycourts.gov/Courts/County-Information/Pages/Jefferson.aspx
> shows no judges where every other county's page lists them — is there another page that
> names Jefferson's circuit and district judges with their circuit or district number?"* The
> appellate half needs nothing: both appellate pages are statewide and already cover
> Jefferson. NOT YET SENT — DRAFTED 2026-10-01; the mailbox thread owns the send and the
> thank-you.
>
> The thirty-day silence clock is retired with the answer. Nothing was re-asked and no
> second copy of the original was sent.
>
> **This ask exists because the geometry arrived without the people.** Kentucky's four court
> maps shipped on 2026-10-01, dissolved offline from statute — no publisher was asked for any
> of them, because KRS 21A.010, 22A.010(2), 23A.020 and 24A.030 write out which counties make
> up each district, circuit and district-court district. So every one of the four cards can
> tell a reader which court covers them and none of them can name a judge, and the missing
> thing is not a map.

**To:** Administrative Office of the Courts, Division of Research & Statistics — Daniel
Sturtevant, Data Officer; (502) 573-2350 x50719
**Subject:** Which district or circuit was each sitting judge elected from?

**Why this desk and not another.** Three offices at the AOC could plausibly hold this: Research
& Statistics, Records Services, and Communications. It goes to the Data Officer because the
question is for a field in a dataset rather than a document or a statement — and because the
answer that would serve best is a table, not prose.

### What the app already has, and the one field it is missing

* **All four court tilings ship and are drawn from statute**, not from a map anyone published:
  7 Supreme Court districts, the 7 Court of Appeals districts that KRS 22A.010(2) defines as
  the same geography, 57 circuits and 59 district-court districts.
* **The Court of Justice already publishes its judges**, by court, which this project can read.
* **What nothing published states is the join** — for a named sitting judge, the number of the
  district or circuit they were elected from. Without it the four cards say, in their own
  words, that the court is known and the judge is not.

**What is deliberately NOT inferred, and the ask says so.** A judge's county of residence is
published and would place most judges in a district by arithmetic. That is a different fact
from the one the ballot settled, and a roster built on it would be this project guessing at an
officeholder, which it does not do. Nor is a circuit's numbered **division** read as a place:
KRS 23A.040 and following make a division a seat elected by the whole circuit, so a division
number is not a district and joining on it would invent boundaries that do not exist.

**What is asked for, in order of usefulness**

| What | Why it would serve |
|---|---|
| A table of sitting judges with the district or circuit number each was elected from | the four cards name a judge the week it arrives, and the join is re-read on a schedule rather than transcribed once |
| A pointer to where that number is already published, if it is | better than a table, because it keeps the AOC out of the loop afterwards |
| "We do not hold that in a form we can share" | a complete answer; it closes the question and the record says the office was asked |

**Why even a no is useful and is said so plainly.** This project tells readers what it does not
know and why. A refusal, or thirty days of silence after one follow-up, lets that record say
the AOC was asked — which is a different and more honest claim than that nobody looked.

**Nothing about reuse terms is asked**, because who holds an elected office is public record,
and nothing is asked of any named judge personally.

## Ask marion-wi-council-districts — two county clerks: how many districts does the City of Marion elect, and which of you files which?

> **WITHDRAW BOTH LETTERS (re-checked 2026-10-06 under the read-the-page-first rule). WAUPACA
> COUNTY ALREADY PUBLISHES THE ANSWER TO BOTH QUESTIONS, in two documents its Clerk's office
> compiles, so the letter would ask a clerk to repeat what her office has printed.** Both hosts
> answer 404 for robots.txt, which permits, and both were read with the county board scraper's own
> token.
>
> 1. **How many districts: three.** The Clerk's Directory of Public Officials
>    (`public4.co.waupaca.wi.us/CountyDirectory`, the page the county board scraper already reads,
>    section `city-officials`) lists the City of Marion's council as Aldermanic District 1, 2 and 3,
>    two alderpersons each: District 1 Wanda Tucker and Neal Westemeier, District 2 David Mattes
>    and one seat printed "Vacant", District 3 Harry Faehling and Joe Larson. It also prints home
>    addresses, which never ship.
> 2. **Which filed number is which: the four filed numbers are three districts.** The Clerk's
>    notice and sample ballot for 7 April 2026 (`April 7, 2026 Combined Insert.pdf`, linked from
>    the county's past-election-results page; text layer, not a scan) lists the City of Marion,
>    wards 1 to 4, with "Alderperson, District 1 & 4", "Alderperson, District 2" and
>    "Alderperson, District 3", and names ward 4 as the part in Shawano County. The state's ward file
>    (read the same day) codes ward 1 `21`, ward 2 `22`, ward 3 `23` (Waupaca) and ward 4 `01`
>    (Shawano). So Shawano's `01` and Waupaca's `21` are one district, District 1, and the map's
>    fourth district does not exist. **One step is inferred, not printed:** that ward 2 is District 2
>    and ward 3 is District 3. Nothing in either document says otherwise, and it is the only
>    reading in which the directory's three districts and the ballot's labels agree.
>
> Marion's own site still refuses us (`www.cityofmarionwi.gov/robots.txt`, re-read 2026-10-06:
> `User-agent: *` / `Disallow: /`), so nothing was read there. The fix is now map work rather than
> a letter: merge `01` into District 1, relabel `21`-`23` as Districts 1-3, and consider the
> directory as a roster source for the six seats. That changes what readers see, so it waits for
> Adam's word. The text below is kept as the record of what was going to be asked.
>
> **DONE 2026-10-07 on Adam's word ("fix marion").** The map draws three Marion districts and the
> cards name the five members the directory lists, with District 2's second seat shown as vacant.
> No letter goes to either county about this.

> **THE SHAWANO LETTER WAS SENT ON 2026-10-01 AND HAS NO REPLY, SO IT GETS A SHORT CLOSING NOTE**
> (decided 2026-10-06). It asks a question the neighbouring county's own publications now answer,
> so a clerk who has not got to it yet should not spend time on it. The note goes as a reply in the
> same thread, so it reads as part of that conversation, and it asks nothing. No follow-up clock
> applies to this ask any more.
>
> **Subject:** Re: One question about the City of Marion's aldermanic districts
>
> > Dear Clerk Rigsby,
> >
> > A quick note so your office doesn't spend time on my question of 1 October about the City of
> > Marion's aldermanic districts: I have found the answer. Waupaca County's sample ballot for the
> > April 2026 election lists Marion's wards 1 and 4 together as Aldermanic District 1, so the
> > ward you file as district 1 is part of that same district rather than a fourth one.
> >
> > No reply is needed. Thank you, and sorry for the extra e-mail.
> >
> > Adam Overberg
> > districtry.com/wi/

> **ONE SENT AND BOUNCED, ONE NOT SENT.** Written 2026-10-01. Two letters, one to each of the two
> county clerks who file the City of Marion's wards. The Waupaca letter went that day and was
> refused as a permanent failure by the county's own mail server, so it reached nobody and
> **Waupaca is not awaiting a reply and no follow-up clock has started** — the bounce note below
> gives the measurement and the two addresses the county itself publishes for the same office. The
> Shawano letter has not been sent. **NO PRIOR-CONTACT SEARCH HAS BEEN RUN FOR THESE TWO ADDRESSES**,
> and that is the Letters thread's step rather than this one's: this thread writes the text, the
> Letters thread searches Adam's sent folder and inbox, turns anything it finds into a follow-up
> rather than a first letter, and creates the Gmail drafts. Nothing here is sent by anybody but
> Adam.
>
> **WHY THE CITY ITSELF IS NOT THE RECIPIENT, THOUGH IT IS THE AUTHORITY.** Marion's own site
> asks automated clients to stay out — `cityofmarionwi.gov`'s robots.txt is `Disallow: /`, which
> this project obeys without exception, so nothing has been read from it. That refusal governs
> what we fetch and not who we may write to, so a letter to the city would be entirely proper;
> what is missing is an address. The Wisconsin Elections Commission's clerk directory names
> Clerk Mary S Rogers and Deputy Clerk Jodilyn Zillmer with the telephone 715-754-2124 and no
> e-mail address, and municipal clerks' e-mail addresses are deliberately not published
> statewide in Wisconsin. So a city letter is a telephone call or a posted letter, which is
> Adam's to make if he would rather go straight to the source; the two county clerks both
> publish an address and both hold part of the answer.
>
> **WHAT IS ACTUALLY UNKNOWN, AND WHAT IS NOT.** The shipped map draws four aldermanic districts
> for Marion, keyed `01`, `21`, `22` and `23`. Measured against the Census Bureau's own county
> boundaries on 2026-10-01, `01` lies in Shawano County and `21`-`23` lie in Waupaca County,
> and `01` sits north of the other three and overlaps none of them — Marion straddles the county
> line, and the two counties file its wards under two different numbering schemes. So the city's
> four drawn districts may be three districts plus a second county's copy of one of them, which
> would mean the map draws a district that does not exist. **The council size is deliberately
> not inferred from the key count, because the key count is the thing in question.**
>
> **AND THIS IS THE ONE OF FOUR CITIES STILL OPEN.** Manawa, Waupaca and Weyauwega were in the
> same position — the state's filing keys their districts somewhere other than 1 upward — and all
> three were settled on 2026-10-01 by reading each city's own council page, which numbers its
> districts from one. Those three are relabelled accordingly. Marion could not be read, which is
> why it takes a letter.

> **THE WAUPACA LETTER BOUNCED AND THE ADDRESS WAS NOT GUESSED — THE COUNTY PUBLISHES IT IN THREE
> PLACES.** Sent 2026-10-01, it was refused at 18:09 as a permanent failure by the county's own
> mail server. Measured the same day, reading each page with the client that crawls and after
> reading each host's robots.txt (`www.co.waupaca.wi.us` and `www.waupacacounty-wi.gov` both answer
> 404 for robots.txt, which permits):
>
> | the county's own page | what it publishes for the clerk |
> |---|---|
> | County Clerk department page (both domains, byte-identical) | `Kristy.Opperman@co.waupaca.wi.us`, telephone (715) 258-6200, fax (715) 258-6212 |
> | County staff directory | `kristy.opperman@co.waupaca.wi.us` — character for character the address that bounced |
> | Directory of Public Officials, updated 5 August 2026, compiled by the Clerk's own office | County Clerk Kristy K. Opperman, 811 Harding St., Waupaca 54981, telephone (715) 258-6200 — **no e-mail address at all** |
>
> **AND THE REJECTION SAYS WHICH KIND OF REFUSAL IT IS, WHICH CHANGES WHAT A SECOND ADDRESS CAN
> FIX.** The server answered `550 permanent failure ... blocked`, not *unknown user*. So the
> clerk's mailbox probably exists and the county's mail server is refusing the SENDER rather than
> the recipient — and if that is what happened, every address at the county will refuse the same
> sender, so trying a third one is not a measurement, it is the same failure again. **If the
> redraft to the Chief Deputy also comes back blocked, do not look for another address**: the
> office's own telephone, (715) 258-6200, is the next step, and that is a person's to make rather
> than this project's. The first reading written here said only that a published mailbox was
> refusing mail, which was true of the address and said nothing about the cause.
>
> So a published mailbox is refusing mail, which is the same shape as the Grundy County bounce
> the same day, and **no replacement is invented here.** Two addresses the county publishes on the
> clerk's own department page are the alternatives, in this order, and both are the county's own
> words rather than a pattern guessed from a name:
>
> 1. **Chief Deputy County Clerk Ellen Radies — `Ellen.Radies@co.waupaca.wi.us`**, same office, same
>    telephone. A deputy clerk answers for the office, so this asks the same office the same question.
> 2. **Deputy County Clerk Nicole Houdek — `Nicole.Houdek@co.waupaca.wi.us`**, likewise.
>
> The redraft went to Ellen Radies on 2026-10-01. **If that also comes back blocked, stop**: the
> office's own telephone and postal address above are what is left, and both are a person's job
> rather than this project's. The second deputy is listed only in case the first address fails for
> a reason specific to it, and a sender-level block is not that reason. **Nothing has been sent to either
> address and Waupaca is not awaiting a reply**, so no follow-up clock has started. The letter text
> below is unchanged and still correct: only the recipient line moves. The Shawano County letter in
> this same ask is unaffected.
>
> One thing deliberately not concluded: the Clerk's own Directory links the elections page on
> `www.waupacacounty-wi.gov`, a newer domain for the same site, which could suggest the county's
> mail has moved too. Both domains serve the identical page naming `@co.waupaca.wi.us` addresses,
> and nothing published here names a mailbox on the new domain, so **no address on it is guessed.**

### Waupaca County Clerk's office — address line to be redrawn, see the bounce note above

**Subject:** Two questions about the City of Marion's aldermanic districts

Dear Clerk Opperman,

I maintain districtry.com/wi/, a free, non-commercial website that helps people in Wisconsin
find out which civic districts they live in and who represents them there. It is not funded by
anyone and carries no advertising.

I have two questions about the City of Marion, which as I understand it lies partly in Waupaca
County and partly in Shawano County.

First, how many aldermanic districts does the Common Council have?

Second, the state's current ward file lists Marion's wards under district numbers 21, 22 and 23
in your county, and under district number 1 in Shawano County. Are those four numbers four
different districts, or are they the two counties' own ways of labelling the same council's
districts?

I ask because our map draws one district for each distinct number it finds, so if Marion's
council has three districts and the two counties label them differently, our map is currently
drawing a fourth district that does not exist, and telling anyone who clicks there that they
live in it.

A one-line answer to each is plenty, and if the City of Marion is the right office to ask
instead, I would be glad to be pointed there.

Thank you for your time.

Adam Overberg
districtry.com/wi/

### Shawano County Clerk — `raymond.rigsby@shawanocountywi.gov`

**Subject:** One question about the City of Marion's aldermanic districts

Dear Clerk Rigsby,

I maintain districtry.com/wi/, a free, non-commercial website that helps people in Wisconsin
find out which civic districts they live in and who represents them there. It is not funded by
anyone and carries no advertising.

I have one question about the part of the City of Marion that lies in Shawano County.

The state's current ward file lists Marion's ward or wards in your county under aldermanic
district number 1, while Waupaca County lists the rest of the city under district numbers 21, 22
and 23. Is the district you file as number 1 a district of its own, or is it the same council
district that Waupaca County files under one of its own numbers?

I ask because our map draws one district for each distinct number it finds, so if those are
labels for the same districts rather than four separate ones, our map is drawing a district that
does not exist and telling anyone who clicks there that they live in it.

A one-line answer is plenty, and if the City of Marion or Waupaca County is the better office to
ask, I would be glad to be pointed there.

Thank you for your time.

Adam Overberg
districtry.com/wi/

### What each answer means

- **A council size and a mapping.** If either clerk says how many districts the council has and
  which filed numbers correspond, the map draws that many districts with the city's own numbers,
  the same way Manawa, Waupaca and Weyauwega now do.
- **"Four separate districts."** Then the map is already right about the count, and only the
  numbering question is left — which `ALDER_DISTRICT_LABELS` in `wi/index.html` can carry as soon
  as somebody states what the city calls them.
- **A refusal, or silence.** Either lets the gap record say the two counties were asked, which is
  the difference between a gap this project has measured and one it has merely noticed. Neither
  changes the shipped map: Marion stays exactly as filed.

**What is deliberately not asked.** Nothing about reuse terms, because ward filings and the
names of elected officers are public record. No request to change either county's filing or the
city's website. And nothing about Marion's robots.txt, which is the city's own choice about
automated clients and is being respected rather than negotiated.
---

---

## Ask ok-csa-precinct-terms — OU Center for Spatial Analysis: the terms on the maps the State Election Board pays it to make

**The board answered, and the answer was a redirection rather than a refusal.** Ask sent to
`info@elections.ok.gov` on 2026-09-30 asked whether districtry may download, simplify and publish
the statewide precinct boundaries from the data warehouse the board's own maps page links. The
board replied that the warehouse is downloadable, and that questions about permission and about
changes belong to the **OU Center for Spatial Analysis**, its contracted mapping provider. That is
why the board's page sends readers there in the first place.

**That settles the provenance question in the project's favour rather than against it.** The
government-publishers-first rule asks who is accountable for a file, not which domain serves it.
The board states the contract on its own page, and now states in writing that permission is the
centre's to give. So the centre is the board's **agent for mapping**, not an independent academic
publisher, and asking it is asking the board's own mapping office. Oklahoma's precinct layer is not
blocked on a policy question; it is blocked on one address.

**The same conclusion reaches the county commissioner districts, and corrects a reading in
Oklahoma's launch plan.** The plan recorded two copies of the 231 commissioner districts: the
Oklahoma Department of Transportation's, and a second, more recently edited copy whose
organisation endpoint returns a null name to an anonymous caller. The plan called that second copy
anonymous, "an organisation that will not say who it is". Measured 2026-10-01, the **item's owner is
`thom0780_uok`**, an enterprise-provider account in the University of Oklahoma's own ArcGIS
organisation — the same channel as the precincts. So it is the centre's copy, not an unattributed
one, and the ruling's outcome is unchanged (ship the transport department's copy, credit the state,
name the centre as where the file came from) while the reason for it is different. **An
organisation that returns no name to an unauthenticated caller is not an organisation with no
name**, which is the Knox shape at the level of a metadata field.

### Recipient — VERIFIED 2026-10-01, and the blocker was an address that had moved

**The letter goes to Chengbin Deng, PhD, the centre's Director (`cdeng@ou.edu`), copying Todd
Fagin, PhD, its Executive Associate Director (`tfagin@ou.edu`)**, both read off the centre's own
Faculty & Staff page at `www.ou.edu/ags/csa/csa-team/csa-faculty-staff`.

**THIS ENTRY SAID THE ADDRESS HAD TO BE READ IN A BROWSER, AND THAT WAS WRONG ABOUT THE CENTRE.**
It recorded that `csa.ou.edu` does not resolve from this project's network and concluded that the
centre's contact page was reachable only in a browser. `csa.ou.edu` still does not resolve, and
that is because **the centre's site is not there any more**: it is at `www.ou.edu/ags/csa`, which
answers normally from here under a robots policy that permits every path read. So a host that had
MOVED was recorded as a network limit on this agent, which is the shape this project keeps finding
— a measurement that was accurate about the thing measured and wrong about the thing it was taken
to describe. **When a host does not resolve, look for the site before recording a blocker.**

The centre publishes no office mailbox that can be relied on — its Contact Us page offers only a
web form in a frame, and the one general address it prints (`contact.us@csa.ou.edu`, in the footer
byline) sits on a domain with no address record — so a policy question about the centre's own data
goes to the Director with the Executive Associate Director copied, rather than to an address that
might quietly fail. The centre's Senior GIS Analyst is named on the warehouse page for help
navigating the site, which is a different question from what may be done with the files, and is
deliberately not the recipient. What else is known:

| known | value |
|---|---|
| the centre's own site | `www.ou.edu/ags/csa` (the old `csa.ou.edu` no longer resolves) |
| its open-data portal | `csagis-uok.opendata.arcgis.com` |
| the precinct layer | `State_Wide_2020_Precincts`, 1,984 features |
| the commissioner copy | `services.arcgis.com/3xOwF6p0r7IHIjfn`, owner `thom0780_uok` |
| the board's statement | its district-and-precinct-maps page, which names the contract and links the portal |

### Draft

> Subject: Permission question about the Oklahoma precinct maps in your data warehouse
>
> Dear Dr Deng,
>
> I run districtry.com, a free public website that answers one question: you click a point on a
> map and it tells you every district you are in and who represents you there. It covers Illinois,
> Wisconsin, Iowa, Michigan, Minnesota, Kentucky, New York City and San Francisco today, and I am
> preparing to add Oklahoma.
>
> I wrote to the State Election Board asking whether I may use the statewide precinct boundaries
> from your data warehouse. They told me the files are downloadable and that questions about
> permission and about changes belong to you, as the board's contracted mapping provider.
>
> So, the question. May I download the statewide precinct boundaries, simplify them for use on a
> web map, and publish them on a free public site? I would credit the Oklahoma State Election
> Board as the authority and name the OU Center for Spatial Analysis as the mapping office, unless
> you would rather it were worded differently — and I would be glad to word it however you prefer.
>
> If there are conditions, I will follow them. If the answer is no, that is a complete answer and I
> will respect it: the site will say that Oklahoma's precincts exist and that we are not able to
> draw them, rather than drawing them from somewhere else.
>
> Two smaller things, if they are easy.
>
> First, one of your organisation's files is a copy of the 231 county commissioner districts. I am
> planning to use the Oklahoma Department of Transportation's copy instead, because it comes from a
> state agency, and to say in the credit that the file originated with your centre. If that is
> wrong — if yours is the current one and the transport department's is stale — I would rather know
> now.
>
> Second, the two copies disagree about one district in Beaver County, by just over one per cent of
> its area. If you happen to know which of the two is right, that would save me asking the county.
>
> One thing about how we work, which may matter to you: we never invent an officeholder's name.
> Where we cannot verify who holds a seat from the body's own publication, the site says so and
> links to that body rather than guessing.
>
> Thank you for your time.
>
> Adam Overberg
> districtry.com

### What each answer means

| answer | what it settles |
|---|---|
| yes, with or without conditions | The precinct layer ships, credited to the board with the centre named as its mapping office. Conditions are followed as written. |
| yes, and "ours is the current commissioner file" | The commissioner layer's source changes, and the plan's currency reading is wrong in the other direction. Re-measure before switching: the transport department is still a state agency, so this would be a documented exception rather than a default. |
| an answer on Beaver County | Closes the one measured disagreement between the two copies without asking the county. The permanent test point inside that district stays either way. |
| no | A clean, citable no. The precinct layer does not ship, Oklahoma records the gap, and the question is closed rather than re-probed. |
| no reply after the follow-up cadence | `UNRESPONSIVE`, and the precinct gap records that the board redirected us to the centre and the centre did not answer — which is a different claim from "nobody publishes Oklahoma's precincts". |

### The roster question is NOT in this letter, deliberately

The 2026-09-30 ask to the board carried a second question: whether a 2026 edition of the biennial
County Officer Roster is expected after the November election. **The board did not answer it, and it
does not belong here** — the roster is the board's own publication and the centre makes maps, so
putting it to the centre asks the wrong office a question it has no reason to know. It is also the
one open question this project can answer without anybody's help: Oklahoma's launch plan already
calls for a weekly check for the next edition's filename, which turns the answer into a measurement
instead of a favour. **So it is dropped rather than re-asked.** If the tripwire is still finding
nothing well after the election, that is the moment to put it back to the board — by then it is a
real question about a missing document rather than a request for a schedule.
---

## Ask ia-linn-supervisor-districts — Linn County Auditor: which precincts are in each supervisor district?

> **NOT YET ASKED — DRAFTED 2026-10-01**, to Linn County Auditor Todd Taylor at the address
> `ia/data/app/ia-county-auditors.json` carries for the county. One message. On send, change
> `NOT YET ASKED — DRAFTED` to `ASKED <date>` in the Linn blocker in
> `docs/DATA_LAYER_GUIDEBOOK.md` AND in `ia/WATCH.md` — Iowa keeps the ledger in both — and add
> an `ask` block to that record reading `pending`.
>
> **THIS ONE IS ASKED BECAUSE A MEASUREMENT CLOSED EVERY OTHER ROUTE, and the measurement is
> what makes it a short letter.** The county's own certified 2024 Primary canvass reports its
> County Board of Supervisors District 3 contest in 41 named precincts, all three party ballots
> agreeing. Placed against the statewide supervisor-district map this project draws, 36 of those
> 41 fall inside that map's district 3 and five fall wholly inside its district 2 — Cedar Rapids
> 01, 04, 07 and 27, and Hiawatha 03. The map's district 3 is a strict subset of the county's:
> 36 of 41, with nothing the other way. So the two are different lines rather than the same
> lines under different numbers, and no renumbering on this side can reconcile them.

### What the app already has, and what it is missing

* **Linn's three supervisors are in hand** and are not in doubt. This asks nothing about them.
* **Every other elected county office ships for Linn.**
* **The supervisor card draws the district and names nobody**, because naming a supervisor
  against a district whose lines this project cannot confirm would put a name on the wrong
  ground.

**What the ask says.** We publish a free map of civic districts, and for Linn County we draw
supervisor districts from the Legislative Services Agency's statewide layer, dated January 2024.
Your county's own certified 2024 Primary canvass reports the District 3 board contest in 41
precincts, and five of those — Cedar Rapids 01, Cedar Rapids 04, Cedar Rapids 07, Cedar Rapids
27 and Hiawatha 03 — sit inside what that statewide layer calls District 2. We would rather ask
than assume which is current. Does the county have its current supervisor-district plan in a
form you can send — a map, a shapefile, or simply a list of which precincts make up each of the
three districts, whichever is easiest? A precinct list would be enough on its own.

**What is deliberately not asked.** Nothing about reuse terms, because district boundaries are
public record. Nothing about the supervisors themselves. Nothing is implied about the
Legislative Services Agency being at fault — a map dated January 2024 may simply predate a
change the county has since adopted, and the question is only what the lines are today.

**Why a no is still useful.** If the county publishes no plan of its own, saying so closes the
question: it tells us the repair belongs with the state agency rather than with the county, and
it lets the record that tells our readers what is missing say the county was asked.

---

## Ask ia-supervisor-district-composition — nineteen Iowa county auditors: which precincts or townships make up each numbered supervisor district?

> **NOT YET ASKED — DRAFTED 2026-10-01**, to the nineteen county auditors in the table below,
> each at the address `ia/data/app/ia-county-auditors.json` carries for that county. **ONE
> MESSAGE PER AUDITOR** — nineteen letters, not one letter to nineteen people, because the
> question names a particular county's own districts and an answer from one office says nothing
> about another. On send, change `NOT YET ASKED — DRAFTED` to `ASKED <date>` in the
> `ia-supervisor-district-seats` record in `docs/DATA_LAYER_GUIDEBOOK.md` AND in `ia/WATCH.md`
> — Iowa keeps the ledger in both — and add an `ask` block reading `pending`.
>
> **FIFTEEN ARE FIRST LETTERS AND FOUR ARE REPLIES ON A THREAD THAT ALREADY EXISTS, AND THE
> SPLIT IS MEASURED FROM THE SENT FOLDER RATHER THAN GUESSED.** Iowa county auditors have only
> ever been written to on 2026-10-01 — there was no earlier batch — and **SIXTEEN** counties
> hold this afternoon's supervisor letter: Black Hawk, Calhoun, Cass, Dickinson, Guthrie, Ida,
> Jones, Lee, Montgomery, Osceola, Palo Alto, Pottawattamie, Sioux, Tama, Washington and
> Wright. **A COUNT OF WHO HAS BEEN WRITTEN TO IS MEANINGLESS WITHOUT SAYING ABOUT WHAT**, and
> this one was first written as seventeen by counting every letter to an Iowa county auditor
> that day: Worth's, sent at 14:42 UTC, was about its city officials page — a different batch on
> a different subject — and Dickinson, which looked like one county with two letters, genuinely
> received the supervisor letter at two addresses. Worth is not among the nineteen either way.
> **CORRECTED 2026-10-06: Ida and Washington are WITHDRAWN before sending** (see their rows
> below — each county already publishes the answer), so this tranche is SEVENTEEN letters, and two
> of them are replies. As first drafted: exactly four of the sixteen were in this tranche — **Ida, Osceola,
> Sioux and Washington** — and for those four the question goes as a **REPLY ON THIS
> AFTERNOON'S THREAD**, opening by acknowledging that letter, never as a separate message. The
> other fifteen are first contacts. **Dickinson is deliberately not on this list**: it has had
> three letters today and it has already refused the pairing in writing, which ends that ask.
> The mailbox thread owns the sent folder and this split; if it reads the folder differently on
> the day, the folder wins.
>
> **LINN IS NOT IN THIS TRANCHE.** It asks the same question and has its own letter, because
> its letter can cite five named precincts that measurably disagree, which no other county's can
> (`Ask ia-linn-supervisor-districts` above). Sending both would ask Linn the same thing twice.

### Why this is asked, in one paragraph

The statewide supervisor-district map this project draws from numbers each county's districts in
its own order, and **that order is not always the county's own**. Measured on seven counties:
Howard's two numberings agree, while Palo Alto, Pocahontas, Monona and Lyon are **one plan under
two numberings** — identical lines, different numbers on them — and Butler and Linn are **two
different plans**. So a county that tells us "District 1 is Smith" and a map whose district 1 is
somewhere else combine into a card naming the wrong person over the wrong ground. There is no way
to tell the two cases apart from the map alone, and every route that does not involve asking the
county has now been measured closed for these nineteen: their board pages do not state it, the
certified election returns published for Iowa break out a board contest by precinct in one county
only, and the state agency's own published plan reports carry the agency's numbering, which is the
numbering being checked.

### What the app already has, and what it is missing

* **The districts are drawn and ship.** A reader clicking in any of these counties sees which
  numbered district covers them.
* **The supervisors are in hand** for most of these counties, from the county officers roster.
* **The two are not joined.** The card lists the county's supervisors without placing any of
  them in a district, and says so, rather than placing one on a number this project cannot
  confirm.

### The nineteen desks

| County | Auditor | Districts drawn | Note |
| --- | --- | --- | --- |
| Adams | Betsy Stormer | 5 | |
| Butler | Leslie Groen | 3 | **Measured: two different plans.** The letter should ask which of the county's two published surfaces is current. |
| Cerro Gordo | Adam Wedmore | 3 | |
| Chickasaw | Sheila Shekleton | 5 | **ANSWERED 2026-10-06 by the elections specialist: the supervisors and their districts are listed on the county website.** Read on 2026-10-07: the board page does print a district beside each supervisor, but nothing there or on the county's election pages says which ground each district covers — the two maps the election site carries draw precincts only. So the county's numbering still cannot be checked against ours and the cards stay unkeyed. The question to send back is the one Winnebago answered: which precincts make up each district. The operator asked for it on 2026-10-07 and a follow-up was drafted below the table, then **WITHDRAWN UNSENT the same evening**: the county's own GIS map (its supervisor-district layer, supplied by the operator as a screenshot) numbers the five districts exactly as this instance does, so **the numbering is CHECKED and Chickasaw's supervisors SHIPPED keyed 2026-10-07**. |
| Franklin | Katy Flint | 3 | |
| Grundy | Alan Tscherter | 5 | **ANSWERED 2026-10-07, USABLE and SHIPPED the same day.** The auditor replied "Here is a map of the precincts and supervisor districts" with the county's own precinct map (PDF, dated 2026-02-03), which the operator put in Drive. It draws each of the county's seven precincts wholly inside one district, and those precincts sit in the same-numbered districts of this instance's layer, so the numbering is CHECKED (identity) and Grundy's supervisors are keyed. Nothing further is owed; a thank-you is optional. |
| Humboldt | Trish Erickson | 5 | Also the county whose board page prints a telephone number per supervisor; this letter asks nothing about those. |
| Ida | Kristy Gilbert | 3 | **WITHDRAWN 2026-10-06, NEVER SENT — THE COUNTY ALREADY PUBLISHES THE ANSWER.** Re-checked before send: the county's own site carries Ordinance 31 (`idacounty.iowa.gov/wp-content/uploads/2021/12/Ordinance-31-Est-Co-Supervisor-Precincts-2021.pdf`, effective 15 January 2022, drawn to the 2020 census), whose text names the townships in each district. Ten townships lie wholly inside one district (Galva and Griggs in 1; Battle, Blaine, Garfield, Hayes, Logan, Maple and Silver Creek in 2; Corwin in 3), and every one of their TIGERweb interior points lands in the same-numbered district of the statewide layer, so the two numberings agree in all three districts. It was found through the site's own search feed, which the September sweep did not read; a letter asking for it would have asked the county for a document it publishes. |
| Madison | Michele Brant | 3 | |
| Mitchell | Rachel Foster | 5 | |
| Osceola | Rochelle Van Tilburg | 5 | **Goes as a reply on this afternoon's thread** — answered Ask 30 on 2026-10-01 with the five pairings. **Re-checked 2026-10-06 and it stands**: the county's site still answers its robots.txt with HTTP 202, the captcha shape, so nothing on it can be read and the letter is the only route. **ANSWERED 2026-10-06 (20:37 UTC) — AND SHE CORRECTED HER 1 OCTOBER LIST.** Jerry Helmers is District 4 and Jeff Loring District 5; the first list had them swapped. The held pairing in `build_ia_supervisor_roster.py` was corrected on 2026-10-07; it had never reached a reader, because Osceola's numbering is unchecked and its board ships unkeyed. She also linked the county's district maps (a Word document on osceolacountyia.gov), which this project cannot fetch: re-checked 2026-10-07 14:05 UTC, that host answers robots.txt with HTTP 202 and a SiteGround captcha. The operator saved the file and shared it on 2026-10-07; its map labels Districts 1-5 the same way our layer numbers them, so Osceola joined `NUMBERING_CHECKED` that day and its five cards name the supervisors from the corrected pairing. |
| Polk | Jamie Fitzgerald | 5 | The address the roster carries is the elections desk rather than a person; the letter goes there as published. **ANSWERED 2026-10-06 (sent 16:48, reply 16:57) — THE COUNTY PUBLISHES THE ANSWER AND OUR NUMBERING MATCHES IT.** The elections office pointed to the county's own web map. It draws from the county's own ArcGIS Server (`gis4.polkcountyiowa.gov/server/rest/services/Elections/Board_of_Supervisors/FeatureServer/0`, owner `portadmin` on the county's portal, copyright "Polk County, Iowa"), whose five district polygons each carry the supervisor's name, term and contact. Compared on a 160x160 grid over the county, 22,799 of the 22,860 sampled points inside either map get the SAME district number from the county's polygons and ours (99.7%); the 61 that differ are slivers along shared edges, and no district number is swapped. Fetch note: the county's Akamai edge answers our token with 403 on robots.txt and every page of both `maps.` and `gis4.`, and serves Chrome with client hints — the same measurement `ia_county_minutes_chair_scraper.py` records for `www.` — so both were read with that client; `maps.` then has no robots.txt (it serves its HTML at that path) and `gis4.` answers 404, allow all. So Polk can be keyed to its own district numbers in a later change. |
| Sac | Renee Roland | 3 | |
| Sioux | Joe Van Tol | 5 | **Goes as a reply on this afternoon's thread** — answered Ask 30 on 2026-10-01. The county's own site fronts every page with a managed challenge, so a letter is the only route there will ever be. **Re-checked 2026-10-06 and it stands**: robots.txt still answers HTTP 202. **ANSWERED 2026-10-06 — THE COUNTY'S GIS TECHNICIAN (Joey Reid) SENT THE DISTRICT MAP.** "Sioux County Supervisor Districts", county GIS, as of 6 April 2022, labelling each district and drawing its townships. All 17 of this instance's Sioux precincts lie inside the same-numbered district of our layer, so the numbering is the same and Sioux was added to `NUMBERING_CHECKED` on 2026-10-07; its five district cards now name the supervisors from the 1 October pairing. |
| Taylor | Judy Henry | 3 | |
| Washington | Tamera Stewart | 5 | **WITHDRAWN 2026-10-06, NEVER SENT — THE AUDITOR HAD ALREADY SENT THE ANSWER.** Her 2026-10-01 reply linked the county's own district map (`washingtoncounty.iowa.gov/DocumentCenter/View/2095/Map-of-Supervisor-Districts---Final`, county GIS, 2022, drawn to the 2020 census). It is a vector PDF with the townships drawn and labelled inside each district. Ten townships lie wholly inside one district (Brighton, Clay, Dutch Creek, Lime Creek and Seventy-Six in 1; English River in 2; Crawford, Highland, Iowa and Oregon in 3), and every interior point lands in the same-numbered district of the statewide layer. Districts 4 and 5 hold no whole township, so they are settled by the split ones: Franklin township's interior point lands in the layer's 4 and the county's map puts Franklin only in 1 and 4, while Jackson's lands in the layer's 5 and the map puts Jackson only in 2 and 5, so the layer's 4 and 5 cannot be swapped. The two numberings agree in all five districts. |
| Webster | Krystal Lloyd | 5 | |
| Winnebago | Karla Weiss | 3 | **ANSWERED 2026-10-06 (18:09 UTC) by Lori Jacobs of the Auditor's office**, listing the precincts in each of the three districts in the body of her e-mail. All ten of this instance's Winnebago precincts lie inside the same-numbered district of our layer (each at least 99.7% of its area), so Winnebago was added to `NUMBERING_CHECKED` on 2026-10-07 and its three cards name the supervisors from the county's own board page. An auto-reply also came on 2026-10-06 (auditor out); it needed nothing. |
| Winneshiek | Benjamin D. Steines | 5 | |

**What the ask says.** We publish a free map of civic districts, and for your county we draw the
board of supervisors districts from the Legislative Services Agency's statewide layer, dated
January 2024. That layer numbers each county's districts in its own order, and on several Iowa
counties we have found its numbering runs differently from the county's own — the same lines,
with different numbers on them — so we are reluctant to tell a reader which supervisor
represents them until we can check it. Could you tell us which precincts, or which townships,
make up each of your numbered supervisor districts? A list is all we need; a map or a shapefile
would do just as well if one is easier to send.

**For the four who already hold this afternoon's letter**, this is not a new message at all: it
is a reply on that same thread, opening by thanking them for answering it and saying plainly
that this is a second and different question — their names and districts are not in doubt, and
what is missing is on our side, because we cannot yet tell whether the district they call 1 is
the one our map calls 1.

**For Butler**, the letter adds that the county appears to publish two different supervisor
district plans and asks which is in force today, rather than asking for a precinct list alone.

**What is deliberately not asked.** Nothing about reuse terms, because district boundaries are
public record. Nothing about the supervisors personally — no home address, no personal telephone
number. Nothing is implied about the Legislative Services Agency being at fault: a numbering
difference is an ordinary consequence of two offices numbering the same plan independently, and
the question is only which order the county itself uses.

**Why a no is still useful.** If the county cannot say, saying so closes the question and lets
the record that tells our readers what is missing say the county was asked — which is a
different and more honest claim than that nobody looked.

### Chickasaw follow-up, drafted 2026-10-07 — which precincts make up each district

**WITHDRAWN 2026-10-07, NEVER SENT.** The county's own GIS map settled it the same evening: the operator opened its supervisor-district layer in a browser (the host answers this project's client with a managed challenge, so nothing there was fetched) and supplied a screenshot. Its Districts 1 to 5 cover the same ground as this instance's 1 to 5, with every rural precinct in the same-numbered district, so Chickasaw's supervisors were keyed without the county having to answer again. The draft below is kept as the record of what was written; the Gmail draft is to be deleted, not sent.

**A reply on the existing thread**, "Chickasaw County supervisor districts — which precincts
make up each one?": Adam's letter to Auditor Shekleton of 2026-10-06 16:49 UTC, and the reply
from Gina Fangman, the county's elections specialist, at 18:58 UTC the same day, which pointed
to the county website. The reply goes to Ms Fangman, copying the auditor's address as her reply
did. Adam sends.

**Why a second letter.** The board page she pointed to does print a district number beside each
supervisor, and that part of the question is answered. What it cannot tell us is whether the
county's District 1 is the same ground as the district our map calls 1, because nothing on the
county's site says which precincts or townships each district covers — the two maps on its
election pages draw precincts only. The first letter asked exactly that, so this one says why
the website did not settle it and makes the answer as small as possible: our map already puts
each precinct wholly inside one district, so she only has to say whether the list is right.

**What our map shows**, measured 2026-10-07 from this instance's precinct and supervisor-district
files (every precinct at least 99.9% inside one district): District 1 Chickasaw North; District 2
Bradford; District 3 Dayton Richland and New Hampton Wards 2 and 3; District 4 New Hampton Wards
1 and 4 and New Hampton Rural; District 5 Lawler-Fredericksburg. The precinct names are the
Census 2020 voting districts, so the county may have renamed or redrawn some since; the letter
says so.

> **Subject:** Re: Chickasaw County supervisor districts — which precincts make up each one?
>
> Dear Ms Fangman,
>
> Thank you for pointing me to the county website. I found the board page, and it does list
> each supervisor with their district number.
>
> What I still cannot find is which part of the county each district covers. Our map draws the
> five districts from the state's January 2024 layer, and in several other Iowa counties that
> layer numbers the districts in a different order from the county's own, so I want to be sure
> your District 1 is the same area as ours before I put a supervisor's name on it.
>
> On our map the precincts fall like this:
>
> - District 1: Chickasaw North
> - District 2: Bradford
> - District 3: Dayton Richland, New Hampton Ward 2, New Hampton Ward 3
> - District 4: New Hampton Ward 1, New Hampton Ward 4, New Hampton Rural
> - District 5: Lawler-Fredericksburg
>
> Could you tell me whether that matches the county's districts? A simple yes is enough. If it
> does not match, or the precincts have changed since 2020, a list of the precincts in each
> district would let me correct it.
>
> Thank you for your help.
>
> Best regards,
>
> Adam Overberg
> adam@overberg.co
> http://districtry.com

**What each answer means.** A yes → Chickasaw joins the counties whose numbering is checked, and
its five district cards name their supervisors, in a pull request Adam approves. A list that
differs → the numbering is mapped from the county's list, checked against the precinct file, and
the same pull request ships. No reply → nothing changes: the County card keeps listing the five
supervisors without placing them, which is true whichever way the numbering runs. A follow-up
would fall due with the rest of this ask, around 22 October.

## Ask il-cumberland-500e — Cumberland County Clerk: does the Western–Central line run along 500E?

> **NOT YET ASKED — DRAFTED 2026-10-06**, to Clerk Bev Howard at `bhoward@cumberlandcoil.gov`, as a
> REPLY in the thread where she sent the map on 2026-10-01 — never as a fresh letter. Prior contact:
> letters 5 August and 16 August, a third on 1 October at 18:11 UTC, her answer at 18:32 UTC with a
> photograph of the county's coloured district map ("Yellow is western district, blue is central
> and green is eastern"), and a thank-you from us at 18:49 UTC. On send, record `ASKED <date>` and
> an `ask` block reading `pending` on the `cumberland-board-districts` record.

**Why this is asked.** Her photograph settles everything but one detail. Read colour by colour
inside each of the county's twelve precincts, it puts Spring Point in Western, the Greenup
precincts, Union and Crooked Creek in Eastern, the rest in Central, and Neoga 1 and Neoga 2 divided
between Western and Central by one straight north-south line. That gives 3, 6 and 5 precincts per
district, which matches the county's own certified returns exactly, and those returns could not
have picked this answer on their own (37 different pairs of divided precincts fit the arithmetic).
What a phone photo cannot settle is the ROAD the line follows. It measures as straight, about five
miles east of the county's west edge, which is the road the county numbers 500E. One yes makes the
county drawable.

> Subject: Re: Cumberland County's three board districts
>
> Dear Clerk Howard,
>
> Thank you again for the map you sent on 1 October. It answered nearly everything: I can now see
> which precincts belong to each of the three districts, and the counts agree with your office's
> certified election results.
>
> One detail I cannot read with confidence from a photograph, and I would rather ask than guess.
> The line between the Western and Central districts runs through the Neoga precincts. Does it run
> north and south along 500E, from the north county line down to the township line at the south
> edge of Neoga 2?
>
> A one-word yes or no is all I need. If the line follows a different road, its name would settle
> it.
>
> With thanks,
>
> <YOUR NAME>
> <YOUR E-MAIL>
> https://districtry.com/il/

**A no is still useful.** It stops a wrong line being drawn, and a road name in its place draws the
right one.

## Ask il-jersey-7 — Jersey County Clerk: HELD, because the county's own 2016 map may already answer it

> **NOT DRAFTED, ON PURPOSE (2026-10-06).** Clerk Pam Warford answered on 2026-10-01 at 19:06 UTC:
> "No changes were made to county board districts in 2021, so the 2016 map is still correct.
> There were some changes to precincts however, which resulted in one precinct being split between
> two county board districts." Her attached table puts Jersey 7's reporting sub-units 0407-03 and
> 0407-04 in District 1 and 0407-01 in District 2. Every other precinct is whole.

**Why no letter yet.** She says the DISTRICT lines did not move; the precinct lines did. So the line
through Jersey 7 is the 2016 line, and the 2016 map is published on the Clerk's own site. Writing
to ask where it runs before reading that map would ask her to repeat something the county already
publishes. The next step is ours: read the 2016 map at Jersey 7. Only if that map is not legible
there does a letter go, and then it asks one narrow question about one precinct.

## Ask il-scott-commissioners-reply — Scott County Clerk: say she is right, and confirm the three names

> **NOT YET SENT, drafted 2026-10-06.** It goes as a reply in Clerk Brooke Smith's thread "RE:
> Scott County commissioners — your members page comes back empty". She wrote back that the page
> is not blank for her.

**She is right, and our letter was wrong.** Re-checked 2026-10-06: the page loads its member list
from the county's own data feed, using settings written into the page itself. Asked that way, the
feed answers in full and names three commissioners — Robert Schafer (County Chair), John Simmons
and Tom Peterson — with the office at 35 E. Market St., Winchester, and 217-742-5532. In August we
asked the feed without those settings, got an error, and found the Internet Archive's copy just as
empty; from that we told her a visitor would see an empty list. That was our reading, not her
page. A headless browser here first seemed to show the list's heading with no names under it;
re-run the same afternoon with a screenshot, it shows the names exactly as her screenshot does, and
the empty reading was our script slicing the page text at the wrong "People". Adam sees the same as
she does in his own browser. So nothing on her side fails: the names arrive a moment after the page,
from the county's feed, and our August check asked that feed the wrong way.

**What it costs nothing to ask.** The three names agree with what the county's certified election
results imply (Schafer won in 2020, Simmons in 2022, Peterson in 2024), so the letter asks only to
be told if any of it is wrong. Shipping the roster from her page is a separate change and waits on
Adam's word.

> Subject: Re: Scott County commissioners — your members page comes back empty
>
> Dear Clerk Smith,
>
> Thank you for checking, and you are right: the page is fine. The fault was in how I read it.
> When I looked in August the list's data came back with an error to my program, and I wrongly
> took that to mean visitors saw an empty list. I am sorry for the trouble.
>
> Read correctly, the page names Robert Schafer as County Chair, with John Simmons and Tom
> Peterson, at the office at 35 E. Market St. in Winchester. Unless you tell me any of that is
> wrong, that is what the site will show, credited to the county's page.
>
> Nothing more is needed from you. Thank you again.
>
> <YOUR NAME>
> <YOUR E-MAIL>
> https://districtry.com/il/

## Re-check of the Illinois "we couldn't read your page" letters, 2026-10-06

Adam asked (6 Oct) that every waiting letter saying we could not read a county's page be
re-checked before he sends it, after Scott County's Clerk showed us her page was fine. Each was
read today with this project's own roster client, robots.txt first, looking for a feed address
in the page the way Scott's carried one.

- **Perry** — kept. The site answers every request, robots.txt included, with SiteGround's
  security check (HTTP 202, `sg-captcha: challenge`). That is an access control and is not worked
  around, so nothing behind it can be read, feed or not; "turns away automated visits" is still
  true.
- **Johnson** — kept. `johnsonco.illinois.gov` points at a hosting company's shared server that
  carries no site for it (its certificate names the server, and plain HTTP answers that host's
  default page). That agrees with the Clerk's own statement of 21 July that there is no website.
- **Henderson** — kept. `hendersoncountyil.gov` serves a domain-parking page (a script sends the
  browser to `/lander`, which loads GoDaddy's parking template). Its robots.txt allows everything,
  so this is what a person sees too.
- **Christian** — wording corrected. The site still shows Cloudflare's "Just a moment" check to
  every request, robots.txt included, so it cannot be read and is not worked around. The letter
  said in the present tense that the board page names only the Chairman and Vice Chairman; we
  cannot know what it shows a person today, so it now says that is what it showed when we could
  last read it.
- **Pope** — wording corrected. The letter said the county's web address serves an empty
  template. `popeco.illinois.gov` has no website at all, and `popecountyil.com` cannot be reached
  from here (connection reset, redirect loop), which says nothing about what a person sees. The
  sentence describing the site is removed; the letter's questions do not depend on it.
- **Clark** (Ask 10, re-checked the same afternoon) — wording corrected. The letter said the
  courthouse switchboard is the only number published. It is not: the county's own board page
  (`clarkcountyil.org/board`) links "County Board Member 2022-2024", a scanned one-page list
  with a phone number and e-mail for each of the seven members, and all seven names still match
  the certified canvasses the roster is built from. It was missed because the list is a scanned
  image with no text layer, so a text reader sees an empty page; it had to be rendered and read
  as an image. The first question now asks whether those numbers are still right and whether
  the county is content to see them on the cards. The list also carries members' home
  addresses, which never ship whatever the answer. The precinct polling-place question stands.
- **Knox** (Ask 21, re-checked the same afternoon) — stands. Its only claim about what is
  published is that nothing records where Knox Seven went. The county's public map server
  (`gis.knoxcountyil.gov`, Public folder) carries no precinct layer; the only precinct layer
  in Knox's published ArcGIS services is the City of Galesburg's own 20 city precincts, from the
  Galesburg Board of Election Commissioners, which is a different election authority and does
  not cover Knox Township's county precincts. The county's main site now shows a Cloudflare
  "Just a moment" check to every request, so it cannot be read and is not worked around.
- **Bureau** (Ask 9, re-checked the same afternoon) — stands. The letter's claims are about the
  licence Ms. Anderson sent, which is a document we hold. The county's site (robots.txt allows
  everything) publishes no board-district map or precinct list on its board, clerk or
  assessments pages or in its linked files, and the public parcel viewer it links (Sidwell
  Portico) carries parcels, townships and roads but no board districts. The site's map link is
  a barn-quilt map. Nothing published makes the letter's question unnecessary.
- **WinGIS outage report** — withdraw. The Winnebago map server answers normally today
  (`maps.wingis.org`, the elected-officials layer returns its metadata). There is no outage to
  report.

## Ask il-cpd-district-commanders — City of Chicago, for the police department: a way to read the district commander list that our reader is allowed to use

> **NOT YET SENT — DRAFTED 2026-10-07 AS A FOLLOW-UP, NOT A NEW ASK.** Adam asked the City for
> this on 9 July, writing to Beth Rochford, Anna Mangahas and Nicole Garcia; Beth offered to pass
> it to the City's tech team and nothing has come back since. So the Letters thread drafted this as
> a reply in that 9 July thread to the same three City recipients, not to CPD's press office. Its
> wording differs from the text below in four ways: it names the site's new name, says our reader
> is now blocked, keeps the same three options, and asks them to point Adam to the right person at
> CPD if this belongs elsewhere. The Gmail draft is the text that goes; the text below is the
> original drafted here. On send, record `ASKED <date>` (follow-up to 9 July).

**Why this is asked.** The police-district card names each district's commander, the station
address and the district's community-policing (CAPS) e-mail, read weekly from the 22 district
pages on the department's site. The weekly refresh of 6 October was turned away by the site's
Cloudflare check: our reader identifies itself by name, and a managed challenge is an access
control this project does not get around (the standing rule since 29 September). The refresh used
to present a browser identity and stopped on 1 October (#1340), on a measurement of the site's
FRONT page, which does serve our name; the district pages and the sitemap do not. That is the
wrong-address reading `user-agent-measurements.json` still records for this host. Nothing else publishes
the list in a form we can read: the city data portal has no commander dataset, and the
department's own station map layer carries only each station's name, address, district and
phone. So the cards keep last week's names, which stay correct until a commander changes, and
this letter asks for a route that does not need the check to be defeated. Three answers all work:
a page or file outside the check, permission for the weekly reader by name, or a clean no.

> Subject: Reading the district commander list on chicagopolice.org
>
> Dear Office of Communications,  *(the sent version greets the three City recipients)*
>
> I run districtry (https://districtry.com/il/), a free public map where a Chicago resident can
> click their address and see who represents them, including their police district, its
> commander, the station address and the district's CAPS e-mail. Each card links back to the
> district's own page on your site.
>
> Once a week a small program reads your 22 district pages so the commander names stay current.
> It identifies itself by name and reads nothing else. Your site's security check now turns it
> away, and I will not try to get around that check. Until it can read the pages again, the map
> keeps showing the names from its last successful read.
>
> Is there a way for us to read the commander list that you are comfortable with? Any of these
> would work:
>
> 1. a page or file with the district commanders that is not behind the security check;
> 2. permission for our weekly program to read the 22 district pages (it can send whatever
>    identifying name or header suits you); or
> 3. a no, which is a perfectly good answer. We would then keep the list current by hand from
>    your announcements.
>
> Thank you for your time.
>
> <YOUR NAME>
> <YOUR E-MAIL>
> https://districtry.com/il/

**What each answer means.** A page outside the check: the scraper reads it instead, after its
robots.txt. Permission: recorded in `scripts/cpd_district_scraper.py` with its date and whatever
identifier the department names, and the Playwright rung stays retired either way. A no: the
roster becomes a hand-checked file like the early-voting list, and the gap is recorded.
