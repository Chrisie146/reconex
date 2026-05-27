'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Check, ChevronDown, Search, X } from 'lucide-react'
import { Account, useAccounts } from '@/lib/hooks/useAccounts'

interface AccountSelectorProps {
  clientId: number | null
  value: number | null
  onChange: (accountId: number | null, account: Account | null) => void
  placeholder?: string
  disabled?: boolean
  className?: string
  /** Limit choices to leaf (postable) accounts. Default true — headers should rarely be selectable. */
  postableOnly?: boolean
  /** Optional account-type filter (e.g. only revenue/expense for a P&L line). */
  typeFilter?: Account['account_type'][]
  /** Display variant. `compact` is for inline table cells. */
  variant?: 'default' | 'compact'
}

/**
 * Searchable combobox that filters by code OR name. Designed to replace the
 * free-text category dropdowns that exist throughout the app today.
 */
export default function AccountSelector({
  clientId,
  value,
  onChange,
  placeholder = 'Select account…',
  disabled = false,
  className = '',
  postableOnly = true,
  typeFilter,
  variant = 'default',
}: AccountSelectorProps) {
  const { accounts, loading } = useAccounts(clientId, { postable: postableOnly })
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const wrapperRef = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const [dropdownStyle, setDropdownStyle] = useState<React.CSSProperties>({})

  // Compute portal position from the trigger button's bounding rect
  const computeDropdownStyle = () => {
    if (!buttonRef.current) return
    const rect = buttonRef.current.getBoundingClientRect()
    const spaceBelow = window.innerHeight - rect.bottom
    const dropdownMaxH = 320
    const style: React.CSSProperties = {
      position: 'fixed',
      left: rect.left,
      width: rect.width,
      zIndex: 9999,
    }
    if (spaceBelow >= dropdownMaxH || spaceBelow >= rect.top) {
      style.top = rect.bottom + 4
    } else {
      style.bottom = window.innerHeight - rect.top + 4
    }
    setDropdownStyle(style)
  }

  // Close on outside click — must check both the wrapper and the portal dropdown
  useEffect(() => {
    if (!open) return
    const onDoc = (e: MouseEvent) => {
      const target = e.target as Node
      const insideWrapper = wrapperRef.current?.contains(target) ?? false
      const insideDropdown = dropdownRef.current?.contains(target) ?? false
      if (!insideWrapper && !insideDropdown) {
        setOpen(false)
        setQuery('')
      }
    }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [open])

  useEffect(() => {
    if (open) {
      // Focus search input as soon as the dropdown opens
      setTimeout(() => inputRef.current?.focus(), 0)
    }
  }, [open])

  const selected = useMemo(
    () => accounts.find(a => a.id === value) ?? null,
    [accounts, value],
  )

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    let list = accounts
    if (typeFilter && typeFilter.length > 0) {
      list = list.filter(a => typeFilter.includes(a.account_type))
    }
    if (!q) return list
    return list.filter(a =>
      a.code.toLowerCase().includes(q) ||
      a.name.toLowerCase().includes(q),
    )
  }, [accounts, query, typeFilter])

  const sizeClasses = variant === 'compact'
    ? 'px-2 py-1 text-xs'
    : 'px-3 py-2 text-sm'

  return (
    <div ref={wrapperRef} className={`relative ${className}`}>
      <button
        ref={buttonRef}
        type="button"
        disabled={disabled || loading}
        onClick={() => {
          computeDropdownStyle()
          setOpen(o => !o)
        }}
        className={`w-full ${sizeClasses} flex items-center justify-between gap-2 border rounded-md
          bg-white dark:bg-slate-800 border-neutral-300 dark:border-slate-600
          text-left text-neutral-800 dark:text-neutral-100
          hover:border-neutral-400 dark:hover:border-slate-500
          disabled:opacity-50 disabled:cursor-not-allowed
          focus:outline-none focus:ring-2 focus:ring-blue-500`}
      >
        <span className="truncate">
          {selected ? (
            <span>
              <span className="font-mono text-neutral-500 dark:text-neutral-400">{selected.code}</span>
              <span className="mx-1.5 text-neutral-300">·</span>
              <span>{selected.name}</span>
            </span>
          ) : (
            <span className="text-neutral-400">{placeholder}</span>
          )}
        </span>
        <ChevronDown className={`w-4 h-4 shrink-0 text-neutral-400 transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && typeof document !== 'undefined' && createPortal(
        <div
          ref={dropdownRef}
          style={dropdownStyle}
          className="bg-white dark:bg-slate-800 border border-neutral-200 dark:border-slate-700
            rounded-md shadow-lg max-h-[320px] flex flex-col"
        >
          <div className="flex items-center gap-2 p-2 border-b border-neutral-200 dark:border-slate-700">
            <Search className="w-3.5 h-3.5 text-neutral-400 shrink-0" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Search by code or name…"
              className="flex-1 text-sm bg-transparent outline-none text-neutral-800 dark:text-neutral-100 placeholder:text-neutral-400"
            />
            {selected && (
              <button
                type="button"
                onClick={() => { onChange(null, null); setOpen(false); setQuery('') }}
                className="text-neutral-400 hover:text-red-500 transition-colors"
                title="Clear selection"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          <div className="overflow-y-auto flex-1">
            {filtered.length === 0 ? (
              <div className="px-3 py-4 text-xs text-neutral-400 text-center">
                {loading ? 'Loading accounts…' : 'No accounts match.'}
              </div>
            ) : (
              filtered.slice(0, 200).map(a => (
                <button
                  key={a.id}
                  type="button"
                  onClick={() => { onChange(a.id, a); setOpen(false); setQuery('') }}
                  className={`w-full text-left px-3 py-1.5 flex items-center gap-2 text-sm
                    hover:bg-blue-50 dark:hover:bg-slate-700/50
                    ${a.id === value ? 'bg-blue-50 dark:bg-slate-700/50' : ''}`}
                >
                  <span className={`shrink-0 w-3.5 ${a.id === value ? 'text-blue-600' : 'text-transparent'}`}>
                    <Check className="w-3.5 h-3.5" />
                  </span>
                  <span className="font-mono text-xs text-neutral-500 dark:text-neutral-400 w-12 shrink-0">{a.code}</span>
                  <span className="truncate text-neutral-800 dark:text-neutral-100">{a.name}</span>
                  <span className="ml-auto text-[10px] uppercase tracking-wider text-neutral-400 shrink-0">
                    {a.account_type}
                  </span>
                </button>
              ))
            )}
          </div>
        </div>,
        document.body
      )}
    </div>
  )
}
