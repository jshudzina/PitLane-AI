<script lang="ts">
  import { get } from 'svelte/store'
  import RaceSelector from '$lib/components/RaceSelector.svelte'
  import AngleCard from '$lib/components/AngleCard.svelte'
  import OutlinePanel from '$lib/components/OutlinePanel.svelte'
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

  let copyLabel = 'Copy Markdown'

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
      stage.set('beat-editing')
    } catch (e) {
      anglesError.set(e instanceof Error ? e.message : 'Approval failed')
    } finally {
      approvalPending.set(false)
    }
  }

  function copyMarkdown() {
    const beats = get(outlineBeats)
    const md = beats.map(b => `## Beat ${b.beat_number}: ${b.beat_title}\n\n${b.data_anchors}`).join('\n\n---\n\n')
    navigator.clipboard.writeText(md).then(() => {
      copyLabel = 'Copied!'
      setTimeout(() => { copyLabel = 'Copy Markdown' }, 2000)
    })
  }

  // Act labels
  const ACT_LABELS: Record<number, string> = {
    1: 'Grid & Qualifying',
    2: 'Lap 1 Chaos',
    3: 'Pit Window',
    4: 'Final Stint',
    5: 'Championship Implications',
  }
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
      on:click={copyMarkdown}
      style="height:36px;background:#e10600;color:#ffffff;font-weight:600;font-size:13px;border:none;border-radius:6px;padding:0 16px;cursor:pointer;"
    >{copyLabel}</button>
  </header>

  <!-- Body -->
  <div style="flex:1;display:flex;overflow:hidden;">

    <!-- Left panel — hidden in Stage 1 -->
    {#if $stage !== 'angle-selection'}
      <aside style="width:280px;background:#1a1a1a;border-right:1px solid #2e2e2e;flex-shrink:0;overflow-y:auto;">
        <div style="padding:16px;font-size:13px;color:#999999;text-transform:uppercase;letter-spacing:0.08em;">Outline</div>
        {#each $outlineBeats as beat}
          <div style="height:40px;display:flex;align-items:center;padding:0 16px;font-size:13px;color:#999999;border-left:2px solid transparent;">
            {beat.beat_number}. {beat.beat_title}
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
        <!-- Stage 3: Beat editor — implemented in 03-06 -->
        <div style="padding:24px;color:#999999;font-size:15px;">Beat editor loading...</div>
      {/if}

    </main>

    <!-- Right sidebar — always visible -->
    <aside style="width:260px;background:#1a1a1a;border-left:1px solid #2e2e2e;flex-shrink:0;overflow-y:auto;">
      <div style="padding:16px;font-size:13px;color:#999999;text-transform:uppercase;letter-spacing:0.08em;border-bottom:1px solid #2e2e2e;">Five Acts</div>
      {#each [1, 2, 3, 4, 5] as n}
        {@const act = $actSidebarData[n]}
        <div style="padding:12px 16px;border-bottom:1px solid #2e2e2e;">
          <div style="font-size:13px;color:#e0e0e0;">Act {n} — {act?.label ?? ACT_LABELS[n]}</div>
          {#if act?.data && Object.keys(act.data).length > 0}
            <div style="font-size:13px;font-family:'Menlo','Consolas',monospace;color:#777777;margin-top:4px;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;">
              {JSON.stringify(act.data).slice(0, 80)}
            </div>
          {:else}
            <div style="font-size:13px;color:#444444;margin-top:4px;">—</div>
          {/if}
        </div>
      {/each}
    </aside>

  </div>
</div>

<style>
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }
</style>
