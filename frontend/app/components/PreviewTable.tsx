"use client"

import React, { useState } from 'react'

// TypeScript interfaces
interface ParsedRow {
  date?: string
  description?: string
  amount?: number | string
  issues?: string[]
}

interface OCRResult {
  rows: ParsedRow[]
  warnings: string[]
}

interface PreviewTableProps {
  result: {
    [key: number]: {
      rows?: ParsedRow[]
      warnings?: string[]
      error?: string
    } | {
      rows: ParsedRow[]
      warnings: string[]
    }
  } | null
}

export default function PreviewTable({ result }: PreviewTableProps){
  // Handle the new result structure (per-page results)
  let allRows: ParsedRow[] = []
  let allWarnings: string[] = []

  if (result) {
    Object.values(result).forEach(pageResult => {
      if (pageResult.rows) {
        allRows = allRows.concat(pageResult.rows)
      }
      if (pageResult.warnings) {
        allWarnings = allWarnings.concat(pageResult.warnings)
      }
    })
  }

  const [rows, setRows] = useState<ParsedRow[]>(allRows)

  const editCell = (idx: number, field: string, val: string) =>{
    const copy = [...rows]
    copy[idx] = {...copy[idx], [field]: val}
    setRows(copy)
  }

  return (
    <div className="overflow-auto border rounded">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-100">
          <tr>
            <th className="p-2">Date</th>
            <th className="p-2">Description</th>
            <th className="p-2">Amount</th>
            <th className="p-2">Issues</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className={r.issues && r.issues.length ? 'bg-yellow-50' : ''}>
              <td className="p-2">
                <input value={r.date || ''} onChange={(e)=>editCell(i,'date', e.target.value)} className="w-36" />
              </td>
              <td className="p-2">
                <input value={r.description || ''} onChange={(e)=>editCell(i,'description', e.target.value)} className="w-80" />
              </td>
              <td className="p-2">
                <input value={r.amount != null ? r.amount : ''} onChange={(e)=>editCell(i,'amount', e.target.value)} className="w-28" />
              </td>
              <td className="p-2 text-xs text-rose-600">{(r.issues || []).join(', ')}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
