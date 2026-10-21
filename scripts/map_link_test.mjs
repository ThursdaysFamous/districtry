// Holds engine/shared/map-link.txt, AS SHIPPED, to the links a reader pastes.
//
// The block reads Google Maps and Apple Maps links in the browser
// (parseMapLink), and every app and the front door run this one copy, so a
// case here is a case in thirteen apps at once. Node runs it with no browser:
// the block uses only URL and String, which Node provides.
//
// The links below were written in the shapes Google and Apple publish and
// that the two apps' share buttons produce; none carries a real person's
// location. A short link is recognised and handed to the lookup
// (services/link-lookup/main.ts), stubbed here: following one is its job.
//
//   node scripts/map_link_test.mjs
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const src = readFileSync(path.join(root, "engine/shared/map-link.txt"), "utf8");
const api = new Function(src + "\nreturn { parseMapLink, mapLinkMessage, resolveShortMapLink, addressAfterName, labelCarriesNumber, labelAtHouse, addressStreet, addressParts, labelOnStreet, addressInTownOf, addressForLookup, addressStateTag, stateTagOfName, stateInSentence, mapLinkForText, zipQuery, zipListed };")();

const near = (a, b) => Math.abs(a - b) < 1e-6;
const cases = [
  // [pasted text, expected]
  ["41.8825, -87.6285", { kind: "point", lat: 41.8825, lng: -87.6285, source: "coordinates" }],
  ["41.8825 -87.6285", { kind: "point", lat: 41.8825, lng: -87.6285, source: "coordinates" }],
  ["(41.8825,-87.6285)", { kind: "point", lat: 41.8825, lng: -87.6285, source: "coordinates" }],
  [`41°52'57.0"N 87°37'42.6"W`, { kind: "point", lat: 41.8825, lng: -87.6285, source: "coordinates" }],
  // two bare whole numbers are an address, not a position
  ["100 200", null],
  ["233 S Wacker Dr, Chicago", null],
  ["120, 40", null],  // latitude out of range
  // Google: the place (!3d!4d) wins over the map centre (@)
  ["https://www.google.com/maps/place/Willis+Tower/@41.8788764,-87.6385741,17z/data=!3m1!4b1!4m6!3m5!1s0x880e2cbe7d1a22d5:0x6d4d1a3f1a1b1b1b!8m2!3d41.8788764!4d-87.6359992!16zL20vMDF4cl9j",
    { kind: "point", lat: 41.8788764, lng: -87.6359992, source: "google" }],
  ["https://www.google.com/maps/@41.8825,-87.6285,15z", { kind: "point", lat: 41.8825, lng: -87.6285, source: "google" }],
  ["https://maps.google.com/?q=41.8825,-87.6285", { kind: "point", lat: 41.8825, lng: -87.6285, source: "google" }],
  ["https://www.google.com/maps/search/?api=1&query=41.8825%2C-87.6285", { kind: "point", lat: 41.8825, lng: -87.6285, source: "google" }],
  ["https://www.google.com/maps/search/41.8825,+-87.6285", { kind: "point", lat: 41.8825, lng: -87.6285, source: "google" }],
  ["https://www.google.com/maps/place/41%C2%B052'57.0%22N+87%C2%B037'42.6%22W/@41.8825,-87.6311,17z",
    { kind: "point", lat: 41.8825, lng: -87.6285, source: "google" }],
  ["https://www.google.co.uk/maps/@51.5,-0.12,12z", { kind: "point", lat: 51.5, lng: -0.12, source: "google" }],
  // a place name and a distant map centre: search the name
  ["https://www.google.com/maps/place/Daley+Plaza/@41.88,-87.63,11z", { kind: "text", text: "Daley Plaza", source: "google" }],
  ["https://maps.google.com/?q=50+W+Washington+St,+Chicago,+IL", { kind: "text", text: "50 W Washington St, Chicago, IL", source: "google" }],
  ["google.com/maps/@41.8825,-87.6285,16z", { kind: "point", lat: 41.8825, lng: -87.6285, source: "google" }],
  // the Google Maps Android app's link: the place's name and address, no position
  ["https://maps.google.com/?q=Starved+Rock+Lodge,+2668+E+875th+Rd,+Oglesby,+IL+61348&ftid=0x880bd2e1b3a8f5d1:0x9b1c2d3e4f5a6b7c&entry=gps",
    { kind: "text", text: "Starved Rock Lodge, 2668 E 875th Rd, Oglesby, IL 61348", source: "google" }],
  // shared from a phone: words around the link
  ["Willis Tower\nhttps://maps.app.goo.gl/AbCdEf123", { kind: "short", source: "google" }],
  ["https://goo.gl/maps/AbCdEf123", { kind: "short", source: "google" }],
  ["https://www.google.com/maps/dir/Chicago/Evanston", { kind: "unreadable", source: "google" }],
  // Apple
  ["https://maps.apple.com/?ll=41.8825,-87.6285&q=Dropped%20Pin", { kind: "point", lat: 41.8825, lng: -87.6285, source: "apple" }],
  ["https://maps.apple.com/place?coordinate=41.8825,-87.6285&name=Daley%20Plaza", { kind: "point", lat: 41.8825, lng: -87.6285, source: "apple" }],
  ["https://maps.apple.com/?address=50%20W%20Washington%20St,%20Chicago,%20IL%2060602", { kind: "text", text: "50 W Washington St, Chicago, IL 60602", source: "apple" }],
  ["https://maps.apple/p/AbCdEf.123", { kind: "short", source: "apple" }],
  ["https://maps.apple.com/?daddr=Evanston", { kind: "unreadable", source: "apple" }],
  // some other link
  ["https://example.com/41.8825,-87.6285", { kind: "unreadable", source: "link" }],
];

