import { Link } from 'react-router-dom'
import {
  Inbox,
  ClipboardCheck,
  Archive,
  BarChart3,
  LogOut,
  Mail,
  Moon,
  Sun,
} from 'lucide-react'
import type { UserProfile } from '@/types/api'

const navItems = [
  { path: '/', label: 'Pipeline', icon: Inbox },
  { path: '/review', label: 'Review', icon: ClipboardCheck },
  { path: '/archive', label: 'Archive', icon: Archive },
  { path: '/metrics', label: 'Metrics', icon: BarChart3 },
]

interface SidebarProps {
  user: UserProfile | null
  onLogout: () => void
  currentPath: string
  dark: boolean
  onToggleDark: () => void
}

export default function Sidebar({ user, onLogout, currentPath, dark, onToggleDark }: SidebarProps) {
  return (
    <aside className="w-64 border-r border-border bg-card flex flex-col">
      <div className="p-4 border-b border-border">
        <div className="flex items-center gap-2">
          <Mail className="h-5 w-5" />
          <span className="font-semibold text-lg">The Mailroom</span>
        </div>
        <p className="text-xs text-muted-foreground mt-1">Optional operator desk</p>
      </div>

      <nav className="flex-1 p-3 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon
          const active = currentPath === item.path
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
                active
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground'
              }`}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </Link>
          )
        })}
      </nav>

      <div className="p-4 border-t border-border space-y-3">
        <button
          type="button"
          onClick={onToggleDark}
          className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground"
        >
          {dark ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
          {dark ? 'Light mode' : 'Dark mode'}
        </button>
        <div className="flex items-center justify-between">
          <div className="text-sm">
            <p className="font-medium">{user?.username}</p>
            <p className="text-xs text-muted-foreground capitalize">{user?.role}</p>
          </div>
          <button
            type="button"
            onClick={onLogout}
            className="p-2 rounded-md hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </aside>
  )
}
