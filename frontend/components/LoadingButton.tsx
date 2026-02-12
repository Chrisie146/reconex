import { ButtonSpinner } from './Spinner'
import { ButtonHTMLAttributes, ReactNode } from 'react'

interface LoadingButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  loading?: boolean
  children: ReactNode
  loadingText?: string
  variant?: 'primary' | 'secondary' | 'danger' | 'success'
}

export default function LoadingButton({
  loading = false,
  children,
  loadingText,
  variant = 'primary',
  disabled,
  className = '',
  ...props
}: LoadingButtonProps) {
  const baseClasses = 'px-4 py-2 rounded font-medium transition-colors flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed'
  
  const variantClasses = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700 disabled:hover:bg-blue-600',
    secondary: 'bg-neutral-200 text-neutral-800 hover:bg-neutral-300 disabled:hover:bg-neutral-200',
    danger: 'bg-red-600 text-white hover:bg-red-700 disabled:hover:bg-red-600',
    success: 'bg-green-600 text-white hover:bg-green-700 disabled:hover:bg-green-600'
  }

  return (
    <button
      className={`${baseClasses} ${variantClasses[variant]} ${className}`}
      disabled={disabled || loading}
      {...props}
    >
      {loading && <ButtonSpinner />}
      {loading && loadingText ? loadingText : children}
    </button>
  )
}
