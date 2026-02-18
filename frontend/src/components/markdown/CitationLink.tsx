interface Props {
  index: number
  onClick: (index: number) => void
}

export function CitationLink({ index, onClick }: Props) {
  return (
    <button
      onClick={() => onClick(index)}
      className="
        inline-flex items-center justify-center
        min-w-[1.25rem] h-5 px-1
        rounded-full bg-burgundy/20 text-burgundy
        text-[0.65rem] font-sans font-bold
        cursor-pointer hover:bg-burgundy/35
        transition-colors align-middle mx-0.5
        leading-none
      "
      aria-label={`Go to source ${index}`}
    >
      {index}
    </button>
  )
}