let failed = 0;
for (const [text, want] of cases) {
  const got = api.parseMapLink(text);
  let ok;
  if (want === null) ok = got === null;
  else ok = got && got.kind === want.kind && got.source === want.source &&
    (want.lat === undefined || near(got.lat, want.lat)) &&
    (want.lng === undefined || near(got.lng, want.lng)) &&
    (want.text === undefined || got.text === want.text);
  if (!ok) {
    failed++;
    console.error("map-link: FAIL " + JSON.stringify(text) + "\n  want " + JSON.stringify(want) + "\n  got  " + JSON.stringify(got));
  }
}

// A short link goes to the lookup, and only the short link: the URL asked is
// the lookup's own address with the link as its one parameter, and the full
// link it answers is read by the same parser.
const LOOKUP = "https://link-lookup.districtry.deno.net/";
const SHORT = "https://maps.app.goo.gl/x";
let asked = [];
globalThis.fetch = (url) => {
  asked.push(String(url));
  return Promise.resolve({ ok: true, json: () => Promise.resolve({
    url: "https://www.google.com/maps/place/Daley+Plaza/@41.8836,-87.6314,17z/data=!3m1!4b1!8m2!3d41.88395!4d-87.63022" }) });
};
const full = await api.resolveShortMapLink({ kind: "short", url: SHORT, source: "google" }).catch((e) => e);
if (asked.length !== 1 || asked[0] !== LOOKUP + "?u=" + encodeURIComponent(SHORT)) {
  failed++; console.error("map-link: FAIL a short link should ask only the lookup, once; asked " + JSON.stringify(asked));
}
if (!full || full.kind !== "point" || !near(full.lat, 41.88395) || !near(full.lng, -87.63022)) {
  failed++; console.error("map-link: FAIL the lookup's full link was not read as its place; got " + JSON.stringify(full));
}
// A FAILED LOOKUP IS TRIED AGAIN, and only when a second try could answer
// differently. The block's waits (1.5 and 4 seconds between tries, 10 more
// before a fourth try when the lookup answered 404, the answer a link too new
// for Google to know gets, and 8 seconds for each try) run here a thousand
// times faster, and every delay it asks for is recorded, so the retry
// schedule is checked rather than waited out.
const realSetTimeout = globalThis.setTimeout;
let waits = [];
globalThis.setTimeout = (fn, ms) => { waits.push(ms); return realSetTimeout(fn, ms / 1000); };
const DAMAGED = { ok: true, json: () => Promise.resolve({ url: SHORT }) };
const PLACE = { ok: true, json: () => Promise.resolve({
  url: "https://www.google.com/maps/place/Daley+Plaza/@41.8836,-87.6314,17z/data=!3m1!4b1!8m2!3d41.88395!4d-87.63022" }) };
const NO_ANSWER = () => Promise.reject(new TypeError("Failed to fetch"));
// a request that never answers until it is cancelled, as a hung one does
const HANG = (url, opts) => new Promise((_, reject) => opts.signal.addEventListener("abort",
  () => { const e = new Error("aborted"); e.name = "AbortError"; reject(e); }));
const lookups = [
  // [what each try answers, tries wanted, resolves?, reason wanted]
  ["the place", [PLACE], 1, true],
  ["a short link again", [DAMAGED], 1, false, "no-map"],
  ["a 400", [{ ok: false, status: 400 }], 1, false, ""],
  ["a 502 on every try", [{ ok: false, status: 502 }], 3, false, "no-answer"],
  ["a 404 on every try", [{ ok: false, status: 404 }], 4, false, "no-map"],
  ["a 404 three times, then the place", [{ ok: false, status: 404 }, { ok: false, status: 404 }, { ok: false, status: 404 }, PLACE], 4, true],
  ["a 404, then a 502 on every try", [{ ok: false, status: 404 }, { ok: false, status: 502 }], 3, false, "no-answer"],
  ["a 502 twice, then a 404", [{ ok: false, status: 502 }, { ok: false, status: 502 }, { ok: false, status: 404 }], 4, false, "no-map"],
  ["no answer on every try", [NO_ANSWER], 3, false, "unreached"],
  ["a hung request on every try", [HANG], 3, false, "timeout"],
  ["a 502, then the place", [{ ok: false, status: 502 }, PLACE], 2, true],
  ["no answer twice, then the place", [NO_ANSWER, NO_ANSWER, PLACE], 3, true],
];
for (const [label, answers, wantTries, wantResolved, wantReason] of lookups) {
  let tries = 0;
  const retried = [];
  waits = [];
  globalThis.fetch = (url, opts) => {
    const a = answers[Math.min(tries++, answers.length - 1)];
    return typeof a === "function" ? a(url, opts) : Promise.resolve(a);
  };
  const got = await api.resolveShortMapLink({ kind: "short", url: SHORT, source: "google" }, undefined,
    (n, err) => retried.push([n, err && err.reason])).then((v) => ({ v }), (e) => ({ e }));
  const pauses = waits.filter((ms) => ms !== 8000);
  const problems = [];
  if (tries !== wantTries) problems.push("asked " + tries + " times, want " + wantTries);
  if (!!got.v !== wantResolved) problems.push(got.v ? "resolved" : "rejected (" + (got.e && got.e.message) + ")");
  if (got.v && got.v.kind !== "point") problems.push("resolved to " + JSON.stringify(got.v));
  if (!wantResolved && got.e && got.e.reason !== wantReason) problems.push("reason " + JSON.stringify(got.e.reason) + ", want " + JSON.stringify(wantReason));
  if (JSON.stringify(pauses) !== JSON.stringify([1500, 4000, 10000].slice(0, wantTries - 1))) problems.push("paused " + JSON.stringify(pauses));
  if (retried.length !== wantTries - 1 || retried.some(([n, r], i) => n !== i + 1 || !r)) problems.push("told the page " + JSON.stringify(retried));
  if (problems.length) { failed++; console.error("map-link: FAIL a lookup answering " + label + ": " + problems.join("; ")); }
}
// A cancelled lookup stops, between tries as well as during one, and says
// it was cancelled rather than that the link could not be read.
for (const during of [true, false]) {
  let tries = 0, told = 0;
  const ctl = new AbortController();
  globalThis.fetch = (url, opts) => {
    tries++;
    if (during) return HANG(url, opts);
    return Promise.resolve({ ok: false, status: 502 });
  };
  const p = api.resolveShortMapLink({ kind: "short", url: SHORT, source: "google" }, ctl.signal,
    () => { told++; if (!during) ctl.abort(); });
  if (during) realSetTimeout(() => ctl.abort(), 1);
  const e = await p.then(() => null, (err) => err);
  // cancelled during a try, the page is never told a new try is coming
  if (!e || e.name !== "AbortError" || tries !== 1 || told !== (during ? 0 : 1)) {
    failed++;
    console.error("map-link: FAIL a lookup cancelled " + (during ? "during a try" : "between tries") +
      " should stop with an AbortError after one try; got " + (e && e.name) + " after " + tries +
      ", telling the page " + told + " time(s) it was trying again");
  }
}
globalThis.setTimeout = realSetTimeout;

