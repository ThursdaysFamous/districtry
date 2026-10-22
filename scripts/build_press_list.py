#!/usr/bin/env python3
"""Generate docs/PRESS_LIST.md from docs/press-list.json.

Same convention as build_county_status.py: the JSON is the data, the markdown is a READING of
it, and the markdown is never hand-edited. `--check` fails if the two have drifted.

Why this is generated rather than written: a press list is a pile of facts that go stale
independently — an address is retired, a weekly changes hands, a desk is folded into another.
Hand-keeping the prose and the data in agreement is exactly the drift this repo generates files
to prevent. Re-verify with scripts/verify_press_list.py, which re-fetches every cited page.
"""
import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "docs" / "press-list.json"
OUT = ROOT / "docs" / "PRESS_LIST.md"

def not_news(send_to):
    """The agents classified some inboxes as `other` — billing support, a web administrator, a
    talk-booking form. They are the only published route to that outlet, so they stay on the list,
    but a press release sent to one is a misfire and the row has to say so."""
    return (send_to or {}).get("purpose", "").strip().lower().startswith("other")


STATE_MARK = {
    "CONFIRMED": "confirmed",
    "BOUNCED": "**BOUNCED**",
    "UNRECHECKED": "**unrechecked**",
    "PARTIAL": "**partial**",
    "NOT_FOUND": "**not found**",
    "UNKNOWN": "**unknown**",
}


def esc(s):
    """Markdown-table-safe: a pipe inside a cell silently splits the row."""
    return re.sub(r"\s+", " ", (s or "").replace("|", "\\|")).strip()


