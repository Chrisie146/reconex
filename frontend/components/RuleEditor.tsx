"use client"

import React from 'react'
import { apiFetch } from '@/lib/apiFetch'

type Condition = { field: string; op: string; value: string }

export default function RuleEditor({ rule, onSave, onClose }: any) {
  const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000'
  const [name, setName] = React.useState(rule?.name || '')
  const [enabled, setEnabled] = React.useState(rule?.enabled ?? true)
  const [priority, setPriority] = React.useState(rule?.priority ?? 100)
  const [autoApply, setAutoApply] = React.useState(rule?.auto_apply ?? false)
  const [conditions, setConditions] = React.useState<Condition[]>(rule?.conditions?.conditions || [{ field: 'description', op: 'contains', value: '' }])
  const [actionType, setActionType] = React.useState(rule?.action?.type || 'set_category')
  const [actionPayload, setActionPayload] = React.useState(rule?.action?.category || rule?.action?.merchant || '')
  const [errors, setErrors] = React.useState<string[]>([])

  React.useEffect(() => {
    if (rule) {
      setName(rule.name || '')
      setEnabled(rule.enabled ?? true)
      setPriority(rule.priority ?? 100)
      setAutoApply(rule.auto_apply ?? false)
      setConditions(rule.conditions?.conditions || [{ field: 'description', op: 'contains', value: '' }])
      setActionType(rule.action?.type || 'set_category')
      setActionPayload(rule.action?.category || rule.action?.merchant || '')
    }
  }, [rule])

  function updateCond(idx: number, key: keyof Condition, val: string) {
    const next = [...conditions]
    ;(next[idx] as any)[key] = val
    setConditions(next)
  }

  function addCond() {
    setConditions([...conditions, { field: 'description', op: 'contains', value: '' }])
  }

  function removeCond(i: number) {
    const next = conditions.filter((_, idx) => idx !== i)
    setConditions(next)
  }

  async function save() {
    const payload: any = {
      name,
      enabled,
      priority,
      conditions: { match_type: 'all', conditions },
      action: actionType === 'set_category' ? { type: 'set_category', category: actionPayload } : { type: 'set_merchant', merchant: actionPayload },
      auto_apply: autoApply
    }

    // Validate before sending
    const errs: string[] = []
    if (!name || name.trim().length < 2) errs.push('Name required (min 2 chars)')
    conditions.forEach((c, i) => {
      if (!c.field) errs.push(`Condition ${i + 1}: field required`)
      if (!c.op) errs.push(`Condition ${i + 1}: operator required`)
      if (c.field === 'amount') {
        if (c.op !== 'gt' && c.op !== 'lt' && c.op !== 'equals') errs.push(`Condition ${i + 1}: amount field supports gt/lt/equals`)
        if (isNaN(Number(c.value))) errs.push(`Condition ${i + 1}: amount value must be a number`)
      }
      if (c.field === 'date') {
        // simple YYYY-MM-DD check
        if (!/^\d{4}-\d{2}-\d{2}$/.test(c.value)) errs.push(`Condition ${i + 1}: date must be YYYY-MM-DD`)
      }
      if (c.op === 'regex') {
        try { new RegExp(c.value) } catch (e) { errs.push(`Condition ${i + 1}: invalid regex`) }
      }
    })
    if (!actionPayload || actionPayload.trim().length === 0) errs.push('Action payload required')

    setErrors(errs)
    if (errs.length > 0) return

    try {
      if (rule && rule.id) {
        await apiFetch(`${API_BASE}/rules/${rule.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
      } else {
        await apiFetch(`${API_BASE}/rules`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
      }
      onSave && onSave()
    } catch (e) {
      alert('Save failed: ' + e)
    }
  }

  return (
    <div className="p-4 border rounded bg-white">
      <div className="mb-2">
        <label className="block text-sm font-semibold">Name</label>
        <input className="w-full border p-2" value={name} onChange={e => setName(e.target.value)} />
      </div>

      <div className="flex items-center space-x-4 mb-2">
        <label className="text-sm">Enabled</label>
        <input type="checkbox" checked={enabled} onChange={e => setEnabled(e.target.checked)} />
        <label className="text-sm">Auto apply on upload</label>
        <input type="checkbox" checked={autoApply} onChange={e => setAutoApply(e.target.checked)} />
      </div>

      <div className="mb-2">
        <label className="block text-sm font-semibold">Priority (lower runs first)</label>
        <input type="number" className="w-28 border p-2" value={priority} onChange={e => setPriority(parseInt(e.target.value || '100'))} />
      </div>

      <div className="mb-2">
        <label className="block font-semibold">Conditions</label>
        {conditions.map((c, i) => (
          <div key={i} className="flex space-x-2 items-center mb-2">
            <select value={c.field} onChange={e => updateCond(i, 'field', e.target.value)} className="border p-2">
              <option value="description">Description</option>
              <option value="amount">Amount</option>
              <option value="date">Date</option>
              <option value="category">Category</option>
            </select>
            <select value={c.op} onChange={e => updateCond(i, 'op', e.target.value)} className="border p-2">
              <option value="contains">contains</option>
              <option value="equals">equals</option>
              <option value="regex">regex</option>
              <option value="gt">&gt;</option>
              <option value="lt">&lt;</option>
            </select>
            <input className="border p-2 flex-1" value={c.value} onChange={e => updateCond(i, 'value', e.target.value)} />
            <button className="px-2 py-1 bg-red-100 text-red-700 rounded" onClick={() => removeCond(i)}>Remove</button>
          </div>
        ))}
        <button className="px-3 py-1 bg-blue-600 text-white rounded" onClick={addCond}>Add Condition</button>
      </div>

      <div className="mb-2">
        <label className="block font-semibold">Action</label>
        <div className="flex space-x-2 items-center">
          <select value={actionType} onChange={e => setActionType(e.target.value)} className="border p-2">
            <option value="set_category">Set Category</option>
            <option value="set_merchant">Set Merchant</option>
          </select>
          <input className="border p-2 flex-1" value={actionPayload} onChange={e => setActionPayload(e.target.value)} placeholder={actionType === 'set_category' ? 'Category name' : 'Merchant name'} />
        </div>
      </div>

      {errors.length > 0 && (
        <div className="mb-2 text-sm text-red-700">
          <ul className="list-disc pl-5">
            {errors.map((e, i) => <li key={i}>{e}</li>)}
          </ul>
        </div>
      )}

      <div className="flex space-x-2">
        <button className="px-3 py-1 bg-green-600 text-white rounded" onClick={save}>Save</button>
        <button className="px-3 py-1 bg-gray-200 rounded" onClick={() => onClose && onClose()}>Cancel</button>
      </div>
    </div>
  )
}
