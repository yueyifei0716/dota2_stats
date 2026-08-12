const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" && ["localhost", "127.0.0.1"].includes(window.location.hostname)
    ? "http://localhost:8000/api"
    : "/api");

const CLIENT_ID_STORAGE_KEY = "dotasense-client-id";
let volatileClientId = "";

function createClientIdentity() {
  return typeof window.crypto?.randomUUID === "function"
    ? window.crypto.randomUUID()
    : `client-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function clientIdentity() {
  if (typeof window === "undefined") return "";
  try {
    const existing = window.localStorage.getItem(CLIENT_ID_STORAGE_KEY);
    if (existing) return existing;
    const created = createClientIdentity();
    window.localStorage.setItem(CLIENT_ID_STORAGE_KEY, created);
    return created;
  } catch {
    if (!volatileClientId) volatileClientId = createClientIdentity();
    return volatileClientId;
  }
}

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers);
  if (!headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const clientId = clientIdentity();
  if (clientId) headers.set("X-DotaSense-Client", clientId);
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });
  if (!res.ok) {
    let detail = "";
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : "";
    } catch {
      detail = "";
    }
    throw new Error(detail || `API error: ${res.status}`);
  }
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

export async function getWardMap(accountId?: string | number) {
  const query = accountId ? `?account_id=${encodeURIComponent(String(accountId))}` : "";
  return fetchApi<import("./types").WardMapData>(`/wardmap${query}`);
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

export async function searchPlayers(q: string) {
  return fetchApi<import("./types").PlayerSearchResponse>(`/players/search?q=${encodeURIComponent(q)}`);
}

export async function getMetaOverview() {
  return fetchApi<import("./types").GlobalMetaOverview>("/meta/overview");
}

export async function getPlayerDashboard(accountId: string | number, limit = 50) {
  return fetchApi<import("./types").PlayerDashboardData>(`/players/${accountId}/dashboard?limit=${limit}`);
}

export async function getPlayerQuickDashboard(accountId: string | number, limit = 20) {
  return fetchApi<import("./types").PlayerDashboardData>(`/players/${accountId}/dashboard/quick?limit=${Math.min(limit, 20)}`);
}

export async function getPlayerMatchScorecard(accountId: string | number, matchId: string | number) {
  return fetchApi<import("./types").PlayerMatchScorecard>(`/players/${accountId}/matches/${matchId}/scorecard`);
}

export async function startTrainingMission(accountId: string | number, focusKey = "") {
  return fetchApi<import("./types").PlayerTrainingState>(`/players/${accountId}/training/missions`, {
    method: "POST",
    body: JSON.stringify({ focus_key: focusKey }),
  });
}

export async function cancelTrainingMission(accountId: string | number, missionId: string) {
  return fetchApi<import("./types").PlayerTrainingState>(`/players/${accountId}/training/missions/${missionId}`, {
    method: "DELETE",
  });
}

export async function confirmMatchPosition(accountId: string | number, matchId: string | number, position: number) {
  return fetchApi<{
    match_id: string;
    position: number;
    position_key: string;
    position_name: string;
    position_source: "user_confirmed";
    updated_at: number;
  }>(`/players/${accountId}/matches/${matchId}/position`, {
    method: "PUT",
    body: JSON.stringify({ position }),
  });
}

export async function getCommercialConfig() {
  return fetchApi<import("./types").CommercialConfig>("/commercial/config");
}

export async function createCommercialLead(payload: import("./types").CommercialLeadPayload) {
  return fetchApi<import("./types").CommercialLeadResponse>("/commercial/leads", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function unlockCommercialAccess(payload: { code: string; account_id?: number; plan?: string }) {
  return fetchApi<import("./types").CommercialAccessResponse>("/commercial/access", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function verifyCommercialAccess(token: string, accountId?: string | number) {
  const query = accountId ? `?account_id=${encodeURIComponent(String(accountId))}` : "";
  return fetchApi<import("./types").CommercialAccessVerifyResponse>(`/commercial/access/verify${query}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export async function getPlayerReviewPreview(accountId: string | number, limit = 30) {
  return fetchApi<import("./types").PlayerReviewResponse>(`/players/${accountId}/review/preview?limit=${limit}`);
}

export async function getPlayerReview(accountId: string | number, accessToken: string, limit = 50) {
  return fetchApi<import("./types").PlayerReviewResponse>(`/players/${accountId}/review?limit=${limit}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ access_token: accessToken }),
  });
}
