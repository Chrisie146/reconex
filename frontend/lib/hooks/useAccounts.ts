'use client'

import { useCallback, useEffect, useState } from 'react'
import { apiFetch } from '../apiFetch'

export type AccountType = 'asset' | 'liability' | 'equity' | 'revenue' | 'expense'
export type NormalBalance = 'DR' | 'CR'
export type CashFlowSection = 'operating' | 'investing' | 'financing' | 'none'
export type VATTreatment = 'standard_15' | 'zero_rated' | 'exempt' | 'out_of_scope'

export interface Account {
  id: number
  client_id: number
  code: string
  name: string
  parent_id: number | null
  path: string
  level: number
  account_type: AccountType
  account_subtype: string | null
  normal_balance: NormalBalance
  cash_flow_section: CashFlowSection
  is_vat_control: boolean
  vat_treatment: VATTreatment | null
  vat_rate: number | null
  is_postable: boolean
  is_active: boolean
  is_system: boolean
  description: string | null
}

export interface AccountNode extends Account {
  children: AccountNode[]
}

interface UseAccountsResult {
  accounts: Account[]
  loading: boolean
  error: string | null
  refresh: () => Promise<void>
}

/**
 * Fetches the flat account list for a client. Caches per-client in module
 * scope so multiple components mounted on the same page share one request.
 */
const cache = new Map<number, Account[]>()
const inflight = new Map<number, Promise<Account[]>>()

export function useAccounts(clientId: number | null, opts: { postable?: boolean } = {}): UseAccountsResult {
  const postable = !!opts.postable
  const [accounts, setAccounts] = useState<Account[]>(() =>
    clientId != null ? cache.get(clientId) ?? [] : [],
  )
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchOnce = useCallback(async (id: number): Promise<Account[]> => {
    const key = id
    if (cache.has(key)) return cache.get(key)!
    if (inflight.has(key)) return inflight.get(key)!
    const params = new URLSearchParams({ client_id: String(id) })
    if (postable) params.set('postable', 'true')
    const p = apiFetch(`/accounts?${params.toString()}`)
      .then((data: Account[] | { accounts?: Account[] }) => {
        const list = Array.isArray(data) ? data : data.accounts ?? []
        cache.set(key, list)
        return list
      })
      .finally(() => inflight.delete(key))
    inflight.set(key, p)
    return p
  }, [postable])

  const refresh = useCallback(async () => {
    if (clientId == null) return
    setLoading(true)
    setError(null)
    try {
      cache.delete(clientId)
      const list = await fetchOnce(clientId)
      setAccounts(list)
    } catch (err: any) {
      setError(err?.message ?? 'Failed to load accounts')
    } finally {
      setLoading(false)
    }
  }, [clientId, fetchOnce])

  useEffect(() => {
    if (clientId == null) {
      setAccounts([])
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)
    fetchOnce(clientId)
      .then(list => { if (!cancelled) setAccounts(list) })
      .catch(err => { if (!cancelled) setError(err?.message ?? 'Failed to load accounts') })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [clientId, fetchOnce])

  return { accounts, loading, error, refresh }
}

/**
 * Invalidate the in-memory cache for a client. Call after a successful mutation
 * (create / update / delete / reassign / re-seed).
 */
export function invalidateAccounts(clientId: number) {
  cache.delete(clientId)
}

export async function fetchAccountTree(clientId: number, postable = false): Promise<AccountNode[]> {
  const params = new URLSearchParams({ client_id: String(clientId) })
  if (postable) params.set('postable', 'true')
  const data = await apiFetch(`/accounts/tree?${params.toString()}`)
  return Array.isArray(data) ? data : data.tree ?? []
}
