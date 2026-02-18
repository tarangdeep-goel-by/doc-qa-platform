import type { Source } from '../types'

export function parseCitations(
  content: string,
  sources: Source[]
): string {
  let result = content

  // Format 1: (Document: "Title", Chunk 123) or [Document: "Title", Chunk 123]
  const docCitationRegex = /[\(\[]Document: "([^"]+)", Chunk (\d+)[\)\]]/g
  let nextIndex = 1
  const seen = new Map<string, number>()

  result = result.replace(docCitationRegex, (match, docTitle, chunkNum) => {
    const sourceIndex = sources.findIndex(s => s.doc_title === docTitle)
    if (sourceIndex === -1) return match

    const key = `${docTitle}:${chunkNum}`
    let index = seen.get(key)
    if (!index) {
      index = nextIndex++
      seen.set(key, index)
    }
    return `[[${index}]]`
  })

  // Format 2: [Source N] — backend LLM output format
  // Maps directly to source index (1-based)
  result = result.replace(/\[Source\s+(\d+)\]/g, (_match, num) => {
    const index = parseInt(num)
    if (index >= 1 && index <= sources.length) {
      return `[[${index}]]`
    }
    return _match
  })

  return result
}
