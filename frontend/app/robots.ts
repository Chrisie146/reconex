import { MetadataRoute } from 'next'

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || 'https://reconex-frontend.onrender.com'

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: '*',
        allow: ['/', '/login', '/register', '/forgot-password', '/privacy', '/terms'],
        disallow: [
          '/dashboard',
          '/clients',
          '/transactions',
          '/sessions',
          '/invoices',
          '/reports',
          '/rules',
          '/categories',
          '/backups',
          '/financial-years',
          '/ocr',
          '/mapping',
        ],
      },
    ],
    sitemap: `${SITE_URL}/sitemap.xml`,
  }
}
