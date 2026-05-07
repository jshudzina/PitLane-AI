<script lang="ts">
  import { onMount, onDestroy } from 'svelte'
  import { Editor } from '@tiptap/core'
  import StarterKit from '@tiptap/starter-kit'
  import { PlaceholderQuote, PlaceholderContext, PlaceholderCausal } from '../extensions/placeholder-nodes'

  let editorElement: HTMLElement
  let editor: Editor | null = null
  let jsonOutput: string = ''
  let spikeResult: string = 'Not run yet'

  onMount(() => {
    editor = new Editor({
      element: editorElement,
      extensions: [
        StarterKit,
        PlaceholderQuote,
        PlaceholderContext,
        PlaceholderCausal,
      ],
      content: {
        type: 'doc',
        content: [
          {
            type: 'paragraph',
            content: [
              { type: 'text', text: 'Test prose: ' },
              { type: 'placeholderQuote', attrs: { type: 'quote' } },
              { type: 'text', text: ' more text ' },
              { type: 'placeholderContext', attrs: { type: 'context' } },
              { type: 'text', text: ' and ' },
              { type: 'placeholderCausal', attrs: { type: 'causal' } },
            ],
          },
        ],
      },
    })

    const json = editor.getJSON()
    jsonOutput = JSON.stringify(json, null, 2)

    const doc = json.content?.[0]?.content ?? []
    const hasQuote = doc.some((n: { type: string }) => n.type === 'placeholderQuote')
    const hasContext = doc.some((n: { type: string }) => n.type === 'placeholderContext')
    const hasCausal = doc.some((n: { type: string }) => n.type === 'placeholderCausal')

    if (hasQuote && hasContext && hasCausal) {
      spikeResult = 'SPIKE PASS: All three placeholder node types round-trip through getJSON()'
    } else {
      spikeResult = `SPIKE FAIL: missing nodes — quote:${hasQuote} context:${hasContext} causal:${hasCausal}`
    }

    return () => {
      editor?.destroy()
      editor = null
    }
  })
</script>

<div style="padding: 24px; background: #0f0f0f; min-height: 100vh; color: #e0e0e0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
  <h1 style="font-size: 20px; font-weight: 600; margin-bottom: 16px;">TipTap + Svelte 5 Spike (D-10)</h1>

  <div style="background: #1a1a1a; border: 1px solid #2e2e2e; border-radius: 8px; padding: 16px; margin-bottom: 16px;">
    <p style="font-size: 13px; color: #999; margin-bottom: 8px;">Spike Result:</p>
    <pre style="font-size: 13px; color: {spikeResult.startsWith('SPIKE PASS') ? '#6acc8a' : '#cf4444'};">{spikeResult}</pre>
  </div>

  <div style="background: #1a1a1a; border: 1px solid #2e2e2e; border-radius: 8px; padding: 16px; margin-bottom: 16px;">
    <p style="font-size: 13px; color: #999; margin-bottom: 8px;">TipTap Editor (contains three placeholder nodes):</p>
    <div bind:this={editorElement} style="background: #0f0f0f; padding: 16px; min-height: 80px; border: 1px solid #2e2e2e; border-radius: 4px;"></div>
  </div>

  <div style="background: #1a1a1a; border: 1px solid #2e2e2e; border-radius: 8px; padding: 16px;">
    <p style="font-size: 13px; color: #999; margin-bottom: 8px;">getJSON() output (must contain placeholderQuote, placeholderContext, placeholderCausal nodes):</p>
    <pre style="font-size: 12px; color: #777; overflow: auto; max-height: 300px;">{jsonOutput}</pre>
  </div>
</div>
