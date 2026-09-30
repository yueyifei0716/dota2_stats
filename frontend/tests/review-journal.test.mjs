import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import ts from "typescript";

// Use the project's compiler so domain tests also run on Node 20 in CI.
const source = readFileSync(new URL("../lib/review-journal.ts", import.meta.url), "utf8");
const { outputText } = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 } });
const { emptyJournal, saveReview, parseJournal, pinReview, archiveReview, recordCheck, followUpMatches, mergeJournal, recentSession, reviewCandidate, sessionHighlight } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString("base64")}`);
const now = Date.UTC(2026, 8, 22, 12);
const match = (id = "101", overrides = {}) => ({ match_id: id, hero_id: 25, hero_name: "莉娜", hero_icon: "", start_time: now / 1000 - 7200, played_at: "2026-09-22 18:00", duration: 3000, win: false, kills: 5, deaths: 0, assists: 10, replay_parsed: false, benchmark_available: false, benchmarks: {}, ...overrides });
const draft = { tag: "对线", note: "留意第一波补给", reminder: "上线前检查补给" };

test("sessions use rest after game end, across midnight and long games", () => {
  const older = match("1", { start_time: Date.UTC(2026, 8, 21, 23) / 1000, duration: 7200 });
  const newer = match("2", { start_time: older.start_time + 7260 });
  const previous = match("3", { start_time: older.start_time - 10000, duration: 1000 });
  assert.deepEqual(recentSession([older, previous, newer, newer]).map((row) => row.match_id), ["2", "1"]);
});
test("unknown timing does not fabricate session continuity", () => {
  assert.deepEqual(recentSession([match("1", { start_time: 0 })]), []);
  assert.deepEqual(recentSession([match("2", { start_time: now / 1000 }), match("1", { duration: 0 })]).map((row) => row.match_id), ["2"]);
});
test("highlight needs a positive measured benchmark, and can come from a loss", () => {
  assert.equal(sessionHighlight([match()]), null);
  assert.equal(sessionHighlight([match("1", { benchmark_available: true, benchmarks: { gold_per_min: { raw: 0, pct: .99 } } })]), null);
  assert.equal(sessionHighlight([match("1", { benchmark_available: true, benchmarks: { gold_per_min: { raw: 500, pct: null } } })]), null);
  const highlight = sessionHighlight([match("1", { benchmark_available: true, benchmarks: { gold_per_min: { raw: 500, pct: .8 } } })]);
  assert.equal(highlight.percentile, 80);
  assert.equal(highlight.match.win, false);
});
test("review candidates prefer evidence and exclude saved matches", () => {
  const plain = match("1"), parsed = match("2", { replay_parsed: true });
  assert.equal(reviewCandidate([plain, parsed], []).match.match_id, "2");
  const state = saveReview(emptyJournal(123), parsed, draft, false, now);
  assert.equal(reviewCandidate([plain, parsed], state.entries).match.match_id, "1");
  assert.equal(reviewCandidate([parsed], state.entries), null);
});
test("notes and reminder survive backup round trip without converting a loss", () => {
  const state = saveReview(emptyJournal(123), match(), draft, true, now);
  assert.deepEqual(parseJournal(JSON.stringify(state), 123), state);
  assert.equal(state.focusMatchId, "101");
  assert.equal(state.entries[0].match.win, false);
  assert.equal(state.entries[0].focusStartedAt, now);
  assert.deepEqual(state.seenMatchIds, ["101"]);
  assert.throws(() => saveReview(state, match(), { ...draft, note: "  " }, true, now));
});
test("check-ins require the same hero and a game after setting the reminder", () => {
  const state = saveReview(emptyJournal(123), match(), draft, true, now);
  const future = match("102", { start_time: now / 1000 + 60 });
  const other = match("103", { start_time: future.start_time, hero_id: 5 });
  assert.deepEqual(followUpMatches(state.entries[0], [match(), future, other]).map((row) => row.match_id), ["102"]);
  assert.throws(() => recordCheck(state, match(), "kept"));
  assert.throws(() => recordCheck(state, other, "kept"));
  const amended = recordCheck(recordCheck(state, future, "missed"), future, "kept");
  assert.equal(amended.entries[0].checks.length, 1);
  assert.equal(amended.entries[0].checks[0].result, "kept");
  assert.deepEqual(parseJournal(JSON.stringify(amended), 123), amended);
});
test("changing action resets feedback, editing a note preserves it", () => {
  const state = recordCheck(saveReview(emptyJournal(123), match(), draft, true, now), match("102", { start_time: now / 1000 + 60 }), "not_applicable");
  const edited = saveReview(state, match(), { ...draft, note: "补充观察" }, true, now + 1000);
  assert.equal(edited.entries[0].checks.length, 1);
  const changed = saveReview(edited, match(), { ...draft, reminder: "留 TP" }, true, now + 2000);
  assert.equal(changed.entries[0].checks.length, 0);
  assert.equal(changed.entries[0].focusStartedAt, now + 2000);
});
test("one active reminder, reversible archive, no deleted notes", () => {
  const one = saveReview(emptyJournal(123), match("1"), draft, true, now);
  const two = saveReview(one, match("2"), draft, true, now + 1000);
  assert.equal(two.focusMatchId, "2");
  assert.equal(two.entries.length, 2);
  const archived = archiveReview(two, "2");
  assert.equal(archived.focusMatchId, null);
  assert.equal(archived.entries.find((entry) => entry.match.match_id === "2").note, draft.note);
  assert.throws(() => pinReview(archived, "2", now));
  assert.equal(pinReview(archiveReview(archived, "2"), "2", now).focusMatchId, "2");
});
test("import cannot mix accounts or overwrite a current note", () => {
  const current = saveReview(emptyJournal(123), match("1"), { ...draft, note: "本机新记录" }, true, now);
  const backup = saveReview(saveReview(emptyJournal(123), match("1"), draft, true, now - 2000), match("2"), draft, false, now - 1000);
  const merged = mergeJournal(current, backup);
  assert.equal(merged.entries.length, 2);
  assert.equal(merged.entries.find((entry) => entry.match.match_id === "1").note, "本机新记录");
  assert.equal(merged.focusMatchId, "1");
  assert.throws(() => parseJournal(JSON.stringify(backup), 456), /其他玩家/);
  assert.throws(() => mergeJournal(current, emptyJournal(456)), /其他玩家/);
});
test("malformed backups reject without modifying existing data", () => {
  const state = saveReview(emptyJournal(123), match(), draft, true, now);
  const original = JSON.stringify(state);
  assert.throws(() => parseJournal("{bad", 123));
  assert.throws(() => parseJournal(JSON.stringify({ ...state, version: 2 }), 123));
  assert.throws(() => parseJournal(JSON.stringify({ ...state, focusMatchId: "missing" }), 123));
  assert.throws(() => parseJournal(JSON.stringify({ ...state, entries: [...state.entries, ...state.entries] }), 123));
  assert.throws(() => parseJournal(JSON.stringify({ ...state, entries: [{ ...state.entries[0], note: "a".repeat(1201) }] }), 123));
  assert.equal(JSON.stringify(state), original);
});
test("import cannot introduce arbitrary external tracking images", () => {
  const state = saveReview(emptyJournal(123), match("1", { hero_icon: "https://evil.example/track" }), draft, false, now);
  assert.equal(state.entries[0].match.hero_icon, "");
});
