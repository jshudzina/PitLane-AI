<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte'
  import { getYears, getRounds } from '$lib/api'

  const dispatch = createEventDispatcher<{ select: { year: number; round: number } }>()

  let years: number[] = []
  let rounds: unknown[] = []
  let selectedYear: number | null = null
  let selectedRound: number | null = null
  let roundsLoading = false
  let error: string | null = null

  onMount(async () => {
    try {
      const res = await getYears()
      years = res.years
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load years'
    }
  })

  async function onYearChange(e: Event) {
    const val = parseInt((e.target as HTMLSelectElement).value)
    selectedYear = isNaN(val) ? null : val
    selectedRound = null
    rounds = []
    if (!selectedYear) return
    roundsLoading = true
    error = null
    try {
      const res = await getRounds(selectedYear)
      rounds = res.rounds
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load rounds'
    } finally {
      roundsLoading = false
    }
  }

  function onRoundChange(e: Event) {
    const val = parseInt((e.target as HTMLSelectElement).value)
    selectedRound = isNaN(val) ? null : val
    if (selectedYear && selectedRound) {
      dispatch('select', { year: selectedYear, round: selectedRound })
    }
  }
</script>

<div style="display:flex;align-items:center;gap:8px;">
  <select
    style="width:100px;background:#1a1a1a;border:1px solid #2e2e2e;color:#e0e0e0;font-size:13px;padding:4px 8px;border-radius:4px;cursor:pointer;"
    on:change={onYearChange}
  >
    <option value="">Year</option>
    {#each years as year}
      <option value={year}>{year}</option>
    {/each}
  </select>

  <select
    style="width:200px;background:#1a1a1a;border:1px solid #2e2e2e;color:{selectedYear ? '#e0e0e0' : '#555555'};font-size:13px;padding:4px 8px;border-radius:4px;cursor:{selectedYear ? 'pointer' : 'not-allowed'};"
    disabled={!selectedYear || roundsLoading}
    on:change={onRoundChange}
  >
    {#if roundsLoading}
      <option value="">Loading...</option>
    {:else if !selectedYear}
      <option value="">Round</option>
    {:else}
      <option value="">Round</option>
      {#each rounds as r, i}
        <option value={i + 1}>Round {i + 1}{typeof r === 'object' && r !== null && 'name' in r ? ` — ${(r as { name: string }).name}` : ''}</option>
      {/each}
    {/if}
  </select>

  {#if error}
    <span style="font-size:13px;color:#cf4444;">{error}</span>
  {/if}
</div>
