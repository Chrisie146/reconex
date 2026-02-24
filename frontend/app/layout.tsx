import type { Metadata } from 'next'
import './globals.css'
import { ClientProvider } from '@/lib/clientContext'
import { Toaster } from 'sonner'

export const metadata: Metadata = {
  title: 'Reconex',
  description: 'Professional bank statement analysis for small businesses',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-white text-neutral-900" suppressHydrationWarning>
        <ClientProvider>
          <Toaster richColors position="top-right" />
          <div className="min-h-screen">
            {children}
          </div>
        </ClientProvider>
      </body>
    </html>
  )
}
