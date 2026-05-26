'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Plus, RefreshCw, X } from 'lucide-react'
import { toast } from 'sonner'
import Header from '@/components/Header'
import Sidebar from '@/components/Sidebar'
import AuthGuard from '@/components/AuthGuard'
import AccountTree from '@/components/AccountTree'
import AccountEditPanel from '@/components/AccountEditPanel'
import AccountCreateModal from '@/components/AccountCreateModal'
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
  const [showCreate, setShowCreate] = useState(false)

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

          <div className="w-full px-3 py-2">
            {/* Page header */}
            <div className="mb-2 flex flex-wrap items-center justify-between gap-3 border-b border-neutral-200 pb-2 dark:border-slate-800">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                  <h1 className="text-base font-semibold text-neutral-950 dark:text-neutral-100">Chart of Accounts</h1>
                  <span className="text-sm text-neutral-500">
                    {currentClient ? currentClient.name : 'Select a client'}
                  </span>
                  {currentClient && (
                    <span className="text-xs text-neutral-500">
                      Total <span className="font-medium text-neutral-800 dark:text-neutral-200">{stats.total}</span>
                      <span className="mx-2 text-neutral-300">|</span>
                      Postable <span className="font-medium text-neutral-800 dark:text-neutral-200">{stats.postable}</span>
                      <span className="mx-2 text-neutral-300">|</span>
                      Headers <span className="font-medium text-neutral-800 dark:text-neutral-200">{stats.headers}</span>
                      <span className="mx-2 text-neutral-300">|</span>
                      Inactive <span className="font-medium text-neutral-800 dark:text-neutral-200">{stats.inactive}</span>
                    </span>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => setShowCreate(true)}
                  disabled={!currentClient}
                  className="inline-flex items-center gap-1.5 rounded bg-neutral-900 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-neutral-800 disabled:opacity-50"
                  title="Create a custom account"
                >
                  <Plus className="h-3.5 w-3.5" />
                  Add account
                </button>
                <button
                  type="button"
                  onClick={load}
                  disabled={loading || !currentClient}
                  className="inline-flex h-8 w-8 items-center justify-center rounded border border-neutral-300 text-neutral-600 hover:bg-neutral-50 dark:border-slate-700 dark:text-neutral-200 dark:hover:bg-slate-800 disabled:opacity-50"
                  title="Refresh"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
                </button>
                <button
                  type="button"
                  onClick={handleSeed}
                  disabled={seeding || !currentClient}
                  className="inline-flex items-center rounded border border-neutral-300 px-2.5 py-1.5 text-xs font-medium text-neutral-700 hover:bg-neutral-50 dark:border-slate-700 dark:text-neutral-200 dark:hover:bg-slate-800 disabled:opacity-50"
                  title="Re-seed missing template accounts (idempotent)"
                >
                  Seed template
                </button>
              </div>
            </div>

            {!currentClient ? (
              <div className="rounded-md border border-dashed border-neutral-300 p-8 text-center text-sm text-neutral-500 dark:border-slate-700">
                Pick a client from the sidebar to manage their Chart of Accounts.
              </div>
            ) : (
              <>
                <div className="relative h-[calc(100vh-125px)]">
                  <div className="h-full overflow-y-auto rounded-md border border-neutral-300 bg-white p-2 dark:border-slate-700 dark:bg-slate-900">
                    {loading && tree.length === 0 ? (
                      <div className="p-6 text-center text-sm text-neutral-400">Loading accounts...</div>
                    ) : tree.length === 0 ? (
                      <div className="p-6 text-center">
                        <p className="text-sm text-neutral-500 mb-3">This client has no accounts yet.</p>
                        <button
                          type="button"
                          onClick={handleSeed}
                          className="inline-flex items-center rounded bg-neutral-900 px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-neutral-800"
                        >
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
                  {selected && (
                    <div className="absolute inset-y-0 right-0 z-20 w-[400px] overflow-hidden rounded-md border border-neutral-300 bg-white shadow-xl dark:border-slate-700 dark:bg-slate-900">
                      <div className="flex h-9 items-center justify-between border-b border-neutral-200 px-3 dark:border-slate-700">
                        <span className="text-xs font-semibold text-neutral-700 dark:text-neutral-200">Account details</span>
                        <button
                          type="button"
                          onClick={() => setSelected(null)}
                          className="inline-flex h-7 w-7 items-center justify-center rounded text-neutral-500 hover:bg-neutral-100 hover:text-neutral-800 dark:hover:bg-slate-800 dark:hover:text-neutral-100"
                          aria-label="Close account details"
                          title="Close"
                        >
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </div>
                      <div className="h-[calc(100%-36px)]">
                        <AccountEditPanel
                          account={selected as Account}
                          clientId={currentClient.id}
                          onSaved={load}
                          onDeleted={() => { setSelected(null); load() }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </div>

        {currentClient && (
          <AccountCreateModal
            open={showCreate}
            clientId={currentClient.id}
            existingAccounts={flatten(tree)}
            initialParentId={selected?.id ?? null}
            onClose={() => setShowCreate(false)}
            onCreated={load}
          />
        )}
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