def render(d):
    L = []
    a = L.append
    n_out = len(d["outlets"])
    n_send = sum(1 for o in d["outlets"] if o["send_to"])
    n_conf = sum(1 for o in d["outlets"] if o["send_to"] and o["send_to"]["state"] == "CONFIRMED")
    n_t1 = sum(1 for o in d["outlets"] if o["tier"] == 1)

    a("# districtry launch — press list")
    a("")
    a("<!-- ==== GENERATED FILE — DO NOT HAND-EDIT ==== -->")
    a("<!-- Emitted by scripts/build_press_list.py from docs/press-list.json.")
    a("     Regenerate:  python3 scripts/build_press_list.py")
    a("     Drift gate:  python3 scripts/build_press_list.py --check")
    a("     Re-verify:   python3 scripts/verify_press_list.py -->")
    a("")
    n_nn = sum(1 for o in d["outlets"] if not_news(o["send_to"]))
    a(f"**{n_out} newsrooms and desks; {n_send} carry a send address, {n_conf} of those "
      f"mechanically confirmed on the page that publishes them. {n_t1} are tier 1.**")
    a("")
    a(f"{n_nn} of those addresses are marked **not a news inbox** — the outlet publishes no "
      f"editorial address and this is its only published route (a general org inbox, an opinion "
      f"desk, membership support, in one case a site administrator). They are kept because they "
      f"are the way in, and flagged because a press release sent to one as though it were a city "
      f"desk is a misfire. Write those as a short personal note, not a release.")
    a("")
    a(f"Compiled {d['verified_date']} for the launch release. Press contact "
      f"`{d['release']['press_contact']}` / {d['release']['press_phone']}; the volunteer ask goes "
      f"to `{d['release']['volunteer_contact']}`.")
    a("")

    a("## The release")
    a("")
    a(d["release"].get("authored", ""))
    a("")
    # Prefix every line once. Chaining two replaces here double-applies and yields nested `> >`.
    for line in d["release"]["body"].split("\n"):
        a(("> " + line) if line.strip() else ">")
    a("")

    a("## How this file is used")
    a("")
    a("The same rules `docs/ASK_DRAFTS.md` sets for outbound asks apply here, for the same reason:")
    a("")
    a("1. **The operator sends. Nothing here is sent automatically, and no pitch is sent by the "
      "agent that compiled the list.** A cold e-mail to a newsroom is outward-facing and cannot "
      "be recalled; it goes when a person decides it goes.")
    a("2. **Record the send date the day it goes, never before**, in the ledger at the foot of "
      "this file. An unsent row and a sent-but-unanswered row are different states and must not "
      "look alike.")
    a("3. **One follow-up, at 6–8 business days, in the same thread, carrying something new.** "
      "Then stop. A newsroom that did not bite is a closed question, not a queue.")
    a("4. **One address per message. No BCC, no mailing-list tool.** A visible blast to thirty "
      "tips inboxes is a filter event, and it is also the thing that makes a sender a spammer "
      "rather than a correspondent.")
    a("5. **A clean no is a good outcome** and worth recording — it closes an outlet for good.")
    a("")

    a("## How each address got here")
    a("")
    a("Two independent steps, because a wrong address does not merely fail — it burns the pitch "
      "and, if it bounces to a shared desk, the sender's name with it.")
    a("")
    a("* **Researched under a no-guessing rule.** The agents that compiled this were forbidden "
      "from inferring an address from a pattern — no `tips@`, no `news@`, nothing reconstructed "
      "from a domain. Every address had to be read on a page the agent actually fetched, and "
      "returned with that page's URL and a verbatim snippet showing it published there.")
    a("* **Then re-checked mechanically.** `scripts/verify_press_list.py` re-fetches every cited "
      "page and looks for the address on it, decoding Cloudflare `data-cfemail` obfuscation and "
      "PDF text along the way — both of which had already produced false misses here, and one of "
      "which (Cloudflare) is the same trick that once silently emptied seven county e-mail "
      "addresses out of this project's own data.")
    a("")
    a("So the **State** column is a measurement, not a confidence:")
    a("")
    a("| State | Means |")
    a("|---|---|")
    a("| `confirmed` | the address was found on the page cited for it |")
    a("| `BOUNCED` | mail to it was rejected. It is left on the list, struck, so nobody tries it "
      "again. |")
    a("| `markup-only` | the address is on the cited page but ONLY inside machine-readable markup "
      "— JSON-LD, a meta tag, a data attribute — and in no text or `mailto:` link a reader ever "
      "sees. **This is the shape the Chicago Tribune's dead address had.** Nobody at the outlet "
      "looks at it, so nobody notices when it dies. Treat as unconfirmed. |")
    a("| `unrechecked` | that page refuses this network (Akamai/Cloudflare 403, a TLS failure). "
      "**This is a fact about the host, not a doubt about the address** — the same inversion "
      "`validate_card_links.py` uses for its `EXPECTED_UNREACHABLE` hosts. Confirm in a browser "
      "before sending. |")
    a("")
    a("")
    a("**And a limit worth stating plainly.** " + d["release"]["deliverability_note"])
    a("")
    a("Rows with **no send address at all** are listed separately. They are not failures: a "
      "newsroom that publishes only a form is answered through its form, and several sites here "
      "sit behind a captcha or a managed challenge that nothing in this repo will route around.")
    a("")

    a("## Where the release goes, and in what order")
    a("")
    a("Every link is tagged `utm_campaign=" + d["utm"]["campaign"] + "` and "
      "`utm_medium=" + d["utm"]["medium"] + "`, with a per-wave `utm_source`, so the whole push "
      "totals as one campaign while each room splits out. That tagging is the only attribution "
      "that will ever exist for most of these sends — and it is checked: the app reads `utm_*` "
      "before the hash router strips them (`il/index.html`), and a `utm_source` other than "
      "`share`/`embed` renders the landing page rather than forwarding, so a Wisconsin editor "
      "clicking a root link is not silently dropped into the Illinois app.")
    a("")
    for i, w in enumerate(d["waves"], 1):
        a(f"### {esc(w['name'])}")
        a("")
        a(f"*{esc(w['when'])}*")
        a("")
        a(f"**Subject:** {esc(w['subject_line'])} ({len(w['subject_line'])} chars)")
        a("")
        a(f"**Opens:** {esc(w['lede'])}")
        a("")
        a(f"**Who:** {esc(w['who'])}")
        a("")
        a(f"**Why this order:** {esc(w['rationale'])}")
        a("")

    a("## The list")
    a("")
    labels = {r["key"]: r for r in d["regions"]}
    for r in d["regions"]:
        rows = [o for o in d["outlets"] if o["region"] == r["key"] and o["send_to"]]
        if not rows:
            continue
        a(f"### {r['label']} — {len(rows)} ({sum(1 for o in rows if o['tier'] == 1)} tier-1)")
        a("")
        a(f"Tag these `utm_source={r['utm_source']}`. The **#** column is the tier (send tier 1 "
          f"first); **Wave** is the day it goes out, and a region can span two waves — ten Chicago "
          f"rooms are lifted into wave 1 because the school-board hook is the only pitch in the "
          f"whole send with a date attached.")
        a("")
        a("| # | Wave | Outlet | What they are | Send to | State | Opening line |")
        a("|---|---|---|---|---|---|---|")
        for o in sorted(rows, key=lambda x: (x["tier"], x["name"])):
            s = o["send_to"]
            name = esc(o["name"])
            if o["also_known_as"]:
                name += " <br>*(also " + esc(", ".join(o["also_known_as"])) + " — one inbox)*"
            state = STATE_MARK.get(s["state"], s["state"])
            if s.get("risk") == "markup_only":
                state += " <br>**markup-only**"
            if s.get("bounced_on"):
                state += " <br>*" + s["bounced_on"] + "*"
            if not_news(s):
                state += " <br>**not a news inbox**"
            if o.get("sent_on"):
                state += " <br>*sent " + o["sent_on"] + "*"
            # The opening line IS the deliverable; the research angle is only what produced it.
            # For the ones already sent, point at the sender's own outbox rather than reproducing
            # his correspondence — this file is public and those e-mails are not.
            if o.get("sent_on"):
                opening = "*already sent — see your own sent mail for the wording used*"
            else:
                opening = esc(o.get("intro") or o["angle"])
            a(f"| {o['tier']} | {o.get('wave', '')} | [{name}]({o['homepage']}) | {esc(o['medium'])} | "
              f"`{s['value']}` <br>[source]({s['source_url']}) | {state} | {opening} |")
        a("")

    noaddr = [o for o in d["outlets"] if not o["send_to"]]
    if noaddr:
        a("### No published address — reach these another way")
        a("")
        a("| Outlet | Region | Route | Why |")
        a("|---|---|---|---|")
        for o in sorted(noaddr, key=lambda x: (x["region"], x["name"])):
            route = o["forms"][0] if o["forms"] else o["homepage"]
            why = esc(o["notes"])[:240]
            a(f"| [{esc(o['name'])}]({o['homepage']}) | {labels[o['region']]['label']} | "
              f"[form / contact page]({route}) | {why} |")
        a("")

    a("## The data desk")
    a("")
    a("Chris's note, 2026-09-02: **address the data reporter or data editor where an outlet has "
      "one.** For a pitch whose entire subject is a dataset nobody had assembled, they are the "
      "reader who knows immediately why 91 counties took months. Every person here was read off "
      "the OUTLET'S OWN staff or author page and every address comes from that page's own markup "
      "— none is inferred from a firstname.lastname pattern, which is the one thing the research "
      "rules forbid outright. The send still goes to the desk; the data reporter is who the first "
      "line names.")
    a("")
    desk = [(o, b) for o in d["outlets"] for b in o["bylines"] if b.get("data_desk")]
    withaddr = sum(1 for _, b in desk if b.get("address"))
    a(f"{len(desk)} across {len({o['name'] for o, _ in desk})} outlets; {withaddr} publish a "
      f"personal address, {len(desk) - withaddr} do not (reach those through the outlet's desk "
      f"address above and name them in the first line).")
    a("")
    a("| Wave | Outlet | Who | Title / why | Address | Source |")
    a("|---|---|---|---|---|---|")
    for o, b in sorted(desk, key=lambda r: (r[0].get("wave", 9), r[0]["name"], r[1]["name"])):
        addr = f"`{b['address']}`" if b.get("address") else "*none published*"
        a(f"| {o.get('wave','')} | {esc(o['name'])} | {esc(b['name'])} | {esc(b.get('beat',''))} "
          f"| {addr} | [page]({b.get('source_url','')}) |")
    a("")
    neg = [o for o in d["outlets"] if o.get("data_desk_finding")]
    if neg:
        a("**Measured absences.** A page that loaded and does not name a data desk is an answer, "
          "not a blank — it is what stops the next pass re-probing the same page.")
        a("")
        for o in sorted(neg, key=lambda x: x["name"]):
            a(f"- **{esc(o['name'])}** — {esc(o['data_desk_finding'])}")
        a("")

    a("## Bylines worth addressing a pitch to")
    a("")
    a("The plan's rule stands: **send to the desk, name the reporter in the first line.** A "
      "personal address is listed only where the outlet publishes it on its own staff page, and "
      "a desk address outlives any reporter's move between now and the send.")
    a("")
    a("| Outlet | Reporter | Beat |")
    a("|---|---|---|")
    for o in d["outlets"]:
        for b in o["bylines"]:
            if not b.get("name"):
                continue
            a(f"| {esc(o['name'])} | {esc(b['name'])} | {esc(b.get('beat', ''))} |")
    a("")

    a("## Send mechanics")
    a("")
    for m in d["mechanics"]:
        a(f"- {esc(m)}")
    a("")
    a("## What could go wrong")
    a("")
    for r in d["risks"]:
        a(f"- {esc(r)}")
    a("")

    a("## Send ledger")
    a("")
    a("**GENERATED from `sent_on` / `attempted_on` in `docs/press-list.json` — this table is not "
      "hand-filled.** `docs/ASK_DRAFTS.md` exists because two ask ledgers in this repo once said "
      "*held* about e-mails that had already been sent. A hand-filled press ledger is that same "
      "failure waiting to happen with strangers on the other end, so the ledger and the per-outlet "
      "rows above are now ONE fact: mark the outlet the day it goes out and both surfaces move "
      "together. A bounce is recorded as an ATTEMPT, never as a send — an outlet that was never "
      "reached still has a pitch owing.")
    a("")
    # A bounce that was later re-sent keeps its own row, so the ledger still shows the attempt.
    log = []
    for o in d["outlets"]:
        if o.get("attempted_on"):
            state = "bounced, re-sent" if o.get("sent_on") else "**BOUNCED — owing**"
            log.append((o["attempted_on"], o, state,
                        o.get("attempted_to") or "", o.get("attempt_outcome") or ""))
        if o.get("sent_on"):
            log.append((o["sent_on"], o, "sent", o.get("sent_to") or "", o.get("reply_note") or ""))
    if not log:
        a("Nothing has been sent yet.")
        a("")
        return "\n".join(L) + "\n"
    log.sort(key=lambda r: (r[0], r[1]["name"]))
    sent = [r for r in log if r[2] == "sent"]
    owing = [r for r in log if r[2].startswith("**BOUNCED")]
    a(f"{len({r[1]['name'] for r in log})} outlets contacted; "
      f"{len(sent)} delivered, {len(owing)} bounced and still owing. "
      f"{sum(1 for r in log if r[4])} rows have an outcome recorded; "
      f"{sum(1 for r in sent if r[1].get('followed_up_on'))} have had their one follow-up.")
    a("")
    a("| Sent | Wave | Outlet | Address used | State | Follow-up | Outcome |")
    a("|---|---|---|---|---|---|---|")
    for day, o, state, addr, note in log:
        follow = ""
        if state == "sent" and o.get("followed_up_on"):
            follow = f"{o['followed_up_on']} to `{o.get('followed_up_to') or addr}`"
        a(f"| {day} | {o.get('wave','')} | [{esc(o['name'])}]({o['homepage']}) | "
          f"`{addr}` | {state} | {follow} | {esc(note)} |")
    a("")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="fail if the file has drifted")
    args = ap.parse_args()
    text = render(json.load(open(DATA, encoding="utf-8")))
    if args.check:
        if not OUT.exists():
            print("FAIL: docs/PRESS_LIST.md is missing; run scripts/build_press_list.py")
            return 1
        if OUT.read_text(encoding="utf-8") != text:
            print("FAIL: docs/PRESS_LIST.md is stale; run scripts/build_press_list.py")
            return 1
        print("OK: docs/PRESS_LIST.md matches docs/press-list.json")
        return 0
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} ({len(text.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
