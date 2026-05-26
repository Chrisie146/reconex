'use client'

import { LogOut, User } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { getAuthUser, logout } from '@/lib/auth'
import ThemeToggle from './ThemeToggle'

export default function Header() {
  const router = useRouter()
  const user = getAuthUser()

  const handleLogout = () => {
    logout()
    router.push('/login')
  }

  return (
    <header className="bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800 transition-colors duration-200">
      <div className="max-w-6xl mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <span className="text-xl font-semibold tracking-tight text-neutral-950 dark:text-white lowercase">reconex</span>
          </div>

          <div className="flex items-center gap-2">
            <ThemeToggle />
            {user && (
              <div className="flex items-center gap-3 ml-2">
                <div className="flex items-center gap-2 text-sm text-neutral-600 dark:text-neutral-400">
                  <User className="w-4 h-4" />
                  <span>{user.email}</span>
                </div>
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-md transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  Logout
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}
