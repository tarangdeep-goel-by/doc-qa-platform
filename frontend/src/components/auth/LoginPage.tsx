import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../../store/authStore'

export function LoginPage() {
  const navigate = useNavigate()
  const login = useAuthStore(s => s.login)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await login(email, password)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-cream flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="bg-cream-dark border border-glass-border rounded-xl shadow-2xl p-fluid-xl">
          <h1 className="font-sans text-fluid-2xl text-ink font-medium text-center mb-fluid-sm">
            Document Q&A
          </h1>
          <p className="font-sans text-fluid-sm text-ink/50 text-center mb-fluid-lg">
            Sign in to continue
          </p>

          <form onSubmit={handleSubmit} className="space-y-fluid-md">
            <div>
              <label className="block font-sans text-fluid-sm text-ink/70 mb-1">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                autoFocus
                className="w-full px-fluid-md py-fluid-sm border border-glass-border bg-cream rounded-lg focus:outline-none focus:ring-2 focus:ring-burgundy/30 font-sans text-fluid-base text-ink"
                placeholder="admin@example.com"
              />
            </div>

            <div>
              <label className="block font-sans text-fluid-sm text-ink/70 mb-1">
                Password
              </label>
              <input
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                className="w-full px-fluid-md py-fluid-sm border border-glass-border bg-cream rounded-lg focus:outline-none focus:ring-2 focus:ring-burgundy/30 font-sans text-fluid-base text-ink"
                placeholder="••••••••"
              />
            </div>

            {error && (
              <p className="font-sans text-fluid-sm text-red-600 text-center">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full px-fluid-lg py-fluid-sm bg-burgundy text-cream rounded-lg hover:bg-burgundy/90 transition-colors font-sans text-fluid-base font-medium disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
