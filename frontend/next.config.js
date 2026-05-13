/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: false,
  },
  eslint: {
    ignoreDuringBuilds: false,
  },
  // Proxy all backend API paths through Next.js so CORS and URL config
  // are handled server-side. Requires BACKEND_URL env var (not NEXT_PUBLIC_).
  async rewrites() {
    const backend = process.env.BACKEND_URL
    if (!backend) return []
    const apiPaths = [
      'accounts', 'auth', 'categories', 'clients', 'rules',
      'upload', 'ocr', 'transactions', 'invoices', 'sessions',
      'reconciliation', 'reports', 'jobs', 'admin', 'column-mapping',
      'health',
    ]
    return apiPaths.flatMap(path => [
      {
        source: `/${path}`,
        destination: `${backend}/${path}`,
      },
      {
        source: `/${path}/:rest*`,
        destination: `${backend}/${path}/:rest*`,
      },
    ])
  },
  webpack: (config, { isServer }) => {
    // Exclude canvas from webpack resolution (optional dependency in pdfjs-dist)
    // This allows pdfjs-dist to work without canvas being installed
    config.resolve.fallback = {
      ...config.resolve.fallback,
      canvas: false,
    }
    return config
  },
}

module.exports = nextConfig
