import type { AngleCandidate, OutlineBeat, ActData } from './store'

const BASE = ''  // same origin — no CORS needed (D-08/D-09)

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(detail.detail ?? `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

// Race selector
export async function getYears(): Promise<{ years: number[] }> {
  return request('GET', '/races/years')
}

export async function getRounds(year: number): Promise<{ year: number; rounds: unknown[] }> {
  return request('GET', `/races/${year}/rounds`)
}

// Article lifecycle
export async function createArticle(race_year: number, race_round: number): Promise<{ article_id: string; status: string }> {
  return request('POST', '/articles', { race_year, race_round })
}

export async function getAngles(article_id: string): Promise<{ angles: AngleCandidate[] }> {
  return request('GET', `/articles/${article_id}/angles`)
}

export async function generateOutline(
  article_id: string,
  angle_id: string,
  angle_name: string,
  angle_rationale: string,
): Promise<{ article_id: string; outline_beats: OutlineBeat[] }> {
  return request('POST', `/articles/${article_id}/outline`, { angle_id, angle_name, angle_rationale })
}

export async function patchOutline(article_id: string, beats: OutlineBeat[]): Promise<{ saved_beats: number }> {
  return request('PATCH', `/articles/${article_id}/outline`, {
    beats: beats.map((b, i) => ({
      beat_number: b.beat_number,
      beat_title: b.beat_title,
      data_anchors: b.data_anchors,
      act_number: b.act_number,
      position: i + 1,
    })),
  })
}

export async function approveOutline(article_id: string): Promise<{ article_id: string; status: string }> {
  return request('POST', `/articles/${article_id}/approve`)
}

export async function getActs(year: number, round: number): Promise<{ acts: Record<string, ActData> }> {
  return request('GET', `/acts/${year}/${round}`)
}

// SSE stream — returns an EventSource instance; caller manages connection lifecycle
export function openBeatStream(article_id: string, beat_number: number): EventSource {
  return new EventSource(`/articles/${article_id}/beats/${beat_number}/stream`)
}
