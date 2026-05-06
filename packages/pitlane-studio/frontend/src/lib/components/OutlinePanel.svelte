<script lang="ts">
  import { createEventDispatcher } from 'svelte'
  import type { OutlineBeat } from '$lib/store'

  export let beats: OutlineBeat[] = []
  export let articleId: string
  export let approving: boolean = false

  const dispatch = createEventDispatcher<{
    approve: void
    update: OutlineBeat[]
    addBeat: void
    removeBeat: number
    reorderBeat: { beat_number: number; direction: 'up' | 'down' }
  }>()

  let deleteConfirm: number | null = null

  const MAX_BEATS = 8

  function updateBeatTitle(beat_number: number, value: string) {
    dispatch('update', beats.map(b => b.beat_number === beat_number ? { ...b, beat_title: value } : b))
  }

  function updateBeatAnchors(beat_number: number, value: string) {
    dispatch('update', beats.map(b => b.beat_number === beat_number ? { ...b, data_anchors: value } : b))
  }
</script>

<div style="padding:24px;">
  <h2 style="font-size:20px;font-weight:600;color:#e0e0e0;margin:0 0 8px;">Review Your Outline</h2>
  <p style="font-size:13px;color:#999999;margin:0 0 24px;line-height:1.4;">
    Edit beat titles and data anchors before approving. You cannot change these after approval.
  </p>

  <div style="display:flex;flex-direction:column;gap:12px;">
    {#each beats as beat, idx}
      <div style="display:flex;gap:12px;align-items:flex-start;">
        <div style="flex-shrink:0;width:24px;height:24px;background:#1a1a1a;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:13px;color:#999999;margin-top:10px;">
          {beat.beat_number}
        </div>

        <div style="flex:1;display:flex;flex-direction:column;gap:6px;">
          {#if deleteConfirm === beat.beat_number}
            <div style="background:#1a1a1a;border:1px solid #cf4444;border-radius:4px;padding:12px;font-size:13px;color:#e0e0e0;">
              Remove this beat? This cannot be undone.
              <div style="margin-top:8px;display:flex;gap:8px;">
                <button
                  on:click={() => { dispatch('removeBeat', beat.beat_number); deleteConfirm = null }}
                  style="background:#cf4444;color:#fff;border:none;padding:4px 12px;border-radius:4px;font-size:13px;cursor:pointer;"
                >Remove Beat</button>
                <button
                  on:click={() => deleteConfirm = null}
                  style="background:#2e2e2e;color:#e0e0e0;border:none;padding:4px 12px;border-radius:4px;font-size:13px;cursor:pointer;"
                >Keep It</button>
              </div>
            </div>
          {:else}
            <input
              type="text"
              value={beat.beat_title}
              on:input={e => updateBeatTitle(beat.beat_number, (e.target as HTMLInputElement).value)}
              style="width:100%;font-size:15px;color:#e0e0e0;background:#1a1a1a;border:1px solid #2e2e2e;border-radius:4px;padding:8px 12px;box-sizing:border-box;outline:none;"
              on:focus={e => (e.target as HTMLElement).style.borderColor='#e10600'}
              on:blur={e => (e.target as HTMLElement).style.borderColor='#2e2e2e'}
            />
            <textarea
              value={beat.data_anchors}
              on:input={e => updateBeatAnchors(beat.beat_number, (e.target as HTMLTextAreaElement).value)}
              style="width:100%;font-size:13px;font-family:'Menlo','Consolas',monospace;color:#999999;background:#141414;border:1px solid #252525;border-radius:4px;padding:8px 12px;min-height:56px;resize:vertical;box-sizing:border-box;outline:none;"
              on:focus={e => (e.target as HTMLElement).style.borderColor='#e10600'}
              on:blur={e => (e.target as HTMLElement).style.borderColor='#252525'}
            />
          {/if}
        </div>

        <div style="display:flex;flex-direction:column;gap:4px;flex-shrink:0;margin-top:8px;">
          <button
            aria-label="Move beat up"
            disabled={idx === 0}
            on:click={() => dispatch('reorderBeat', { beat_number: beat.beat_number, direction: 'up' })}
            style="background:none;border:none;color:#555555;cursor:{idx === 0 ? 'not-allowed' : 'pointer'};font-size:16px;padding:2px;line-height:1;"
          >↑</button>
          <button
            aria-label="Move beat down"
            disabled={idx === beats.length - 1}
            on:click={() => dispatch('reorderBeat', { beat_number: beat.beat_number, direction: 'down' })}
            style="background:none;border:none;color:#555555;cursor:{idx === beats.length - 1 ? 'not-allowed' : 'pointer'};font-size:16px;padding:2px;line-height:1;"
          >↓</button>
          <button
            aria-label="Remove beat"
            on:click={() => deleteConfirm = beat.beat_number}
            style="background:none;border:none;color:#555555;cursor:pointer;font-size:16px;padding:2px;line-height:1;"
            on:mouseenter={e => (e.target as HTMLElement).style.color='#cf4444'}
            on:mouseleave={e => (e.target as HTMLElement).style.color='#555555'}
          >🗑</button>
        </div>
      </div>
    {/each}
  </div>

  {#if beats.length < MAX_BEATS}
    <button
      on:click={() => dispatch('addBeat')}
      style="margin-top:16px;background:none;border:none;color:#999999;font-size:13px;cursor:pointer;display:flex;align-items:center;gap:4px;padding:0;"
    >
      + Add Beat
    </button>
  {:else}
    <span style="margin-top:16px;display:block;font-size:13px;color:#555555;">Maximum 8 beats reached</span>
  {/if}

  <div style="margin-top:48px;">
    <p style="font-size:13px;color:#999999;font-style:italic;margin:0 0 12px;">
      Once approved, you cannot edit beats. Prose generation will begin immediately.
    </p>
    <button
      on:click={() => dispatch('approve')}
      disabled={approving}
      style="width:100%;height:48px;background:{approving ? '#333333' : '#e10600'};color:{approving ? '#666666' : '#ffffff'};font-weight:600;font-size:15px;border:none;border-radius:6px;padding:0 32px;cursor:{approving ? 'not-allowed' : 'pointer'};"
    >
      {#if approving}Generating Beat 1 of {beats.length}...{:else}Approve Outline and Generate Prose{/if}
    </button>
  </div>
</div>
