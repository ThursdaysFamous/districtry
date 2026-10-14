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
const api = new Function(src + "\nreturn { parseMapLink, mapLinkMessage, resolveShortMapLink, addressAfterName, labelCarriesNumber };")();

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
// A lookup that answers with another short link, or fails, is a rejection.
for (const answer of [{ ok: true, json: () => Promise.resolve({ url: SHORT }) }, { ok: false, status: 502 }]) {
  globalThis.fetch = () => Promise.resolve(answer);
  await api.resolveShortMapLink({ kind: "short", url: SHORT, source: "google" })
    .then(() => { failed++; console.error("map-link: FAIL a lookup answering " + JSON.stringify(answer.status || "a short link") + " resolved"); }, () => {});
}
if (!/short Google Maps link/.test(api.mapLinkMessage({ kind: "short", source: "google" }))) {
  failed++; console.error("map-link: FAIL the short-link message does not name Google Maps");
}

// The address behind a place's name: tried alone when the whole string
// matches nothing. Anything that does not open with words and then reach a
// house number after a comma is left alone.
const bare = [
  ["Starved Rock Lodge, 2668 E 875th Rd, Oglesby, IL 61348", "2668 E 875th Rd, Oglesby, IL 61348"],
  ["Cozy Dog Drive In, 2935 S 6th St, Springfield, IL 62703, United States", "2935 S 6th St, Springfield, IL 62703, United States"],
  ["Joe's, Suite 4, 100 Main St, Peoria, IL", "100 Main St, Peoria, IL"],
  ["Queens Library, 89-11 Merrick Blvd, Jamaica, NY 11432", "89-11 Merrick Blvd, Jamaica, NY 11432"],
  ["233 S Wacker Dr, Chicago, IL 60606", null],          // already an address
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

const total = cases.length + 5 + bare.length + carry.length;
if (failed) { console.error("map-link: " + failed + " of " + total + " checks failed"); process.exit(1); }
console.log("map-link: OK — " + cases.length + " pasted texts read as expected; a short link is sent only to the lookup; " +
  bare.length + " place names split from their addresses as expected; " + carry.length +
  " answers held to the address's house number as expected");
