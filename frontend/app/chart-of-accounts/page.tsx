'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { RefreshCw, Sparkles } from 'lucide-react'
import { toast } from 'sonner'
import Header from '@/components/Header'
import Sidebar from '@/components/Sidebar'
import AuthGuard from '@/components/AuthGuard'
import AccountTree from '@/components/AccountTree'
import AccountEditPanel from '@/components/AccountEditPanel'
import { useClient } from '@/lib/clientContext'
import { apiFetch } from '@/lib/apiFetch'
import {
  Account,
  AccountNode,
  fetchAccountTree,
  invalidateAccounts,
} from '@/lib/hooks/useAccounts'

export default function ChartOfAccountsPage() {
  const { currentClient } = useClient()
  const [tree, setTree] = useState<AccountNode[]>([])
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState<AccountNode | null>(null)
  const [seeding, setSeeding] = useState(false)

  const load = useCallback(async () => {
    if (!currentClient) return
    setLoading(true)
    try {
      invalidateAccounts(currentClient.id)
      const t = await fetchAccountTree(currentClient.id)
      setTree(t)
      // Preserve selection across reload if the account still exists
      if (selected) {
        const flat = flatten(t)
        const refreshed = flat.find(a => a.id === selected.id) ?? null
        setSelected(refreshed)
      }
    } catch (err: any) {
      toast.error(err?.message ?? 'Failed to load accounts')
    } finally {
      setLoading(false)
    }
  }, [currentClient?.id])

  useEffect(() => {
    if (currentClient) load()
  }, [currentClient?.id, load])

  const handleSeed = async () => {
    if (!currentClient) return
    setSeeding(true)
    try {
      const res = await apiFetch('/accounts/seed-template', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ client_id: currentClient.id, template_name: 'sa_sme_v1' }),
      })
      toast.success(`Seeded ${res.created} account(s) (${res.skipped} already present)`)
      await load()
    } catch (err: any) {
      toast.error(err?.message ?? 'Seed failed')
    } finally {
      setSeeding(false)
    }
  }

  const stats = useMemo(() => {
    const flat = flatten(tree)
    return {
      total: flat.length,
      postable: flat.filter(a => a.is_postable && a.is_active).length,
      headers: flat.filter(a => !a.is_postable).length,
      inactive: flat.filter(a => !a.is_active).length,
    }
  }, [tree])

  return (
    <AuthGuard>
      <main className="bg-white dark:bg-slate-950 min-h-screen">
        <Sidebar sessionId={null} />

        <div className="transition-all duration-300" style={{ marginLeft: 'var(--sidebar-w, 256px)' }}>
          <Header />

          <div className="p-6 max-w-[1500px] mx-auto">
            {/* Page header */}
            <div className="flex items-start justify-between mb-6">
              <div>
                <h1 className="text-2xl font-semibold text-neutral-800 dark:text-neutral-100">Chart of Accounts</h1>
                <p className="text-sm text-neutral-500 mt-1">
                  {currentClient ? (
                    <>Per-client account hierarchy for <span className="font-medium">{currentClient.name}</span></>
                  ) : (
                    'Select a client to view its Chart of Accounts'
                  )}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={load}
                  disabled={loading || !currentClient}
                  className="inline-flex items-center gap-2 px-3 py-2 rounded-md text-sm text-neutral-700 dark:text-neutral-200 border border-neutral-300 dark:border-slate-700 hover:bg-neutral-50 dark:hover:bg-slate-800 disabled:opacity-50"
                >
                  <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                  Refresh
                </button>
                <button
                  type="button"
                  onClick={handleSeed}
                  disabled={seeding || !currentClient}
                  className="inline-flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
                  title="Re-seed missing template accounts (idempotent)"
                >
                  <Sparkles className="w-4 h-4" />
                  Seed template
                </button>
              </div>
            </div>

            {!currentClient ? (
              <div className="rounded-lg border border-dashed border-neutral-300 dark:border-slate-700 p-12 text-center text-neutral-500">
                Pick a client from the sidebar to manage their Chart of Accounts.
              </div>
            ) : (
              <>
                {/* Stats strip */}
                <div className="grid grid-cols-4 gap-3 mb-6">
                  <Stat label="Total" value={stats.total} />
                  <Stat label="Postable" value={stats.postable} />
                  <Stat label="Headers" value={stats.headers} />
                  <Stat label="Inactive" value={stats.inactive} tone="muted" />
                </div>

                {/* Two-pane layout */}
                <div className="grid grid-cols-[1fr_420px] gap-4 h-[calc(100vh-280px)]">
                  <div className="border border-neutral-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-900 overflow-y-auto p-3">
                    {loading && tree.length === 0 ? (
                      <div className="p-8 text-center text-sm text-neutral-400">Loading accounts…</div>
                    ) : tree.length === 0 ? (
                      <div className="p-8 text-center">
                        <p className="text-sm text-neutral-500 mb-3">This client has no accounts yet.</p>
                        <button
                          type="button"
                          onClick={handleSeed}
                          className="inline-flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium bg-blue-600 text-white hover:bg-blue-700"
                        >
                          <Sparkles className="w-4 h-4" />
                          Seed SA SME template
                        </button>
                      </div>
                    ) : (
                      <AccountTree
                        nodes={tree}
                        selectedId={selected?.id ?? null}
                        onSelect={setSelected}
                      />
                    )}
                  </div>

                  <div className="border border-neutral-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-900 overflow-hidden">
                    <AccountEditPanel
                      account={selected as Account | null}
                      clientId={currentClient.id}
                      onSaved={load}
                      onDeleted={() => { setSelected(null); load() }}
                    />
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </main>
    </AuthGuard>
  )
}

function flatten(nodes: AccountNode[]): AccountNode[] {
  const out: AccountNode[] = []
  const walk = (n: AccountNode) => {
    out.push(n)
    n.children?.forEach(walk)
  }
  nodes.forEach(walk)
  return out
}

function Stat({ label, value, tone = 'default' }: { label: string; value: number; tone?: 'default' | 'muted' }) {
  return (
    <div className={`rounded-lg border border-neutral-200 dark:border-slate-700 p-3 bg-white dark:bg-slate-900 ${tone === 'muted' ? 'opacity-70' : ''}`}>
      <p className="text-[10px] uppercase tracking-wider text-neutral-400">{label}</p>
      <p className="text-2xl font-semibold text-neutral-800 dark:text-neutral-100 mt-1">{value}</p>
    </div>
  )
}
