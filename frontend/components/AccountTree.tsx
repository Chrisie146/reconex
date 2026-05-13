'use client'

import { useMemo, useState } from 'react'
import { ChevronDown, ChevronRight, Lock, Tag, AlertCircle } from 'lucide-react'
import type { AccountNode } from '@/lib/hooks/useAccounts'

interface AccountTreeProps {
  nodes: AccountNode[]
  selectedId: number | null
  onSelect: (node: AccountNode) => void
  /** Code prefix → background tint for the root-level group. */
  groupTints?: Record<string, string>
}

const DEFAULT_TINTS: Record<string, string> = {
  '1': 'bg-emerald-50 dark:bg-emerald-950/30',
  '2': 'bg-rose-50 dark:bg-rose-950/30',
  '3': 'bg-violet-50 dark:bg-violet-950/30',
  '4': 'bg-blue-50 dark:bg-blue-950/30',
  '5': 'bg-amber-50 dark:bg-amber-950/30',
  '6': 'bg-amber-50 dark:bg-amber-950/30',
  '7': 'bg-orange-50 dark:bg-orange-950/30',
  '8': 'bg-orange-50 dark:bg-orange-950/30',
  '9': 'bg-neutral-100 dark:bg-slate-800/60',
}

export default function AccountTree({ nodes, selectedId, onSelect, groupTints }: AccountTreeProps) {
  // Default to all roots expanded.
  const [expanded, setExpanded] = useState<Set<number>>(() => new Set(nodes.map(n => n.id)))
  const tints = groupTints ?? DEFAULT_TINTS

  const toggle = (id: number) =>
    setExpanded(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })

  return (
    <div className="space-y-1">
      {nodes.map(root => (
        <TreeNode
          key={root.id}
          node={root}
          depth={0}
          expanded={expanded}
          onToggle={toggle}
          selectedId={selectedId}
          onSelect={onSelect}
          rootTint={tints[root.code.charAt(0)] ?? ''}
        />
      ))}
    </div>
  )
}

interface TreeNodeProps {
  node: AccountNode
  depth: number
  expanded: Set<number>
  onToggle: (id: number) => void
  selectedId: number | null
  onSelect: (node: AccountNode) => void
  rootTint: string
}

function TreeNode({ node, depth, expanded, onToggle, selectedId, onSelect, rootTint }: TreeNodeProps) {
  const hasChildren = node.children && node.children.length > 0
  const isOpen = expanded.has(node.id)
  const isSelected = selectedId === node.id
  const indent = depth * 16

  return (
    <div>
      <div
        className={`
          flex items-center gap-2 rounded-md cursor-pointer select-none
          py-1.5 pr-2 group
          ${isSelected ? 'bg-blue-100 dark:bg-blue-900/40 ring-1 ring-blue-300 dark:ring-blue-700' : 'hover:bg-neutral-100 dark:hover:bg-slate-800'}
          ${depth === 0 ? rootTint : ''}
        `}
        style={{ paddingLeft: 8 + indent }}
        onClick={() => onSelect(node)}
      >
        <button
          type="button"
          onClick={e => { e.stopPropagation(); if (hasChildren) onToggle(node.id) }}
          className={`w-4 h-4 shrink-0 flex items-center justify-center text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200
            ${hasChildren ? '' : 'invisible'}`}
        >
          {isOpen ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
        </button>

        <span className="font-mono text-xs text-neutral-500 dark:text-neutral-400 w-12 shrink-0">
          {node.code}
        </span>
        <span className={`text-sm truncate flex-1 ${depth === 0 ? 'font-semibold uppercase tracking-wide text-neutral-700 dark:text-neutral-200' : 'text-neutral-800 dark:text-neutral-100'}`}>
          {node.name}
        </span>

        {/* Inline badges */}
        <div className="flex items-center gap-1 shrink-0">
          {node.is_vat_control && (
            <span className="text-[9px] uppercase tracking-wider bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300 px-1.5 py-0.5 rounded">
              VAT
            </span>
          )}
          {!node.is_postable && (
            <span className="text-[9px] uppercase tracking-wider bg-neutral-200 text-neutral-600 dark:bg-slate-700 dark:text-neutral-300 px-1.5 py-0.5 rounded">
              Header
            </span>
          )}
          {node.vat_treatment === 'standard_15' && (
            <span className="text-[9px] uppercase tracking-wider text-neutral-500 dark:text-neutral-400 px-1">
              15%
            </span>
          )}
          {node.is_system && (
            <Lock className="w-3 h-3 text-neutral-400 dark:text-neutral-500" />
          )}
          {!node.is_active && (
            <AlertCircle className="w-3 h-3 text-rose-500" />
          )}
        </div>
      </div>

      {isOpen && hasChildren && (
        <div>
          {node.children.map(child => (
            <TreeNode
              key={child.id}
              node={child}
              depth={depth + 1}
              expanded={expanded}
              onToggle={onToggle}
              selectedId={selectedId}
              onSelect={onSelect}
              rootTint={rootTint}
            />
          ))}
        </div>
      )}
    </div>
  )
}
