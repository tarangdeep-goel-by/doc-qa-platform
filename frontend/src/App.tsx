import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { AppLayout } from './layouts/AppLayout'
import { NewChatScreen } from './components/chat/NewChatScreen'
import { ChatInterface } from './components/chat/ChatInterface'
import { DocumentsPage } from './pages/DocumentsPage'
import { LoginPage } from './components/auth/LoginPage'
import { RequireAuth } from './components/auth/RequireAuth'
import { RequireRole } from './components/auth/RequireRole'

function App() {
  return (
    <BrowserRouter>
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: '#18181b',
            color: '#f0f0f0',
            border: '1px solid rgba(255,255,255,0.08)',
          },
        }}
      />
      <Routes>
        {/* Public */}
        <Route path="/login" element={<LoginPage />} />

        {/* Authenticated */}
        <Route element={<RequireAuth />}>
          <Route path="/" element={<AppLayout />}>
            <Route index element={<NewChatScreen />} />
            <Route path="chat/:chatId" element={<ChatInterface />} />
            <Route path="documents" element={
              <RequireRole allow={(u) => u.role === 'admin' || !!u.features?.client_document_view}>
                <DocumentsPage />
              </RequireRole>
            } />
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
