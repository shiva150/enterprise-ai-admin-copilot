const NAV = [
  { icon: "dashboard", label: "Dashboard", active: false },
  { icon: "terminal", label: "Deployments", active: true },
  { icon: "psychology", label: "Inference", active: false },
  { icon: "query_stats", label: "Observability", active: false },
  { icon: "settings", label: "Settings", active: false },
];

const AVATAR_URL =
  "https://lh3.googleusercontent.com/aida-public/AB6AXuAkwv9y82Pz8Er7yrpv6UQuKV4Ln7Ug5dY58I_vHHaI-ArX3GWnHmGYJwErBlWfMXZt5dehzdHjrQ9oBo2qYXgHJK9Q7KzOKsN1fB832zGwNvWhU1Ua8UzNaXvesPnK0xonnIx-n938dQpq4g333Yu4-ikXZZtXwGKG7L8pD8USkKt-rKr1cWOPJie0ZcEczDFbif13yDUnEwfI2ocrm1K7xaicI60JBZV1aiva_aeoO0IgjHtObGYt7YGDghA6VkTM9E5ZbERiJu1t";

export function Sidebar() {
  return (
    <>
      {/* SideNavBar (Shared Component) */}
      <nav className="hidden md:flex flex-col h-full w-[260px] z-50 fixed left-0 top-0 border-r border-slate-800 dark:border-[#1E293B] bg-slate-900 dark:bg-[#0B0F1A] font-inter antialiased tracking-tight">
        <div className="flex items-center gap-3 p-6 border-b border-slate-800 dark:border-[#1E293B]">
          <div className="h-8 w-8 rounded bg-indigo-500/20 flex items-center justify-center text-indigo-500">
            <span
              className="material-symbols-outlined"
              style={{ fontVariationSettings: "'FILL' 1" }}
            >
              dataset
            </span>
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tighter text-slate-100 leading-tight">
              Aether Core
            </h1>
            <p className="text-xs text-slate-500">v2.4.0-stable</p>
          </div>
        </div>

        <div className="flex-1 py-6 px-4 space-y-1 overflow-y-auto">
          {NAV.map((item) => (
            <a
              key={item.label}
              href="#"
              onClick={(e) => e.preventDefault()}
              className={
                item.active
                  ? "flex items-center gap-3 px-3 py-2 rounded-DEFAULT bg-indigo-500/10 text-indigo-400 border-r-2 border-indigo-500"
                  : "flex items-center gap-3 px-3 py-2 rounded-DEFAULT text-slate-400 hover:text-slate-100 hover:bg-slate-800/50 transition-colors duration-200"
              }
            >
              <span className="material-symbols-outlined text-[20px]">{item.icon}</span>
              <span className="font-label-sm text-label-sm">{item.label}</span>
            </a>
          ))}
        </div>

        <div className="p-4 border-t border-slate-800 dark:border-[#1E293B]">
          <div className="flex items-center gap-3 px-2">
            <img
              alt="System Operator"
              className="h-8 w-8 rounded-full border border-slate-700"
              src={AVATAR_URL}
            />
            <div className="flex-1 overflow-hidden">
              <p className="font-label-sm text-label-sm text-slate-300 truncate">
                System Operator
              </p>
              <p className="text-[10px] text-slate-500 truncate">sysadmin@aether.ops</p>
            </div>
          </div>
        </div>
      </nav>

      {/* TopNavBar (Mobile Only) */}
      <nav className="md:hidden fixed top-0 w-full flex items-center justify-between h-16 px-4 bg-slate-900/80 dark:bg-[#0B0F1A]/80 backdrop-blur-md border-b border-slate-800 dark:border-[#1E293B] z-40">
        <span className="text-lg font-black text-slate-100 font-inter">Aether Ops</span>
        <div className="flex gap-4">
          <button className="text-slate-400 hover:text-indigo-400 transition-all">
            <span className="material-symbols-outlined">menu</span>
          </button>
        </div>
      </nav>
    </>
  );
}
