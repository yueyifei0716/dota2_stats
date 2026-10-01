import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import ts from "typescript";

const source = readFileSync(new URL("../lib/hero-evidence.ts", import.meta.url), "utf8");
const { outputText } = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 } });
const { defaultBuildGroup, patchLabel } = await import(`data:text/javascript;base64,${Buffer.from(outputText).toString("base64")}`);
const group = (lane, logs, sample, patch = 60) => ({ lane_role: lane, purchase_log_sample: logs, sample, patch_id: patch });

test("Arc opens six logged mid games instead of seven unknown inventory-only games", () => {
  const mid = group(2, 6, 6);
  assert.equal(defaultBuildGroup({ patch_id: 60, primary_lane_role: null, groups: [group(null, 0, 7), mid] }, 113), mid);
});
test("current patch wins over older logs, then any logged lane wins over inventory only", () => {
  const logged = group(3, 3, 3);
  const data = { patch_id: 60, groups: [group(2, 24, 24, 59), group(2, 0, 6), logged] };
  assert.equal(defaultBuildGroup(data, 113), logged);
  assert.equal(defaultBuildGroup({ patch_id: 60, groups: [] }, 113), undefined);
});
test("other heroes prefer purchase evidence without interpreting a lane as a position", () => {
  const logged = group(1, 4, 4);
  const groups = [group(null, 0, 12), logged];
  assert.equal(defaultBuildGroup({ patch_id: 60, groups }, 26), logged);
  assert.equal(groups[0].lane_role, null);
});
test("an explicitly authored learning lane wins when it has purchase logs", () => {
  const mid = group(2, 3, 3);
  const carry = group(1, 8, 8);
  assert.equal(defaultBuildGroup({ patch_id: 60, groups: [carry, mid] }, 13, 2), mid);
  assert.equal(defaultBuildGroup({ patch_id: 60, groups: [carry, group(2, 0, 5)] }, 13, 2), carry);
});
test("the backend primary lane preserves the default while mechanics load", () => {
  const mid = group(2, 3, 3);
  assert.equal(defaultBuildGroup({ patch_id: 60, primary_lane_role: 2, groups: [group(1, 8, 8), mid] }, 13), mid);
});
test("raw patch IDs and a different patch's label cannot leak into displayed versions", () => {
  assert.equal(patchLabel(60, { patch_id: 60, patch_name: null }), "未知");
  assert.equal(patchLabel(60, { patch_id: 60, patch_name: "60" }), "未知");
  assert.equal(patchLabel(59, { patch_id: 60, patch_name: "7.41" }), "未知");
  assert.equal(patchLabel(60, { patch_id: 60, patch_name: "7.41" }), "7.41");
  assert.equal(patchLabel(59, { patch_id: 60, patch_names: { 59: "7.40d" } }), "7.40d");
});
