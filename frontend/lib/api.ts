const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function getDashboard() {
  return fetchApi<import("./types").DashboardData>("/dashboard");
}

export async function getMatches(params?: { hero?: string; role?: number; limit?: number }) {
  const query = new URLSearchParams();
  if (params?.hero) query.set("hero", params.hero);
  if (params?.role) query.set("role", String(params.role));
  if (params?.limit) query.set("limit", String(params.limit));
  const qs = query.toString();
  return fetchApi<import("./types").Match[]>(`/matches${qs ? `?${qs}` : ""}`);
}

export async function getHeroMatchups(heroId: number) {
  return fetchApi<{ best: import("./types").HeroMatchup[]; worst: import("./types").HeroMatchup[] }>(`/hero_matchups/${heroId}`);
}

export async function saveMatchNote(matchId: string, note: string) {
  return fetchApi<{ success: boolean; message: string }>("/match_notes", {
    method: "POST",
    body: JSON.stringify({ match_id: matchId, note }),
  });
}

export async function updateData(fetchItems = false) {
  return fetchApi<{ success: boolean; message: string }>("/update_data", {
    method: "POST",
    body: JSON.stringify({ fetch_items: fetchItems }),
  });
}

export async function updateMmr(mmr: number, result?: string) {
  return fetchApi<{ success: boolean }>("/update_mmr", {
    method: "POST",
    body: JSON.stringify({ mmr, result }),
  });
}

export async function calibrateMmr(mmr: number) {
  return fetchApi<{ success: boolean }>("/calibrate_mmr", {
    method: "POST",
    body: JSON.stringify({ mmr }),
  });
}

// ── New feature APIs ──

export async function getAllHeroes() {
  return fetchApi<import("./types").AllHero[]>("/all_heroes");
}

export async function getWardMap() {
  return fetchApi<import("./types").WardMapData>("/wardmap");
}

export async function getHistogram(field: string) {
  return fetchApi<import("./types").HistogramData>(`/histograms/${field}`);
}

export async function getCounts() {
  return fetchApi<import("./types").CountsData>("/counts");
}

export async function getHeroItems(heroId: number) {
  return fetchApi<import("./types").HeroItemsData>(`/hero_items/${heroId}`);
}

export async function getHeroDurations(heroId: number) {
  return fetchApi<import("./types").HeroDurationsData>(`/hero_durations/${heroId}`);
}

export async function getProEncounters() {
  return fetchApi<import("./types").ProEncountersData>("/pro_encounters");
}
