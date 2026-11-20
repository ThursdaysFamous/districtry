// Tests for the link lookup. Run: node --experimental-strip-types --test main_test.ts
// (Deno runs it too: deno test). Nothing here touches the network; every
// answer from Google, Apple or the Census Bureau is stood in for.
import { test } from "node:test";
import assert from "node:assert/strict";
import { handler, isAddress, resolve } from "./main.ts";

// A stand-in fetch answering each URL from a table: a string is a redirect
// target, null is a 200 page, anything missing fails the test.
function hops(table: Record<string, string | null>) {
  const asked: string[] = [];
  const fn = (async (url: string) => {
    asked.push(url);
    if (!(url in table)) throw new Error("unexpected fetch " + url);
    const to = table[url];
    return to === null
      ? new Response("page", { status: 200 })
      : new Response(null, { status: 302, headers: { location: to } });
  }) as typeof fetch;
  return { fn, asked };
}

test("a short Google link is followed to the full map link", async () => {
  const { fn } = hops({ "https://maps.app.goo.gl/abc": "https://www.google.com/maps/place/X/@41.88,-87.62,17z" });
  assert.equal(await resolve(new URL("https://maps.app.goo.gl/abc"), fn),
    "https://www.google.com/maps/place/X/@41.88,-87.62,17z");
});

test("a hop to any host but Google's or Apple's is refused before it is fetched", async () => {
  for (const evil of ["https://evil.example/x", "https://google.com.evil.example/maps", "http://maps.google.com/maps?q=1",
                      "https://169.254.169.254/latest/meta-data/", "https://localhost/maps"]) {
    const { fn, asked } = hops({ "https://maps.app.goo.gl/abc": evil });
    assert.equal(await resolve(new URL("https://maps.app.goo.gl/abc"), fn), null, evil);
    assert.deepEqual(asked, ["https://maps.app.goo.gl/abc"], evil);
  }
});

test("a consent page is read for its destination, and a loop gives up", async () => {
  const dest = "https://www.google.com/maps/place/Y";
  const { fn } = hops({ "https://maps.app.goo.gl/c": "https://consent.google.com/m?continue=" + encodeURIComponent(dest) });
  assert.equal(await resolve(new URL("https://maps.app.goo.gl/c"), fn), dest);
  const loop = hops({ "https://maps.app.goo.gl/a": "https://maps.app.goo.gl/b", "https://maps.app.goo.gl/b": "https://maps.app.goo.gl/a" });
  assert.equal(await resolve(new URL("https://maps.app.goo.gl/a"), loop.fn), null);
  assert.ok(loop.asked.length <= 6);
});

test("a link that ends on a page rather than a map is not an answer", async () => {
  const { fn } = hops({ "https://maps.app.goo.gl/p": null });
  assert.equal(await resolve(new URL("https://maps.app.goo.gl/p"), fn), null);
});

test("isAddress wants a number and a comma, and nothing a person would not type", () => {
  assert.ok(isAddress("121 N LaSalle St, Chicago, IL 60602"));
  assert.ok(!isAddress("Chicago City Hall"));
  assert.ok(!isAddress("121 N LaSalle St Chicago"));
  assert.ok(!isAddress("121 N LaSalle St,\u0000Chicago"));
  assert.ok(!isAddress("1, " + "x".repeat(200)));
});

test("the handler refuses a link that is not a short map link, and answers CORS for the site only", async () => {
  const bad = await handler(new Request("https://lookup.test/?u=https://example.com/", { headers: { origin: "https://districtry.com" } }));
  assert.equal(bad.status, 400);
  assert.equal(bad.headers.get("access-control-allow-origin"), "https://districtry.com");
  const other = await handler(new Request("https://lookup.test/?u=https://example.com/", { headers: { origin: "https://evil.example" } }));
  assert.equal(other.headers.get("access-control-allow-origin"), null);
  assert.equal((await handler(new Request("https://lookup.test/?a=no+number"))).status, 400);
  assert.equal((await handler(new Request("https://lookup.test/", { method: "POST" }))).status, 405);
});
