<script lang="ts">
  import { createEventDispatcher } from 'svelte'
  import type { AngleCandidate } from '$lib/store'

  export let angle: AngleCandidate
  export let selected: boolean = false

  const dispatch = createEventDispatcher<{ select: string | null }>()

  function confidenceLabel(c: number): { label: string; bg: string; text: string } {
    if (c >= 0.7) return { label: 'HIGH', bg: 'rgba(58,122,74,0.3)', text: '#6acc8a' }
    if (c >= 0.4) return { label: 'MED', bg: 'rgba(160,120,40,0.3)', text: '#ccaa44' }
    return { label: 'LOW', bg: 'rgba(120,60,60,0.3)', text: '#cc8888' }
  }

  $: conf = confidenceLabel(angle.confidence)

  function handleClick() {
    dispatch('select', selected ? null : angle.angle_id)
  }
</script>

<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- svelte-ignore a11y-no-static-element-interactions -->
<div
  on:click={handleClick}
  style="
    min-height:200px;
    background:{selected ? 'rgba(225,6,0,0.06)' : '#242424'};
    border:2px solid {selected ? '#e10600' : '#2e2e2e'};
    box-shadow:{selected ? '0 0 0 1px #e10600' : 'none'};
    border-radius:8px;
    padding:16px;
    cursor:pointer;
    transition:background 0.1s,border-color 0.1s;
  "
>
  <div style="font-size:13px;background:#1a1a1a;border:1px solid #2e2e2e;padding:4px 8px;border-radius:4px;display:inline-block;color:#999999;">
    {angle.signal_type}
  </div>

  <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-top:8px;gap:8px;">
    <div style="font-size:20px;font-weight:600;color:#e0e0e0;line-height:1.2;">{angle.name}</div>
    <span style="flex-shrink:0;background:{conf.bg};color:{conf.text};font-size:13px;padding:2px 8px;border-radius:100px;white-space:nowrap;">
      {conf.label}
    </span>
  </div>

  <div style="font-size:13px;font-family:'Menlo','Consolas',monospace;color:#999999;line-height:1.5;margin-top:8px;overflow:hidden;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;">
    {angle.data_rationale}
  </div>
</div>
