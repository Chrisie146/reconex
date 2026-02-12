"use client"

import React from 'react'
import { apiFetch } from '@/lib/apiFetch'
import RuleEditor from './RuleEditor'
import PreviewModal from './PreviewModal'

export default function RulesTable() {
  const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000'
  const [rules, setRules] = React.useState<any[]>([])
  const [loading, setLoading] = React.useState(true)
  const [editing, setEditing] = React.useState<any>(null)
  const [previewOpen, setPreviewOpen] = React.useState(false)
  const [previewData, setPreviewData] = React.useState<any>({ matches: [], count: 0, ruleId: null })

  async function load() {
    setLoading(true)
    try {
      const j = await apiFetch(`${API_BASE}/rules`)
      setRules(j.rules || [])
    } catch (e) {
      console.error(e)
      setRules([])
    } finally {
      setLoading(false)
    }
  }

  React.useEffect(() => { load() }, [])

  async function del(id: number) {
    if (!confirm('Delete rule?')) return
    try {
      await apiFetch(`${API_BASE}/rules/${id}`, { method: 'DELETE' })
      await load()
    } catch (e) {
      alert('Delete failed')
    }
  }

  async function preview(id: number) {
    const sid = prompt('Enter session_id to preview against:')
    if (!sid) return
    try {
      const j = await apiFetch(`${API_BASE}/rules/${id}/preview`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ session_id: sid }) })
      setPreviewData({ matches: j.matches || [], count: j.count || 0, ruleId: id, sessionId: sid })
      setPreviewOpen(true)
    } catch (e: any) {
      alert('Preview failed: ' + (e.message || e))
    }
  }

  async function applyRule(ruleId: number, sessionId: string) {
    if (!confirm('Apply rule to session? This can be undone via Undo.')) return
    try {
      const j = await apiFetch(`${API_BASE}/rules/${ruleId}/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId })
      })
      alert(j.message || `Updated ${j.updated_count || 0}`)
      setPreviewOpen(false)
      await load()
    } catch (e: any) {
      alert('Apply failed: ' + (e.message || e))
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">Rules</h2>
        <div>
          <button className="px-3 py-1 bg-blue-600 text-white rounded" onClick={() => setEditing({})}>Create Rule</button>
          <button className="ml-2 px-3 py-1 bg-gray-200 rounded" onClick={load}>Refresh</button>
        </div>
      </div>

      {loading ? (
        <div>Loading...</div>
      ) : rules.length === 0 ? (
        <div>No rules defined.</div>
      ) : (
        <div className="space-y-2">
          {rules.map(r => (
            <div key={r.id} className="p-3 border rounded flex items-center justify-between">
              <div>
                <div className="font-medium">{r.name}</div>
                <div className="text-sm text-neutral-600">Priority: {r.priority} • {r.enabled ? 'Enabled' : 'Disabled'} • Auto apply: {r.auto_apply ? 'Yes' : 'No'}</div>
              </div>
              <div className="flex items-center space-x-2">
                <button className="px-2 py-1 bg-gray-200 rounded" onClick={() => { setEditing(r) }}>Edit</button>
                <button className="px-2 py-1 bg-yellow-100 rounded" onClick={() => preview(r.id)}>Preview</button>
                <button className="px-2 py-1 bg-red-100 text-red-700 rounded" onClick={() => del(r.id)}>Delete</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {editing && (
        <div className="mt-4">
          <RuleEditor rule={editing} onSave={() => { setEditing(null); load() }} onClose={() => { setEditing(null) }} />
        </div>
      )}

      {previewOpen && (
        <PreviewModal data={previewData} onClose={() => setPreviewOpen(false)} onApply={applyRule} />
      )}
    </div>
  )
}
