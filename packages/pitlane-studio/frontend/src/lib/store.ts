import { writable } from 'svelte/store'

// App stage — controls which UI section is visible
// 'angle-selection' → 'outline-review' → 'beat-editing'
export type AppStage = 'angle-selection' | 'outline-review' | 'beat-editing'
export const stage = writable<AppStage>('angle-selection')

// Race selection
export const selectedYear = writable<number | null>(null)
export const selectedRound = writable<number | null>(null)

// Article lifecycle
export const articleId = writable<string | null>(null)

// Angles (Stage 1)
export interface AngleCandidate {
  angle_id: string
  name: string
  signal_type: string
  confidence: number
  data_rationale: string
}
export const angles = writable<AngleCandidate[]>([])
export const selectedAngleId = writable<string | null>(null)
export const anglesLoading = writable(false)
export const anglesError = writable<string | null>(null)

// Outline (Stage 2)
export interface OutlineBeat {
  beat_number: number
  beat_title: string
  data_anchors: string
  act_number: number | null
}
export const outlineBeats = writable<OutlineBeat[]>([])
export const outlineGenerating = writable(false)
export const approvalPending = writable(false)

// Beat prose (Stage 3)
export type BeatStatus = 'pending' | 'streaming' | 'complete' | 'error'
export interface BeatProseState {
  beat_number: number
  beat_title: string
  prose: string
  placeholder_markers: Array<{ type: string; offset: number }>
  status: BeatStatus
}
export const beatProseStates = writable<Record<number, BeatProseState>>({})

// Five-act sidebar
export interface ActData {
  label: string
  data: Record<string, unknown>
}
export const actSidebarData = writable<Record<number, ActData>>({})
