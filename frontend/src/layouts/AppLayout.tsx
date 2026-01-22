import { Outlet } from 'react-router-dom'
import { AppSidebar } from '../components/sidebar/AppSidebar'

export function AppLayout() {
  return (
    <div className="flex h-screen bg-cream">
      {/* Sidebar */}
      <AppSidebar />

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <Outlet />
      </div>
    </div>
  )
}
