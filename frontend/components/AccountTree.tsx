'use client'

import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import type { AccountNode } from '@/lib/hooks/useAccounts'

interface AccountTreeProps {
  nodes: AccountNode[]
  selectedId: number | null
  onSelect: (node: AccountNode) => void
}

const ROOT_TINTS: Record<string, string> = {
  '1': 'bg-emerald-50 text-emerald-950 dark:bg-emerald-950/30 dark:text-emerald-100',
  '2': 'bg-rose-50 text-rose-950 dark:bg-rose-950/30 dark:text-rose-100',
  '3': 'bg-violet-50 text-violet-950 dark:bg-violet-950/30 dark:text-violet-100',
  '4': 'bg-sky-50 text-sky-950 dark:bg-sky-950/30 dark:text-sky-100',
  '5': 'bg-amber-50 text-amber-950 dark:bg-amber-950/30 dark:text-amber-100',
  '6': 'bg-amber-50 text-amber-950 dark:bg-amber-950/30 dark:text-amber-100',
  '7': 'bg-orange-50 text-orange-950 dark:bg-orange-950/30 dark:text-orange-100',
  '8': 'bg-orange-50 text-orange-950 dark:bg-orange-950/30 dark:text-orange-100',
  '9': 'bg-neutral-100 text-neutral-950 dark:bg-slate-800 dark:text-neutral-100',
}

export default function AccountTree({ nodes, selectedId, onSelect }: AccountTreeProps) {
  const [expanded, setExpanded] = useState<Set<number>>(() => new Set(nodes.map(n => n.id)))

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
          rootTint={ROOT_TINTS[root.code.charAt(0)] ?? ''}
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
          flex items-center gap-2 rounded cursor-pointer select-none
          py-1 pr-2 group
          ${isSelected ? 'bg-neutral-900 text-white dark:bg-neutral-100 dark:text-neutral-950' : depth === 0 ? rootTint : 'hover:bg-neutral-100 dark:hover:bg-slate-800'}
        `}
        style={{ paddingLeft: 8 + indent }}
        onClick={() => onSelect(node)}
      >
        <button
          type="button"
          onClick={e => { e.stopPropagation(); if (hasChildren) onToggle(node.id) }}
          className={`flex h-4 w-4 shrink-0 items-center justify-center text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-200 ${hasChildren ? '' : 'invisible'}`}
        >
          {isOpen ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
        </button>

        <span className={`w-12 shrink-0 font-mono text-xs ${isSelected ? 'text-white/75 dark:text-neutral-600' : 'text-neutral-500 dark:text-neutral-400'}`}>
          {node.code}
        </span>
        <span className={`flex-1 truncate text-sm ${depth === 0 ? 'font-semibold' : 'text-neutral-800 dark:text-neutral-100'} ${isSelected ? '!text-white dark:!text-neutral-950' : ''}`}>
          {node.name}
        </span>

        <div className="flex shrink-0 items-center gap-1">
          {node.is_vat_control && (
            <span className={`px-1 text-[9px] uppercase tracking-wider ${isSelected ? 'text-white/75 dark:text-neutral-600' : 'text-neutral-500 dark:text-neutral-400'}`}>
              VAT
            </span>
          )}
          {!node.is_postable && (
            <span className={`px-1 text-[9px] uppercase tracking-wider ${isSelected ? 'text-white/75 dark:text-neutral-600' : 'text-neutral-500 dark:text-neutral-400'}`}>
              Header
            </span>
          )}
          {node.vat_treatment === 'standard_15' && (
            <span className={`px-1 text-[9px] uppercase tracking-wider ${isSelected ? 'text-white/75 dark:text-neutral-600' : 'text-neutral-500 dark:text-neutral-400'}`}>
              15%
            </span>
          )}
          {node.is_system && (
            <span className={`text-[9px] uppercase tracking-wider ${isSelected ? 'text-white/75 dark:text-neutral-600' : 'text-neutral-400 dark:text-neutral-500'}`}>
              System
            </span>
          )}
          {!node.is_active && (
            <span className="text-[9px] uppercase tracking-wider text-rose-500">Inactive</span>
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
