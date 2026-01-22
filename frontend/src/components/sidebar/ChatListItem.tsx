import { useState } from 'react'
import { MessageSquare, Trash2 } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import type { Chat } from '../../types'
import { useAppStore } from '../../store/appStore'

interface Props {
  chat: Chat
  isActive: boolean
  onClick: () => void
}

export function ChatListItem({ chat, isActive, onClick }: Props) {
  const { deleteChat } = useAppStore()
  const [isDeleting, setIsDeleting] = useState(false)

  const handleDelete = async (e: React.MouseEvent) => {
    e.stopPropagation()
    if (confirm(`Delete chat "${chat.name}"?`)) {
      setIsDeleting(true)
      await deleteChat(chat.id)
      // Component will unmount after successful deletion
    }
  }

  const timeAgo = formatDistanceToNow(new Date(chat.updated_at), { addSuffix: true })

  return (
    <div
      onClick={onClick}
      className={`
        group relative px-fluid-md py-fluid-sm rounded-lg cursor-pointer transition-colors
        ${isActive
          ? 'bg-burgundy/10 border border-burgundy/20'
          : 'hover:bg-ink/5 border border-transparent'
        }
        ${isDeleting ? 'opacity-50 pointer-events-none' : ''}
      `}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <h3 className="font-sans text-fluid-sm text-ink font-medium truncate">
            {chat.name}
          </h3>
          <div className="flex items-center gap-2 mt-1">
            <p className="font-sans text-fluid-xs text-ink/50">
              {timeAgo}
            </p>
            {chat.message_count > 0 && (
              <div className="flex items-center gap-1">
                <MessageSquare className="w-3 h-3 text-ink/40" />
                <span className="font-sans text-fluid-xs text-ink/40">
                  {chat.message_count}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Delete button - show on hover */}
        <button
          onClick={handleDelete}
          className="opacity-0 group-hover:opacity-100 p-1 hover:bg-red-500/10 rounded transition-opacity"
          title="Delete chat"
        >
          <Trash2 className="w-4 h-4 text-red-500" />
        </button>
      </div>

      {/* Document count indicator */}
      {chat.doc_ids.length > 0 && (
        <div className="mt-2 flex items-center gap-1">
          <div className="w-1.5 h-1.5 rounded-full bg-burgundy/40" />
          <span className="font-sans text-fluid-xs text-ink/40">
            {chat.doc_ids.length} {chat.doc_ids.length === 1 ? 'document' : 'documents'}
          </span>
        </div>
      )}
    </div>
  )
}
