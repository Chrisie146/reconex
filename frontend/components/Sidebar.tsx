'use client'

import { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  ChevronLeft, ChevronRight, BarChart3, Upload, MapPin, List,
  Archive, Eye, Tag, Zap, Sparkles, FileText, FileSpreadsheet,
  FolderOpen, ChevronDown, Receipt, Users, Download,
  Settings2, PanelLeftClose, PanelLeft, Loader2, CalendarRange, HardDrive,
  AlertTriangle
} from 'lucide-react'
import axios from '@/lib/axiosClient'
import { toast } from 'sonner'
import { posthog } from '@/lib/posthog'
import ClientSelector from './ClientSelector'
import StatementSelector from './StatementSelector'
import VATExportModal from './VATExportModal'
import CategoriesExportModal from './CategoriesExportModal'
import UnusualTransactionsModal from './UnusualTransactionsModal'
import { useClient } from '@/lib/clientContext'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/* ── Types ──────────────────────────────────────────────────────────── */
interface SidebarProps {
  sessionId: string | null
  selectedStatement?: string
  onStatementChange?: (statementId: string) => void
}

interface NavItem {
  href: string
  icon: React.ReactNode
  label: string
  matchPrefix: string
}

/* ── Section collapse helper ────────────────────────────────────────── */
function SectionHeader({
  label, open, toggle, collapsed,
}: { label: string; open: boolean; toggle: () => void; collapsed: boolean }) {
  if (collapsed) return null
  return (
    <button onClick={toggle}
      className="flex items-center justify-between w-full px-3 pt-4 pb-1 group">
      <span className="text-[10px] font-bold uppercase tracking-widest text-neutral-500 group-hover:text-neutral-300 transition-colors">
        {label}
      </span>
      <ChevronDown className={`w-3 h-3 text-neutral-500 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
    </button>
  )
}

/* ══════════════════════════════════════════════════════════════════════
   SIDEBAR
   ══════════════════════════════════════════════════════════════════════ */
export default function Sidebar({ sessionId, selectedStatement = '', onStatementChange }: SidebarProps) {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [isMounted, setIsMounted] = useState(false)

  // Sync sidebar width to a CSS variable so content areas can respond
  useEffect(() => {
    document.documentElement.style.setProperty('--sidebar-w', isCollapsed ? '60px' : '256px')
  }, [isCollapsed])
  const [exporting, setExporting] = useState(false)
  const { currentClient } = useClient()

  // collapsible sections
  const [exportsOpen, setExportsOpen] = useState(false)
  const [configOpen, setConfigOpen] = useState(false)
  const [moreOpen, setMoreOpen] = useState(false)

  // modals
  const [showVATModal, setShowVATModal] = useState(false)
  const [showCategoriesModal, setShowCategoriesModal] = useState(false)
  const [showUnusualModal, setShowUnusualModal] = useState(false)

  const pathname = usePathname()

  useEffect(() => { setIsMounted(true) }, [])

  /* ── export handler ────────────────────────────────────────────── */
  const handleExport = useCallback(async (type: 'transactions' | 'summary' | 'categories' | 'accountant' | 'vat') => {
    if (!sessionId && !currentClient?.id) return
    if (type === 'vat')        { setShowVATModal(true); return }
    if (type === 'categories') { setShowCategoriesModal(true); return }

    setExporting(true)
    try {
      const params: any = { format: 'excel' }
      if (currentClient?.id) { params.client_id = currentClient.id }
      else if (sessionId) { params.session_id = sessionId }
      // Always include VAT columns for applicable exports
      if (['transactions', 'summary', 'accountant'].includes(type)) {
        params.include_vat = true
      }
      const filename = `${type}_${sessionId?.substring(0, 8) || currentClient?.id || 'export'}.xlsx`
      const response = await axios.get(`${API_BASE_URL}/export/${type}`, {
        params,
        responseType: 'blob',
      })
      const url = window.URL.createObjectURL(response.data)
      const link = document.createElement('a')
      link.href = url; link.download = filename
      document.body.appendChild(link); link.click()
      document.body.removeChild(link); window.URL.revokeObjectURL(url)
      posthog.capture('export_triggered', { type, format: 'xlsx' })
    } catch { toast.error('Export failed. Please try again.') }
    finally { setExporting(false) }
  }, [sessionId, currentClient])

  /* ── active helpers ────────────────────────────────────────────── */
  const isActive = (prefix: string) => {
    if (prefix === '/dashboard') return pathname === '/dashboard'
    return pathname.startsWith(prefix)
  }

  /* ── nav items ─────────────────────────────────────────────────── */
  const sessionNav: NavItem[] = sessionId ? [
    { href: `/dashboard?session_id=${sessionId}`, icon: <BarChart3 className="w-[18px] h-[18px]" />, label: 'Dashboard',        matchPrefix: '/dashboard' },
    { href: `/transactions?session_id=${sessionId}`, icon: <List className="w-[18px] h-[18px]" />,     label: 'Transactions',     matchPrefix: '/transactions' },
    { href: `/invoices?session_id=${sessionId}`,     icon: <Eye className="w-[18px] h-[18px]" />,      label: 'Invoices',         matchPrefix: '/invoices' },
    { href: `/mapping?session_id=${sessionId}`,      icon: <MapPin className="w-[18px] h-[18px]" />,   label: 'Map Transactions', matchPrefix: '/mapping' },
  ] : []

  const exportItems = [
    { type: 'accountant'   as const, icon: <FileSpreadsheet className="w-[18px] h-[18px]" />, label: 'For Accountant',  title: 'Comprehensive report for accountants' },
    { type: 'transactions' as const, icon: <FileText className="w-[18px] h-[18px]" />,        label: 'Transactions',    title: 'All transactions' },
    { type: 'summary'      as const, icon: <BarChart3 className="w-[18px] h-[18px]" />,       label: 'Summary',         title: 'Monthly summary' },
    { type: 'categories'   as const, icon: <FolderOpen className="w-[18px] h-[18px]" />,      label: 'Categories',      title: 'By category' },
    { type: 'vat'          as const, icon: <Receipt className="w-[18px] h-[18px]" />,         label: 'VAT Report',      title: 'VAT report with calculations' },
  ]

  const configItems: NavItem[] = sessionId ? [
    { href: `/rules?session_id=${sessionId}`,              icon: <Tag className="w-[18px] h-[18px]" />,      label: 'Categories',       matchPrefix: '/rules' },
    { href: `/rules?session_id=${sessionId}&tab=rules`,    icon: <Zap className="w-[18px] h-[18px]" />,      label: 'Manual Rules',     matchPrefix: '/rules' },
    { href: `/rules?session_id=${sessionId}&tab=learned`,  icon: <Sparkles className="w-[18px] h-[18px]" />, label: 'Learned Patterns', matchPrefix: '/rules' },
  ] : []

  /* ══════════════════════════════════════════════════════════════════
     RENDER
     ══════════════════════════════════════════════════════════════════ */
  return (
    <div className={`fixed left-0 top-0 h-full z-50 flex flex-col
      bg-slate-900 text-neutral-100 border-r border-slate-800
      transition-all duration-300 ease-in-out
      ${isCollapsed ? 'w-[60px]' : 'w-64'}`}>

      {/* ── Brand header ─────────────────────────────────────────── */}
      <div className="flex items-center justify-between h-14 px-3 border-b border-slate-800 shrink-0">
        {!isCollapsed && (
          <div className="flex items-center gap-2.5 min-w-0">
            <span className="text-sm font-bold tracking-tight truncate lowercase">recon<span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-blue-600">ex</span></span>
          </div>
        )}
        <button onClick={() => setIsCollapsed(!isCollapsed)}
          className="p-1.5 rounded-lg text-neutral-400 hover:text-white hover:bg-slate-800 transition-colors shrink-0"
          title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}>
          {isCollapsed ? <PanelLeft className="w-4 h-4" /> : <PanelLeftClose className="w-4 h-4" />}
        </button>
      </div>

      {/* ── Client & Statement selectors ─────────────────────────── */}
      <div className="shrink-0 border-b border-slate-800">
        {/* Client */}
        {isMounted && !isCollapsed && (
          <div className="px-3 pt-3 pb-2">
            <p className="text-[10px] font-bold uppercase tracking-widest text-neutral-500 mb-2 px-0.5">Client</p>
            <ClientSelector isDarkMode={true} isCollapsed={isCollapsed} />
          </div>
        )}
        {isMounted && isCollapsed && (
          <div className="flex justify-center py-3">
            <ClientSelector isDarkMode={true} isCollapsed={isCollapsed} />
          </div>
        )}

        {/* Statement */}
        {isMounted && !isCollapsed && (
          <div className="px-0 pb-2">
            <StatementSelector
              selectedStatement={selectedStatement}
              onStatementChange={onStatementChange || (() => {})}
              isCollapsed={isCollapsed}
            />
          </div>
        )}
      </div>

      {/* ── Scrollable Navigation ────────────────────────────────── */}
      <nav className={`flex-1 overflow-y-auto overflow-x-hidden py-2 space-y-0.5 scrollbar-thin scrollbar-thumb-neutral-700 ${isCollapsed ? 'px-1.5' : 'px-2'}`}>

        {/* Upload */}
        <NavLink href="/dashboard"
          icon={<Upload className="w-[18px] h-[18px]" />}
          label="Upload Statement"
          active={isActive('/dashboard')}
          collapsed={isCollapsed} />

        {/* Session links */}
        {isMounted && sessionId && sessionNav.length > 0 && (
          <>
            {!isCollapsed && (
              <p className="text-[10px] font-bold uppercase tracking-widest text-neutral-500 px-3 pt-4 pb-1">Session</p>
            )}
            {isCollapsed && <div className="my-1.5 mx-2 border-t border-slate-800" />}
            {sessionNav.map(item => (
              <NavLink key={item.matchPrefix} href={item.href}
                icon={item.icon} label={item.label}
                active={isActive(item.matchPrefix)} collapsed={isCollapsed} />
            ))}

            {/* ── Exports ──────────────────────────────────────────── */}
            <SectionHeader label="Exports" open={exportsOpen} toggle={() => setExportsOpen(!exportsOpen)} collapsed={isCollapsed} />
            {isCollapsed && <div className="my-1.5 mx-2 border-t border-slate-800" />}
            {(exportsOpen || isCollapsed) && exportItems.map(item => (
              <ExportButton key={item.type}
                icon={item.icon} label={item.label} title={item.title}
                collapsed={isCollapsed} loading={exporting}
                onClick={() => handleExport(item.type)} />
            ))}
            {(exportsOpen || isCollapsed) && (
              <ExportButton
                icon={<AlertTriangle className="w-[18px] h-[18px]" />}
                label="Unusual Transactions"
                title="Flag irregular or unusual transactions"
                collapsed={isCollapsed}
                loading={false}
                onClick={() => setShowUnusualModal(true)}
              />
            )}

            {/* ── Configuration ────────────────────────────────────── */}
            <SectionHeader label="Configuration" open={configOpen} toggle={() => setConfigOpen(!configOpen)} collapsed={isCollapsed} />
            {isCollapsed && <div className="my-1.5 mx-2 border-t border-slate-800" />}
            {(configOpen || isCollapsed) && configItems.map(item => (
              <NavLink key={item.label} href={item.href}
                icon={item.icon} label={item.label}
                active={isActive(item.matchPrefix)} collapsed={isCollapsed} />
            ))}
          </>
        )}

        {/* ── More ──────────────────────────────────────────────── */}
        <SectionHeader label="More" open={moreOpen} toggle={() => setMoreOpen(!moreOpen)} collapsed={isCollapsed} />
        {isCollapsed && <div className="my-1.5 mx-2 border-t border-slate-800" />}
        {(moreOpen || isCollapsed) && (
          <>
            <NavLink href="/clients" icon={<Users className="w-[18px] h-[18px]" />}
              label="Clients" active={isActive('/clients')} collapsed={isCollapsed} />
            <NavLink href="/sessions" icon={<Archive className="w-[18px] h-[18px]" />}
              label="All Statements" active={isActive('/sessions')} collapsed={isCollapsed} />
            <NavLink href="/financial-years" icon={<CalendarRange className="w-[18px] h-[18px]" />}
              label="Financial Years" active={isActive('/financial-years')} collapsed={isCollapsed} />
            <NavLink href="/backups" icon={<HardDrive className="w-[18px] h-[18px]" />}
              label="Backups" active={isActive('/backups')} collapsed={isCollapsed} />
          </>
        )}
      </nav>

      {/* ── Footer ──────────────────────────────────────────────── */}
      {!isCollapsed && (
        <div className="shrink-0 border-t border-slate-800 px-4 py-3">
          <p className="text-[10px] text-neutral-600 text-center">Reconex v2.0</p>
        </div>
      )}

      {/* ── Modals ──────────────────────────────────────────────── */}
      <VATExportModal isOpen={showVATModal} onClose={() => setShowVATModal(false)} sessionId={sessionId} clientId={currentClient?.id} />
      <CategoriesExportModal isOpen={showCategoriesModal} onClose={() => setShowCategoriesModal(false)} sessionId={sessionId} clientId={currentClient?.id} />
      <UnusualTransactionsModal isOpen={showUnusualModal} onClose={() => setShowUnusualModal(false)} sessionId={sessionId} clientId={currentClient?.id} />
    </div>
  )
}

/* ╔══════════════════════════════════════════════════════════════════════
   ║  SUB-COMPONENTS
   ╚══════════════════════════════════════════════════════════════════════ */

/* ── NavLink ────────────────────────────────────────────────────────── */
function NavLink({
  href, icon, label, active, collapsed,
}: { href: string; icon: React.ReactNode; label: string; active: boolean; collapsed: boolean }) {
  return (
    <Link href={href} title={collapsed ? label : undefined}
      className={`group flex items-center gap-3 rounded-lg px-3 py-2 text-[13px] font-medium transition-colors relative
        ${active
          ? 'bg-blue-600/20 text-blue-300'
          : 'text-neutral-400 hover:text-neutral-100 hover:bg-slate-800'
        }
        ${collapsed ? 'justify-center px-0' : ''}
      `}>
      {active && <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full bg-blue-500" />}
      <span className={`shrink-0 ${active ? 'text-blue-400' : 'text-neutral-500 group-hover:text-neutral-300'}`}>{icon}</span>
      {!collapsed && <span className="truncate">{label}</span>}
    </Link>
  )
}

/* ── ExportButton ───────────────────────────────────────────────────── */
function ExportButton({
  icon, label, title, collapsed, loading, onClick,
}: { icon: React.ReactNode; label: string; title: string; collapsed: boolean; loading: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} disabled={loading} title={collapsed ? label : title}
      className={`group flex items-center gap-3 rounded-lg px-3 py-2 text-[13px] font-medium w-full text-left transition-colors
        text-neutral-400 hover:text-neutral-100 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed
        ${collapsed ? 'justify-center px-0' : ''}
      `}>
      <span className={`shrink-0 text-neutral-500 group-hover:text-neutral-300 ${loading ? 'animate-pulse' : ''}`}>
        {loading ? <Loader2 className="w-[18px] h-[18px] animate-spin" /> : icon}
      </span>
      {!collapsed && <span className="truncate">{label}</span>}
    </button>
  )
}