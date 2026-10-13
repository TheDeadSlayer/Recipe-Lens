import type { ReactNode } from 'react'

interface Props {
  children: ReactNode
  className?: string
}

export default function PageContainer({ children, className = '' }: Props) {
  return (
    <div className={`max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 ${className}`}>
      {children}
    </div>
  )
}
