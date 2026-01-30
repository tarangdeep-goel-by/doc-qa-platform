import { useEffect, useState } from 'react'
import { useNavigate, useParams, useLocation } from 'react-router-dom'
import { Plus, FileText, Trash2, X, Check } from 'lucide-react'
import toast from 'react-hot-toast'
import { useAppStore } from '../../store/appStore'
import { ChatListItem } from './ChatListItem'
import { NewChatModal } from '../modals/NewChatModal'
import * as api from '../../api/client'

export function AppSidebar() {
  const navigate = useNavigate()
  const location = useLocation()
  const { chatId } = useParams()
  const { chats, loadChats, loadDocuments } = useAppStore()
  const [showNewChatModal, setShowNewChatModal] = useState(false)
  const [selectionMode, setSelectionMode] = useState(false)
  const [selectedChats, setSelectedChats] = useState<Set<string>>(new Set())
  const [isBulkDeleting, setIsBulkDeleting] = useState(false)

  useEffect(() => {
    loadChats()
    loadDocuments()
  }, [loadChats, loadDocuments])

  const handleChatClick = (id: string) => {
    if (selectionMode) {
      toggleSelection(id)
    } else {
      navigate(`/chat/${id}`)
    }
  }

  const handleNewChat = () => {
    setShowNewChatModal(true)
  }

  const toggleSelection = (chatId: string) => {
    const newSelection = new Set(selectedChats)
    if (newSelection.has(chatId)) {
      newSelection.delete(chatId)
    } else {
      newSelection.add(chatId)
    }
    setSelectedChats(newSelection)
  }

  const toggleSelectionMode = () => {
    setSelectionMode(!selectionMode)
    setSelectedChats(new Set())
  }

  const handleBulkDelete = async () => {
    if (selectedChats.size === 0) return

    if (!confirm(`Delete ${selectedChats.size} chat(s)?\n\nThis action cannot be undone.`)) {
      return
    }

    setIsBulkDeleting(true)
    try {
      const response = await api.bulkDeleteChats(Array.from(selectedChats))

      if (response.successful > 0) {
        toast.success(`${response.successful} chat(s) deleted successfully`)
      }

      if (response.failed > 0) {
        toast.error(`${response.failed} chat(s) failed to delete`)
      }

      // Reload chats
      await loadChats()
      setSelectedChats(new Set())
      setSelectionMode(false)

      // Navigate to home if active chat was deleted
      if (chatId && selectedChats.has(chatId)) {
        navigate('/')
      }
    } catch (error) {
      toast.error('Bulk delete failed')
    } finally {
      setIsBulkDeleting(false)
    }
  }

  return (
    <>
      <aside className="w-80 bg-cream border-r border-ink/10 flex flex-col">
        {/* Header */}
        <div className="p-fluid-lg border-b border-ink/10">
          <h1 className="font-serif text-fluid-xl text-ink font-medium mb-fluid-md">
            Document Q&A
          </h1>

          {selectionMode ? (
            <div className="flex gap-2">
              <button
                onClick={handleBulkDelete}
                disabled={selectedChats.size === 0 || isBulkDeleting}
                className="flex-1 flex items-center justify-center gap-2 px-fluid-md py-fluid-sm bg-red-500 text-white rounded-lg hover:bg-red-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-sans text-fluid-sm"
              >
                <Trash2 className="w-4 h-4" />
                Delete {selectedChats.size > 0 ? selectedChats.size : ''}
              </button>
              <button
                onClick={toggleSelectionMode}
                className="px-fluid-md py-fluid-sm border border-ink/20 text-ink rounded-lg hover:bg-ink/5 transition-colors font-sans text-fluid-sm"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <div className="flex gap-2">
              <button
                onClick={handleNewChat}
                className="flex-1 flex items-center justify-center gap-2 px-fluid-md py-fluid-sm bg-burgundy text-cream rounded-lg hover:bg-burgundy/90 transition-colors font-sans text-fluid-sm"
              >
                <Plus className="w-4 h-4" />
                New Chat
              </button>
              {chats.length > 0 && (
                <button
                  onClick={toggleSelectionMode}
                  className="px-fluid-md py-fluid-sm border border-ink/20 text-ink rounded-lg hover:bg-ink/5 transition-colors font-sans text-fluid-sm"
                  title="Select chats"
                >
                  <Check className="w-4 h-4" />
                </button>
              )}
            </div>
          )}
        </div>

        {/* Navigation */}
        <div className="p-fluid-sm border-b border-ink/10">
          <button
            onClick={() => navigate('/documents')}
            className={`
              w-full flex items-center gap-2 px-fluid-md py-fluid-sm rounded-lg transition-colors font-sans text-fluid-sm
              ${location.pathname === '/documents'
                ? 'bg-burgundy/10 text-burgundy border border-burgundy/20'
                : 'text-ink/70 hover:bg-ink/5'
              }
            `}
          >
            <FileText className="w-4 h-4" />
            Documents
          </button>
        </div>

        {/* Chat list */}
        <div className="flex-1 overflow-y-auto">
          {chats.length === 0 ? (
            <div className="p-fluid-lg text-center">
              <p className="font-sans text-fluid-sm text-ink/50">
                No chats yet. Create your first chat to get started.
              </p>
            </div>
          ) : (
            <div className="p-fluid-sm space-y-1">
              {chats.map(chat => (
                <ChatListItem
                  key={chat.id}
                  chat={chat}
                  isActive={chat.id === chatId}
                  onClick={() => handleChatClick(chat.id)}
                  selectionMode={selectionMode}
                  isSelected={selectedChats.has(chat.id)}
                  onToggleSelection={() => toggleSelection(chat.id)}
                />
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-fluid-md border-t border-ink/10">
          <p className="font-sans text-fluid-xs text-ink/40 text-center">
            Powered by RAG
          </p>
        </div>
      </aside>

      {/* New Chat Modal */}
      {showNewChatModal && (
        <NewChatModal
          onClose={() => setShowNewChatModal(false)}
          onChatCreated={(chatId) => {
            setShowNewChatModal(false)
            navigate(`/chat/${chatId}`)
          }}
        />
      )}
    </>
  )
}
