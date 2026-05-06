<script lang="ts">
  import { onMount, onDestroy, createEventDispatcher } from 'svelte'
  import { Editor } from '@tiptap/core'
  import StarterKit from '@tiptap/starter-kit'
  import { PlaceholderQuote, PlaceholderContext, PlaceholderCausal } from '../extensions/placeholder-nodes'
  import { openBeatStream } from '$lib/api'
  import type { BeatProseState } from '$lib/store'

  export let beat_number: number
  export let beat_title: string
  export let article_id: string
  export let auto_stream: boolean = false

  const dispatch = createEventDispatcher<{
    streamComplete: { beat_number: number }
  }>()

  let editorElement: HTMLElement
  let editor: Editor | null = null
  let status: 'pending' | 'streaming' | 'complete' | 'error' = 'pending'
  let streamingText = ''
  let errorMessage = ''
  let wordCount = 0

  export function getEditorJSON() {
    return editor?.getJSON() ?? null
  }

  onMount(() => {
    editor = new Editor({
      element: editorElement,
      extensions: [StarterKit, PlaceholderQuote, PlaceholderContext, PlaceholderCausal],
      content: '',
    })
    editor.on('update', () => {
      wordCount = editor?.getText().split(/\s+/).filter(Boolean).length ?? 0
    })
    if (auto_stream) startStream()
    return () => {
      editor?.destroy()
      editor = null
    }
  })

  export function startStream() {
    if (status === 'streaming' || status === 'complete') return
    status = 'streaming'
    streamingText = ''
    const es = openBeatStream(article_id, beat_number)
    es.addEventListener('beat_start', () => {
      console.log(`[BeatEditor] beat_start: beat ${beat_number} — ${beat_title}`)
    })
    es.addEventListener('token', (e: MessageEvent) => {
      const data = JSON.parse(e.data)
      streamingText += data.token
    })
    es.addEventListener('beat_done', (e: MessageEvent) => {
      const data = JSON.parse(e.data)
      editor?.commands.setContent(data.prose ?? '')
      const markers = [...(data.placeholder_markers ?? [])].sort((a: { offset: number }, b: { offset: number }) => b.offset - a.offset)
      for (const m of markers) {
        const nodeType = m.type === 'quote' ? 'placeholderQuote' : m.type === 'context' ? 'placeholderContext' : 'placeholderCausal'
        editor?.chain().insertContentAt(m.offset, { type: nodeType, attrs: { type: m.type } }).run()
      }
      wordCount = editor?.getText().split(/\s+/).filter(Boolean).length ?? 0
      status = 'complete'
      streamingText = ''
      es.close()
      dispatch('streamComplete', { beat_number })
    })
    es.addEventListener('error', (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data ?? '{}')
        errorMessage = data.message ?? 'Stream error'
      } catch {
        errorMessage = 'Stream error'
      }
      status = 'error'
      es.close()
    })
    es.onerror = () => {
      if (status !== 'complete') {
        status = 'error'
        errorMessage = 'Connection lost'
        es.close()
      }
    }
  }

  $: isStreaming = status === 'streaming'
  $: isComplete = status === 'complete'
</script>

<div style="
  border:1px solid {isStreaming ? '#2a5a8a' : '#2e2e2e'};
  border-radius:4px;
  overflow:hidden;
  margin-bottom:16px;
  transition:border-color 0.2s;
  {isStreaming ? 'animation:pulse-stream 1.5s ease-in-out infinite;' : ''}
">
  <!-- Beat header bar -->
  <div style="height:40px;background:#1a1a1a;border-bottom:1px solid #2e2e2e;display:flex;align-items:center;padding:0 12px;gap:12px;">
    <span style="font-size:13px;color:#e0e0e0;flex:1;">
      Beat {beat_number} — {beat_title}
    </span>

    {#if isStreaming}
      <span style="font-size:13px;color:#5a9acc;display:flex;align-items:center;gap:6px;">
        <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#5a9acc;animation:spin-dot 1s linear infinite;"></span>
        Generating...
      </span>
    {:else if isComplete}
      <span style="font-size:13px;color:#6acc8a;">✓</span>
    {/if}

    <button
      aria-label="Bold"
      on:click={() => editor?.chain().focus().toggleBold().run()}
      disabled={!editor || isStreaming}
      style="background:{editor?.isActive('bold') ? '#2e2e2e' : 'none'};border:none;color:{isStreaming ? '#444444' : '#999999'};font-size:13px;font-weight:700;cursor:{isStreaming ? 'not-allowed' : 'pointer'};padding:4px 8px;border-radius:3px;"
    >B</button>
    <button
      aria-label="Italic"
      on:click={() => editor?.chain().focus().toggleItalic().run()}
      disabled={!editor || isStreaming}
      style="background:{editor?.isActive('italic') ? '#2e2e2e' : 'none'};border:none;color:{isStreaming ? '#444444' : '#999999'};font-size:13px;font-style:italic;cursor:{isStreaming ? 'not-allowed' : 'pointer'};padding:4px 8px;border-radius:3px;"
    >I</button>
  </div>

  <!-- Editor canvas -->
  <div style="position:relative;background:{isStreaming ? '#1a2a3a' : '#0f0f0f'};transition:background 0.2s;min-height:120px;">
    <div
      bind:this={editorElement}
      style="padding:16px 20px;min-height:120px;font-size:15px;color:#e0e0e0;line-height:1.6;{isStreaming || status === 'pending' ? 'display:none;' : ''}"
    ></div>
    {#if isStreaming}
      <div style="padding:16px 20px;font-size:15px;color:#e0e0e0;line-height:1.6;white-space:pre-wrap;">{streamingText}<span style="display:inline-block;width:2px;height:1em;background:#5a9acc;animation:blink 1s step-end infinite;vertical-align:text-bottom;margin-left:2px;"></span></div>
    {:else if status === 'pending'}
      <div style="padding:16px 20px;font-size:13px;color:#444444;font-style:italic;">Waiting to generate...</div>
    {/if}
  </div>

  <!-- Error state -->
  {#if status === 'error'}
    <div style="background:rgba(207,68,68,0.12);border-top:1px solid #cf4444;padding:12px 16px;display:flex;align-items:center;gap:12px;">
      <span style="font-size:13px;color:#cf4444;flex:1;">{errorMessage}</span>
      <button
        on:click={startStream}
        style="background:#cf4444;color:#fff;border:none;padding:4px 12px;border-radius:4px;font-size:13px;cursor:pointer;"
      >Retry</button>
    </div>
  {/if}

  <!-- Beat footer bar -->
  <div style="height:32px;background:#141414;border-top:1px solid #252525;display:flex;align-items:center;padding:0 12px;">
    <span style="font-size:13px;color:#555555;">{wordCount} words</span>
  </div>
</div>

<style>
  @keyframes pulse-stream {
    0%, 100% { background: #1a2a3a; }
    50% { background: #1e3040; }
  }
  @keyframes spin-dot {
    0% { opacity: 1; }
    50% { opacity: 0.3; }
    100% { opacity: 1; }
  }
  @keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0; }
  }
  :global(.ProseMirror) {
    outline: none;
  }
  :global(.ProseMirror p) {
    margin: 0 0 12px;
  }
  :global(.ProseMirror p:last-child) {
    margin-bottom: 0;
  }
</style>
