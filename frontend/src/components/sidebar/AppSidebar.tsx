import { useEffect, useState } from 'react'
import { useNavigate, useParams, useLocation } from 'react-router-dom'
import { Plus, FileText } from 'lucide-react'
import { useAppStore } from '../../store/appStore'
import { ChatListItem } from './ChatListItem'
import { NewChatModal } from '../modals/NewChatModal'

export function AppSidebar() {
  const navigate = useNavigate()
  const location = useLocation()
  const { chatId } = useParams()
  const { chats, loadChats, loadDocuments } = useAppStore()
  const [showNewChatModal, setShowNewChatModal] = useState(false)

  useEffect(() => {
    loadChats()
    loadDocuments()
  }, [loadChats, loadDocuments])

  const handleChatClick = (id: string) => {
    navigate(`/chat/${id}`)
  }

  const handleNewChat = () => {
    setShowNewChatModal(true)
  }

  return (
    <>
      <aside className="w-80 bg-cream border-r border-ink/10 flex flex-col">
        {/* Header */}
        <div className="p-fluid-lg border-b border-ink/10">
          <h1 className="font-serif text-fluid-xl text-ink font-medium mb-fluid-md">
            Document Q&A
          </h1>
          <button
            onClick={handleNewChat}
            className="w-full flex items-center justify-center gap-2 px-fluid-md py-fluid-sm bg-burgundy text-cream rounded-lg hover:bg-burgundy/90 transition-colors font-sans text-fluid-sm"
          >
            <Plus className="w-4 h-4" />
            New Chat
          </button>
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
