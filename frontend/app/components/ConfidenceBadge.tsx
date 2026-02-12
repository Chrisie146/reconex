"use client"

import React from "react"

type Props = { classification: string }

export default function ConfidenceBadge({ classification }: Props) {
  const cls = (classification || "Low").toLowerCase()
  const bg = cls === "high" ? "bg-green-100 text-green-800" : cls === "medium" ? "bg-yellow-100 text-yellow-800" : "bg-gray-100 text-gray-800"
  return (
    <span className={`inline-block px-2 py-1 rounded text-xs font-semibold ${bg}`}>{classification}</span>
  )
}
