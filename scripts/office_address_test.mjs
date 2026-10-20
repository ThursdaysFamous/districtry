// Holds engine/index.html/office-helpers.txt, AS SHIPPED, to the district
// offices the legislator cards drop a map pin on, and since 2026-10-20 the
// address tidy-up in engine/index.html/poi-geocode.txt that runs on the way to
// the map service (cleanPoiAddress).
//
// officeAddressForGeocode turns a roster's districtOffice lines into the one
// address the pin is looked up by, in every app that names a legislator. Until
// 2026-10-20 it dropped any line that merely CONTAINED something phone-like,
// so a ZIP+4 city line went ("Fort Smith, AR 72903-5083" holds "903-5083") and
// so did a street named Katella or Kattelville ("tel"): measured that day, 8 of
// the 693 district offices the apps shipped were looked up with no city or
// with their telephone numbers, and nothing had ever run the function.
//
// Two parts. The first holds it to exact answers: the 8 offices that broke,
// the shapes the Louisiana legislature publishes (headings, a post office box
// first, three offices in one block), and the near-misses a looser rule would
// trip on. The second runs it over every district office every app ships
// today and asks the two questions that broke: is the address free of
// telephone numbers, and does it end with the block's own city and ZIP line
// wherever the block has one. A weekly roster refresh that brings a new shape
// fails here, on its own pull request, rather than on a reader's map.
//
// The tidy-up removes suites, rooms and boxes before the lookup, and on the
// same day it was found removing more: seven New York offices name their
// building before the street ("Dulles State Office Building 317 Washington
// St."), and the rule for "Building 3" read the house number as a building
// number and removed it, so Senate 49 was looked up as "Dulles State Office
// Washington St., Watertown"; "Post Office Box 188" and "P.O. Box I" stayed in
// two Illinois lookups. So the whole lookup is held too: to exact answers, and
// over every shipped office, to keeping the address's numbered street and
// dropping a box that follows a street.
//
//   node scripts/office_address_test.mjs
import { readFileSync, readdirSync, existsSync, statSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const src = readFileSync(path.join(root, "engine/index.html/office-helpers.txt"), "utf8");
const poiSrc = readFileSync(path.join(root, "engine/index.html/poi-geocode.txt"), "utf8");
// officeFieldHtml, in the same block, calls sanitize only when it runs, and
// the geocode queue in the second calls the app's provider only when it runs.
const { officeAddressForGeocode, cleanPoiAddress } =
  new Function(src + "\n" + poiSrc + "\nreturn { officeAddressForGeocode, cleanPoiAddress };")();

let failed = 0;
function fail(msg) {
  failed++;
  console.error("office-address: FAIL " + msg);
}

const cases = [
  // The 8 shipped offices that broke, exactly as their rosters carried them.
  // A ZIP+4 city line was read as a telephone number and dropped.
  [["6101 Phoenix Ave, Suite 4", "Fort Smith, AR 72903-5083", "Phone: 479-424-1146"],
    "6101 Phoenix Ave, Suite 4, Fort Smith, AR 72903-5083"],
  [["355 S Washington St, Suite 210", "Danville, IN 46122-1779", "Phone: 317-563-5567"],
    "355 S Washington St, Suite 210, Danville, IN 46122-1779"],
  [["501 Laurel St", "Brainerd City Hall", "Brainerd, MN 56401-3595", "Phone: 218-355-0862"],
    "501 Laurel St, Brainerd City Hall, Brainerd, MN 56401-3595"],
  [["800 Market St, Suite 110", "Knoxville, TN 37902-2327", "Phone: 865-523-3772"],
    "800 Market St, Suite 110, Knoxville, TN 37902-2327"],
  [["355 N Belvedere Dr, Suite 308", "Gallatin, TN 37066-5466", "Phone: 615-206-8204"],
    "355 N Belvedere Dr, Suite 308, Gallatin, TN 37066-5466"],
  [["20 S Main St, Suite 10", "Janesville, WI 53545-3959", "Phone: 608-752-4050"],
    "20 S Main St, Suite 10, Janesville, WI 53545-3959"],
  // "tel" inside a street name dropped the whole address, and the fallback
  // looked up every line, the telephone numbers included.
  [["2400 E. Katella Ave., Suite 640, Anaheim, CA 92806", "Phone: 714-939-8469"],
    "2400 E. Katella Ave., Suite 640, Anaheim, CA 92806"],
  [["1 Kattelville Road Suite 1, Binghamton, NY 13901", "Phone: 607-648-6080", "Fax: 607-648-6089"],
    "1 Kattelville Road Suite 1, Binghamton, NY 13901"],

  // The Louisiana legislature's blocks, as its members' pages publish them.
  [["Physical Address:", "101 Milam Street", "Suite 100", "Shreveport, LA 71101", "Mailing Address:", "P. O. Box 2113", "Shreveport, LA 71166", "(318) 676-7747"],
    "101 Milam Street, Suite 100, Shreveport, LA 71101"],
  [["Physical Address:", "181 Barron Road", "Pollock, LA 71467-3643", "Mailing Address:", "P. O. Box 640", "Pollock, LA 71467", "(318) 765-9606"],
    "181 Barron Road, Pollock, LA 71467-3643"],
  // the box first: the street address after it is the office
  [["P. O. Box 51499", "Lafayette, LA 70505", "Physical Address:", "1438 South College", "Lafayette, LA 70503", "(337)295-1765"],
    "1438 South College, Lafayette, LA 70503"],
  [["P.O. Box 660", "Harrisonburg, LA 71340", "119 Pine Street", "Suite B", "Harrisonburg, LA 71340", "(318)744-0005"],
    "119 Pine Street, Suite B, Harrisonburg, LA 71340"],
  // three offices in one block: the first is the one pinned
  [["1206 South 5th Street", "Leesville, LA 71446", "218 West 4th Street", "DeQuincy, LA 70633", "401 West 1st Street", "DeRidder, LA 70634", "(337)238-6435"],
    "1206 South 5th Street, Leesville, LA 71446"],
  [["943 Washington Street", "Franklinton, LA 70438", "2nd District Office:", "748 Avenue F,", "Bogalusa, LA 70427", "(985) 515-1020"],
    "943 Washington Street, Franklinton, LA 70438"],
  // the state written out and the ZIP on a line of its own
  [["700 N. 10th Street", "Baton Rouge, Louisiana", "70802", "(225) 256-0850"],
    "700 N. 10th Street, Baton Rouge, Louisiana, 70802"],
  // a note after the address is not part of it
  [["6387 Jefferson Highway", "Harahan, LA 70123", "*Not ADA accessible. Please call to make accommodations.", "(504) 737-0315"],
    "6387 Jefferson Highway, Harahan, LA 70123"],
  // only a box: kept, because it is all the block gives (a five-digit box
  // number is not a ZIP code, so the city line stays with it)
  [["P.O. Box 91245", "Lafayette, LA 70509", "(337)267-7520"],
    "P.O. Box 91245, Lafayette, LA 70509"],
  [["9 Main Street", "West Monroe, La 71291", "(318) 555-0100"],
    "9 Main Street, West Monroe, La 71291"],
  // a heading ends the address before it, ZIP or not
  [["9 W. Park Ave.", "Ruston, LA", "Mailing Address:", "P.O. Box 9", "Ruston, LA 71273", "(318) 555-0100"],
    "9 W. Park Ave., Ruston, LA"],

  // Shapes the apps already ship, which must read as they always did.
  [["6117 West Cermak Road", "Cicero, IL 60804", "(708) 222-5240", "(708) 222-5241 Fax"],
    "6117 West Cermak Road, Cicero, IL 60804"],
  [["185-06 Union Turnpike, Fresh Meadows, NY 11366", "Phone: 718-454-3027", "Fax: 718-454-3178",
    "Also: Room 5, 111-12 Atlantic Ave., Richmond Hill, NY 11419 · Phone: 718-805-2381"],
    "185-06 Union Turnpike, Fresh Meadows, NY 11366"],
  [["242-09 Northern Boulevard", "Douglaston, NY 11363", "Phone: 718-631-0400"],
    "242-09 Northern Boulevard, Douglaston, NY 11363"],
  [["275 N. Division St.", "PO Box 173", "Woodhull, IL 61490", "(309) 334-7474", "(309) 334-8000 Fax"],
    "275 N. Division St., PO Box 173, Woodhull, IL 61490"],
  [["2300 W Main St", "Suite M200", "Belleville, 62226", "(618) 416-7407"],
    "2300 W Main St, Suite M200, Belleville, 62226"],
  // no ZIP anywhere: the address lines, joined as before
  [["3465 Camino del Rio S, 350", "San Diego, CA", "Phone: 619-280-5353"],
    "3465 Camino del Rio S, 350, San Diego, CA"],

  // Near-misses a looser rule trips on.
  // a city named Mobile is not a mobile number
  [["9 Government St", "Mobile, AL 36602", "Phone: 251-555-0100"],
    "9 Government St, Mobile, AL 36602"],
  // a five-digit suite is not a ZIP code
  [["455 Golden Gate Ave. Suite 14800", "San Francisco, CA 94102", "Phone: 415-555-0100"],
    "455 Golden Gate Ave. Suite 14800, San Francisco, CA 94102"],
  // nothing but a telephone number: no pin, rather than a lookup of the number
  [["Phone: 217-555-0100"], null],
  [["(217) 555-0100", "(217) 555-0101 Fax"], null],
  [[], null],
  // no number anywhere, so no place a pin could go: Illinois House 13 and
  // Wisconsin Senate 6, as their rosters carry them
  [["By appointment only", "(773) 657-4655"], null],
  [["WI", "Phone: 414-313-1241"], null],
];

for (const [lines, want] of cases) {
  const got = officeAddressForGeocode(lines);
  if (got !== want) fail(JSON.stringify(lines) + "\n  want " + JSON.stringify(want) + "\n  got  " + JSON.stringify(got));
}
if (officeAddressForGeocode(null) !== null) fail("officeAddressForGeocode(null) is not null");

// The whole lookup, office lines to the string the map service is asked.
const lookups = [
  // A building or floor named before the street: the number after it is the
  // house number. New York Senate 49, 50, 52, 4 and 30 and Assembly 123 and
  // 150, as their rosters carry them.
  [["Dulles State Office Building 317 Washington St., Suite 418, Watertown, NY 13601", "Phone: 315-782-3418",
    "Also: Fulton County Office Building 223 W. Main St., Suite B10, Johnstown, NY 12095 · Phone: 518-762-3733"],
    "317 Washington St., Watertown, NY 13601"],
  [["Oswego City Hall, Second Floor 13 W. Oneida St., Oswego, NY 13126",
    "Also: Room 800, State Office Building 333 E. Washington St., Syracuse, NY 13202 · Phone: 315-428-7632"],
    "13 W. Oneida St., Oswego, NY 13126"],
  [["1607 State Office Building 44 Hawley St., Binghamton, NY 13901", "Phone: 607-773-8771"],
    "44 Hawley St., Binghamton, NY 13901"],
  [["Room 3B-41-42, Hauppauge State Office Building 250 Veterans Highway, Hauppauge, NY 11788", "Phone: 631-341-7111"],
    "250 Veterans Highway, Hauppauge, NY 11788"],
  [["Adam Clayton Powell, Jr. State Office Building 163 W. 125th St., Suite 912, New York, NY 10027", "Phone: 212-222-7315"],
    "163 W. 125th St., New York, NY 10027"],
  [["State Office Building, 17th Floor 44 Hawley St., Binghamton, NY 13901", "Phone: 607-723-9047"],
    "44 Hawley St., Binghamton, NY 13901"],
  [["Fenton Building 2 E. 2nd St., Suite 320, Jamestown, NY 14701", "Phone: 716-664-7773"],
    "2 E. 2nd St., Jamestown, NY 14701"],
  // A box after the street, spelled out or lettered: Illinois House 102 and 110.
  [["100 Norb Avenue, Suite 1", "Post Office Box 188", "Dieterich, IL 62424", "(217) 813-6036"],
    "100 Norb Avenue, Dieterich, IL 62424"],
  [["152 South Church Street", "P.O. Box I", "Louisville, IL 62858", "(618) 665-4109"],
    "152 South Church Street, Louisville, IL 62858"],
  // A building AFTER the street is a unit and goes; so does a box with no street.
  [["28 Wells Ave., Building 3 5th Floor, Yonkers, NY 10701", "Phone: 914-423-4031"],
    "28 Wells Ave., Yonkers, NY 10701"],
  [["13405 Folsom Blvd., Building 700 Suite A, Folsom, CA 95630", "Phone: 916-294-9774"],
    "13405 Folsom Blvd., Folsom, CA 95630"],
  [["3245 Route 112 Building 2, Suite 6, Medford, NY 11763", "Phone: 631-207-0073"],
    "3245 Route 112, Medford, NY 11763"],
  [["P.O. Box 91245", "Lafayette, LA 70509", "(337)267-7520"],
    "P.O. Box 91245, Lafayette, LA 70509"],
];
for (const [lines, want] of lookups) {
  const address = officeAddressForGeocode(lines);
  const got = address && cleanPoiAddress(address);
  if (got !== want) fail("lookup " + JSON.stringify(lines) + "\n  want " + JSON.stringify(want) + "\n  got  " + JSON.stringify(got));
}

// Every district office every app ships. An instance is a top-level folder
// with an index.html and a data/app/, the rule the registration gate
// discovers by, so a new state's rosters are read the day they land.
const PHONE = /(?:\(\d{3}\)\s*|\b\d{3}[-.])\d{3}[-.]\d{4}\b|\b(?:phone|fax|e-?mail)\s*:/i;
const CITY_LINE = /\b[A-Z]{2}\s+\d{5}(?:-\d{4})?\s*$/;
// a house number and the street it is on: "317 Washington St", "2-6 E. 2nd St"
const NUMBERED_STREET = new RegExp("(?:^|[\\s,])(\\d+[a-z]?(?:-\\d+[a-z]?)?\\s+(?:[nsew]\\.?\\s+)?" +
  "(?:[a-z0-9][a-z0-9'.-]*\\s+){0,3}(?:street|st|avenue|ave|road|rd|boulevard|blvd|drive|dr|lane|ln|place|pl|" +
  "court|ct|highway|hwy|parkway|pkwy|terrace|ter|circle|cir|square|sq|trail|trl|way|turnpike|tpke|plaza|plz))\\b", "i");
const BOX_AFTER_STREET = /\S[,\s]+\(?\s*(?:p\.?\s*o\.?|post\s+office)\s*box\b/i;
const apps = new Set();
let offices = 0;
let withCity = 0;
let numbered = 0;
for (const tag of readdirSync(root).sort()) {
  const dir = path.join(root, tag, "data", "app");
  if (!existsSync(path.join(root, tag, "index.html")) || !existsSync(dir) || !statSync(dir).isDirectory()) continue;
  for (const file of readdirSync(dir).sort()) {
    if (!file.endsWith(".json")) continue;
    const text = readFileSync(path.join(dir, file), "utf8");
    if (!text.includes('"districtOffice"')) continue;
    const roster = JSON.parse(text);
    if (!roster || typeof roster !== "object") continue;
    for (const key of Object.keys(roster)) {
      const member = roster[key];
      const lines = member && typeof member === "object" ? member.districtOffice : null;
      if (!Array.isArray(lines) || !lines.length) continue;
      apps.add(tag);
      offices++;
      const where = tag + "/data/app/" + file + " " + key + " " + JSON.stringify(lines);
      const got = officeAddressForGeocode(lines);
      if (got && PHONE.test(got)) fail(where + "\n  is looked up with a telephone number: " + JSON.stringify(got));
      const lookup = got && cleanPoiAddress(got);
      const street = got && got.match(NUMBERED_STREET);
      if (street) {
        numbered++;
        if (lookup.indexOf(street[1]) < 0) fail(where + "\n  is looked up without its street number: " + JSON.stringify(lookup));
      }
      if (lookup && BOX_AFTER_STREET.test(lookup)) {
        fail(where + "\n  is looked up with a post office box after its street: " + JSON.stringify(lookup));
      }
      const cities = lines.map((l) => String(l).trim()).filter((l) => CITY_LINE.test(l));
      if (!cities.length) continue;
      withCity++;
      if (!got || !cities.some((c) => got.endsWith(c))) {
        fail(where + "\n  is looked up without its city and ZIP line: " + JSON.stringify(got));
      }
    }
  }
}
// It cannot pass by finding nothing: the rosters moving or a renamed field
// would otherwise read as every office being fine.
if (apps.size < 2 || offices < 100 || numbered < 100) {
  fail("found " + offices + " district offices in " + apps.size + " apps, " + numbered + " with a numbered street; " +
    "expected the fleet's rosters (693 offices in 15 apps, 635 with a numbered street, on 2026-10-20)");
}

if (failed) {
  console.error("office-address: " + failed + " check(s) failed");
  process.exit(1);
}
console.log("office-address: OK — " + cases.length + " office blocks and " + lookups.length +
  " lookups read as expected; " + offices + " district offices in " + apps.size +
  " apps are looked up with no telephone number and no post office box after a street, the " + withCity +
  " that carry a city and ZIP line are looked up with it, and the " + numbered +
  " with a numbered street keep its number");
