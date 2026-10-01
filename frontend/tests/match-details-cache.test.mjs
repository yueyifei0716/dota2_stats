import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import ts from "typescript";

const compile = (source) => ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 } }).outputText;
const url = (source) => `data:text/javascript;base64,${Buffer.from(compile(source)).toString("base64")}`;
const cacheUrl = url(readFileSync(new URL("../lib/match-details-cache.ts", import.meta.url), "utf8"));
const cache = await import(cacheUrl);
const apiSource = readFileSync(new URL("../lib/api.ts", import.meta.url), "utf8").replace('"./match-details-cache"', JSON.stringify(cacheUrl));
const api = await import(url(apiSource));
const ready = (id = "9022234630", stamp = Date.now() / 1000) => ({ match_id: id,
  detail_available: true, detail_status: "ready", detail_fetched_at: stamp,
  equipment_available: true, level: 21, gold_per_min: 356, xp_per_min: 605,
  items: [1, 0, 36, 116, 214, 267].map((item_id) => ({ item_id })), neutral_item: { item_id: 680 },
});

test("scorecard then list reuses the complete successful row and requests only unread matches", async () => {
  const previousFetch = globalThis.fetch;
  const calls = [];
  const detail = ready();
  globalThis.fetch = async (path) => {
    calls.push(path);
    return { ok: true, json: async () => path.endsWith("/scorecard")
      ? { match: { match_id: detail.match_id }, match_detail: detail }
      : { matches: [{ match_id: "9022234631", detail_status: "retryable", detail_error: "upstream unavailable" }] } };
  };
  try {
    await api.getPlayerMatchScorecard(894447460, detail.match_id);
    const result = await api.getPlayerMatchDetails(894447460, [detail.match_id, "9022234631"]);
    assert.equal(calls.length, 2);
    assert.match(calls[1], /match_ids=9022234631$/);
    assert.equal(result.matches[0].gold_per_min, 356);
    assert.equal(result.matches[0].xp_per_min, 605);
    assert.equal(result.matches[0].detail_fetched_at, detail.detail_fetched_at);
    assert.deepEqual(result.matches[0].items.map((item) => item.item_id), [1, 0, 36, 116, 214, 267]);
    assert.equal(result.matches[0].neutral_item.item_id, 680);
    assert.equal(result.matches[0].detail_error, "");
    assert.equal(result.matches[1].detail_status, "retryable");
    const again = await api.getPlayerMatchDetails(894447460, [detail.match_id]);
    assert.equal(calls.length, 2);
    assert.equal(again.matches[0].detail_status, "ready");
  } finally { globalThis.fetch = previousFetch; }
});

test("a failed later batch cannot erase success or its original source time", () => {
  const detail = ready("200", 1790836000);
  cache.rememberMatchDetails(1, [detail], 1790836000000);
  cache.rememberMatchDetails(1, [{ match_id: "200", detail_status: "retryable", detail_error: "timeout" }], 1790836001000);
  const saved = cache.cachedMatchDetail(1, "200", 1790836002000);
  assert.equal(saved.gold_per_min, 356);
  assert.equal(saved.detail_fetched_at, 1790836000);
  assert.equal(saved.detail_error, "");
});

test("same match ID stays isolated by account", () => {
  const now = Date.now();
  cache.rememberMatchDetails(2, [ready("300")], now);
  assert.equal(cache.cachedMatchDetail(3, "300", now), undefined);
  assert.equal(cache.cachedMatchDetail(2, "300", now).gold_per_min, 356);
});

test("a late older successful response cannot replace a newer scoreboard", () => {
  const now = 1790836000000;
  cache.rememberMatchDetails(5, [ready("500", now / 1000)], now);
  cache.rememberMatchDetails(5, [{ ...ready("500", now / 1000 - 60), gold_per_min: 0, detail_error: "cached upstream" }], now + 1000);
  const saved = cache.cachedMatchDetail(5, "500", now + 2000);
  assert.equal(saved.gold_per_min, 356);
  assert.equal(saved.detail_fetched_at, now / 1000);
  assert.equal(saved.detail_error, "");
});

test("a successful dashboard row cannot be downgraded by the old view's failure", () => {
  const source = ready("600");
  assert.equal(cache.mergeMatchDetail(source, { match_id: "600", detail_status: "retryable", detail_error: "timeout" }), source);
});

test("cache expiry and source age do not renew original evidence", () => {
  const now = 1790836000000;
  cache.rememberMatchDetails(4, [ready("400", now / 1000)], now);
  assert.equal(cache.cachedMatchDetail(4, "400", now + 600000), undefined);
  cache.rememberMatchDetails(4, [ready("401", (now - 86400001) / 1000)], now);
  assert.equal(cache.cachedMatchDetail(4, "401", now), undefined);
});
