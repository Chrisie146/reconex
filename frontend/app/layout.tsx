import type { Metadata } from 'next'
import './globals.css'
import { ClientProvider } from '@/lib/clientContext'

export const metadata: Metadata = {
  title: 'Bank Statement Analyzer',
  description: 'Professional bank statement analysis for small businesses',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-white text-neutral-900">
        <ClientProvider>
          <div className="min-h-screen">
            {children}
          </div>
        </ClientProvider>
      </body>
    </html>
  )
}
