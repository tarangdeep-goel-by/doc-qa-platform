import type { Source } from '../types'

export interface CitationInfo {
  sourceIndex: number
  docTitle: string
  chunkNum: number
}

export interface ParsedContent {
  cleanedContent: string
  citationMap: Map<number, CitationInfo>
}

export function parseCitations(
  content: string,
  sources: Source[]
): ParsedContent {
  // Match: (Document: "Title", Chunk 123) or [Document: "Title", Chunk 123]
  const citationRegex = /[\(\[]Document: "([^"]+)", Chunk (\d+)[\)\]]/g
  const citationMap = new Map<number, CitationInfo>()
  let nextIndex = 1
  const seen = new Map<string, number>()

  const cleanedContent = content.replace(citationRegex, (match, docTitle, chunkNum) => {
    // Find matching source by document title
    const sourceIndex = sources.findIndex(s => s.doc_title === docTitle)

    if (sourceIndex === -1) {
      return match // Keep original if not found
    }

    // Check for duplicate citation
    const key = `${docTitle}:${chunkNum}`
    let index = seen.get(key)

    if (!index) {
      index = nextIndex++
      seen.set(key, index)
      citationMap.set(index, { sourceIndex, docTitle, chunkNum: parseInt(chunkNum) })
    }

    return `[[${index}]]` // Placeholder for later conversion
  })

  return { cleanedContent, citationMap }
}
