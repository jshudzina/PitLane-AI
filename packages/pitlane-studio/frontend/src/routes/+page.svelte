<script lang="ts">
  import { get } from 'svelte/store'
  import RaceSelector from '$lib/components/RaceSelector.svelte'
  import AngleCard from '$lib/components/AngleCard.svelte'
  import OutlinePanel from '$lib/components/OutlinePanel.svelte'
  import BeatEditor from '$lib/components/BeatEditor.svelte'
  import FiveActSidebar from '$lib/components/FiveActSidebar.svelte'
  import { exportMarkdown } from '$lib/utils/markdown-export'
  import {
    stage,
    selectedYear,
    selectedRound,
    articleId,
    angles,
    selectedAngleId,
    anglesLoading,
    anglesError,
    outlineBeats,
    outlineGenerating,
    approvalPending,
    actSidebarData,
    type OutlineBeat,
  } from '$lib/store'
  import {
    createArticle,
    getAngles,
    generateOutline,
    patchOutline,
    approveOutline,
    getActs,
  } from '$lib/api'

  let copyButtonLabel = 'Copy Markdown'
  let editorRefs: any[] = []
  let currentStreamingBeat: number | null = null
  let allBeatsComplete = false

  async function onRaceSelect(e: CustomEvent<{ year: number; round: number }>) {
    const { year, round } = e.detail
    selectedYear.set(year)
    selectedRound.set(round)
    anglesLoading.set(true)
    anglesError.set(null)
    angles.set([])
    try {
      const art = await createArticle(year, round)
      articleId.set(art.article_id)
      const [anglesRes, actsRes] = await Promise.all([
        getAngles(art.article_id),
        getActs(year, round),
      ])
      angles.set(anglesRes.angles)
      actSidebarData.set(actsRes.acts as Record<number, { label: string; data: Record<string, unknown> }>)
    } catch (e) {
      anglesError.set(e instanceof Error ? e.message : 'Failed to load angles')
    } finally {
      anglesLoading.set(false)
    }
  }

  function onAngleSelect(e: CustomEvent<string | null>) {
    selectedAngleId.set(e.detail)
  }

  async function developAngle() {
    const aid = get(articleId)
    const sid = get(selectedAngleId)
    const ang = get(angles).find(a => a.angle_id === sid)
    if (!aid || !sid || !ang) return
    outlineGenerating.set(true)
    try {
      const res = await generateOutline(aid, ang.angle_id, ang.name, ang.data_rationale)
      outlineBeats.set(res.outline_beats)
      stage.set('outline-review')
    } catch (e) {
      anglesError.set(e instanceof Error ? e.message : 'Failed to generate outline')
    } finally {
      outlineGenerating.set(false)
    }
  }

  function onOutlineUpdate(e: CustomEvent<OutlineBeat[]>) {
    outlineBeats.set(e.detail)
    const aid = get(articleId)
    if (aid) patchOutline(aid, e.detail).catch(() => {})
  }

  function onAddBeat() {
    outlineBeats.update(beats => {
      const next = beats.length + 1
      return [...beats, { beat_number: next, beat_title: `Beat ${next}`, data_anchors: '', act_number: null }]
    })
  }

  function onRemoveBeat(e: CustomEvent<number>) {
    outlineBeats.update(beats => beats.filter(b => b.beat_number !== e.detail))
  }

  function onReorderBeat(e: CustomEvent<{ beat_number: number; direction: 'up' | 'down' }>) {
    outlineBeats.update(beats => {
      const idx = beats.findIndex(b => b.beat_number === e.detail.beat_number)
      if (idx === -1) return beats
      const swap = e.detail.direction === 'up' ? idx - 1 : idx + 1
      if (swap < 0 || swap >= beats.length) return beats
      const next = [...beats]
      ;[next[idx], next[swap]] = [next[swap], next[idx]]
      return next
    })
  }

  async function onApprove() {
    const aid = get(articleId)
    if (!aid) return
    approvalPending.set(true)
    try {
      await approveOutline(aid)
      currentStreamingBeat = 1
      allBeatsComplete = false
      stage.set('beat-editing')
    } catch (e) {
      anglesError.set(e instanceof Error ? e.message : 'Approval failed')
    } finally {
      approvalPending.set(false)
    }
  }

  function onStreamComplete(e: CustomEvent<{ beat_number: number }>) {
    const beats = get(outlineBeats)
    const completedIdx = beats.findIndex(b => b.beat_number === e.detail.beat_number)
    const nextBeat = beats[completedIdx + 1]
    if (nextBeat) {
      currentStreamingBeat = nextBeat.beat_number
    } else {
      currentStreamingBeat = null
      allBeatsComplete = true
    }
  }

  async function handleCopyMarkdown() {
    const beatJsonMap = new Map<number, any>()
    const beats = get(outlineBeats)
    beats.forEach((beat, i) => {
      const ref = editorRefs[i]
      if (ref) {
        const json = ref.getEditorJSON()
        if (json) beatJsonMap.set(beat.beat_number, json)
      }
    })
    const markdown = beatJsonMap.size > 0
      ? exportMarkdown(beatJsonMap)
      : beats.map(b => `## Beat ${b.beat_number}: ${b.beat_title}\n\n${b.data_anchors}`).join('\n\n---\n\n')
    await navigator.clipboard.writeText(markdown)
    copyButtonLabel = 'Copied!'
    setTimeout(() => { copyButtonLabel = 'Copy Markdown' }, 2000)
  }

  function getBeatStatus(beatNumber: number): 'pending' | 'streaming' | 'complete' {
    if (currentStreamingBeat === beatNumber) return 'streaming'
    if (allBeatsComplete) return 'complete'
    const beats = get(outlineBeats)
    const beatIdx = beats.findIndex(b => b.beat_number === beatNumber)
    const streamingIdx = currentStreamingBeat != null ? beats.findIndex(b => b.beat_number === currentStreamingBeat) : -1
    if (streamingIdx > -1 && beatIdx < streamingIdx) return 'complete'
    return 'pending'
  }

  $: beatStatusMap = (() => {
    const beats = get(outlineBeats)
    const map: Record<number, 'pending' | 'streaming' | 'complete'> = {}
    beats.forEach(b => { map[b.beat_number] = getBeatStatus(b.beat_number) })
    return map
  })()
