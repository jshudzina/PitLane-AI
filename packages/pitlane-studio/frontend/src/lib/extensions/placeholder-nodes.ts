import { Node, mergeAttributes } from '@tiptap/core'

export const PlaceholderQuote = Node.create({
  name: 'placeholderQuote',
  group: 'inline',
  inline: true,
  atom: true,

  addAttributes() {
    return {
      type: { default: 'quote' },
    }
  },

  parseHTML() {
    return [{ tag: 'span[data-placeholder-type="quote"]' }]
  },

  renderHTML({ HTMLAttributes }) {
    return ['span', mergeAttributes(HTMLAttributes, {
      'data-placeholder-type': 'quote',
      class: 'placeholder-hook placeholder-hook--quote',
      contenteditable: 'false',
      style: 'display:inline-block;background:#1a3a2a;border:1px solid #2a6a4a;color:#5aaa7a;font-family:Menlo,Consolas,monospace;font-size:13px;padding:2px 8px;border-radius:3px;cursor:default',
    }), 'JOURNALIST: Add quote']
  },
})

export const PlaceholderContext = Node.create({
  name: 'placeholderContext',
  group: 'inline',
  inline: true,
  atom: true,

  addAttributes() {
    return {
      type: { default: 'context' },
    }
  },

  parseHTML() {
    return [{ tag: 'span[data-placeholder-type="context"]' }]
  },

  renderHTML({ HTMLAttributes }) {
    return ['span', mergeAttributes(HTMLAttributes, {
      'data-placeholder-type': 'context',
      class: 'placeholder-hook placeholder-hook--context',
      contenteditable: 'false',
      style: 'display:inline-block;background:#1a2a3a;border:1px solid #2a4a6a;color:#5a8aaa;font-family:Menlo,Consolas,monospace;font-size:13px;padding:2px 8px;border-radius:3px;cursor:default',
    }), 'JOURNALIST: Add context']
  },
})

export const PlaceholderCausal = Node.create({
  name: 'placeholderCausal',
  group: 'inline',
  inline: true,
  atom: true,

  addAttributes() {
    return {
      type: { default: 'causal' },
    }
  },

  parseHTML() {
    return [{ tag: 'span[data-placeholder-type="causal"]' }]
  },

  renderHTML({ HTMLAttributes }) {
    return ['span', mergeAttributes(HTMLAttributes, {
      'data-placeholder-type': 'causal',
      class: 'placeholder-hook placeholder-hook--causal',
      contenteditable: 'false',
      style: 'display:inline-block;background:#2a2a1a;border:1px solid #5a4a2a;color:#aaaa5a;font-family:Menlo,Consolas,monospace;font-size:13px;padding:2px 8px;border-radius:3px;cursor:default',
    }), 'JOURNALIST: Add causal reasoning']
  },
})
