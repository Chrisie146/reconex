"use client"

import React, { useState, useEffect } from 'react'
import Sidebar from '@/components/Sidebar'
import CategoriesManager from '@/components/CategoriesManager'
import RulesManager from '@/components/RulesManager'
import LearnedRulesManager from '@/components/LearnedRulesManager'
import { FolderOpen, Settings2, Sparkles, AlertCircle, ArrowRight } from 'lucide-react'

const TABS = [
  { key: 'categories' as const, label: 'Categories',        icon: FolderOpen, accent: 'indigo' },
  { key: 'rules'      as const, label: 'Manual Rules',      icon: Settings2,  accent: 'indigo' },
  { key: 'learned'    as const, label: 'Learned Patterns',  icon: Sparkles,   accent: 'violet' },
]

export default function Page() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'categories' | 'rules' | 'learned'>('categories')

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    let sid = params.get('session_id')
    const tab = params.get('tab') as 'categories' | 'rules' | 'learned' | null

    if (!sid) {
      sid = localStorage.getItem('session_id') ||
            localStorage.getItem('current_session_id') ||
            localStorage.getItem('lastSessionId')
    }

    if (sid) { setSessionId(sid); localStorage.setItem('session_id', sid) }
    if (tab === 'rules' || tab === 'categories' || tab === 'learned') setActiveTab(tab)
  }, [])

  return (
    <div className="bg-neutral-50 min-h-screen">
      <Sidebar sessionId={sessionId} />

      <div className="ml-64 transition-all duration-300">
        <div className="max-w-[1400px] mx-auto px-6 py-6 space-y-6">

          {/* ── Page header ─────────────────────────────────────── */}
          <div>
            <h1 className="text-2xl font-bold text-neutral-900 tracking-tight flex items-center gap-2.5">
              <Settings2 className="w-6 h-6 text-indigo-500" />
              Categories &amp; Rules
            </h1>
            <p className="text-sm text-neutral-500 mt-1">
              Create custom categories, configure keyword rules, and manage auto-learned patterns.
            </p>
          </div>

          {/* ── Tab bar ─────────────────────────────────────────── */}
          <div className="flex items-center gap-1 rounded-xl border border-neutral-200 bg-white p-1 shadow-sm w-fit">
            {TABS.map(t => {
              const Icon = t.icon
              const isActive = activeTab === t.key
              return (
                <button
                  key={t.key}
                  onClick={() => setActiveTab(t.key)}
                  className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-all ${
                    isActive
                      ? t.accent === 'violet'
                        ? 'bg-violet-600 text-white shadow-sm'
                        : 'bg-indigo-600 text-white shadow-sm'
                      : 'text-neutral-600 hover:bg-neutral-100 hover:text-neutral-900'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {t.label}
                </button>
              )
            })}
          </div>

          {/* ── Tab content ─────────────────────────────────────── */}
          {activeTab === 'categories' && sessionId && <CategoriesManager sessionId={sessionId} />}
          {activeTab === 'rules'      && sessionId && <RulesManager sessionId={sessionId} />}
          {activeTab === 'learned'    && sessionId && <LearnedRulesManager sessionId={sessionId} />}

          {/* ── No session state ────────────────────────────────── */}
          {!sessionId && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 p-6 space-y-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-amber-500 mt-0.5 shrink-0" />
                <div>
                  <p className="text-sm font-medium text-amber-800">No statement selected</p>
                  <p className="text-sm text-amber-700 mt-1">Upload a statement first to access category and rule management.</p>
                </div>
              </div>
              <ol className="text-sm text-amber-700 space-y-1.5 list-decimal list-inside pl-8">
                <li>Go to the <a href="/" className="font-medium text-indigo-600 hover:underline inline-flex items-center gap-0.5">Dashboard <ArrowRight className="w-3 h-3" /></a></li>
                <li>Upload a CSV or PDF file</li>
                <li>Click &quot;Categories &amp; Rules&quot; in the sidebar</li>
              </ol>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

