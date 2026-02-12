"use client"

import React, { useEffect, useState } from "react"
import { DragDropContext, Droppable, Draggable, DropResult, DragStart } from "@hello-pangea/dnd"
import { apiFetch } from "@/lib/apiFetch"

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000"

type Txn = {
  id: number
  date: string
  description: string
  amount: number
  category: string
}

export default function MappingPage() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [categories, setCategories] = useState<string[]>([])
  const [uncategorized, setUncategorized] = useState<Txn[]>([])
  const [byCategory, setByCategory] = useState<Record<string, Txn[]>>({})
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [draggingIds, setDraggingIds] = useState<number[] | null>(null)
  const [expandedCats, setExpandedCats] = useState<Record<string, boolean>>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Initialize collapsed state for any new categories.
    setExpandedCats(prev => {
      const next = { ...prev }
      categories.forEach(c => {
        if (next[c] === undefined) next[c] = false
      })
      return next
    })
  }, [categories])

  useEffect(() => {
    const params = new URLSearchParams(typeof window !== 'undefined' ? window.location.search : '')
    const sid = params.get('session_id')
    setSessionId(sid)
    if (sid) {
      loadData(sid)
    } else {
      setLoading(false)
    }
  }, [])

  async function loadData(sid: string) {
    setLoading(true)
    try {
      const catRes = await apiFetch(`${API_BASE}/categories?session_id=${encodeURIComponent(sid)}`)
      const catJson = await catRes.json()
      const cats: string[] = catJson.categories || []
      setCategories(cats)

      const txRes = await apiFetch(`${API_BASE}/transactions?session_id=${encodeURIComponent(sid)}`)
      const txJson = await txRes.json()
      const txns: Txn[] = txJson.transactions || []

      const unc = txns.filter(t => !t.category || t.category === 'Other')
      setUncategorized(unc)

      const mapping: Record<string, Txn[]> = {}
      cats.forEach(c => (mapping[c] = []))
      txns.filter(t => t.category && t.category !== 'Other').forEach(t => {
        if (!mapping[t.category]) mapping[t.category] = []
        mapping[t.category].push(t)
      })
      setByCategory(mapping)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  async function applyCategoryToIds(ids: number[], category: string) {
    if (!sessionId) return
    try {
      const res = await apiFetch(`${API_BASE}/bulk-categorise/ids?session_id=${encodeURIComponent(sessionId)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids, category })
      })
      if (!res.ok) {
        const txt = await res.text()
        throw new Error(txt || 'Failed')
      }
      const j = await res.json()
      if (j.transactions) {
        const all: Txn[] = j.transactions
        const unc = all.filter(t => !t.category || t.category === 'Other')
        const mapping: Record<string, Txn[]> = {}
        categories.forEach(c => (mapping[c] = []))
        all.filter(t => t.category && t.category !== 'Other').forEach(t => {
          if (!mapping[t.category]) mapping[t.category] = []
          mapping[t.category].push(t)
        })
        setUncategorized(unc)
        setByCategory(mapping)
      } else {
        await loadData(sessionId)
      }
    } catch (e) {
      console.error('Apply category failed', e)
      await loadData(sessionId)
    }
  }

  function onDragStart(start: DragStart) {
    const draggedId = parseInt(start.draggableId, 10)
    // Disable multi-item dragging to avoid react-beautiful-dnd registry issues.
    // Always set the dragging ids to the single dragged item. Bulk operations
    // can still be performed with the selection + "Apply category" button.
    if (!selectedIds.includes(draggedId)) {
      setSelectedIds([draggedId])
    }
    setDraggingIds([draggedId])
  }

  function onDragEnd(result: DropResult) {
    const { source, destination } = result
    if (!destination) {
      setDraggingIds(null)
      return
    }

    const idsToMove = draggingIds && draggingIds.length > 0 ? draggingIds : [parseInt(result.draggableId, 10)]
    if (idsToMove.length === 0) {
      setDraggingIds(null)
      return
    }

    const srcId = source.droppableId
    const destId = destination.droppableId

    if (srcId === 'uncategorized' && destId !== 'uncategorized') {
      setUncategorized(prev => prev.filter(t => !idsToMove.includes(t.id)))
      setByCategory(prev => {
        const copy = { ...prev }
        const movedItems = idsToMove.map(id => ({ id, date: '', description: '', amount: 0, category: destId }))
        copy[destId] = [...movedItems, ...(copy[destId] || [])]
        return copy
      })
      applyCategoryToIds(idsToMove, destId)
      setDraggingIds(null)
      return
    }

    if (srcId !== 'uncategorized' && destId !== 'uncategorized') {
      if (srcId === destId) {
        setDraggingIds(null)
        return
      }
      setByCategory(prev => {
        const copy = { ...prev }
        const moved: Txn[] = []
        copy[srcId] = (copy[srcId] || []).filter(t => {
          if (idsToMove.includes(t.id)) {
            const newItem = { ...t, category: destId }
            moved.push(newItem)
            return false
          }
          return true
        })
        copy[destId] = [...moved, ...(copy[destId] || [])]
        return copy
      })
      applyCategoryToIds(idsToMove, destId)
      setDraggingIds(null)
      return
    }

    if (destId === 'uncategorized') {
      setByCategory(prev => {
        const copy = { ...prev }
        const moved: Txn[] = []
        Object.keys(copy).forEach(cat => {
          if (cat === 'Other') return
          copy[cat] = (copy[cat] || []).filter(t => {
            if (idsToMove.includes(t.id)) {
              moved.push({ ...t, category: 'Other' })
              return false
            }
            return true
          })
        })
        setUncategorized(prevUn => [...moved, ...prevUn])
        return copy
      })
      applyCategoryToIds(idsToMove, 'Other')
      setDraggingIds(null)
      return
    }

    setDraggingIds(null)
  }

  if (!sessionId) {
    return <div className="p-4">Provide a `session_id` query parameter in the URL.</div>
  }

  return (
    <div className="p-4">
      <h2 className="text-xl font-semibold mb-4">Transaction Mapping</h2>
      {loading ? (
        <div>Loading...</div>
      ) : (
        <>
          <div className="mb-4 flex items-center gap-3">
            <div className="text-sm">Selected: <strong>{selectedIds.length}</strong></div>
            <button
              className="px-2 py-1 bg-gray-100 rounded border text-sm"
              onClick={() => {
                const allIds: number[] = [
                  ...uncategorized.map(t => t.id),
                  ...Object.values(byCategory).flat().map(t => t.id)
                ]
                setSelectedIds(Array.from(new Set(allIds)))
              }}
            >
              Select all
            </button>
            <button 
              className="px-2 py-1 bg-gray-100 rounded border text-sm" 
              onClick={() => setSelectedIds([])}
            >
              Clear selection
            </button>

            <div className="ml-4 flex items-center gap-2">
              <select className="border rounded px-2 py-1 text-sm" id="bulk-cat-select">
                {categories.map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
              <button
                className="px-3 py-1 bg-indigo-600 text-white rounded text-sm"
                onClick={async () => {
                  const sel = (document.getElementById('bulk-cat-select') as HTMLSelectElement)?.value
                  if (!sel || selectedIds.length === 0) return
                  await applyCategoryToIds(selectedIds, sel)
                  setSelectedIds([])
                }}
                disabled={selectedIds.length === 0}
              >
                Apply category
              </button>
            </div>

            <div className="ml-auto">
              <button
                className="px-3 py-1 bg-yellow-100 rounded border text-sm"
                onClick={async () => {
                  if (!sessionId) return
                  try {
                    const j = await apiFetch(`${API_BASE}/bulk-categorise/undo?session_id=${encodeURIComponent(sessionId)}`, { method: 'POST' })
                    if (j.transactions) {
                      const all: Txn[] = j.transactions
                      const unc = all.filter(t => !t.category || t.category === 'Other')
                      const mapping: Record<string, Txn[]> = {}
                      categories.forEach(c => (mapping[c] = []))
                      all.filter(t => t.category && t.category !== 'Other').forEach(t => {
                        if (!mapping[t.category]) mapping[t.category] = []
                        mapping[t.category].push(t)
                      })
                      setUncategorized(unc)
                      setByCategory(mapping)
                    } else {
                      await loadData(sessionId)
                    }
                    setSelectedIds([])
                  } catch (e) {
                    console.error('Undo failed', e)
                  }
                }}
              >
                Undo last bulk
              </button>
            </div>
          </div>

          <DragDropContext onDragStart={onDragStart} onDragEnd={onDragEnd}>
            <div className="flex gap-6 h-[calc(100vh-250px)]">
              {/* LEFT SIDE: Transactions */}
              <div className="w-1/2 bg-gray-50 p-4 rounded-lg shadow-sm border-2 border-gray-200 flex flex-col">
                <h3 className="text-lg font-semibold mb-3 text-gray-700">Uncategorized Transactions</h3>
                <Droppable droppableId="uncategorized">
                  {(provided, snapshot) => (
                    <div 
                      ref={provided.innerRef} 
                      {...provided.droppableProps} 
                      className={`space-y-2 overflow-y-auto flex-1 p-2 rounded ${
                        snapshot.isDraggingOver ? 'bg-blue-50 border-2 border-blue-300' : ''
                      }`}
                    >
                      {uncategorized.map((t, idx) => (
                        <Draggable key={t.id} draggableId={String(t.id)} index={idx}>
                          {(prov, snap) => (
                            <div
                              ref={prov.innerRef}
                              {...prov.draggableProps}
                              {...prov.dragHandleProps}
                              className={`bg-white rounded-lg border-2 cursor-move transition-all ${
                                snap.isDragging
                                  ? 'p-2 shadow-lg rotate-2 border-blue-400 scale-85 opacity-90 max-w-[200px] w-[200px] text-sm'
                                  : 'p-3 border-gray-300'
                              } ${
                                selectedIds.includes(t.id) ? 'ring-2 ring-indigo-400 bg-indigo-50' : 'hover:border-gray-400'
                              }`}
                              onClick={(e) => {
                                if (e.ctrlKey || e.metaKey) {
                                  setSelectedIds(prev => 
                                    prev.includes(t.id) ? prev.filter(x => x !== t.id) : [...prev, t.id]
                                  )
                                } else {
                                  setSelectedIds([t.id])
                                }
                              }}
                            >
                              <div className="text-sm font-medium text-gray-900">{t.description}</div>
                              <div className="text-xs text-gray-500 mt-1">{t.date} • ${t.amount.toFixed(2)}</div>
                            </div>
                          )}
                        </Draggable>
                      ))}
                      {provided.placeholder}
                      {uncategorized.length === 0 && (
                        <div className="text-center text-gray-400 mt-8">
                          <div className="text-lg">🎉</div>
                          <div className="mt-2">All transactions categorized!</div>
                        </div>
                      )}
                    </div>
                  )}
                </Droppable>
              </div>

              {/* RIGHT SIDE: Categories */}
              <div className="w-1/2 bg-gray-50 p-4 rounded-lg shadow-sm border-2 border-gray-200 flex flex-col">
                <h3 className="text-lg font-semibold mb-3 text-gray-700">Categories</h3>
                <div className="grid grid-cols-2 gap-3 overflow-y-auto flex-1">
                  {categories.map((cat) => (
                    <div key={cat} className="bg-white p-3 rounded-lg shadow-sm border border-gray-300 flex flex-col">
                      <div className="flex items-center justify-between gap-2 mb-2 text-sm font-semibold text-gray-800 border-b pb-2">
                        <button
                          className="flex items-center gap-2"
                          onClick={() => setExpandedCats(prev => ({ ...prev, [cat]: !(prev[cat] ?? false) }))}
                        >
                          <span className="text-xs px-1.5 py-0.5 rounded bg-gray-100 border">{(byCategory[cat] || []).length}</span>
                          <span>{cat}</span>
                          <span className="text-gray-500 text-xs">{(expandedCats[cat] ?? false) ? '[-]' : '[+]'}</span>
                        </button>
                        <span className="text-[11px] text-gray-500">Click to toggle</span>
                      </div>
                      <Droppable droppableId={cat}>
                        {(provided, snapshot) => {
                          const isExpanded = expandedCats[cat] ?? false
                          const count = (byCategory[cat] || []).length
                          return (
                            <div
                              ref={provided.innerRef}
                              {...provided.droppableProps}
                              className={`rounded transition-all ${
                                isExpanded
                                  ? `${snapshot.isDraggingOver ? 'bg-green-50 border-2 border-green-400' : 'border border-gray-200'} space-y-1.5 min-h-[100px] flex-1 overflow-y-auto p-1`
                                  : `${snapshot.isDraggingOver ? 'border-2 border-green-400 bg-green-50' : 'border border-gray-200 bg-gray-50'} min-h-[56px] p-2 flex items-center justify-between text-xs text-gray-600`}
                              }`}
                            >
                              {isExpanded ? (
                                <>
                                  {(byCategory[cat] || []).map((t, idx) => (
                                    <Draggable key={t.id} draggableId={String(t.id)} index={idx}>
                                      {(prov, snap) => (
                                        <div
                                          ref={prov.innerRef}
                                          {...prov.draggableProps}
                                          {...prov.dragHandleProps}
                                          className={`bg-gray-50 rounded border cursor-move text-xs transition-all ${
                                            snap.isDragging
                                              ? 'p-1.5 shadow-md border-green-400 scale-85 opacity-90 max-w-[200px] w-[200px]'
                                              : 'p-2 border-gray-200'
                                          } ${
                                            selectedIds.includes(t.id) ? 'ring-2 ring-indigo-400 bg-indigo-50' : 'hover:bg-gray-100'
                                          }`}
                                          onClick={(e) => {
                                            if (e.ctrlKey || e.metaKey) {
                                              setSelectedIds(prev => 
                                                prev.includes(t.id) ? prev.filter(x => x !== t.id) : [...prev, t.id]
                                              )
                                            } else {
                                              setSelectedIds([t.id])
                                            }
                                          }}
                                        >
                                          <div className="font-medium text-gray-900 truncate">{t.description}</div>
                                          <div className="text-gray-500 mt-0.5">${t.amount.toFixed(2)}</div>
                                        </div>
                                      )}
                                    </Draggable>
                                  ))}
                                  {provided.placeholder}
                                  {count === 0 && (
                                    <div className="text-xs text-gray-400 py-2 text-center">Drop transactions here</div>
                                  )}
                                </>
                              ) : (
                                <>
                                  <div className="flex-1 text-xs text-gray-600">Drop here to add</div>
                                  <div className="text-[11px] text-gray-500">Items: {count}</div>
                                  {provided.placeholder}
                                </>
                              )}
                            </div>
                          )
                        }}
                      </Droppable>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </DragDropContext>
        </>
      )}
    </div>
  )
}
