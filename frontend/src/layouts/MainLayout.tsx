import { Outlet, NavLink } from 'react-router-dom';
import { GraduationCap, LayoutDashboard, MessageSquare, ShieldCheck } from 'lucide-react';

export default function MainLayout() {
  return (
    <div className="flex flex-col h-screen bg-aast-light text-slate-800 font-sans">
      <header className="flex-none flex items-center h-16 px-6 bg-aast-navy text-white shadow-md z-10">
        <div className="flex items-center gap-3">
          <GraduationCap className="text-aast-gold" size={28} />
          <h1 className="text-xl font-bold tracking-tight">
            AAST <span className="text-aast-gold">Decision Support</span>
          </h1>
        </div>
        
        <nav className="ml-10 flex gap-1">
          <NavLink
            to="/dashboard"
            className={({ isActive }) =>
              `flex items-center gap-2 px-4 py-2 rounded-md transition-colors ${
                isActive ? 'bg-white/10 text-aast-gold font-medium' : 'hover:bg-white/5 text-slate-300'
              }`
            }
          >
            <LayoutDashboard size={18} />
            Dashboard
          </NavLink>
          <NavLink
            to="/chat"
            className={({ isActive }) =>
              `flex items-center gap-2 px-4 py-2 rounded-md transition-colors ${
                isActive ? 'bg-white/10 text-aast-gold font-medium' : 'hover:bg-white/5 text-slate-300'
              }`
            }
          >
            <MessageSquare size={18} />
            AI Agent
          </NavLink>
          <NavLink
            to="/admin"
            className={({ isActive }) =>
              `flex items-center gap-2 px-4 py-2 rounded-md transition-colors ${
                isActive ? 'bg-white/10 text-aast-gold font-medium' : 'hover:bg-white/5 text-slate-300'
              }`
            }
          >
            <ShieldCheck size={18} />
            Admin
          </NavLink>
        </nav>
      </header>

      <main className="flex-1 overflow-hidden relative">
        <Outlet />
      </main>
    </div>
  );
}
