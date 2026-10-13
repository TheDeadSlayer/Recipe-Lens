import { NavLink } from 'react-router-dom'
import { ChefHat } from 'lucide-react'
import { useState } from 'react'
import { Menu, X } from 'lucide-react'

const navLinks = [
  { to: '/', label: 'Analyze', end: true },
  { to: '/recipes', label: 'Recipes', end: false },
]

export default function Header() {
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <header className="bg-white border-b border-slate-200 sticky top-0 z-40">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Brand */}
          <NavLink
            to="/"
            className="flex items-center gap-2 group"
            aria-label="RecipeLens home"
          >
            <span className="flex items-center justify-center w-8 h-8 bg-amber-500 rounded-lg text-white">
              <ChefHat size={18} strokeWidth={2.5} />
            </span>
            <span className="text-lg font-bold text-slate-900 tracking-tight">
              Recipe<span className="text-amber-500">Lens</span>
            </span>
          </NavLink>

          {/* Desktop nav */}
          <nav className="hidden sm:flex items-center gap-1" aria-label="Main navigation">
            {navLinks.map(({ to, label, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  [
                    'px-4 py-2 text-sm font-medium rounded-lg transition-colors',
                    isActive
                      ? 'bg-amber-50 text-amber-700'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100',
                  ].join(' ')
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>

          {/* Mobile hamburger */}
          <button
            className="sm:hidden p-2 rounded-lg text-slate-600 hover:bg-slate-100 transition-colors"
            onClick={() => setMobileOpen((o) => !o)}
            aria-label={mobileOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={mobileOpen}
          >
            {mobileOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {/* Mobile nav drawer */}
      {mobileOpen && (
        <nav
          className="sm:hidden border-t border-slate-200 bg-white px-4 py-3 flex flex-col gap-1"
          aria-label="Mobile navigation"
        >
          {navLinks.map(({ to, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) =>
                [
                  'px-4 py-2.5 text-sm font-medium rounded-lg transition-colors',
                  isActive
                    ? 'bg-amber-50 text-amber-700'
                    : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100',
                ].join(' ')
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
      )}
    </header>
  )
}
