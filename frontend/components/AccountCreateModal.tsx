'use client'

import { useEffect, useMemo, useState } from 'react'
import { X, Plus, RefreshCw } from 'lucide-react'
import { toast } from 'sonner'
import { apiFetch } from '@/lib/apiFetch'
import {
  Account,
  AccountType,
  CashFlowSection,
  NormalBalance,
  VATTreatment,
  invalidateAccounts,
} from '@/lib/hooks/useAccounts'

interface AccountCreateModalProps {
  open: boolean
  clientId: number
  existingAccounts: Account[]
  initialParentId?: number | null
  onClose: () => void
  onCreated: () => void
}

const TYPE_OPTIONS: AccountType[] = ['asset', 'liability', 'equity', 'revenue', 'expense']
const CASH_FLOW_OPTIONS: CashFlowSection[] = ['operating', 'investing', 'financing', 'none']
const VAT_OPTIONS: VATTreatment[] = ['standard_15', 'zero_rated', 'exempt', 'out_of_scope']

const DEFAULT_BALANCE_BY_TYPE: Record<AccountType, NormalBalance> = {
  asset: 'DR',
  expense: 'DR',
  liability: 'CR',
  equity: 'CR',
  revenue: 'CR',
}

export default function AccountCreateModal({
  open,
  clientId,
  existingAccounts,
  initialParentId = null,
  onClose,
  onCreated,
}: AccountCreateModalProps) {
  const [code, setCode] = useState('')
  const [name, setName] = useState('')
  const [parentId, setParentId] = useState<string>('')
  const [accountType, setAccountType] = useState<AccountType>('expense')
  const [accountSubtype, setAccountSubtype] = useState('')
  const [normalBalance, setNormalBalance] = useState<NormalBalance>('DR')
  const [cashFlow, setCashFlow] = useState<CashFlowSection>('operating')
  const [isPostable, setIsPostable] = useState(true)
  const [isVatControl, setIsVatControl] = useState(false)
  const [vatTreatment, setVatTreatment] = useState<VATTreatment | ''>('')
  const [vatRate, setVatRate] = useState('')
  const [description, setDescription] = useState('')
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!open) return
    setCode('')
    setName('')
    setParentId(initialParentId == null ? '' : String(initialParentId))
    setAccountType('expense')
    setAccountSubtype('')
    setNormalBalance(DEFAULT_BALANCE_BY_TYPE.expense)
    setCashFlow('operating')
    setIsPostable(true)
    setIsVatControl(false)
    setVatTreatment('')
    setVatRate('')
    setDescription('')
  }, [open, initialParentId])

  useEffect(() => {
    setNormalBalance(DEFAULT_BALANCE_BY_TYPE[accountType])
  }, [accountType])

  const parentOptions = useMemo(() => {
    return [...existingAccounts].sort((a, b) => {
      if (a.code === b.code) return a.name.localeCompare(b.name)
      return a.code.localeCompare(b.code)
    })
  }, [existingAccounts])

  if (!open) return null

  const submit = async () => {
    if (!code.trim() || !name.trim()) {
      toast.error('Code and name are required')
      return
    }

    setSubmitting(true)
    try {
      const payload = {
        client_id: clientId,
        code: code.trim(),
        name: name.trim(),
        parent_id: parentId ? Number(parentId) : null,
        account_type: accountType,
        account_subtype: accountSubtype.trim() || null,
        normal_balance: normalBalance,
        cash_flow_section: cashFlow,
        is_vat_control: isVatControl,
        vat_treatment: vatTreatment || null,
        vat_rate: vatRate === '' ? null : Number(vatRate),
        is_postable: isPostable,
        description: description.trim() || null,
      }

      await apiFetch('/accounts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      invalidateAccounts(clientId)
      toast.success(`Created account ${code.trim()} - ${name.trim()}`)
      onCreated()
      onClose()
    } catch (err: any) {
      toast.error(err?.message ?? 'Failed to create account')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[100]">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="absolute inset-x-0 top-0 mx-auto mt-10 w-full max-w-2xl rounded-xl border border-neutral-200 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-2xl">
        <div className="flex items-center justify-between border-b border-neutral-200 dark:border-slate-700 px-5 py-4">
          <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-100">Add Account</h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1.5 text-neutral-500 hover:bg-neutral-100 dark:hover:bg-slate-800"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="grid grid-cols-2 gap-4 p-5 max-h-[70vh] overflow-y-auto">
          <Field label="Code *">
            <input
              value={code}
              onChange={e => setCode(e.target.value)}
              placeholder="e.g. 5115"
              className="w-full rounded-md border border-neutral-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
            />
          </Field>

          <Field label="Name *">
            <input
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="e.g. Software Subscriptions"
              className="w-full rounded-md border border-neutral-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
            />
          </Field>

          <Field label="Parent">
            <select
              value={parentId}
              onChange={e => setParentId(e.target.value)}
              className="w-full rounded-md border border-neutral-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
            >
              <option value="">None (top level)</option>
              {parentOptions.map(a => (
                <option key={a.id} value={a.id}>
                  {a.code} - {a.name}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Type">
            <select
              value={accountType}
              onChange={e => setAccountType(e.target.value as AccountType)}
              className="w-full rounded-md border border-neutral-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
            >
              {TYPE_OPTIONS.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </Field>

          <Field label="Subtype">
            <input
              value={accountSubtype}
              onChange={e => setAccountSubtype(e.target.value)}
              placeholder="Optional"
              className="w-full rounded-md border border-neutral-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
            />
          </Field>

          <Field label="Normal Balance">
            <select
              value={normalBalance}
              onChange={e => setNormalBalance(e.target.value as NormalBalance)}
              className="w-full rounded-md border border-neutral-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
            >
              <option value="DR">DR</option>
              <option value="CR">CR</option>
            </select>
          </Field>

          <Field label="Cash Flow Section">
            <select
              value={cashFlow}
              onChange={e => setCashFlow(e.target.value as CashFlowSection)}
              className="w-full rounded-md border border-neutral-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
            >
              {CASH_FLOW_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </Field>

          <Field label="VAT Treatment">
            <select
              value={vatTreatment}
              onChange={e => setVatTreatment(e.target.value as VATTreatment | '')}
              className="w-full rounded-md border border-neutral-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
            >
              <option value="">None</option>
              {VAT_OPTIONS.map(v => <option key={v} value={v}>{v}</option>)}
            </select>
          </Field>

          <Field label="VAT Rate (%)">
            <input
              type="number"
              step="0.01"
              value={vatRate}
              onChange={e => setVatRate(e.target.value)}
              placeholder="Optional"
              className="w-full rounded-md border border-neutral-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm"
            />
          </Field>

          <div className="col-span-2 grid grid-cols-2 gap-4">
            <label className="flex items-center gap-2 text-sm text-neutral-700 dark:text-neutral-200">
              <input
                type="checkbox"
                checked={isPostable}
                onChange={e => setIsPostable(e.target.checked)}
                className="rounded border-neutral-300"
              />
              <span>Postable account</span>
            </label>
            <label className="flex items-center gap-2 text-sm text-neutral-700 dark:text-neutral-200">
              <input
                type="checkbox"
                checked={isVatControl}
                onChange={e => setIsVatControl(e.target.checked)}
                className="rounded border-neutral-300"
              />
              <span>VAT control account</span>
            </label>
          </div>

          <div className="col-span-2">
            <Field label="Description">
              <textarea
                value={description}
                onChange={e => setDescription(e.target.value)}
                rows={3}
                className="w-full rounded-md border border-neutral-300 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm resize-y"
              />
            </Field>
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-neutral-200 dark:border-slate-700 px-5 py-4">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-neutral-300 dark:border-slate-600 px-4 py-2 text-sm text-neutral-700 dark:text-neutral-200 hover:bg-neutral-50 dark:hover:bg-slate-800"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={submitting}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {submitting ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
            Create account
          </button>
        </div>
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="mb-1.5 block text-[11px] uppercase tracking-wider text-neutral-500 dark:text-neutral-400">{label}</label>
      {children}
    </div>
  )
}
