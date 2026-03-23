const navItems = [
  { icon: "layout-dashboard", label: "Dashboard",     path: "index.html",        roles: ["manager", "customer"] },
  { icon: "piggy-bank",       label: "Apply for Loan",path: "loan-center.html",  roles: ["customer"] },
  { icon: "file-text",        label: "My Applications",path:"applications.html",  roles: ["customer"] },
  { icon: "file-text",        label: "All Applications",path:"applications.html", roles: ["manager"] },
  { icon: "users",            label: "Customers",     path: "customers.html",     roles: ["manager"] },
  { icon: "credit-card",      label: "Transactions",  path: "transactions.html",  roles: ["manager", "customer"] },
  { icon: "settings",         label: "Settings",      path: "settings.html",      roles: ["manager", "customer"] },
];

async function initDashboard() {
  const sidebarContainer = document.getElementById('sidebar-container');
  if (!sidebarContainer) return;

  const user = window.currentUser;
  const role = user.role;

  sidebarContainer.innerHTML = `
  <aside id="app-sidebar" class="bg-sidebar text-sidebar-foreground border-r border-sidebar-border h-full flex flex-col transition-all duration-300">
    <div class="h-16 flex items-center px-6 gap-3 border-b border-sidebar-border/50 shrink-0">
      <div class="w-8 h-8 rounded-lg bg-sidebar-primary flex items-center justify-center shrink-0">
        <i data-lucide="layers" size="18" class="text-sidebar-primary-foreground"></i>
      </div>
      <span class="font-semibold text-lg nav-label tracking-tight truncate">Lendmark</span>
    </div>

    <div class="p-5 border-b border-sidebar-border/50 nav-label shrink-0">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-full bg-sidebar-accent flex items-center justify-center shrink-0 border border-sidebar-border">
          <i data-lucide="user" size="16" class="text-sidebar-foreground/70"></i>
        </div>
        <div class="overflow-hidden">
          <p id="user-name" class="text-sm font-medium truncate"></p>
          <p id="user-role" class="text-xs text-sidebar-foreground/60 capitalize truncate"></p>
        </div>
      </div>
    </div>

    <nav id="nav-items" class="flex-1 overflow-y-auto py-6 px-3 space-y-1"></nav>

    <div class="p-3 border-t border-sidebar-border/50 shrink-0 flex flex-col gap-1">
      <button id="theme-toggle" class="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent transition-colors">
        <i data-lucide="moon" size="18" class="shrink-0 hidden dark:block"></i>
        <i data-lucide="sun"  size="18" class="shrink-0 block dark:hidden"></i>
        <span class="text-sm font-medium nav-label transition-opacity">Toggle Theme</span>
      </button>
      <button id="sign-out-btn" class="flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent transition-colors">
        <i data-lucide="log-out" size="18" class="shrink-0"></i>
        <span class="text-sm font-medium nav-label transition-opacity">Sign Out</span>
      </button>
    </div>

    <button id="collapse-toggle" class="h-12 border-t border-sidebar-border/50 flex items-center justify-center text-sidebar-foreground/50 hover:text-sidebar-foreground hover:bg-sidebar-accent transition-colors shrink-0">
      <i id="collapse-icon" data-lucide="chevron-left" size="18"></i>
    </button>
  </aside>
  `;

  document.getElementById('user-name').textContent = user.full_name || user.email;
  document.getElementById('user-role').textContent = role;

  const navList = document.getElementById('nav-items');
  const currentPage = window.location.pathname.split('/').pop() || 'index.html';

  navItems.filter(item => item.roles.includes(role)).forEach(item => {
    const active = currentPage === item.path;
    const btn = document.createElement('button');
    btn.className = `flex items-center gap-3 w-full px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
      active
        ? "bg-sidebar-primary text-sidebar-primary-foreground shadow-sm"
        : "text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent"
    }`;
    btn.innerHTML = `
      <i data-lucide="${item.icon}" size="18" class="shrink-0 ${active ? '' : 'text-sidebar-foreground/60'}"></i>
      <span class="nav-label transition-opacity whitespace-nowrap truncate">${item.label}</span>
    `;
    btn.onclick = () => window.location.href = item.path;
    navList.appendChild(btn);
  });

  lucide.createIcons();

  document.getElementById('theme-toggle').onclick = () => {
    if (typeof toggleDarkMode === 'function') toggleDarkMode();
    lucide.createIcons();
  };

  document.getElementById('sign-out-btn').onclick = async () => {
    await window.api.signOut();
    window.location.href = 'auth.html';
  };

  const sidebarWrapper = document.getElementById('sidebar-container');
  const collapseToggle = document.getElementById('collapse-toggle');
  const collapseIcon  = document.getElementById('collapse-icon');

  collapseToggle.onclick = () => {
    sidebarWrapper.classList.toggle('collapsed');
    const isCollapsed = sidebarWrapper.classList.contains('collapsed');
    document.querySelectorAll('.nav-label').forEach(el => {
      if (isCollapsed) el.classList.add('opacity-0', 'w-0', 'overflow-hidden');
      else el.classList.remove('opacity-0', 'w-0', 'overflow-hidden');
    });
    collapseIcon.setAttribute('data-lucide', isCollapsed ? 'chevron-right' : 'chevron-left');
    lucide.createIcons();
  };
}

window.initDashboard = initDashboard;
