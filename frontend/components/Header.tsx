import { Upload } from 'lucide-react'

export default function Header() {
  return (
    <header className="bg-white border-b border-neutral-200">
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-neutral-100 rounded-lg">
            <Upload className="w-6 h-6 text-neutral-900" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-neutral-900">Bank Statement Analyzer</h1>
            <p className="text-neutral-600 mt-1">Professional financial statement processing for small businesses</p>
          </div>
        </div>
      </div>
    </header>
  )
}
