"use client"

import React, { useEffect, useState } from "react"
import Sidebar from "../../components/Sidebar"
import InvoiceReviewList from "../components/InvoiceReviewList"

export const dynamic = 'force-dynamic'

export default function Page() {
  const [sessionId, setSessionId] = useState<string | null>(null)

  useEffect(() => {
    const params = new URLSearchParams(typeof window !== 'undefined' ? window.location.search : '')
    const sid = params.get('session_id')
    setSessionId(sid)
  }, [])

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar sessionId={sessionId} />
      <div className="flex-1 ml-64 overflow-auto">
        <div className="p-6 max-w-6xl mx-auto">
          <InvoiceReviewList sessionId={sessionId} />
          <div className="mt-4 text-xs text-gray-500">
            <strong>Disclaimer:</strong> Matches are suggestions only. No accounting entries or VAT claims are made automatically. Confirm each match before taking action.
          </div>
        </div>
      </div>
    </div>
  )
}
