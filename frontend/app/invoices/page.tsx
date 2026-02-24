"use client"

import React, { useEffect, useState } from "react"
import Sidebar from "../../components/Sidebar"
import InvoiceReviewList from "../components/InvoiceReviewList"

export const dynamic = 'force-dynamic'

export default function Page() {
  const [sessionId, setSessionId] = useState<string | null>(null)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    setSessionId(params.get('session_id'))
  }, [])

  return (
    <div className="flex h-screen bg-neutral-50">
      <Sidebar sessionId={sessionId} />
      <div className="flex-1 overflow-auto" style={{ marginLeft: 'var(--sidebar-w, 256px)', transition: 'margin-left 300ms ease-in-out' }}>
        <div className="px-8 py-6 max-w-7xl mx-auto">
          <InvoiceReviewList sessionId={sessionId} />
        </div>
      </div>
    </div>
  )
}
