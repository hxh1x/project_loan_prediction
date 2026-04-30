const navItems = [
  { icon: "layout-dashboard", label: "Overview",           path: "index.html",        roles: ["manager", "customer"] },
  { icon: "file-plus",       label: "Apply for Loan",     path: "loan-center.html",  roles: ["customer"] },
  { icon: "file-text",        label: "My Applications",    path: "applications.html", roles: ["customer"] },
  { icon: "file-text",        label: "Submission Queue",   path: "applications.html", roles: ["manager"] },
  { icon: "users",            label: "Customer Records",   path: "customers.html",    roles: ["manager"] },
  { icon: "credit-card",      label: "Transactions",       path: "transactions.html", roles: ["manager", "customer"] },
  { icon: "calendar-clock",   label: "Repayment Schedule", path: "emi-reminders.html",roles: ["customer"] },
  { icon: "bar-chart-2",      label: "ML Analytics",       path: "ml-insights.html",  roles: ["manager"] },
  { icon: "settings",         label: "Settings",           path: "settings.html",     roles: ["manager", "customer"] },
];

async function initDashboard() {
  const sidebarContainer = document.getElementById('sidebar-container');
  if (!sidebarContainer) return;

  const user = window.currentUser;
  const role = user.role;

  sidebarContainer.innerHTML = `
  <aside id="app-sidebar" class="bg-sidebar text-sidebar-foreground border-r border-sidebar-border h-full flex flex-col transition-all duration-300">

    <!-- Brand Header -->
    <div class="h-14 flex items-center px-5 gap-3 border-b border-sidebar-border/40 shrink-0">
      <div class="w-7 h-7 rounded bg-sidebar-primary flex items-center justify-center shrink-0">
        <i data-lucide="landmark" size="15" class="text-sidebar-primary-foreground"></i>
      </div>
      <span class="font-semibold text-sm nav-label tracking-wide truncate text-sidebar-foreground">Lendmark</span>
    </div>

    <!-- User Profile -->
    <div class="px-4 py-4 border-b border-sidebar-border/30 nav-label shrink-0">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded bg-sidebar-accent flex items-center justify-center shrink-0 border border-sidebar-border/50 overflow-hidden">
          ${user.profile_photo 
            ? `<img src="/uploads/${user.profile_photo}" class="w-full h-full object-cover" alt="Profile">`
            : `<i data-lucide="user" size="14" class="text-sidebar-foreground/60"></i>`}
        </div>
        <div class="overflow-hidden">
          <p id="user-name" class="text-xs font-semibold truncate text-sidebar-foreground"></p>
          <p id="user-role" class="text-[10px] text-sidebar-foreground/50 capitalize truncate tracking-wide"></p>
        </div>
      </div>
    </div>

    <!-- Divider label -->
    <p class="nav-label px-4 pt-4 pb-1 text-[9px] font-semibold uppercase tracking-widest text-sidebar-foreground/35">Navigation</p>

    <!-- Nav Items -->
    <nav id="nav-items" class="flex-1 overflow-y-auto pb-4 px-2 space-y-0.5"></nav>

    <!-- Footer Actions -->
    <div class="px-2 py-3 border-t border-sidebar-border/30 shrink-0 flex flex-col gap-0.5">
      <button id="theme-toggle" class="flex items-center gap-3 w-full px-3 py-2 rounded text-sidebar-foreground/55 hover:text-sidebar-foreground hover:bg-sidebar-accent transition-colors text-xs">
        <i data-lucide="moon" size="15" class="shrink-0 hidden dark:block"></i>
        <i data-lucide="sun"  size="15" class="shrink-0 block dark:hidden"></i>
        <span class="nav-label font-medium">Toggle Theme</span>
      </button>
      <button id="sign-out-btn" class="flex items-center gap-3 w-full px-3 py-2 rounded text-sidebar-foreground/55 hover:text-sidebar-foreground hover:bg-sidebar-accent transition-colors text-xs">
        <i data-lucide="log-out" size="15" class="shrink-0"></i>
        <span class="nav-label font-medium">Sign Out</span>
      </button>
    </div>

    <!-- Collapse Toggle -->
    <button id="collapse-toggle" class="h-9 border-t border-sidebar-border/30 flex items-center justify-center text-sidebar-foreground/40 hover:text-sidebar-foreground hover:bg-sidebar-accent transition-colors shrink-0">
      <i id="collapse-icon" data-lucide="chevron-left" size="16"></i>
    </button>
  </aside>
  `;

  document.getElementById('user-name').textContent = user.full_name || user.email;
  document.getElementById('user-role').textContent = role === 'manager' ? 'Branch Manager' : 'Account Holder';

  const navList = document.getElementById('nav-items');
  const currentPage = window.location.pathname.split('/').pop() || 'index.html';

  navItems.filter(item => item.roles.includes(role)).forEach(item => {
    const active = currentPage === item.path;
    const btn = document.createElement('button');
    btn.className = `flex items-center gap-3 w-full px-3 py-2 rounded text-xs font-medium transition-colors ${
      active
        ? "bg-sidebar-primary text-sidebar-primary-foreground"
        : "text-sidebar-foreground/60 hover:text-sidebar-foreground hover:bg-sidebar-accent"
    }`;
    btn.innerHTML = `
      <i data-lucide="${item.icon}" size="15" class="shrink-0 ${active ? 'text-sidebar-primary-foreground' : 'text-sidebar-foreground/50'}"></i>
      <span class="nav-label whitespace-nowrap truncate">${item.label}</span>
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
