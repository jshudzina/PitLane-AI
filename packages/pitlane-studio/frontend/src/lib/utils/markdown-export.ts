import type { JSONContent } from '@tiptap/core'

function serializeNode(node: JSONContent): string {
  if (!node) return ''

  switch (node.type) {
    case 'doc':
      return (node.content ?? []).map(serializeNode).join('')
    case 'paragraph':
      return (node.content ?? []).map(serializeNode).join('') + '\n\n'
    case 'text': {
      let text = node.text ?? ''
      if (node.marks) {
        for (const mark of node.marks) {
          if (mark.type === 'bold') text = `**${text}**`
          if (mark.type === 'italic') text = `_${text}_`
        }
      }
      return text
    }
    case 'placeholderQuote':
      return '[JOURNALIST: quote]'
    case 'placeholderContext':
      return '[JOURNALIST: context]'
    case 'placeholderCausal':
      return '[JOURNALIST: causal]'
    default:
      return (node.content ?? []).map(serializeNode).join('')
  }
}

export function exportMarkdown(beatJsonMap: Map<number, JSONContent | null>): string {
  const parts: string[] = []
  const sortedKeys = [...beatJsonMap.keys()].sort((a, b) => a - b)
  for (const beatNum of sortedKeys) {
    const json = beatJsonMap.get(beatNum)
    if (json) {
      parts.push(`## Beat ${beatNum}\n\n`)
      parts.push(serializeNode(json).trim())
      parts.push('\n\n')
    }
  }
  return parts.join('').trim()
}
