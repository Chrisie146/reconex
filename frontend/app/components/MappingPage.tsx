"use client"

import React, { useEffect, useState, useMemo } from "react"
import { DragDropContext, Droppable, Draggable, DropResult, DragStart } from "@hello-pangea/dnd"
import { apiFetch } from "@/lib/apiFetch"
import { useClient } from "@/lib/clientContext"
import {
  Search, Undo2, CheckSquare, Square, Tag, Inbox,
  FolderOpen, ChevronDown, ChevronRight, GripVertical,
  Loader2, Sparkles, ArrowRight, X, CheckCircle2, AlertCircle
} from "lucide-react"

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

/* ── Category colour tokens (shared with TransactionsTable) ──────────── */
const CATEGORY_COLORS: Record<string, { bg: string; text: string; border: string; accent: string }> = {
  'Income':          { bg: 'bg-emerald-50',  text: 'text-emerald-700',  border: 'border-emerald-200',  accent: 'bg-emerald-500' },
  'Salary':          { bg: 'bg-emerald-50',  text: 'text-emerald-700',  border: 'border-emerald-200',  accent: 'bg-emerald-500' },
  'Transfer':        { bg: 'bg-blue-50',     text: 'text-blue-700',     border: 'border-blue-200',     accent: 'bg-blue-500' },
  'Transfers':       { bg: 'bg-blue-50',     text: 'text-blue-700',     border: 'border-blue-200',     accent: 'bg-blue-500' },
  'Bank Charges':    { bg: 'bg-amber-50',    text: 'text-amber-700',    border: 'border-amber-200',    accent: 'bg-amber-500' },
  'Bank Fees':       { bg: 'bg-amber-50',    text: 'text-amber-700',    border: 'border-amber-200',    accent: 'bg-amber-500' },
  'Insurance':       { bg: 'bg-violet-50',   text: 'text-violet-700',   border: 'border-violet-200',   accent: 'bg-violet-500' },
  'Groceries':       { bg: 'bg-lime-50',     text: 'text-lime-700',     border: 'border-lime-200',     accent: 'bg-lime-500' },
  'Fuel':            { bg: 'bg-orange-50',   text: 'text-orange-700',   border: 'border-orange-200',   accent: 'bg-orange-500' },
  'Utilities':       { bg: 'bg-cyan-50',     text: 'text-cyan-700',     border: 'border-cyan-200',     accent: 'bg-cyan-500' },
  'Entertainment':   { bg: 'bg-pink-50',     text: 'text-pink-700',     border: 'border-pink-200',     accent: 'bg-pink-500' },
  'Medical':         { bg: 'bg-red-50',      text: 'text-red-700',      border: 'border-red-200',      accent: 'bg-red-500' },
  'Rent':            { bg: 'bg-blue-50',   text: 'text-blue-700',   border: 'border-blue-200',   accent: 'bg-blue-500' },
  'Subscriptions':   { bg: 'bg-fuchsia-50',  text: 'text-fuchsia-700',  border: 'border-fuchsia-200',  accent: 'bg-fuchsia-500' },
  'Loan':            { bg: 'bg-rose-50',     text: 'text-rose-700',     border: 'border-rose-200',     accent: 'bg-rose-500' },
  'Loan Repayment':  { bg: 'bg-rose-50',     text: 'text-rose-700',     border: 'border-rose-200',     accent: 'bg-rose-500' },
}
const DEFAULT_CAT_STYLE = { bg: 'bg-neutral-50', text: 'text-neutral-700', border: 'border-neutral-200', accent: 'bg-neutral-400' }

function getCatStyle(category: string) {
  if (!category) return DEFAULT_CAT_STYLE
  return CATEGORY_COLORS[category] ||
    Object.entries(CATEGORY_COLORS).find(([k]) => k.toLowerCase() === category.toLowerCase())?.[1] ||
    DEFAULT_CAT_STYLE
}

/* ── Debounce hook ──────────────────────────────────────────────────── */
function useDebounce<T>(value: T, ms = 250): T {
  const [deb, setDeb] = useState(value)
  useEffect(() => { const t = setTimeout(() => setDeb(value), ms); return () => clearTimeout(t) }, [value, ms])
  return deb
}

/* ── Types ──────────────────────────────────────────────────────────── */
type Txn = {
  id: number
  date: string
  description: string
  amount: number
  category: string
}

