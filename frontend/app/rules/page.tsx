"use client"

import React, { useState, useEffect } from 'react'
import Sidebar from '@/components/Sidebar'
import CategoriesManager from '@/components/CategoriesManager'
import RulesManager from '@/components/RulesManager'
import LearnedRulesManager from '@/components/LearnedRulesManager'

export default function Page() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'categories' | 'rules' | 'learned'>('categories')

  useEffect(() => {
    // Get session ID and tab from URL parameters
    const params = new URLSearchParams(window.location.search)
    let sid = params.get('session_id')
    const tab = params.get('tab') as 'categories' | 'rules' | 'learned' | null
    
    // If not in URL, try common localStorage keys
    if (!sid) {
      sid = localStorage.getItem('session_id') || 
            localStorage.getItem('current_session_id') ||
            localStorage.getItem('lastSessionId')
    }
    
    if (sid) {
      setSessionId(sid)
      // Store for future use
      localStorage.setItem('session_id', sid)
    }

    // Set active tab if specified in URL
    if (tab === 'rules' || tab === 'categories' || tab === 'learned') {
      setActiveTab(tab)
    }
  }, [])

  return (
    <div className="bg-white">
      <Sidebar sessionId={sessionId} />

      <div className="ml-64 transition-all duration-300">
        <div className="container mx-auto p-4">
          <div className="mb-6">
            <h1 className="text-3xl font-bold text-gray-900 mb-4">Category & Rule Management</h1>
            <p className="text-gray-600">Create custom categories, set up rules, and manage auto-learned patterns</p>
          </div>

          {/* Tab Navigation */}
          <div className="flex border-b border-gray-200 mb-6">
            <button
              onClick={() => setActiveTab('categories')}
              className={`px-6 py-3 font-medium text-sm ${
                activeTab === 'categories'
                  ? 'border-b-2 border-blue-500 text-blue-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              📁 Categories
            </button>
            <button
              onClick={() => setActiveTab('rules')}
              className={`px-6 py-3 font-medium text-sm ${
                activeTab === 'rules'
                  ? 'border-b-2 border-blue-500 text-blue-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              ⚙️ Manual Rules
            </button>
            <button
              onClick={() => setActiveTab('learned')}
              className={`px-6 py-3 font-medium text-sm ${
                activeTab === 'learned'
                  ? 'border-b-2 border-purple-500 text-purple-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              ✨ Learned Patterns
            </button>
          </div>

          {/* Tab Content */}
          {activeTab === 'categories' && sessionId && <CategoriesManager sessionId={sessionId} />}
          {activeTab === 'rules' && sessionId && <RulesManager sessionId={sessionId} />}
          {activeTab === 'learned' && sessionId && <LearnedRulesManager sessionId={sessionId} />}
          
          {!sessionId && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
              <p className="text-gray-600 mb-4">Please upload a statement first to access category and rule management</p>
              <ol className="text-gray-600 space-y-2 text-sm list-decimal list-inside">
                <li>Go to the <a href="/" className="text-blue-600 hover:underline">Dashboard</a></li>
                <li>Upload a CSV or PDF file</li>
                <li>Click "Categories & Rules" in the left menu, or click the "Rules" button that appears after upload</li>
              </ol>
              <p className="text-gray-500 text-sm mt-4">Or navigate directly with URL: <code className="bg-gray-100 px-2 py-1 rounded">/rules?session_id=YOUR_SESSION_ID</code></p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

