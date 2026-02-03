interface Props {
  index: number
  onClick: (index: number) => void
}

export function CitationLink({ index, onClick }: Props) {
  return (
    <sup>
      <button
        onClick={() => onClick(index)}
        className="text-burgundy hover:underline font-sans text-[0.75em] font-medium cursor-pointer"
        aria-label={`Go to source ${index}`}
      >
        [{index}]
      </button>
    </sup>
  )
}
