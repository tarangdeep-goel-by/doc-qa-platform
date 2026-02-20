import { Outlet } from 'react-router-dom'
import { AppSidebar } from '../components/sidebar/AppSidebar'
import { useUIStore } from '../store/uiStore'

export function AppLayout() {
  const { sidebarOpen, closeSidebar } = useUIStore()

  return (
    <div className="flex h-screen bg-cream">
      {/* Backdrop — mobile only, animated */}
      <div
        className={`
          fixed inset-0 z-40 md:hidden
          bg-black/50 backdrop-blur-[2px]
          transition-[opacity,visibility] duration-250
          ${sidebarOpen ? 'opacity-100 visible' : 'opacity-0 invisible'}
        `}
        onClick={closeSidebar}
        aria-hidden={!sidebarOpen}
      />

      {/* Sidebar — drawer on mobile, static on desktop */}
      <div
        className={`
          fixed inset-y-0 left-0 z-50 w-80
          transition-transform duration-250 ease-[cubic-bezier(0.16,1,0.3,1)]
          md:static md:translate-x-0 md:transition-none
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
        `}
      >
        <AppSidebar />
      </div>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <Outlet />
      </div>
    </div>
  )
}