// The message names the maker and, when the lookup said, which side failed.
const said = [
  [{ kind: "short", source: "google" }, undefined, /^That short Google Maps link couldn't be read just now\. /],
  [{ kind: "short", source: "google" }, { reason: "unreached" }, /\(districtry couldn't reach the service that reads short links\)/],
  [{ kind: "short", source: "google" }, { reason: "timeout" }, /\(the service that reads short links didn't answer in time\)/],
  [{ kind: "short", source: "google" }, { reason: "no-map" }, /\(Google didn't say where it leads\)/],
  [{ kind: "short", source: "apple" }, { reason: "no-answer" }, /^That short Apple Maps link .*\(Apple didn't answer the service that reads short links\)/],
];
for (const [link, err, want] of said) {
  const msg = api.mapLinkMessage(link, err);
  if (!want.test(msg) || /address bar/.test(msg)) {
    failed++; console.error("map-link: FAIL the short-link message for " + JSON.stringify(err) + " reads " + JSON.stringify(msg));
  }
}

// The address behind a place's name: tried alone when the whole string
// matches nothing. Anything that does not open with words and then reach a
// house number after a comma is left alone.
const bare = [
  ["Starved Rock Lodge, 2668 E 875th Rd, Oglesby, IL 61348", "2668 E 875th Rd, Oglesby, IL 61348"],
  ["Cozy Dog Drive In, 2935 S 6th St, Springfield, IL 62703, United States", "2935 S 6th St, Springfield, IL 62703, United States"],
  ["Joe's, Suite 4, 100 Main St, Peoria, IL", "100 Main St, Peoria, IL"],
  ["Queens Library, 89-11 Merrick Blvd, Jamaica, NY 11432", "89-11 Merrick Blvd, Jamaica, NY 11432"],
  // a Wisconsin grid number, as Photon holds Devil's Lake State Park's (2026-10-16)
  ["Devil's Lake State Park, S5975 Park Rd, Baraboo, WI 53913", "S5975 Park Rd, Baraboo, WI 53913"],
  ["Farm Stand, W123N4567 Main St, Menomonee Falls, WI 53051", "W123N4567 Main St, Menomonee Falls, WI 53051"],
  ["N2 Bar, 100 Main St, Peoria, IL 61602", "100 Main St, Peoria, IL 61602"],   // a name, not a grid number
  ["7-Eleven, 100 Main St, Peoria, IL 61602", "100 Main St, Peoria, IL 61602"], // a name that opens with a digit
  ["233 S Wacker Dr, Chicago, IL 60606", null],          // already an address
  ["W123N4567 Main St, Menomonee Falls, WI 53051", null], // already an address, with a grid number
  ["Daley Plaza", null],                                // a name and nothing else
  ["Starved Rock State Park, Oglesby, IL 61348", null], // no house number to fall back to
  ["Willis Tower, 2", null],                            // half-typed: a number, no street yet
];
for (const [text, want] of bare) {
  const got = api.addressAfterName(text);
  if (got !== want) {
    failed++;
    console.error("map-link: FAIL addressAfterName(" + JSON.stringify(text) + ")\n  want " + JSON.stringify(want) + "\n  got  " + JSON.stringify(got));
  }
}

// An answer to the address alone counts only if it carries the address's
// house number. The two 3rd Street labels are the answers Photon gave for
// Starved Rock Lodge's address on 2026-10-14; the rest are written the way
// the apps label an answer, and "2668" alone is how the front door reads a
// Photon housenumber.
const carry = [
  ["2668 East 875th Road, Oglesby, Illinois, 61348", "2668 E 875th Rd, Oglesby, IL 61348", true],
  ["West 3rd Street, Oglesby, Illinois", "2668 E 875th Rd, Oglesby, IL 61348", false],
  ["East 3rd Street, Oglesby, Illinois", "2668 E 875th Rd, Oglesby, IL 61348", false],
  ["26680 Main Street, Oglesby, Illinois", "2668 E 875th Rd, Oglesby, IL 61348", false], // a longer number
  ["Lodge, 12668 Road, Illinois", "2668 E 875th Rd, Oglesby, IL 61348", false],
  ["89-11 Merrick Boulevard, Queens, New York, NY, USA", "89-11 Merrick Blvd, Jamaica, NY 11432", true],
  ["Devil's Lake State Park, S5975 Park Road, Baraboo, Wisconsin, 53913", "S5975 Park Rd, Baraboo, WI 53913", true],
  ["N5975 Park Road, Baraboo, Wisconsin", "S5975 Park Rd, Baraboo, WI 53913", false],  // north of the line, not south
  ["5975 Park Road, Baraboo, Wisconsin", "S5975 Park Rd, Baraboo, WI 53913", false],
  ["W123N4567 Main Street, Menomonee Falls, Wisconsin", "W123N4567 Main St, Menomonee Falls, WI 53051", true],
  ["2668", "2668 E 875th Rd, Oglesby, IL 61348", true],                                // a housenumber alone
  ["", "2668 E 875th Rd, Oglesby, IL 61348", false],
  [undefined, "2668 E 875th Rd, Oglesby, IL 61348", false],
  ["2668 East 875th Road, Oglesby", "Starved Rock Lodge", false],                     // no number to hold to
];
for (const [label, address, want] of carry) {
  const got = api.labelCarriesNumber(label, address);
  if (got !== want) {
    failed++;
    console.error("map-link: FAIL labelCarriesNumber(" + JSON.stringify(label) + ", " + JSON.stringify(address) + ")\n  want " + want + "\n  got  " + got);
  }
}

// An answer is the house an address names when a part of its label opens
// with the house number and goes on to name the address's street. On
// 2026-10-19 the one answer the Illinois map's search gave for one of 49
// Cook County addresses was that number on another street, which carries
// the number and is not the house. The house numbers here are made up.
const EUGENIE_9 = "9 W Eugenie St, Chicago, IL 60614";
const house = [
  ["9 West Eugenie Street, Lincoln Park, North Chicago Township, Illinois, 60614", EUGENIE_9, true],
  ["9 W EUGENIE ST, CHICAGO, IL, 60614", EUGENIE_9, true],                         // as the Census Bureau writes it
  ["Joe's, 9 West Eugenie Street, Chicago, Illinois, 60614", EUGENIE_9, true],     // a name before it
  ["9 West North Avenue, Wicker Park, Chicago, Illinois, 60622", EUGENIE_9, false], // the number on another street
  ["9 East Eugenie Street, Chicago, Illinois, 60614", EUGENIE_9, false],           // another direction
  ["9 Eugenie Street, Chicago, Illinois, 60614", EUGENIE_9, true],                 // its direction left off
  ["19 West Eugenie Street, Chicago, Illinois, 60614", EUGENIE_9, false],          // another number on it
  ["West Eugenie Street, Chicago, Illinois, 60614", EUGENIE_9, false],             // the street alone
  ["West Eugenie Street, 9, Chicago, Illinois", EUGENIE_9, false],                 // the number alone in a part
  ["9 West Eugenie Street, Chicago, Illinois", "9 W Eugenie, Chicago", true],      // typed without its street type
  ["9 West Eugenie Street, Chicago, Illinois", "9 W Eugenie St Chicago IL 60614", true], // its town typed with no comma
  ["9 West Eugenie Street, Chicago, Illinois", "9 W Eugenie Chicago", false],      // neither its type nor a comma: listed, not taken
  ["9 N LA SALLE ST, CHICAGO, IL, 60602", "9 N LaSalle St, Chicago, IL 60602", true], // the spaces in a name
  ["9 Saint Louis Avenue, Chicago, Illinois", "9 S St Louis Ave, Chicago, IL", true],  // Saint and St
  ["9 South Doctor Martin Luther King Junior Drive, Chicago, Illinois", "9 S Dr Martin Luther King Jr Dr, Chicago, IL", true],
  ["9 South Doctor Martin Luther King Junior Drive, Chicago, Illinois", "9 S King Dr, Chicago, IL", false], // fewer of its words
  ["9 Oak Park Avenue, Berwyn, Illinois", "9 Oak Ave, Berwyn, IL", false],         // Oak Avenue is not Oak Park Avenue
  ["9 Oak Avenue, Berwyn, Illinois", "9 Oak Park Ave, Berwyn, IL", false],
  ["9 O'Brien Lane, Peoria, Illinois", "9 OBrien Ln, Peoria, IL", true],            // the marks inside a name
  ["9 Peña Boulevard, Denver, Colorado", "9 Pena Blvd, Denver, CO", true],      // and its accents
  ["9 West Oakley Drive, Westmont, Illinois, 60559", "9 W Oakley Dr NW Westmont", true],
  ["9 West Oakley Drive Southwest, Westmont, Illinois, 60559", "9 W Oakley Dr NW Westmont", false], // NW is not SW
  ["9 West Oakley Drive Southwest, Westmont, Illinois, 60559", "9 W Oakley Dr NW, Westmont, IL 60559", false],
  ["S5975 Park Road, Baraboo, Wisconsin, 53913", "S5975 Park Rd, Baraboo, WI 53913", true],
  ["N5975 Park Road, Baraboo, Wisconsin, 53913", "S5975 Park Rd, Baraboo, WI 53913", false],
  ["89-11 Merrick Boulevard, Queens, New York, NY, USA", "89-11 Merrick Blvd, Jamaica, NY 11432", true],
  ["2668", "2668 E 875th Rd, Oglesby, IL 61348", false],                            // a number with no street
  ["9 West Eugenie Street, Chicago, Illinois", "Starved Rock Lodge", false],       // no number to hold to
  [undefined, EUGENIE_9, false],
];
for (const [label, address, want] of house) {
  const got = api.labelAtHouse(label, address);
  if (got !== want) {
    failed++;
    console.error("map-link: FAIL labelAtHouse(" + JSON.stringify(label) + ", " + JSON.stringify(address) + ")\n  want " + want + "\n  got  " + got);
  }
}

// An address's parts, for the street it is on: the number, the street (a
// unit at its end left off), the town before the state and the ZIP code.
const parts = [
  ["9 W Oakley Dr NW, Westmont, IL 60559", { number: "9", street: "W Oakley Dr NW", town: "Westmont", zip: "60559" }],
  ["2935 S 6th St, Springfield, IL 62703, United States", { number: "2935", street: "S 6th St", town: "Springfield", zip: "62703" }],
  ["100 Main St Suite 4, Peoria, IL", { number: "100", street: "Main St", town: "Peoria", zip: "" }],
  ["89-11 Merrick Blvd, Jamaica, NY 11432", { number: "89-11", street: "Merrick Blvd", town: "Jamaica", zip: "11432" }],
  ["S5975 Park Rd, Baraboo, WI 53913", { number: "S5975", street: "Park Rd", town: "Baraboo", zip: "53913" }],
  ["W123N4567 Main St, Menomonee Falls, WI 53051", { number: "W123N4567", street: "Main St", town: "Menomonee Falls", zip: "53051" }],
  ["Starved Rock Lodge", null],
  ["2668 E 875th Rd", null],  // no town or ZIP to hold a street to
];
for (const [address, want] of parts) {
  const got = api.addressParts(address);
  if (JSON.stringify(got) !== JSON.stringify(want)) {
    failed++;
    console.error("map-link: FAIL addressParts(" + JSON.stringify(address) + ")\n  want " + JSON.stringify(want) + "\n  got  " + JSON.stringify(got));
  }
}

// The house number and the street an address opens with, a unit at the
// street's end left off; null unless it opens with a house number.
const streets = [
  ["1600 W North Ave", { number: "1600", street: "W North Ave" }],
  ["1600 W North Ave Apt 2, Chicago", { number: "1600", street: "W North Ave" }],
  ["1600 W North Ave Chicago IL", { number: "1600", street: "W North Ave Chicago IL" }],
  ["S5975 Park Rd", { number: "S5975", street: "Park Rd" }],
  ["2nd St, Chicago", null],
  ["Starved Rock Lodge", null],
];
for (const [address, want] of streets) {
  const got = api.addressStreet(address);
  if (JSON.stringify(got) !== JSON.stringify(want)) {
    failed++;
    console.error("map-link: FAIL addressStreet(" + JSON.stringify(address) + ")\n  want " + JSON.stringify(want) + "\n  got  " + JSON.stringify(got));
  }
}

// An answer is on the address's street when one part names the same street,
// abbreviated, and another is its town or ZIP code. The Westmont labels are
// the six streets Photon answered on 2026-10-14 for the address of a place
// Adam shared from the Google Maps app, on W Oakley Dr NW (its house number
// is not repeated here), and only one of them is that street.
const OAKLEY = "9 W Oakley Dr NW, Westmont, IL 60559";
const street = [
  ["West Oakley Drive Northwest, Westmont, Illinois, 60559", OAKLEY, true],
  ["Oakley Drive North, Westmont, Illinois, 60559", OAKLEY, false],
  ["Oakley Drive South, Westmont, Illinois, 60559", OAKLEY, false],
  ["Oakley Drive West, Westmont, Illinois, 60559", OAKLEY, false],
  ["Oakley Drive Southwest, Westmont, Illinois, 60559", OAKLEY, false],
  ["West Oakley Drive Northwest, Westmont, Illinois", OAKLEY, true],                 // the town alone
  ["West Oakley Drive Northwest, DuPage County, Illinois, 60559", OAKLEY, true],    // the ZIP code alone
  ["West Oakley Drive Northwest, Downers Grove, Illinois, 60515", OAKLEY, false],   // another town's street
  ["28 West Oakley Drive Northwest, Westmont, Illinois, 60559", OAKLEY, true],      // another number on it
  ["Joe's, 40 West Oakley Drive Northwest, Westmont, Illinois, 60559", OAKLEY, true],
  ["Oakley Drive, Westmont, Illinois, 60559", OAKLEY, true],                        // its directions left off
  ["East Oakley Drive Northwest, Westmont, Illinois, 60559", OAKLEY, false],
  ["West 3rd Street, Oglesby, Illinois", "2668 E 875th Rd, Oglesby, IL 61348", false],
  ["East 875th Road, Oglesby, Illinois, 61348", "2668 E 875th Rd, Oglesby, IL 61348", true],
  ["West North Avenue, Chicago, Illinois, 60622", "1600 North Ave, Chicago, IL 60622", true],
  ["North Avenue, Chicago, Illinois", "1600 W North Ave, Chicago, IL 60622", true],  // a street named North
  ["North Avenue, Chicago, Illinois", "1600 W Ave, Chicago, IL 60622", false],
  ["North Northwest Highway, Chicago, Illinois", "5555 N Northwest Hwy, Chicago, IL 60630", true],
  ["West Oakley Drive Northwest, Westmont, Illinois, 60559", "Oakley Cake Shop", false],    // a name, no address
  ["Park Road, Baraboo, Wisconsin, 53913", "S5975 Park Rd, Baraboo, WI 53913", true],
  ["S5975 Park Road, Baraboo, Wisconsin", "S5975 Park Rd, Baraboo, WI 53913", true],       // its grid number left off
  // the Census Bureau writes every street type as the Postal Service does,
  // as in its answers of 2026-10-19 (the house numbers are made up)
  ["9 ARROWHEAD TRCE, OAK FOREST, IL, 60452", "9 Arrowhead Trace, Oak Forest, IL", true],
  ["Arrowhead Trace, Oak Forest, Illinois, 60452", "9 Arrowhead Trce, Oak Forest, IL 60452", true],
  ["9 ARROWHEAD TRL, OAK FOREST, IL, 60452", "9 Arrowhead Trace, Oak Forest, IL", false],   // a trail is not a trace
  ["Spring Crossing, Elgin, Illinois", "1 Spring Xing, Elgin, IL", true],
  ["Parks Road, Baraboo, Wisconsin, 53913", "S5975 Park Rd, Baraboo, WI 53913", false],   // a plural is another name
];
for (const [label, address, want] of street) {
  const got = api.labelOnStreet(label, address);
  if (got !== want) {
    failed++;
    console.error("map-link: FAIL labelOnStreet(" + JSON.stringify(label) + ", " + JSON.stringify(address) + ")\n  want " + want + "\n  got  " + got);
  }
}

// An address typed with no town, or with a town and no comma before it, is
// put in the town of an answer on its street, read from the answer's label,
// the part before a state's name; an address that names a town keeps it,
// and a ZIP code typed with it is kept too, for the Census Bureau's lookup.
// The labels are in the shape the apps build from Photon (photonLabel).
const WICKER = "West North Avenue, Wicker Park, Chicago, Illinois, 60622";
const MELROSE = "West North Avenue, Melrose Park, Illinois, 60160";
const EUGENIE = "West Eugenie Street, Lincoln Park, North Chicago Township, Illinois, 60614";
const inTown = [
  ["1600 W North Ave", WICKER, "1600 W North Ave, Chicago, IL"],
  ["1600 W North Ave", MELROSE, "1600 W North Ave, Melrose Park, IL"],
  ["1600 West North Avenue", WICKER, "1600 West North Avenue, Chicago, IL"],
  ["1600 W North Ave Chicago", WICKER, "1600 W North Ave, Chicago, IL"],
  ["1600 W North Ave chicago il", WICKER, "1600 W North Ave, Chicago, IL"],
  ["1600 W North Ave Chicago", MELROSE, null],                 // the town typed is another
  ["1600 W North Ave Melrose Park", WICKER, null],
  ["1600 W North Ave, Chicago, IL 60622", WICKER, "1600 W North Ave, Chicago, IL 60622"],
  ["1600 W North Ave Chicago IL 60622", WICKER, "1600 W North Ave, Chicago, IL 60622"],   // a ZIP code with no comma
  ["1600 W North Ave, Chicago, IL 60622-4321", WICKER, "1600 W North Ave, Chicago, IL 60622"],
  ["1600 W North Ave, Wicker Park", WICKER, "1600 W North Ave, Chicago, IL"],   // a neighbourhood the label names
  ["1600 W North Ave, Chicago", MELROSE, null],
  ["1600 W North Ave Apt 2", WICKER, "1600 W North Ave, Chicago, IL"],
  ["1600 E North Ave", WICKER, null],                          // two different directions
  ["1600 W North Ave", "North Avenue, Chicago, Illinois", "1600 W North Ave, Chicago, IL"],  // a direction left off
  ["1600 W North Ave", "West Division Street, Chicago, Illinois", null],                     // another street
  ["1600 W North Ave", "West North Avenue, Wicker Park, Chicago", null],                     // no state named
  ["1600 W North Ave", "1600 West North Avenue, Chicago, Illinois", "1600 W North Ave, Chicago, IL"],
  ["S5975 Park Rd", "Park Road, Baraboo, Wisconsin, 53913", "S5975 Park Rd, Baraboo, WI"],
  ["Starved Rock Lodge", WICKER, null],
  // Photon names the Cook County township where Chicago's name would be
  // (2026-10-19); an address that names no town takes it, as it did before,
  // with the ZIP code typed, with which the Census Bureau's lookup found the
  // Lincoln Park Zoo under the township's name. The house numbers here are
  // made up.
  ["9 W Eugenie St", EUGENIE, "9 W Eugenie St, North Chicago Township, IL"],
  ["9 W Eugenie St, IL 60614", EUGENIE, "9 W Eugenie St, North Chicago Township, IL 60614"],
  ["9 Kemman Ave, La Grange Park, IL 60526", "Kemman Avenue, La Grange Park, Illinois, 60526", "9 Kemman Ave, La Grange Park, IL 60526"],
];
// An address that names a town the answer is in only by its ZIP code keeps
// that town, so the Census Bureau's lookup is asked about the address as it
// was typed, and its answer is then on the street of what it was asked about
// (ENGINE geocoder-search lookupAddressRanges). Answers that name the city,
// the township or a town that shares the ZIP code then give one address, not
// two towns to pick from. These are left out of the check below, because the
// label they are read from names neither the town nor a ZIP code it carries.
const kept = [
  ["9 W Eugenie St, Chicago, IL 60614", EUGENIE, "9 W Eugenie St, Chicago, IL 60614", "9 W EUGENIE ST, CHICAGO, IL, 60614"],
  ["9 W Eugenie St, Chicago IL 60614", EUGENIE, "9 W Eugenie St, Chicago, IL 60614", "9 W EUGENIE ST, CHICAGO, IL, 60614"],
  ["9 N Orchard St, Chicago, IL 60614", "North Orchard Street, Lincoln Park, North Chicago Township, Illinois, 60614",
    "9 N Orchard St, Chicago, IL 60614", "9 N ORCHARD ST, CHICAGO, IL, 60614"],
  ["9 Kemman Ave, La Grange Park, IL 60526", "North Kemman Avenue, La Grange, Illinois, 60526",
    "9 Kemman Ave, La Grange Park, IL 60526", "9 KEMMAN AVE, LA GRANGE PARK, IL, 60526"],
];
for (const [address, label, want, census] of kept) {
  const got = api.addressInTownOf(address, label);
  if (got !== want) {
    failed++;
    console.error("map-link: FAIL addressInTownOf(" + JSON.stringify(address) + ", " + JSON.stringify(label) + ")\n  want " + JSON.stringify(want) + "\n  got  " + JSON.stringify(got));
  } else if (!api.labelOnStreet(census, got) || !api.labelAtHouse(census, got)) {
    failed++;
    console.error("map-link: FAIL the Census answer " + JSON.stringify(census) + " is not at " + JSON.stringify(got));
  }
}
// an answer naming the city and one naming its township give one address
const ORCHARD = "9 N Orchard St, Chicago, IL 60614";
const fromCity = api.addressInTownOf(ORCHARD, "North Orchard Street, Lincoln Park, Chicago, Illinois, 60614");
const fromTownship = api.addressInTownOf(ORCHARD, "North Orchard Street, Lincoln Park, North Chicago Township, Illinois, 60614");
if (!fromCity || fromCity !== fromTownship) {
  failed++;
  console.error("map-link: FAIL answers naming Chicago and its township put " + ORCHARD + " at " + JSON.stringify(fromCity) + " and " + JSON.stringify(fromTownship));
}
for (const [address, label, want] of inTown) {
  const got = api.addressInTownOf(address, label);
  if (got !== want) {
    failed++;
    console.error("map-link: FAIL addressInTownOf(" + JSON.stringify(address) + ", " + JSON.stringify(label) + ")\n  want " + JSON.stringify(want) + "\n  got  " + JSON.stringify(got));
  }
}
// What addressInTownOf gives is an address addressParts and labelOnStreet read
for (const [address, label, want] of inTown) {
  if (!want) continue;
  if (!api.addressParts(want) || !api.labelOnStreet(label, want)) {
    failed++;
    console.error("map-link: FAIL addressInTownOf(" + JSON.stringify(address) + ") gave " + JSON.stringify(want) + ", which labelOnStreet does not put on " + JSON.stringify(label));
  }
}
// An address the map's search cannot place, nor find its street, is asked
// about as the lookup is asked about every other (ENGINE geocoder-search
// showStreetOnly): the number and the street, the town, the state and the
// ZIP code, each after a comma, with the app's own state when the address
// names none. The house numbers here are made up.
const forLookup = [
  ["9 W Oakley Dr NW, Westmont", "il", "9 W Oakley Dr NW, Westmont, IL"],
  ["9 W Oakley Dr NW, Westmont, IL 60559", "il", "9 W Oakley Dr NW, Westmont, IL 60559"],
  ["9 W Oakley Dr NW, Westmont IL 60559", "il", "9 W Oakley Dr NW, Westmont, IL 60559"],  // no comma after the town
  ["9 W Oakley Dr NW, Westmont il", "il", "9 W Oakley Dr NW, Westmont, IL"],
  ["9 W Oakley Dr NW, Westmont, il", "wi", "9 W Oakley Dr NW, Westmont, IL"],            // the reader's state, not the app's
  ["9 W Oakley Dr NW, Westmont, Illinois 60559", "wi", "9 W Oakley Dr NW, Westmont, IL 60559"],
  ["9 W Oakley Dr NW, Westmont 60559", "il", "9 W Oakley Dr NW, Westmont, IL 60559"],
  ["9 W Oakley Dr NW, 60559", "il", "9 W Oakley Dr NW, IL 60559"],
  ["9 W Oakley Dr NW, IL 60559", "wi", "9 W Oakley Dr NW, IL 60559"],
  ["9 W Oakley Dr NW Apt 2, Westmont", "il", "9 W Oakley Dr NW, Westmont, IL"],          // a unit left off
  ["9 S 4th St, Oregon", "il", "9 S 4th St, Oregon, IL"],                              // a town named for a state
  ["9 S 4th St, Oregon, IL 61061", "il", "9 S 4th St, Oregon, IL 61061"],
  ["9 Franklin St, Port Washington", "wi", "9 Franklin St, Port Washington, WI"],
  ["9 Main St, IL", "il", null],                                                       // no town and no ZIP code
  ["9 W Oakley Dr NW", "il", null],
  ["Starved Rock Lodge, Oglesby", "il", null],
  ["9 W Oakley Dr NW, Westmont", "", null],                                            // no state to write
];
for (const [address, tag, want] of forLookup) {
  const got = api.addressForLookup(address, tag);
  if (got !== want) {
    failed++;
    console.error("map-link: FAIL addressForLookup(" + JSON.stringify(address) + ", " + JSON.stringify(tag) + ")\n  want " + JSON.stringify(want) + "\n  got  " + JSON.stringify(got));
  } else if (want && (!api.addressParts(want) || api.addressForLookup(want, "") !== want)) {
    // what it writes is an address it reads back as itself
    failed++;
    console.error("map-link: FAIL addressForLookup(" + JSON.stringify(address) + ") gave " + JSON.stringify(want) + ", which it does not read back as itself");
  }
}
for (const [name, want] of [["Wisconsin", "wi"], ["  new   york ", "ny"], ["District of Columbia", "dc"], ["IL", ""], ["Chicago", ""]]) {
  const got = api.stateTagOfName(name);
  if (got !== want) {
    failed++;
    console.error("map-link: FAIL stateTagOfName(" + JSON.stringify(name) + ")\n  want " + JSON.stringify(want) + "\n  got  " + JSON.stringify(got));
  }
}

// The state a place's address names, read from its end: a postal code in
// capitals or before a ZIP code, or a state's name. A link to a place in
// another state is that state's app's to search (ENGINE geocoder-search
// showLinkElsewhere, and the front door's namedState).
const states = [
  ["Devil's Lake State Park, S5975 Park Rd, Baraboo, WI 53913", "wi"],
  ["Cozy Dog Drive In, 2935 S 6th St, Springfield, IL 62703, United States", "il"],
  ["Lambeau Field, 1265 Lombardi Ave, Green Bay, WI 54304, USA", "wi"],
  ["Wisconsin Dells Inn, 1 Main St, Rockford, IL 61101", "il"],     // only the end is read
  ["A Place, 1 Main St, Baraboo, Wisconsin", "wi"],
  ["A Place, 1 Main St, Grand Rapids, Michigan 49503", "mi"],
  ["The White House, 1600 Pennsylvania Ave NW, Washington, DC 20500", "dc"],
  ["Union Terminal, 1301 Western Ave, Cincinnati, OH 45203", "oh"],
  ["Queens Library, 89-11 Merrick Blvd, Jamaica, NY 11432", "ny"],
  ["Monument Circle, Indianapolis, IN 46204", "in"],
  ["A Place, 5 Main St, Juneau, ak 99801", "ak"],                   // lower case before a ZIP code
  ["Starved Rock Lodge, Oglesby, il", ""],                           // lower case alone: a word, maybe
  ["Daley Plaza", ""],
  ["Lake Michigan", ""],
  ["Come on in", ""],
  ["CN Tower, 290 Bremner Blvd, Toronto, ON M5V 3L9, Canada", ""],
];
for (const [text, want] of states) {
  const got = api.addressStateTag(text);
  if (got !== want) {
    failed++;
    console.error("map-link: FAIL addressStateTag(" + JSON.stringify(text) + ")\n  want " + JSON.stringify(want) + "\n  got  " + JSON.stringify(got));
  }
}
for (const [tag, want] of [["oh", "Ohio"], ["dc", "the District of Columbia"], ["wi", "Wisconsin"]]) {
  if (api.stateInSentence(tag) !== want) {
    failed++; console.error("map-link: FAIL stateInSentence(" + tag + ") reads " + JSON.stringify(api.stateInSentence(tag)));
  }
}

// A link handed to another app is rebuilt from its words, and that app's
// parser reads it back as the same words from the same maker, punctuation at
// the end included, alone or inside the words a share puts around it.
const rebuilt = [
  ["Devil's Lake State Park, S5975 Park Rd, Baraboo, WI 53913", "google"],
  ["A+B Hardware & Co, 12 Main St #4, Peoria, IL 61602", "apple"],
  ["Caf\u00e9 Lulu, 1 1st Ave, Rockford, Illinois 61101", "google"],
  ["Joe's Diner (Main St)", "google"],
  ["Yum!", "apple"],
  ["Acme Inc.,", "google"],
];
for (const [text, source] of rebuilt) {
  const url = api.mapLinkForText({ text, source });
  for (const pasted of [url, "Shared from a phone\n" + url]) {
    const got = api.parseMapLink(pasted);
    if (!got || got.kind !== "text" || got.source !== source || got.text !== text) {
      failed++;
      console.error("map-link: FAIL mapLinkForText(" + JSON.stringify(text) + ") = " + JSON.stringify(url) + " reads back as " + JSON.stringify(got));
    }
  }
}

// A ZIP code typed alone, with "ZIP" before it or a state beside it, is a
// search for the whole ZIP code (ENGINE geocoder-search runZipSearch, and the
// front door's address box); typed with a town or a street it is an address,
// searched as before.
const zips = [
  ["60625", "60625"],
  [" 60625 ", "60625"],
  ["ZIP 60625", "60625"],
  ["zip code 60625", "60625"],
  ["Zipcode 60625", "60625"],
  ["postal code 60625", "60625"],
  ["IL 60625", "60625"],
  ["60625 IL", "60625"],
  ["60625, Illinois", "60625"],
  ["Illinois 60625", "60625"],
  ["new york 10001", "10001"],
  ["10001 New York", "10001"],
  ["in 46204", "46204"],
  ["60625-1234", "60625"],
  ["60625 USA", "60625"],
  ["60625, IL, USA", "60625"],
  ["60625 united states of america", "60625"],
  ["60625 chicago", ""],          // a town makes it an address
  ["Chicago, IL 60625", ""],
  ["123 Main St 60625", ""],
  ["21001 S Wolf Rd", ""],        // a house number is not a ZIP code
  ["district 60625", ""],
  ["us 60625", ""],
  ["606250", ""],
  ["6062", ""],
  ["zip", ""],
];
for (const [text, want] of zips) {
  const got = api.zipQuery(text);
  if (got !== want) {
    failed++;
    console.error("map-link: FAIL zipQuery(" + JSON.stringify(text) + ")\n  want " + JSON.stringify(want) + "\n  got  " + JSON.stringify(got));
  }
}
// fleet-zips.json lists each app's ZIP codes as one string of five-digit
// codes in order (scripts/build_zip_index.mjs), and zipListed finds one in it
// by halving: every code listed is found, and none between or beyond them.
const LISTED = ["00501", "10001", "53703", "60625", "60626", "70112", "99950"];
const listed = LISTED.map((zip) => [LISTED.join(""), zip, true]).concat(
  ["00500", "10000", "53704", "60624", "60627", "99951"].map((zip) => [LISTED.join(""), zip, false]),
  [["", "60625", false], ["60625", "60625", true], ["60625", "60626", false]]);
for (const [codes, zip, want] of listed) {
  if (api.zipListed(codes, zip) !== want) {
    failed++;
    console.error("map-link: FAIL zipListed(" + JSON.stringify(codes) + ", " + JSON.stringify(zip) + ") reads " + !want);
  }
}

const total = cases.length + 2 + lookups.length + 2 + said.length + bare.length + carry.length + house.length + parts.length + street.length +
  kept.length + 1 + forLookup.length + states.length + 3 + rebuilt.length * 2 +
  zips.length + listed.length;
if (failed) { console.error("map-link: " + failed + " of " + total + " checks failed"); process.exit(1); }
console.log("map-link: OK — " + cases.length + " pasted texts read as expected; a short link is sent only to the lookup; " +
  lookups.length + " lookup answers tried again or not as expected, a cancelled lookup stops, and " + said.length +
  " short-link messages say which side failed; " +
  bare.length + " place names split from their addresses as expected; " + carry.length +
  " answers held to the address's house number and " + house.length + " to the house itself as expected; " + parts.length + " addresses split into their parts, " +
  streets.length + " into a number and a street, and " + street.length + " answers held to the address's street as expected; " +
  inTown.length + " addresses put in an answer's town and " + kept.length + " kept in the town typed as expected; " +
  forLookup.length + " written out for the Census lookup as expected; " + states.length +
  " addresses read for their state, " + rebuilt.length + " links rebuilt from their words, " + zips.length +
  " searches read for a ZIP code and " + listed.length + " ZIP codes looked for in a list as expected");
