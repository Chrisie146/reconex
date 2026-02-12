"use client"

import React from 'react'
import MappingPage from '../components/MappingPage'
import Sidebar from '@/components/Sidebar'

export default function Page() {
  // Extract session_id from URL
  const searchParams = new URLSearchParams(typeof window !== 'undefined' ? window.location.search : '')
  const sessionId = searchParams.get('session_id')

  return (
    <div className="bg-white">
      <Sidebar sessionId={sessionId} />
      
      <div className="ml-64 transition-all duration-300">
        <div className="container mx-auto p-4">
          <MappingPage />
        </div>
      </div>
    </div>
  )
}
