import type { Metadata } from 'next'
import './globals.css'
import { ClientProvider } from '@/lib/clientContext'
import { ThemeProvider } from '@/lib/theme'
import { Toaster } from 'sonner'
import PostHogProvider from '@/components/PostHogProvider'

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
      <body className="bg-white text-neutral-900 dark:bg-neutral-950 dark:text-neutral-100 transition-colors duration-200" suppressHydrationWarning>
        <PostHogProvider>
          <ThemeProvider>
            <ClientProvider>
              <Toaster richColors position="top-right" />
              <div className="min-h-screen">
                {children}
              </div>
            </ClientProvider>
          </ThemeProvider>
        </PostHogProvider>
      </body>
    </html>
  )
}
