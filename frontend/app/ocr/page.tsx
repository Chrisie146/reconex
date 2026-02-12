"use client"

import React, { useState } from 'react'
import dynamic from 'next/dynamic'
import PreviewTable from '../components/PreviewTable'
import Sidebar from '@/components/Sidebar'
import { v4 as uuidv4 } from 'uuid'
import axios from '@/lib/axiosClient'

// Dynamically import OCRCanvas to avoid SSR issues with react-pdf
const OCRCanvas = dynamic(() => import('../components/OCRCanvas'), {
  ssr: false,
  loading: () => <div className="border p-4 text-center">Loading PDF viewer...</div>
})

// TypeScript interfaces
interface Region {
  x: number
  y: number
  w: number
  h: number
}

interface RegionsByPage {
  [page: number]: {
    [key: string]: Region
  }
}

interface OCRResult {
  [key: number]: {
    rows?: Array<{
      date?: string
      description?: string
      amount?: number | string
      issues?: string[]
    }>
    warnings?: string[]
    error?: string
  } | {
    rows: Array<{
      date?: string
      description?: string
      amount?: number | string
      issues?: string[]
    }>
    warnings: string[]
  }
}

export default function OCRPage(){
  const [file, setFile] = useState<File | null>(null)
  const [sessionId, setSessionId] = useState<string>('')
  const [ocrResult, setOcrResult] = useState<OCRResult | null>(null)
  const [pageCount, setPageCount] = useState<number>(1)
  const [selectedPages, setSelectedPages] = useState<Set<number>>(new Set())
  const [extracting, setExtracting] = useState<boolean>(false)
  const [pageProgress, setPageProgress] = useState<{[key: number]: string}>({})
  const [step, setStep] = useState<number>(1)

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) {
      setFile(f)
      setSessionId(uuidv4())
    }
  }

  const handlePageInfo = ({ pageCount }: { pageCount: number }) => {
    setPageCount(pageCount)
    // preselect first page by default
    setSelectedPages(new Set([1]))
  }

  const togglePage = (p: number) => {
    setSelectedPages(prev => {
      const copy = new Set(prev)
      if(copy.has(p)) copy.delete(p)
      else copy.add(p)
      return copy
    })
  }

  const selectAllPages = () => {
    setSelectedPages(new Set(Array.from({length: pageCount}, (_,i)=>i+1)))
  }

  const clearSelection = () => setSelectedPages(new Set<number>())

  const handleSaveRegions = async (regionsByPage: RegionsByPage, amountType: string = 'single') => {
    // regionsByPage: { 1: {date_region:..., description_region:..., amount_region:...}, 2: {...} }
    const payload = { pages: regionsByPage, amount_type: amountType }
    await axios.post('/ocr/regions?session_id=' + sessionId, payload)
    setStep(3)
  }

  const handleRunOCR = async () => {
    if(!file) return
    setExtracting(true)
    setPageProgress({})

    try{
      // If no pages explicitly selected, call extract for all saved pages (backend will run all)
      if(!selectedPages || selectedPages.size === 0){
        const fd = new FormData()
        fd.append('file', file)
        const res = await axios.post('/ocr/extract?session_id=' + sessionId, fd, { headers: { 'Content-Type': 'multipart/form-data' } })
        setOcrResult(res.data.results || res.data.result || res.data)
        setExtracting(false)
        return
      }

      // Otherwise run extraction per selected page and aggregate results (sequential to show progress)
      const pages = Array.from(selectedPages).sort((a,b)=>a-b)
      const results: {[key: number]: any} = {}
      for(const p of pages){
        setPageProgress(prev=>({ ...prev, [p]: 'pending' }))
        try{
          const fd = new FormData()
          fd.append('file', file)
          const res = await axios.post('/ocr/extract?session_id=' + sessionId + '&page=' + p, fd, { headers: { 'Content-Type': 'multipart/form-data' } })
          results[p] = res.data.result || res.data.results || res.data
          setPageProgress(prev=>({ ...prev, [p]: 'done' }))
        }catch(err: any){
          setPageProgress(prev=>({ ...prev, [p]: 'failed' }))
          results[p] = { error: err?.message || 'failed' }
        }
      }

      setOcrResult(results)
    }finally{
      setExtracting(false)
    }
  }

  return (
    <>
      <Sidebar sessionId={null} />
      
      <div className="ml-64 transition-all duration-300">
        <div className="p-6">
          <h2 className="text-2xl font-semibold mb-4">Guided OCR Wizard</h2>

          <div className="mb-4">
            <label className="block mb-2">Upload scanned PDF (single file)</label>
            <input type="file" accept="application/pdf" onChange={handleFile} />
          </div>

          {file && (
            <div>
              <OCRCanvas file={file} onSaveRegions={handleSaveRegions} step={step} setStep={setStep} onPageInfoChange={handlePageInfo} />

              <div className="mt-4">
                <label className="block font-medium mb-2">Select pages to run OCR (choose none to run all saved pages)</label>
                <div className="flex gap-2 flex-wrap items-center">
                  <button className="px-2 py-1 border rounded bg-white" onClick={selectAllPages} disabled={extracting}>Select All</button>
                  <button className="px-2 py-1 border rounded bg-white" onClick={clearSelection} disabled={extracting}>Clear</button>
                  {Array.from({length: pageCount}, (_,i)=>i+1).map(p=> (
                    <button key={p} onClick={()=>togglePage(p)} disabled={extracting} className={`px-2 py-1 border rounded ${selectedPages.has(p) ? 'bg-sky-600 text-white' : 'bg-white'}`}>
                      Page {p}
                      {pageProgress[p] === 'pending' && <span className="ml-2 text-xs text-yellow-600">●</span>}
                      {pageProgress[p] === 'done' && <span className="ml-2 text-xs text-green-600">✓</span>}
                      {pageProgress[p] === 'failed' && <span className="ml-2 text-xs text-rose-600">✕</span>}
                    </button>
                  ))}
                </div>
              </div>

              <div className="mt-4">
                <button className="px-4 py-2 bg-sky-600 text-white rounded" onClick={handleRunOCR}>Run OCR & Preview</button>
              </div>
            </div>
          )}

          {ocrResult && (
            <div className="mt-6">
              <h3 className="text-xl font-medium mb-2">Preview Results</h3>
              <PreviewTable result={ocrResult} />
            </div>
          )}
        </div>
      </div>
    </>
  )
}
