'use client'

import { useEffect, useState } from 'react'
import { Lock, Save, Trash2, AlertCircle, RefreshCw } from 'lucide-react'
import { toast } from 'sonner'
import { apiFetch } from '@/lib/apiFetch'
import { Account, CashFlowSection, VATTreatment, invalidateAccounts } from '@/lib/hooks/useAccounts'

interface AccountEditPanelProps {
  account: Account | null
  clientId: number
  onSaved: () => void
  onDeleted: () => void
}

const CASH_FLOW_OPTIONS: CashFlowSection[] = ['operating', 'investing', 'financing', 'none']
const VAT_OPTIONS: VATTreatment[] = ['standard_15', 'zero_rated', 'exempt', 'out_of_scope']

export default function AccountEditPanel({ account, clientId, onSaved, onDeleted }: AccountEditPanelProps) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [cashFlow, setCashFlow] = useState<CashFlowSection>('none')
  const [vatTreatment, setVatTreatment] = useState<VATTreatment | ''>('')
  const [vatRate, setVatRate] = useState<string>('')
  const [isActive, setIsActive] = useState(true)
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    if (!account) return
    setName(account.name)
    setDescription(account.description ?? '')
    setCashFlow(account.cash_flow_section)
    setVatTreatment(account.vat_treatment ?? '')
    setVatRate(account.vat_rate == null ? '' : String(account.vat_rate))
    setIsActive(account.is_active)
  }, [account?.id])

  if (!account) {
    return (
      <div className="flex flex-col items-center justify-center text-neutral-400 dark:text-neutral-500 h-full p-12 text-center">
        <p className="text-sm">Select an account from the tree to view or edit it.</p>
      </div>
    )
  }

  const isSystem = account.is_system
  const dirty =
    name !== account.name ||
    description !== (account.description ?? '') ||
    cashFlow !== account.cash_flow_section ||
    (vatTreatment || null) !== (account.vat_treatment ?? null) ||
    (vatRate === '' ? null : Number(vatRate)) !== account.vat_rate ||
    isActive !== account.is_active

  const save = async () => {
    setSaving(true)
    try {
      const body: Record<string, unknown> = {
        name,
        description: description || null,
        cash_flow_section: cashFlow,
        vat_treatment: vatTreatment || null,
        vat_rate: vatRate === '' ? null : Number(vatRate),
        is_active: isActive,
      }
      await apiFetch(`/accounts/${account.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      invalidateAccounts(clientId)
      toast.success(`${account.code} saved`)
      onSaved()
    } catch (err: any) {
      toast.error(err?.message ?? 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const remove = async () => {
    if (!confirm(`Delete account ${account.code} — ${account.name}?\n\nIf the account has any postings the API will refuse — you'll need to reassign first.`)) return
    setDeleting(true)
    try {
      await apiFetch(`/accounts/${account.id}`, { method: 'DELETE' })
      invalidateAccounts(clientId)
      toast.success('Account deactivated')
      onDeleted()
    } catch (err: any) {
      toast.error(err?.message ?? 'Delete failed')
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="p-6 space-y-5 overflow-y-auto h-full">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <span className="font-mono text-xs text-neutral-500 dark:text-neutral-400">{account.code}</span>
          {isSystem && (
            <span className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider bg-neutral-100 dark:bg-slate-800 text-neutral-600 dark:text-neutral-300 px-1.5 py-0.5 rounded">
              <Lock className="w-3 h-3" /> System
            </span>
          )}
          {account.is_vat_control && (
            <span className="text-[10px] uppercase tracking-wider bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300 px-1.5 py-0.5 rounded">
              VAT control
            </span>
          )}
          {!account.is_postable && (
            <span className="text-[10px] uppercase tracking-wider bg-neutral-200 dark:bg-slate-700 text-neutral-600 dark:text-neutral-300 px-1.5 py-0.5 rounded">
              Header
            </span>
          )}
        </div>
        <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-100">{account.name}</h2>
      </div>

      {isSystem && (
        <div className="flex items-start gap-2 text-xs bg-blue-50 dark:bg-blue-950/30 text-blue-800 dark:text-blue-200 border border-blue-200 dark:border-blue-900 rounded-md p-3">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <p>
            This is a template-seeded account. Only name, description, cash flow section, VAT treatment and rate, and active status are editable.
          </p>
        </div>
      )}

      {/* Read-only meta */}
      <div className="grid grid-cols-2 gap-4 text-xs">
        <MetaRow label="Type" value={account.account_type} />
        <MetaRow label="Subtype" value={account.account_subtype ?? '—'} />
        <MetaRow label="Normal balance" value={account.normal_balance} />
        <MetaRow label="Postable" value={account.is_postable ? 'Yes' : 'No (header)'} />
      </div>

      {/* Editable fields */}
      <Field label="Name">
        <input
          value={name}
          onChange={e => setName(e.target.value)}
          className="w-full px-3 py-2 text-sm rounded-md border border-neutral-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </Field>

      <Field label="Description">
        <textarea
          value={description}
          onChange={e => setDescription(e.target.value)}
          rows={2}
          className="w-full px-3 py-2 text-sm rounded-md border border-neutral-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-y"
        />
      </Field>

      <Field label="Cash flow section">
        <select
          value={cashFlow}
          onChange={e => setCashFlow(e.target.value as CashFlowSection)}
          className="w-full px-3 py-2 text-sm rounded-md border border-neutral-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {CASH_FLOW_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </Field>

      <div className="grid grid-cols-2 gap-4">
        <Field label="VAT treatment">
          <select
            value={vatTreatment}
            onChange={e => setVatTreatment(e.target.value as VATTreatment | '')}
            className="w-full px-3 py-2 text-sm rounded-md border border-neutral-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">— None —</option>
            {VAT_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </Field>
        <Field label="VAT rate (%)">
          <input
            type="number"
            step="0.01"
            value={vatRate}
            onChange={e => setVatRate(e.target.value)}
            placeholder="—"
            className="w-full px-3 py-2 text-sm rounded-md border border-neutral-300 dark:border-slate-600 bg-white dark:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </Field>
      </div>

      <Field label="Status">
        <label className="flex items-center gap-2 text-sm text-neutral-700 dark:text-neutral-200">
          <input
            type="checkbox"
            checked={isActive}
            onChange={e => setIsActive(e.target.checked)}
            className="rounded border-neutral-300"
          />
          <span>Active</span>
        </label>
      </Field>

      {/* Actions */}
      <div className="flex items-center gap-3 pt-2 border-t border-neutral-200 dark:border-slate-700">
        <button
          type="button"
          onClick={save}
          disabled={saving || !dirty}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          Save
        </button>

        {!isSystem && (
          <button
            type="button"
            onClick={remove}
            disabled={deleting}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-300 hover:bg-rose-100 dark:hover:bg-rose-900/50"
          >
            <Trash2 className="w-4 h-4" />
            Delete
          </button>
        )}
      </div>
    </div>
  )
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wider text-neutral-400 mb-0.5">{label}</p>
      <p className="text-neutral-700 dark:text-neutral-200 capitalize">{value}</p>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-[11px] uppercase tracking-wider text-neutral-500 dark:text-neutral-400 mb-1.5">{label}</label>
      {children}
    </div>
  )
}
