"use client"

import React, { useEffect, useRef, useState } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'

// Set up PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.js`

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

interface OCRCanvasProps {
  file: File | null
  onSaveRegions: (regions: RegionsByPage, amountType: string) => void
  step: number
  setStep: (step: number) => void
  onPageInfoChange: (info: { pageCount: number }) => void
}

// Simple canvas-based region selector that renders PDF pages with react-pdf
export default function OCRCanvas({ file, onSaveRegions, step, setStep, onPageInfoChange }: OCRCanvasProps){
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const pdfContainerRef = useRef<HTMLDivElement>(null)
  const [regionsByPage, setRegionsByPage] = useState<RegionsByPage>({})
  const [drawing, setDrawing] = useState<boolean>(false)
  const [startPt, setStartPt] = useState<{x: number, y: number} | null>(null)
  const [currentRect, setCurrentRect] = useState<{x: number, y: number, w: number, h: number} | null>(null)
  const [mode, setMode] = useState<string>('date')
  const [pageCount, setPageCount] = useState<number>(1)
  const [currentPage, setCurrentPage] = useState<number>(1)
  const [pdfFile, setPdfFile] = useState<string | null>(null)

  useEffect(()=>{
    if(!file) {
      setPdfFile(null)
      return
    }

    const reader = new FileReader()
    reader.onload = (ev) => {
      if (ev.target?.result) {
        setPdfFile(ev.target.result as string)
      }
    }
    reader.readAsDataURL(file)
  }, [file])

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setPageCount(numPages)
    if(onPageInfoChange) onPageInfoChange({ pageCount: numPages })
  }

  const onDocumentLoadError = (error: Error) => {
    console.error('PDF load error:', error)
  }

  useEffect(()=>{
    // draw saved regions overlays for current page
    const canvas = canvasRef.current
    if(!canvas) return
    const ctx = canvas.getContext('2d')
    if(!ctx) return
    ctx.clearRect(0,0,canvas.width, canvas.height)
    // assume PDF rendering remains; caller will re-render when page changes
    const regions = regionsByPage[currentPage] || {}
    for(const key of Object.keys(regions)){
      const r = regions[key]
      ctx.fillStyle = 'rgba(56,189,248,0.25)'
      ctx.fillRect(r.x * canvas.width, r.y * canvas.height, r.w * canvas.width, r.h * canvas.height)
      ctx.strokeStyle = 'rgba(56,189,248,0.9)'
      ctx.lineWidth = 2
      ctx.strokeRect(r.x * canvas.width, r.y * canvas.height, r.w * canvas.width, r.h * canvas.height)
    }
    if(currentRect){
      ctx.fillStyle = 'rgba(96,165,250,0.25)'
      ctx.fillRect(currentRect.x, currentRect.y, currentRect.w, currentRect.h)
      ctx.strokeStyle = 'rgba(96,165,250,0.9)'
      ctx.lineWidth = 2
      ctx.strokeRect(currentRect.x, currentRect.y, currentRect.w, currentRect.h)
    }
  }, [regionsByPage, currentRect, currentPage])

  const toRelative = (rect: {x: number, y: number, w: number, h: number}, canvas: HTMLCanvasElement) => ({
    x: rect.x / canvas.width,
    y: rect.y / canvas.height,
    w: rect.w / canvas.width,
    h: rect.h / canvas.height
  })

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) =>{
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    setStartPt({x,y})
    setDrawing(true)
  }

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) =>{
    if(!drawing) return
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    const sx = startPt?.x || 0
    const sy = startPt?.y || 0
    const rx = Math.min(sx, x)
    const ry = Math.min(sy, y)
    const rw = Math.abs(x - sx)
    const rh = Math.abs(y - sy)
    setCurrentRect({x: rx, y: ry, w: rw, h: rh})
  }

  const handleMouseUp = (e: React.MouseEvent<HTMLCanvasElement>) =>{
    setDrawing(false)
    const canvas = canvasRef.current
    if(!currentRect || !canvas) return
    const rel = toRelative(currentRect, canvas)
    // save under current mode for current page
    const key = mode === 'date' ? 'date_region' : mode === 'description' ? 'description_region' : mode === 'amount' ? 'amount_region' : mode
    setRegionsByPage(prev=>{ const copy = {...prev}; const p = copy[currentPage] ? {...copy[currentPage]} : {}; p[key]=rel; copy[currentPage]=p; return copy })
    setCurrentRect(null)
  }

  const handleNextMode = () =>{
    if(mode === 'date') setMode('description')
    else if(mode === 'description') setMode('amount')
    else setMode('done')
  }

  const handleSave = () =>{
    // save all pages' regions via callback
    onSaveRegions(regionsByPage, 'single')
  }

  const goToPage = (p: number) =>{
    const pnum = Math.max(1, Math.min(pageCount, p))
    setCurrentPage(pnum)
  }

  return (
    <div>
      <div className="mb-2">
        <div className="flex items-center justify-between">
          <div>
            <label className="font-medium">Step: {mode}</label>
            <div className="text-sm text-slate-600">{mode === 'date' ? 'Drag a box around where transaction dates appear.' : mode === 'description' ? 'Now select the transaction descriptions column.' : mode === 'amount' ? 'Select the amounts column.' : 'Done'}</div>
          </div>
          <div className="space-x-2">
            <button className="px-2 py-1 bg-gray-100 rounded" onClick={()=>goToPage(currentPage-1)}>- Prev</button>
            <span>Page {currentPage} / {pageCount}</span>
            <button className="px-2 py-1 bg-gray-100 rounded" onClick={()=>goToPage(currentPage+1)}>Next +</button>
          </div>
        </div>
      </div>

      <div className="border relative" ref={pdfContainerRef}>
        {pdfFile && (
          <Document
            file={pdfFile}
            onLoadSuccess={onDocumentLoadSuccess}
            onLoadError={onDocumentLoadError}
          >
            <Page pageNumber={currentPage} scale={1.5} />
          </Document>
        )}
        <canvas
          ref={canvasRef}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: 'auto',
            display: 'block',
            touchAction: 'none',
            pointerEvents: 'auto'
          }}
        />
      </div>

      <div className="mt-3 flex gap-2">
        <button className="px-3 py-1 bg-gray-200 rounded" onClick={()=>setMode('date')}>Date</button>
        <button className="px-3 py-1 bg-gray-200 rounded" onClick={()=>setMode('description')}>Description</button>
        <button className="px-3 py-1 bg-gray-200 rounded" onClick={()=>setMode('amount')}>Amount</button>
        <button className="px-3 py-1 bg-sky-600 text-white rounded" onClick={handleNextMode}>Next</button>
        <button className="px-3 py-1 bg-green-600 text-white rounded" onClick={handleSave}>Save All Pages</button>
      </div>
    </div>
  )
}