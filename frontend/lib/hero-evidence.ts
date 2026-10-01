import type { HeroBuildGroup, HeroBuilds } from "./types";

// Choose usable purchase evidence within the current patch before inventory-only
// groups. Authored learning lanes are context; replay lanes are not positions.
export function defaultBuildGroup(data: HeroBuilds, heroId: number, learningLane?: number | null): HeroBuildGroup | undefined {
  const preferredLane = learningLane ?? (heroId === 113 ? 2 : data.primary_lane_role ?? undefined);
  return [...(data.groups || [])].sort((a, b) => {
    const score = (group: HeroBuildGroup) => [
      Number(group.patch_id === data.patch_id),
      Number(group.purchase_log_sample > 0 && group.lane_role === preferredLane),
      Number(group.purchase_log_sample > 0),
      Number(group.lane_role === preferredLane),
      Number(group.lane_role !== null),
      group.purchase_log_sample,
      group.sample,
    ];
    const left = score(a), right = score(b);
    for (let i = 0; i < left.length; i++) {
      if (left[i] !== right[i]) return right[i] - left[i];
    }
    return 0;
  })[0];
}

export function patchLabel(patchId: number | null | undefined, data: HeroBuilds): string {
  const mapped = patchId == null ? undefined : data.patch_names?.[String(patchId)];
  const name = mapped || (patchId != null && patchId === data.patch_id ? data.patch_name : null);
  return typeof name === "string" && /^\d+\.\d+[a-z]?$/i.test(name) ? name : "未知";
}
