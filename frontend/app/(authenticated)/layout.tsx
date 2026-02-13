import AuthGuard from '@/components/AuthGuard'

export default function AuthenticatedLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <AuthGuard>
      {children}
    </AuthGuard>
  )
}