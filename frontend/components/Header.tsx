'use client'

import { Upload, LogOut, User } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { getAuthUser, logout } from '@/lib/auth'

export default function Header() {
  const router = useRouter()
  const user = getAuthUser()

  const handleLogout = () => {
    logout()
    router.push('/login')
  }

  return (
    <header className="bg-white border-b border-neutral-200">
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-neutral-100 rounded-lg">
              <Upload className="w-6 h-6 text-neutral-900" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-neutral-900">Bank Statement Analyzer</h1>
              <p className="text-neutral-600 mt-1">Professional financial statement processing for small businesses</p>
            </div>
          </div>

          {user && (
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2 text-sm text-neutral-600">
                <User className="w-4 h-4" />
                <span>{user.email}</span>
              </div>
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 px-3 py-1.5 text-sm text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100 rounded-md transition-colors"
              >
                <LogOut className="w-4 h-4" />
                Logout
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
