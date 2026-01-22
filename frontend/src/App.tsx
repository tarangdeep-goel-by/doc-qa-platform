import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { AppLayout } from './layouts/AppLayout'
import { WelcomeScreen } from './components/welcome/WelcomeScreen'
import { ChatInterface } from './components/chat/ChatInterface'
import { DocumentsPage } from './pages/DocumentsPage'

function App() {
  return (
    <BrowserRouter>
      <Toaster position="bottom-right" />
      <Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<WelcomeScreen />} />
          <Route path="chat/:chatId" element={<ChatInterface />} />
          <Route path="documents" element={<DocumentsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
