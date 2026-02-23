import { useState, useEffect } from "react";
import { Link, Outlet, useLocation } from "react-router";
import { TrendingUp, BarChart3, Briefcase, Star, Scale, Activity, MessageSquare, ChevronLeft, ChevronRight, Menu } from "lucide-react";

export function Layout() {
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    document.documentElement.classList.add('dark');
  }, []);

  const navLinks = [
    { path: "/", label: "Dashboard", icon: BarChart3 },
    { path: "/predictions", label: "Predictions", icon: TrendingUp },
    { path: "/sentiment", label: "Sentiment", icon: MessageSquare },
    { path: "/portfolio", label: "Portfolio", icon: Briefcase },
    { path: "/watchlist", label: "Watchlist", icon: Star },
    { path: "/compare", label: "Compare", icon: Scale },
    { path: "/backtest", label: "Backtest", icon: Activity },
  ];

  return (
    <div className="min-h-screen bg-[#0a0f1e] flex">
      {/* Sidebar */}
      <aside className={`sticky top-0 h-screen flex flex-col border-r border-white/5 bg-[#070b16] transition-all duration-300 ${collapsed ? 'w-[68px]' : 'w-[220px]'}`}>
        {/* Logo */}
        <div className={`flex items-center gap-2 px-4 py-5 border-b border-white/5 ${collapsed ? 'justify-center' : ''}`}>
          <div className="bg-gradient-to-br from-[#3b82f6] to-[#2563eb] p-2 rounded-lg shrink-0">
            <TrendingUp className="w-5 h-5 text-white" />
          </div>
          {!collapsed && (
            <span className="text-lg font-semibold bg-gradient-to-r from-white to-gray-300 bg-clip-text text-transparent whitespace-nowrap">
              Market Sentinel
            </span>
          )}
        </div>

        {/* Nav Links */}
        <nav className="flex-1 py-4 px-2 space-y-1">
          {navLinks.map((link) => {
            const Icon = link.icon;
            const isActive = location.pathname === link.path || (link.path !== '/' && location.pathname.startsWith(link.path));
            return (
              <Link key={link.path} to={link.path} title={collapsed ? link.label : ''}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all text-sm ${isActive
                    ? "bg-[#3b82f6]/15 text-[#3b82f6] border border-[#3b82f6]/20"
                    : "text-gray-400 hover:text-white hover:bg-white/5 border border-transparent"
                  } ${collapsed ? 'justify-center' : ''}`}>
                <Icon className="w-[18px] h-[18px] shrink-0" />
                {!collapsed && <span>{link.label}</span>}
              </Link>
            );
          })}
        </nav>

        {/* Collapse Button */}
        <div className="p-2 border-t border-white/5">
          <button onClick={() => setCollapsed(!collapsed)}
            className={`w-full flex items-center gap-2 px-3 py-2.5 rounded-lg text-gray-500 hover:text-white hover:bg-white/5 transition-all text-sm ${collapsed ? 'justify-center' : ''}`}>
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <><ChevronLeft className="w-4 h-4" /><span>Collapse</span></>}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        {/* Top Bar */}
        <header className="sticky top-0 z-40 border-b border-white/5 backdrop-blur-xl bg-[#0a0f1e]/80 px-6 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button onClick={() => setCollapsed(!collapsed)} className="p-2 hover:bg-white/5 rounded-lg transition-colors lg:hidden">
                <Menu className="w-5 h-5 text-gray-400" />
              </button>
              <h1 className="text-lg font-semibold text-white">
                {navLinks.find(l => l.path === location.pathname || (l.path !== '/' && location.pathname.startsWith(l.path)))?.label || 'Dashboard'}
              </h1>
            </div>
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg">
                <div className="w-2 h-2 bg-[#10b981] rounded-full animate-pulse" />
                <span className="text-xs text-gray-400">IST {new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata' })}</span>
              </div>
              <div className="flex items-center gap-2 px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg">
                <span className="text-xs text-gray-400">NSE/BSE Hours: 9:15 AM – 3:30 PM</span>
              </div>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="p-6 max-w-[1440px] mx-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}