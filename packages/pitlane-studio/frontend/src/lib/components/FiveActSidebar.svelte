<script lang="ts">
  import type { ActData } from '$lib/store'

  export let acts: Record<number, ActData> = {}

  const ACT_LABELS: Record<number, string> = {
    1: 'Grid & Qualifying',
    2: 'Lap 1 Chaos',
    3: 'Pit Window',
    4: 'Final Stint',
    5: 'Championship Implications',
  }

  function getKeyDataPoint(act: ActData | undefined): string {
    if (!act?.data) return '—'
    const val = Object.values(act.data).find(v => typeof v === 'string' || typeof v === 'number')
    if (val === undefined) return '—'
    return String(val)
  }

  function getDataSources(act: ActData | undefined): string {
    if (!act?.data || Object.keys(act.data).length === 0) return '—'
    return Object.keys(act.data).join(', ')
  }
</script>

<div style="padding:16px;font-size:13px;color:#999999;text-transform:uppercase;letter-spacing:0.08em;border-bottom:1px solid #2e2e2e;">Five Acts</div>

{#each [1, 2, 3, 4, 5] as n}
  {@const act = acts[n]}
  <div style="padding:12px 16px;border-bottom:1px solid #2e2e2e;min-height:56px;">
    <div style="font-size:13px;color:#e0e0e0;">Act {n} — {act?.label ?? ACT_LABELS[n]}</div>
    <div style="font-size:13px;color:#999999;margin-top:2px;">{getDataSources(act)}</div>
    <div style="font-size:13px;font-family:'Menlo','Consolas',monospace;color:#777777;margin-top:2px;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;">
      {getKeyDataPoint(act)}
    </div>
  </div>
{/each}