</script>

<!-- three-column layout -->
<div style="display:flex;flex-direction:column;height:100vh;background:#0f0f0f;color:#e0e0e0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;min-width:1100px;">

  <!-- Header 48px -->
  <header style="height:48px;background:#1a1a1a;border-bottom:1px solid #e10600;display:flex;align-items:center;padding:0 24px;gap:24px;flex-shrink:0;">
    <span style="font-size:15px;font-weight:600;color:#e0e0e0;">PitLane Studio</span>
    <div style="display:flex;align-items:center;gap:8px;">
      <span style="font-size:13px;color:#999999;">Race:</span>
      <RaceSelector on:select={onRaceSelect} />
    </div>
    <div style="flex:1;"></div>
    <button
      on:click={handleCopyMarkdown}
      style="height:36px;background:#e10600;color:#ffffff;font-weight:600;font-size:13px;border:none;border-radius:6px;padding:0 16px;cursor:pointer;"
    >{copyButtonLabel}</button>
  </header>

  <!-- Body -->
  <div style="flex:1;display:flex;overflow:hidden;">

    <!-- Left panel — hidden in Stage 1 -->
    {#if $stage !== 'angle-selection'}
      <aside style="width:280px;background:#1a1a1a;border-right:1px solid #2e2e2e;flex-shrink:0;overflow-y:auto;">
        <div style="padding:16px;font-size:13px;color:#999999;text-transform:uppercase;letter-spacing:0.08em;">Outline</div>
        {#each $outlineBeats as beat}
          {@const bStatus = $stage === 'beat-editing' ? (currentStreamingBeat === beat.beat_number ? 'streaming' : (allBeatsComplete || (currentStreamingBeat != null && beat.beat_number < currentStreamingBeat) ? 'complete' : 'pending')) : 'pending'}
          <div style="height:40px;display:flex;align-items:center;padding:0 16px;font-size:13px;color:{bStatus === 'complete' || currentStreamingBeat === beat.beat_number ? '#e0e0e0' : '#999999'};border-left:2px solid {currentStreamingBeat === beat.beat_number ? '#e10600' : 'transparent'};">
            <span style="flex:1;">{beat.beat_number}. {beat.beat_title}</span>
            {#if bStatus === 'complete'}
              <span style="color:#6acc8a;">✓</span>
            {:else if bStatus === 'streaming'}
              <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#5a9acc;animation:spin-dot 1s linear infinite;"></span>
            {:else}
              <span style="color:#444444;">—</span>
            {/if}
          </div>
        {/each}
      </aside>
    {/if}

    <!-- Main content -->
    <main style="flex:1;overflow-y:auto;padding:24px;min-width:480px;">

      {#if $stage === 'angle-selection'}
        {#if !$selectedYear}
          <!-- Empty state: no race selected -->
          <div style="text-align:center;margin-top:80px;">
            <h2 style="font-size:20px;font-weight:600;color:#e0e0e0;margin:0 0 12px;">Select a race to begin</h2>
            <p style="font-size:15px;color:#999999;line-height:1.6;">Choose a year and round above to surface story angles from ELO signal data.</p>
          </div>

        {:else if $anglesLoading}
          <!-- Skeleton cards -->
          <p style="font-size:13px;color:#999999;margin-bottom:16px;">Surfacing story angles...</p>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
            {#each [1, 2, 3] as _}
              <div style="height:200px;background:#1a1a1a;border:1px solid #2e2e2e;border-radius:8px;animation:pulse 1.5s ease-in-out infinite;"></div>
            {/each}
          </div>

        {:else if $anglesError}
          <!-- Error banner -->
          <div style="background:rgba(207,68,68,0.12);border:1px solid #cf4444;border-radius:6px;padding:16px;color:#cf4444;font-size:14px;">
            Something went wrong. {$anglesError} Please try again.
          </div>

        {:else if $angles.length === 0}
          <!-- No angles returned -->
          <div style="text-align:center;margin-top:80px;">
            <h2 style="font-size:20px;font-weight:600;color:#e0e0e0;margin:0 0 12px;">No angles available</h2>
            <p style="font-size:15px;color:#999999;line-height:1.6;">This race may be too recent or have incomplete data. Try another race.</p>
          </div>

        {:else}
          <!-- Angle cards grid -->
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
            {#each $angles as angle}
              <AngleCard
                {angle}
                selected={$selectedAngleId === angle.angle_id}
                on:select={onAngleSelect}
              />
            {/each}
          </div>

          <!-- Develop This Angle button -->
          <div style="display:flex;justify-content:flex-end;margin-top:16px;">
            <button
              on:click={developAngle}
              disabled={!$selectedAngleId || $outlineGenerating}
              style="height:44px;background:{$selectedAngleId && !$outlineGenerating ? '#e10600' : '#333333'};color:{$selectedAngleId && !$outlineGenerating ? '#ffffff' : '#666666'};font-weight:600;font-size:15px;border:none;border-radius:6px;padding:0 24px;cursor:{$selectedAngleId && !$outlineGenerating ? 'pointer' : 'not-allowed'};"
            >
              {$outlineGenerating ? 'Generating Outline...' : 'Develop This Angle'}
            </button>
          </div>
        {/if}

      {:else if $stage === 'outline-review'}
        <OutlinePanel
          beats={$outlineBeats}
          articleId={$articleId ?? ''}
          approving={$approvalPending}
          on:approve={onApprove}
          on:update={onOutlineUpdate}
          on:addBeat={onAddBeat}
          on:removeBeat={onRemoveBeat}
          on:reorderBeat={onReorderBeat}
        />

      {:else if $stage === 'beat-editing'}
        <!-- Stage 3: Beat editor — SSE streaming per beat -->
        {#if allBeatsComplete}
          <div style="background:#3a7a4a;border-radius:6px;padding:16px;margin-bottom:24px;font-size:14px;color:#6acc8a;">
            Prose complete. Review and fill in the placeholder hooks before exporting.
          </div>
        {/if}

        {#each $outlineBeats as beat, i}
          <BeatEditor
            bind:this={editorRefs[i]}
            beat_number={beat.beat_number}
            beat_title={beat.beat_title}
            article_id={$articleId ?? ''}
            auto_stream={currentStreamingBeat === beat.beat_number}
            on:streamComplete={onStreamComplete}
          />
        {/each}
      {/if}

    </main>

    <!-- Right sidebar — always visible -->
    <aside style="width:260px;background:#1a1a1a;border-left:1px solid #2e2e2e;flex-shrink:0;overflow-y:auto;">
      <FiveActSidebar acts={$actSidebarData} />
    </aside>

  </div>
</div>

<style>
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }
  @keyframes spin-dot {
    0% { opacity: 1; }
    50% { opacity: 0.3; }
    100% { opacity: 1; }
  }
</style>
