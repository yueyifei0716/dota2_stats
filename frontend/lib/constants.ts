export const RANK_TIERS: Record<number, string> = {
  0: "未校准",
  10: "先锋 I", 11: "先锋 I", 12: "先锋 II", 13: "先锋 III", 14: "先锋 IV", 15: "先锋 V",
  20: "卫士 I", 21: "卫士 I", 22: "卫士 II", 23: "卫士 III", 24: "卫士 IV", 25: "卫士 V",
  30: "中军 I", 31: "中军 I", 32: "中军 II", 33: "中军 III", 34: "中军 IV", 35: "中军 V",
  40: "统帅 I", 41: "统帅 I", 42: "统帅 II", 43: "统帅 III", 44: "统帅 IV", 45: "统帅 V",
  50: "传奇 I", 51: "传奇 I", 52: "传奇 II", 53: "传奇 III", 54: "传奇 IV", 55: "传奇 V",
  60: "万古流芳 I", 61: "万古流芳 I", 62: "万古流芳 II", 63: "万古流芳 III", 64: "万古流芳 IV", 65: "万古流芳 V",
  70: "超凡入圣 I", 71: "超凡入圣 I", 72: "超凡入圣 II", 73: "超凡入圣 III", 74: "超凡入圣 IV", 75: "超凡入圣 V",
  80: "冠绝一世",
};

export const ROLE_NAMES: Record<number, string> = {
  1: "优势路",
  2: "中路",
  3: "劣势路",
  4: "打野",
};

export function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

export function formatKda(k: number, d: number, a: number): string {
  return `${k}/${d}/${a}`;
}
