"use client"

import React from 'react'

export default function PreviewModal({ data, onClose, onApply }: any) {
  const { matches = [], count = 0, ruleId = null, sessionId = null } = data || {}

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black opacity-40" onClick={() => onClose()} />
      <div className="bg-white rounded shadow-lg w-[90%] max-w-4xl z-50 p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Preview Matches ({count})</h3>
          <div>
            <button className="px-3 py-1 bg-gray-200 rounded mr-2" onClick={() => onClose()}>Close</button>
            {ruleId && sessionId && (
              <button className="px-3 py-1 bg-green-600 text-white rounded" onClick={() => onApply(ruleId, sessionId)}>Apply Rule</button>
            )}
          </div>
        </div>

        <div className="max-h-96 overflow-auto">
          {matches.length === 0 ? (
            <div className="text-neutral-600">No matches.</div>
          ) : (
            <table className="w-full table-auto border-collapse">
              <thead>
                <tr className="text-left">
                  <th className="p-2 border">ID</th>
                  <th className="p-2 border">Date</th>
                  <th className="p-2 border">Description</th>
                  <th className="p-2 border">Amount</th>
                  <th className="p-2 border">Category</th>
                </tr>
              </thead>
              <tbody>
                {matches.map((m: any) => (
                  <tr key={m.id} className="odd:bg-gray-50">
                    <td className="p-2 border align-top">{m.id}</td>
                    <td className="p-2 border align-top">{m.date ? (typeof m.date === 'string' ? m.date : (m.date.toString?.() || '')) : ''}</td>
                    <td className="p-2 border align-top">{m.description}</td>
                    <td className="p-2 border align-top">{m.amount}</td>
                    <td className="p-2 border align-top">{m.category}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )
}