/* ══════════════════════════════════════════════════════════════════════
   MAPPING PAGE
   ══════════════════════════════════════════════════════════════════════ */
export default function MappingPage() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [categories, setCategories] = useState<string[]>([])
  const [uncategorized, setUncategorized] = useState<Txn[]>([])
  const [byCategory, setByCategory] = useState<Record<string, Txn[]>>({})
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [draggingIds, setDraggingIds] = useState<number[] | null>(null)
  const [expandedCats, setExpandedCats] = useState<Record<string, boolean>>({})
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState("")
  const [bulkCategory, setBulkCategory] = useState("")
  const { currentClient } = useClient()
  const clientId = currentClient?.id || null

  const debouncedSearch = useDebounce(searchQuery, 250)

  /* ── derived stats ─────────────────────────────────────────────── */
  const totalCategorized = useMemo(
    () => Object.values(byCategory).reduce((s, arr) => s + arr.length, 0),
    [byCategory]
  )
  const totalAll = totalCategorized + uncategorized.length
  const progressPct = totalAll > 0 ? Math.round((totalCategorized / totalAll) * 100) : 0

  /* ── filtered uncategorized (search) ───────────────────────────── */
  const filteredUncategorized = useMemo(() => {
    if (!debouncedSearch.trim()) return uncategorized
    const q = debouncedSearch.toLowerCase()
    return uncategorized.filter(t =>
      t.description.toLowerCase().includes(q) ||
      t.date.toLowerCase().includes(q) ||
      String(t.amount).includes(q)
    )
  }, [uncategorized, debouncedSearch])

  /* ── effects ───────────────────────────────────────────────────── */
  useEffect(() => {
    setExpandedCats(prev => {
      const next = { ...prev }
      categories.forEach(c => { if (next[c] === undefined) next[c] = false })
      return next
    })
  }, [categories])

  useEffect(() => {
    const params = new URLSearchParams(typeof window !== 'undefined' ? window.location.search : '')
    const sid = params.get('session_id')
    setSessionId(sid)
    if (sid || clientId) loadData(sid, clientId)
    else setLoading(false)
  }, [clientId])

  useEffect(() => {
    if (categories.length > 0 && !bulkCategory) setBulkCategory(categories[0])
  }, [categories, bulkCategory])

  /* ── data ──────────────────────────────────────────────────────── */
  async function loadData(sid: string | null, cid: number | null = null) {
    setLoading(true)
    try {
      // Build query params: when using client_id, fetch client-scoped categories
      const catParams = (cid ? `client_id=${cid}` : (sid ? `session_id=${encodeURIComponent(sid)}` : ''))
      const catJson = await apiFetch(`${API_BASE}/categories${catParams ? '?' + catParams : ''}`)
      const cats: string[] = (catJson.categories || []).map((cat: any) => typeof cat === 'string' ? cat : cat.name)
      setCategories(cats)

      // Fetch transactions: use client_id to get ALL statements, fallback to session_id
      let txParam: string
      if (cid) {
        txParam = `client_id=${cid}`
      } else if (sid) {
        txParam = `session_id=${encodeURIComponent(sid)}`
      } else {
        setLoading(false)
        return
      }
      const txJson = await apiFetch(`${API_BASE}/transactions?${txParam}`)
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

  function rebuildState(all: Txn[]) {
    const unc = all.filter(t => !t.category || t.category === 'Other')
    const mapping: Record<string, Txn[]> = {}
    categories.forEach(c => (mapping[c] = []))
    all.filter(t => t.category && t.category !== 'Other').forEach(t => {
      if (!mapping[t.category]) mapping[t.category] = []
      mapping[t.category].push(t)
    })
    setUncategorized(unc)
    setByCategory(mapping)
  }

  async function applyCategoryToIds(ids: number[], category: string) {
    if (!sessionId && !clientId) return
    try {
      const param = clientId
        ? `client_id=${clientId}`
        : `session_id=${encodeURIComponent(sessionId!)}`
      const j = await apiFetch(`${API_BASE}/bulk-categorise/ids?${param}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids, category })
      })
      if (j.transactions) rebuildState(j.transactions)
      else await loadData(sessionId, clientId)
    } catch (e) {
      console.error('Apply category failed', e)
      await loadData(sessionId, clientId)
    }
  }

  async function handleUndo() {
    if (!sessionId && !clientId) return
    try {
      const param = clientId
        ? `client_id=${clientId}`
        : `session_id=${encodeURIComponent(sessionId!)}`
      const j = await apiFetch(`${API_BASE}/bulk-categorise/undo?${param}`, { method: 'POST' })
      if (j.transactions) rebuildState(j.transactions)
      else await loadData(sessionId, clientId)
      setSelectedIds([])
    } catch (e) {
      console.error('Undo failed', e)
    }
  }

  /* ── drag handlers ─────────────────────────────────────────────── */
  function onDragStart(start: DragStart) {
    const draggedId = parseInt(start.draggableId, 10)
    if (!selectedIds.includes(draggedId)) setSelectedIds([draggedId])
    setDraggingIds([draggedId])
  }

  function onDragEnd(result: DropResult) {
    const { source, destination } = result
    if (!destination) { setDraggingIds(null); return }

    const idsToMove = draggingIds && draggingIds.length > 0 ? draggingIds : [parseInt(result.draggableId, 10)]
    if (idsToMove.length === 0) { setDraggingIds(null); return }

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
      if (srcId === destId) { setDraggingIds(null); return }
      setByCategory(prev => {
        const copy = { ...prev }
        const moved: Txn[] = []
        copy[srcId] = (copy[srcId] || []).filter(t => {
          if (idsToMove.includes(t.id)) { moved.push({ ...t, category: destId }); return false }
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
            if (idsToMove.includes(t.id)) { moved.push({ ...t, category: 'Other' }); return false }
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

  /* ── selection helpers ─────────────────────────────────────────── */
  function toggleSelect(id: number, multi: boolean) {
    if (multi) setSelectedIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])
    else setSelectedIds([id])
  }

  function selectAll() {
    const allIds = [...uncategorized.map(t => t.id), ...Object.values(byCategory).flat().map(t => t.id)]
    setSelectedIds(Array.from(new Set(allIds)))
  }

  /* ── no session guard ──────────────────────────────────────────── */
  if (!sessionId && !clientId) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <div className="text-center space-y-3">
          <AlertCircle className="w-10 h-10 text-amber-400 mx-auto" />
          <p className="text-sm text-neutral-500">No session selected. Choose a statement from the sidebar to begin mapping.</p>
        </div>
      </div>
    )
  }

  /* ══════════════════════════════════════════════════════════════════
     RENDER
     ══════════════════════════════════════════════════════════════════ */
  return (
    <div className="space-y-5">
      {/* ── Page Header ─────────────────────────────────────────── */}
      <div>
        <h2 className="text-2xl font-bold text-neutral-900 tracking-tight flex items-center gap-2">
          <Tag className="w-6 h-6 text-blue-500" />
          Transaction Mapping
        </h2>
        <p className="text-sm text-neutral-500 mt-1">
          Drag transactions into categories, or use bulk actions to categorize many at once.
        </p>
      </div>

      {loading ? (
        /* ── Skeleton loader ──────────────────────────────────── */
        <div className="flex flex-col items-center justify-center h-[50vh] gap-3">
          <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
          <p className="text-sm text-neutral-400">Loading transactions...</p>
        </div>
      ) : (
        <>
          {/* ── Progress bar ─────────────────────────────────────── */}
          <div className="rounded-xl border border-neutral-200 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-3 text-sm text-neutral-600">
                <span className="flex items-center gap-1.5">
                  <Inbox className="w-4 h-4 text-amber-500" />
                  <span className="font-medium">{uncategorized.length}</span> uncategorized
                </span>
                <span className="text-neutral-300">|</span>
                <span className="flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500" />
                  <span className="font-medium">{totalCategorized}</span> categorized
                </span>
                <span className="text-neutral-300">|</span>
                <span className="font-medium">{totalAll}</span> total
              </div>
              <span className="text-xs font-semibold text-blue-600">{progressPct}% complete</span>
            </div>
            <div className="h-2 rounded-full bg-neutral-100 overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-blue-500 to-emerald-400 transition-all duration-500 ease-out"
                style={{ width: `${progressPct}%` }}
              />
            </div>
          </div>

          {/* ── Toolbar ──────────────────────────────────────────── */}
          <div className="flex flex-wrap items-center gap-2 rounded-xl border border-neutral-200 bg-white px-4 py-3 shadow-sm">
            {/* selection controls */}
            <button
              onClick={selectAll}
              className="inline-flex items-center gap-1.5 rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 transition-colors"
            >
              <CheckSquare className="w-3.5 h-3.5" /> Select all
            </button>
            <button
              onClick={() => setSelectedIds([])}
              className="inline-flex items-center gap-1.5 rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-1.5 text-xs font-medium text-neutral-600 hover:bg-neutral-100 transition-colors"
            >
              <X className="w-3.5 h-3.5" /> Clear
            </button>

            {selectedIds.length > 0 && (
              <span className="rounded-full bg-blue-100 text-blue-700 px-2.5 py-0.5 text-xs font-semibold tabular-nums">
                {selectedIds.length} selected
              </span>
            )}

            {/* separator */}
            <div className="mx-1 h-6 w-px bg-neutral-200" />

            {/* bulk categorize */}
            <div className="flex items-center gap-2">
              <select
                value={bulkCategory}
                onChange={e => setBulkCategory(e.target.value)}
                className="rounded-lg border border-neutral-200 bg-neutral-50 px-3 py-1.5 text-xs font-medium text-neutral-700 focus:outline-none focus:ring-2 focus:ring-blue-300"
              >
                {categories.map(c => {
                  const cs = getCatStyle(c)
                  return <option key={c} value={c}>{c} ({(byCategory[c] || []).length})</option>
                })}
              </select>
              <button
                disabled={selectedIds.length === 0}
                onClick={async () => {
                  if (!bulkCategory || selectedIds.length === 0) return
                  await applyCategoryToIds(selectedIds, bulkCategory)
                  setSelectedIds([])
                }}
                className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3.5 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ArrowRight className="w-3.5 h-3.5" /> Apply
              </button>
            </div>

            {/* undo */}
            <div className="ml-auto">
              <button
                onClick={handleUndo}
                className="inline-flex items-center gap-1.5 rounded-lg border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700 hover:bg-amber-100 transition-colors"
              >
                <Undo2 className="w-3.5 h-3.5" /> Undo last
              </button>
            </div>
          </div>

          {/* ── Main drag-drop area ─────────────────────────────── */}
          <DragDropContext onDragStart={onDragStart} onDragEnd={onDragEnd}>
            <div className="flex gap-5 h-[calc(100vh-320px)] min-h-[400px]">

              {/* ─── LEFT: Uncategorized ─────────────────────────── */}
              <div className="w-[42%] flex flex-col rounded-xl border border-neutral-200 bg-white shadow-sm overflow-hidden">
                {/* header */}
                <div className="flex items-center gap-3 border-b border-neutral-100 bg-neutral-50/80 px-4 py-3">
                  <Inbox className="w-5 h-5 text-amber-500" />
                  <h3 className="text-sm font-semibold text-neutral-800">Uncategorized</h3>
                  <span className="ml-auto rounded-full bg-amber-100 text-amber-700 px-2 py-0.5 text-[11px] font-bold tabular-nums">
                    {uncategorized.length}
                  </span>
                </div>

                {/* search */}
                <div className="px-3 py-2 border-b border-neutral-100">
                  <div className="relative">
                    <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-neutral-400" />
                    <input
                      type="text"
                      placeholder="Search transactions..."
                      value={searchQuery}
                      onChange={e => setSearchQuery(e.target.value)}
                      className="w-full rounded-lg border border-neutral-200 bg-neutral-50 pl-8 pr-3 py-1.5 text-xs text-neutral-700 placeholder:text-neutral-400 focus:outline-none focus:ring-2 focus:ring-blue-200 focus:border-blue-300 transition-colors"
                    />
                    {searchQuery && (
                      <button onClick={() => setSearchQuery("")} className="absolute right-2.5 top-1/2 -translate-y-1/2">
                        <X className="w-3.5 h-3.5 text-neutral-400 hover:text-neutral-600" />
                      </button>
                    )}
                  </div>
                  {debouncedSearch && (
                    <p className="text-[11px] text-neutral-400 mt-1 pl-1">
                      Showing {filteredUncategorized.length} of {uncategorized.length}
                    </p>
                  )}
                </div>

                {/* droppable list */}
                <Droppable droppableId="uncategorized">
                  {(provided, snapshot) => (
                    <div
                      ref={provided.innerRef}
                      {...provided.droppableProps}
                      className={`flex-1 overflow-y-auto p-3 space-y-1.5 transition-colors ${
                        snapshot.isDraggingOver ? 'bg-blue-50/60' : ''
                      }`}
                    >
                      {filteredUncategorized.map((t, idx) => (
                        <Draggable key={t.id} draggableId={String(t.id)} index={idx}>
                          {(prov, snap) => (
                            <div
                              ref={prov.innerRef}
                              {...prov.draggableProps}
                              {...prov.dragHandleProps}
                              className={`group flex items-start gap-2 rounded-lg border bg-white cursor-grab active:cursor-grabbing transition-all duration-150 ${
                                snap.isDragging
                                  ? 'shadow-xl border-blue-400 ring-2 ring-blue-200 rotate-1 scale-[0.92] opacity-95 p-2'
                                  : 'p-2.5 border-neutral-200 hover:border-neutral-300 hover:shadow-sm'
                              } ${
                                selectedIds.includes(t.id)
                                  ? 'ring-2 ring-blue-400 bg-blue-50/50 border-blue-300'
                                  : ''
                              }`}
                              onClick={(e) => toggleSelect(t.id, e.ctrlKey || e.metaKey)}
                            >
                              <GripVertical className="w-3.5 h-3.5 text-neutral-300 mt-0.5 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
                              <div className="flex-1 min-w-0">
                                <p className="text-[13px] font-medium text-neutral-800 truncate leading-snug">{t.description}</p>
                                <div className="flex items-center gap-2 mt-0.5">
                                  <span className="text-[11px] text-neutral-400">{t.date}</span>
                                  <span className={`text-[11px] font-semibold tabular-nums ${t.amount >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                                    R {Math.abs(t.amount).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
                                  </span>
                                </div>
                              </div>
                              {/* selection indicator */}
                              <div className="shrink-0 mt-0.5">
                                {selectedIds.includes(t.id)
                                  ? <CheckSquare className="w-4 h-4 text-blue-500" />
                                  : <Square className="w-4 h-4 text-neutral-300 opacity-0 group-hover:opacity-100 transition-opacity" />
                                }
                              </div>
                            </div>
                          )}
                        </Draggable>
                      ))}
                      {provided.placeholder}

                      {/* empty state */}
                      {filteredUncategorized.length === 0 && !debouncedSearch && (
                        <div className="flex flex-col items-center justify-center py-12 text-center">
                          <div className="rounded-full bg-emerald-100 p-3 mb-3">
                            <Sparkles className="w-6 h-6 text-emerald-500" />
                          </div>
                          <p className="text-sm font-medium text-neutral-700">All transactions categorized!</p>
                          <p className="text-xs text-neutral-400 mt-1">Great job — nothing left to sort.</p>
                        </div>
                      )}
                      {filteredUncategorized.length === 0 && debouncedSearch && (
                        <div className="flex flex-col items-center justify-center py-10 text-center">
                          <Search className="w-6 h-6 text-neutral-300 mb-2" />
                          <p className="text-sm text-neutral-500">No matches for &quot;{debouncedSearch}&quot;</p>
                        </div>
                      )}
                    </div>
                  )}
                </Droppable>
              </div>

              {/* ─── RIGHT: Categories ───────────────────────────── */}
              <div className="flex-1 flex flex-col rounded-xl border border-neutral-200 bg-white shadow-sm overflow-hidden">
                {/* header */}
                <div className="flex items-center gap-3 border-b border-neutral-100 bg-neutral-50/80 px-4 py-3">
                  <FolderOpen className="w-5 h-5 text-blue-500" />
                  <h3 className="text-sm font-semibold text-neutral-800">Categories</h3>
                  <span className="ml-auto rounded-full bg-blue-100 text-blue-700 px-2 py-0.5 text-[11px] font-bold tabular-nums">
                    {categories.length}
                  </span>
                </div>

                <div className="flex-1 overflow-y-auto p-3">
                  <div className="grid grid-cols-2 gap-2.5">
                    {categories.map(cat => {
                      const cs = getCatStyle(cat)
                      const items = byCategory[cat] || []
                      const isExpanded = expandedCats[cat] ?? false

                      return (
                        <div key={cat} className={`rounded-lg border ${cs.border} bg-white flex flex-col overflow-hidden`}>
                          {/* category header */}
                          <button
                            onClick={() => setExpandedCats(prev => ({ ...prev, [cat]: !isExpanded }))}
                            className={`flex items-center gap-2 px-3 py-2.5 text-left w-full group transition-colors hover:bg-neutral-50/60 ${cs.bg}`}
                          >
                            <div className={`w-2 h-2 rounded-full ${cs.accent} shrink-0`} />
                            <span className={`text-xs font-semibold ${cs.text} truncate flex-1`}>{cat}</span>
                            <span className={`text-[10px] font-bold ${cs.text} rounded-full px-1.5 py-0.5 bg-white/70 border ${cs.border} tabular-nums`}>
                              {items.length}
                            </span>
                            {isExpanded
                              ? <ChevronDown className={`w-3.5 h-3.5 ${cs.text} shrink-0`} />
                              : <ChevronRight className={`w-3.5 h-3.5 ${cs.text} shrink-0`} />
                            }
                          </button>

                          {/* droppable area */}
                          <Droppable droppableId={cat}>
                            {(provided, snapshot) => (
                              <div
                                ref={provided.innerRef}
                                {...provided.droppableProps}
                                className={`transition-all ${
                                  isExpanded
                                    ? `${snapshot.isDraggingOver ? 'bg-emerald-50/50 border-t-2 border-emerald-300' : 'border-t border-neutral-100'} space-y-1 min-h-[80px] max-h-[260px] overflow-y-auto p-2 flex-1`
                                    : `${snapshot.isDraggingOver ? 'bg-emerald-50/50 border-t-2 border-emerald-300' : 'border-t border-neutral-100 bg-neutral-50/40'} min-h-[36px] px-3 py-2 flex items-center text-xs text-neutral-500`
                                }`}
                              >
                                {isExpanded ? (
                                  <>
                                    {items.map((t, idx) => (
                                      <Draggable key={t.id} draggableId={String(t.id)} index={idx}>
                                        {(prov, snap) => (
                                          <div
                                            ref={prov.innerRef}
                                            {...prov.draggableProps}
                                            {...prov.dragHandleProps}
                                            className={`group flex items-center gap-1.5 rounded-md border bg-white cursor-grab active:cursor-grabbing text-xs transition-all duration-150 ${
                                              snap.isDragging
                                                ? 'shadow-lg border-blue-400 ring-2 ring-blue-200 rotate-1 scale-95 p-1.5'
                                                : 'p-1.5 border-neutral-150 hover:border-neutral-300 hover:shadow-sm'
                                            } ${
                                              selectedIds.includes(t.id)
                                                ? 'ring-2 ring-blue-400 bg-blue-50/50 border-blue-300'
                                                : ''
                                            }`}
                                            onClick={(e) => toggleSelect(t.id, e.ctrlKey || e.metaKey)}
                                          >
                                            <div className="flex-1 min-w-0">
                                              <p className="font-medium text-neutral-800 truncate leading-tight">{t.description}</p>
                                              <span className={`text-[10px] font-semibold tabular-nums ${t.amount >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                                                R {Math.abs(t.amount).toLocaleString('en-ZA', { minimumFractionDigits: 2 })}
                                              </span>
                                            </div>
                                            {selectedIds.includes(t.id) && (
                                              <CheckSquare className="w-3.5 h-3.5 text-blue-500 shrink-0" />
                                            )}
                                          </div>
                                        )}
                                      </Draggable>
                                    ))}
                                    {provided.placeholder}
                                    {items.length === 0 && (
                                      <div className="flex items-center justify-center py-4 text-[11px] text-neutral-400">
                                        <span>Drop transactions here</span>
                                      </div>
                                    )}
                                  </>
                                ) : (
                                  <>
                                    <span className="flex-1 truncate">
                                      {items.length === 0 ? 'Drop here to add' : `${items.length} transaction${items.length !== 1 ? 's' : ''}`}
                                    </span>
                                    {provided.placeholder}
                                  </>
                                )}
                              </div>
                            )}
                          </Droppable>
                        </div>
                      )
                    })}
                  </div>
                </div>
              </div>

            </div>
          </DragDropContext>
        </>
      )}
    </div>
  )
}
