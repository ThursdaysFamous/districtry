// Holds engine/shared/map-link.txt, AS SHIPPED, to the links a reader pastes.
//
// The block reads Google Maps and Apple Maps links in the browser
// (parseMapLink), and every app and the front door run this one copy, so a
// case here is a case in thirteen apps at once. Node runs it with no browser:
// the block uses only URL and String, which Node provides.
//
// The links below were written in the shapes Google and Apple publish and
// that the two apps' share buttons produce; none carries a real person's
// location. A short link is recognised and never followed: following one is
// the lookup's job (services/link-lookup/main.ts).
//
//   node scripts/map_link_test.mjs
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const src = readFileSync(path.join(root, "engine/shared/map-link.txt"), "utf8");
const api = new Function(src + "\nreturn { parseMapLink, mapLinkMessage, resolveShortMapLink };")();

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

// With no lookup configured, a short link is never sent anywhere.
let sent = false;
globalThis.fetch = () => { sent = true; return Promise.reject(new Error("fetch")); };
await api.resolveShortMapLink({ kind: "short", url: "https://maps.app.goo.gl/x", source: "google" })
  .then(() => { failed++; console.error("map-link: FAIL a short link resolved with no lookup configured"); }, () => {});
if (sent) { failed++; console.error("map-link: FAIL a short link was sent with no lookup configured"); }
if (!/Short Google Maps links/.test(api.mapLinkMessage({ kind: "short", source: "google" }))) {
  failed++; console.error("map-link: FAIL the short-link message does not name Google Maps");
}

if (failed) { console.error("map-link: " + failed + " of " + (cases.length + 2) + " checks failed"); process.exit(1); }
console.log("map-link: OK — " + cases.length + " pasted texts read as expected; no short link is sent without a lookup");
