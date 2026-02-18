import { Navigate, Outlet } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'
import type { User } from '../../types'

interface Props {
  role?: string
  allow?: (user: User) => boolean
  children?: React.ReactNode
}

export function RequireRole({ role, allow, children }: Props) {
  const user = useAuthStore(s => s.user)

  if (!user) return <Navigate to="/" replace />

  const allowed = allow ? allow(user) : user.role === role
  if (!allowed) return <Navigate to="/" replace />

  return children ? <>{children}</> : <Outlet />
}
