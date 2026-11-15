import { useState, useEffect, useMemo, useCallback, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, NavLink, useLocation } from "react-router-dom";
import {
  Activity,
  Award,
  Banknote,
  BarChart3,
  Bell,
  BookOpen,
  Briefcase,
  Building2,
  Calendar,
  CalendarCheck,
  CalendarDays,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Cpu,
  FileSpreadsheet,
  GraduationCap,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageSquare,
  Moon,
  ShieldCheck,
  Sun,
  User,
  UserPlus,
  Users,
  Wallet,
} from "lucide-react";
import { SIDEBAR_NAV_ITEMS, type NavItemConfig } from "@/config/navigation";
import { setAppLanguage, type SupportedLanguage } from "@/i18n";
import { useTheme } from "@/lib/theme";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/features/auth/store/authStore";
import { useBrandingStore } from "@/features/institutions/store/brandingStore";
import { AcademicLogo } from "@/features/institutions/components/AcademicLogo";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown";
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle } from "@/components/ui/drawer";

const NAV_ICONS: Record<NavItemConfig["iconName"], ReactNode> = {
  overview: <LayoutDashboard className="h-4 w-4 shrink-0" />,
  institution: <Building2 className="h-4 w-4 shrink-0" />,
  academics: <Calendar className="h-4 w-4 shrink-0" />,
  students: <GraduationCap className="h-4 w-4 shrink-0" />,
  admissions: <UserPlus className="h-4 w-4 shrink-0" />,
  attendance: <CalendarCheck className="h-4 w-4 shrink-0" />,
  exams: <Award className="h-4 w-4 shrink-0" />,
  results: <FileSpreadsheet className="h-4 w-4 shrink-0" />,
  fees: <Banknote className="h-4 w-4 shrink-0" />,
  accounting: <BookOpen className="h-4 w-4 shrink-0" />,
  payroll: <Wallet className="h-4 w-4 shrink-0" />,
  staff: <Users className="h-4 w-4 shrink-0" />,
  devices: <Cpu className="h-4 w-4 shrink-0" />,
  communications: <MessageSquare className="h-4 w-4 shrink-0" />,
  calendar: <CalendarDays className="h-4 w-4 shrink-0" />,
  operations: <Briefcase className="h-4 w-4 shrink-0" />,
  reports: <BarChart3 className="h-4 w-4 shrink-0" />,
  audit: <ShieldCheck className="h-4 w-4 shrink-0" />,
  system: <Activity className="h-4 w-4 shrink-0" />,
};

interface AppShellProps {
  children: ReactNode;
  permissions?: string[];
  userType?: string;
  onLogout?: () => void;
}

export function AppShell({ children, permissions, userType, onLogout }: AppShellProps) {
  const { t, i18n } = useTranslation();
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [branch, setBranch] = useState("main");
  const [session, setSession] = useState("2026");

  const currentLang: SupportedLanguage = i18n.language === "bn" ? "bn" : "en";
  const { branding, fetchBranding, getLocalizedName, getLogoUrl } = useBrandingStore();

  useEffect(() => {
    void fetchBranding();
  }, [fetchBranding]);

  const schoolName = getLocalizedName(currentLang);
  const schoolLogo = getLogoUrl();
  const schoolEIIN = branding?.eiin;

  const [openSections, setOpenSections] = useState<Record<string, boolean>>({});

  const user = useAuthStore((s) => s.user);
  const effectivePermissions = permissions !== undefined ? permissions : user?.permissions;
  const effectiveUserType = userType !== undefined ? userType : user?.user_type;

  const isSuper =
    effectivePermissions?.includes("*") ||
    effectiveUserType === "superadmin" ||
    effectiveUserType === "super_admin" ||
    effectiveUserType === "admin";

  const hasPerm = useCallback((requiredPerm?: string) => {
    if (!requiredPerm) return true;
    if (effectivePermissions === undefined) return true;
    if (isSuper) return true;
    return effectivePermissions.includes(requiredPerm);
  }, [effectivePermissions, isSuper]);

  const visibleNavItems = useMemo(
    () =>
      SIDEBAR_NAV_ITEMS.map((item) => {
        if (!hasPerm(item.permission)) {
          return null;
        }
        const filteredChildren = item.children?.filter((child) => hasPerm(child.permission));
        return {
          ...item,
          children: filteredChildren,
        };
      }).filter(Boolean) as NavItemConfig[],
    [hasPerm],
  );

  // Auto-expand the active section based on current location
  useEffect(() => {
    visibleNavItems.forEach((item) => {
      if (item.children) {
        const matchesChild = item.children.some(
          (child) => location.pathname === child.to || location.pathname.startsWith(child.to + "/"),
        );
        const matchesParent = location.pathname === item.to || location.pathname.startsWith(item.to + "/");
        if (matchesChild || matchesParent) {
          setOpenSections((prev) => ({ ...prev, [item.id]: true }));
        }
      }
    });
  }, [location.pathname, visibleNavItems]);

  const toggleSection = (id: string) => {
    setOpenSections((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const handleLanguageChange = (nextLang: SupportedLanguage) => {
    if (nextLang !== currentLang) {
      setAppLanguage(nextLang);
    }
  };

  const renderNavLinks = (isCollapsed: boolean, onNavigate?: () => void) =>
    visibleNavItems.map((item) => {
      const hasChildren = Boolean(item.children && item.children.length > 0);
      const isOpen = Boolean(openSections[item.id]);
      const isParentActive =
        location.pathname === item.to ||
        Boolean(item.children?.some((c) => location.pathname === c.to || location.pathname.startsWith(c.to + "/")));

      if (isCollapsed) {
        return (
          <NavLink
            key={item.id}
            to={item.to}
            end={item.end}
            onClick={onNavigate}
            title={t(item.labelKey)}
            className={({ isActive }) =>
              cn(
                "flex items-center justify-center rounded-md p-2 text-xs font-medium transition-colors",
                isActive || isParentActive
                  ? "bg-primary-soft text-primary"
                  : "text-ink-muted hover:bg-canvas hover:text-ink",
              )
            }
          >
            {NAV_ICONS[item.iconName]}
          </NavLink>
        );
      }

      if (!hasChildren) {
        return (
          <NavLink
            key={item.id}
            to={item.to}
            end={item.end}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors",
                isActive
                  ? "bg-primary-soft text-primary font-semibold"
                  : "text-ink-muted hover:bg-canvas hover:text-ink",
              )
            }
          >
            {NAV_ICONS[item.iconName]}
            <span className="truncate">{t(item.labelKey)}</span>
          </NavLink>
        );
      }

      return (
        <div key={item.id} className="space-y-0.5">
          <div
            className={cn(
              "group flex items-center justify-between rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors",
              isParentActive
                ? "bg-primary-soft/60 text-primary font-semibold"
                : "text-ink-muted hover:bg-canvas hover:text-ink",
            )}
          >
            <NavLink
              to={item.to}
              end={item.end}
              onClick={() => {
                setOpenSections((prev) => ({ ...prev, [item.id]: true }));
                if (onNavigate) onNavigate();
              }}
              className="flex flex-1 items-center gap-2.5 min-w-0"
            >
              {NAV_ICONS[item.iconName]}
              <span className="truncate">{t(item.labelKey)}</span>
            </NavLink>
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                toggleSection(item.id);
              }}
              aria-label={isOpen ? `Collapse ${t(item.labelKey)}` : `Expand ${t(item.labelKey)}`}
              className="ml-1 p-0.5 rounded text-ink-subtle hover:text-ink hover:bg-surface transition-colors"
            >
              <ChevronDown
                className={cn(
                  "h-3.5 w-3.5 transition-transform duration-200",
                  isOpen ? "rotate-0" : "-rotate-90",
                )}
              />
            </button>
          </div>

          {isOpen && item.children && (
            <div className="ml-4 pl-2.5 border-l border-border/70 space-y-0.5 py-0.5">
              {item.children.map((child) => (
                <NavLink
                  key={child.id}
                  to={child.to}
                  end={child.end}
                  onClick={onNavigate}
                  className={({ isActive }) =>
                    cn(
                      "block rounded-md px-2 py-1 text-[11px] font-medium transition-colors truncate",
                      isActive
                        ? "bg-primary-soft text-primary font-semibold"
                        : "text-ink-muted hover:bg-canvas hover:text-ink",
                    )
                  }
                >
                  {t(child.labelKey)}
                </NavLink>
              ))}
            </div>
          )}
        </div>
      );
    });

  return (
    <div className="flex min-h-screen bg-canvas text-ink">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:rounded-md focus:bg-primary focus:px-3 focus:py-1.5 focus:text-xs focus:font-medium focus:text-white"
      >
        {t("app.skipToContent")}
      </a>

      <aside
        className={cn(
          "no-print sticky top-0 hidden h-screen shrink-0 flex-col border-r border-border bg-surface transition-[width] duration-200 ease-out md:flex",
          collapsed ? "w-16" : "w-60",
        )}
        aria-label="Primary Navigation"
      >
        <div className="flex h-12 items-center justify-between border-b border-border px-3">
          <div className={cn("flex items-center gap-2 overflow-hidden", collapsed && "justify-center w-full")}>
            <AcademicLogo
              logoUrl={schoolLogo}
              name={schoolName}
              size="sm"
              className="h-7 w-7 rounded-md"
            />
            {!collapsed ? (
              <div className="min-w-0">
                <p className="truncate text-xs font-bold leading-tight text-ink" title={schoolName}>
                  {schoolName}
                </p>
                <p className="truncate text-[10px] leading-tight text-ink-subtle">
                  {schoolEIIN ? `${t("auth.eiinLabel")}: ${schoolEIIN}` : t("app.brandTag")}
                </p>
              </div>
            ) : null}
          </div>
        </div>

        <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 py-2.5">
          {renderNavLinks(collapsed)}
        </nav>

        <div className="border-t border-border p-2">
          <button
            type="button"
            onClick={() => setCollapsed((prev) => !prev)}
            aria-label={collapsed ? t("nav.expandSidebar") : t("nav.collapseSidebar")}
            className="flex w-full items-center justify-center gap-2 rounded-md px-2 py-1.5 text-xs text-ink-subtle transition-colors hover:bg-canvas hover:text-ink"
          >
            {collapsed ? (
              <ChevronRight className="h-4 w-4" />
            ) : (
              <>
                <ChevronLeft className="h-4 w-4" />
                <span>{t("nav.collapseSidebar")}</span>
              </>
            )}
          </button>
        </div>
      </aside>

      <Drawer open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <DrawerContent side="left" closeLabel={t("ui.dialog.close")}>
          <DrawerHeader className="flex items-center gap-2.5 border-b border-border pb-3">
            <AcademicLogo
              logoUrl={schoolLogo}
              name={schoolName}
              size="sm"
              className="h-8 w-8 rounded-md"
            />
            <DrawerTitle className="text-sm font-bold truncate">{schoolName}</DrawerTitle>
          </DrawerHeader>
          <nav className="mt-3 space-y-0.5" aria-label="Mobile Navigation">
            {renderNavLinks(false, () => setMobileNavOpen(false))}
          </nav>
        </DrawerContent>
      </Drawer>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="no-print sticky top-0 z-20 flex h-12 items-center justify-between gap-2 border-b border-border bg-surface/95 px-3 backdrop-blur-sm md:px-4">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setMobileNavOpen(true)}
              aria-label={t("nav.openMenu")}
              className="rounded-md border border-border p-1.5 text-ink-muted hover:bg-canvas hover:text-ink md:hidden"
            >
              <Menu className="h-4 w-4" />
            </button>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  className="inline-flex items-center gap-1.5 rounded-md border border-border bg-canvas px-2.5 py-1 text-xs font-medium text-ink transition-colors hover:border-border-strong"
                >
                  <Building2 className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                  <span>
                    {branch === "main" ? t("topbar.branchMain") : t("topbar.branchMorning")}
                  </span>
                  <ChevronDown className="h-3 w-3 text-ink-subtle" aria-hidden="true" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start">
                <DropdownMenuLabel>{t("topbar.switchBranch")}</DropdownMenuLabel>
                <DropdownMenuItem onSelect={() => setBranch("main")}>
                  {t("topbar.branchMain")}
                </DropdownMenuItem>
                <DropdownMenuItem onSelect={() => setBranch("morning")}>
                  {t("topbar.branchMorning")}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  className="hidden items-center gap-1.5 rounded-md border border-border bg-canvas px-2.5 py-1 text-xs text-ink-muted transition-colors hover:border-border-strong sm:inline-flex"
                >
                  <Calendar className="h-3.5 w-3.5 text-ink-subtle" aria-hidden="true" />
                  <span>
                    {session === "2026" ? t("topbar.sessionLabel") : t("topbar.session2025")}
                  </span>
                  <ChevronDown className="h-3 w-3 text-ink-subtle" aria-hidden="true" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start">
                <DropdownMenuLabel>{t("topbar.switchSession")}</DropdownMenuLabel>
                <DropdownMenuItem onSelect={() => setSession("2026")}>
                  {t("topbar.sessionLabel")}
                </DropdownMenuItem>
                <DropdownMenuItem onSelect={() => setSession("2025")}>
                  {t("topbar.session2025")}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>

          <div className="flex items-center gap-2">
            <div
              className="inline-flex items-center rounded-md border border-border bg-canvas p-0.5"
              role="group"
              aria-label={t("app.language.label")}
            >
              <button
                type="button"
                onClick={() => handleLanguageChange("en")}
                aria-pressed={currentLang === "en"}
                aria-label={t("app.language.switchToEnglish")}
                className={cn(
                  "rounded px-2 py-1 text-[11px] font-semibold transition-colors",
                  currentLang === "en"
                    ? "bg-primary text-white shadow-sm"
                    : "text-ink-muted hover:text-ink",
                )}
              >
                {t("app.language.en")}
              </button>
              <button
                type="button"
                onClick={() => handleLanguageChange("bn")}
                aria-pressed={currentLang === "bn"}
                aria-label={t("app.language.switchToBangla")}
                className={cn(
                  "rounded px-2 py-1 text-[11px] font-semibold transition-colors",
                  currentLang === "bn"
                    ? "bg-primary text-white shadow-sm"
                    : "text-ink-muted hover:text-ink",
                )}
              >
                {t("app.language.bn")}
              </button>
            </div>

            <button
              type="button"
              onClick={toggleTheme}
              aria-label={theme === "light" ? t("topbar.darkMode") : t("topbar.lightMode")}
              className="rounded-md border border-border bg-canvas p-1.5 text-ink-muted transition-colors hover:text-ink"
            >
              {theme === "light" ? (
                <Moon className="h-3.5 w-3.5" aria-hidden="true" />
              ) : (
                <Sun className="h-3.5 w-3.5" aria-hidden="true" />
              )}
            </button>

            <button
              type="button"
              aria-label={t("topbar.notifications")}
              className="rounded-md border border-border bg-canvas p-1.5 text-ink-muted transition-colors hover:text-ink"
            >
              <Bell className="h-3.5 w-3.5" aria-hidden="true" />
            </button>

            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  aria-label={t("topbar.userMenu")}
                  className="inline-flex items-center gap-1.5 rounded-md border border-border bg-canvas px-2 py-1 text-xs font-medium text-ink transition-colors hover:border-border-strong"
                >
                  <User className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                  <span className="hidden sm:inline">
                    {useAuthStore.getState().user?.full_name || useAuthStore.getState().user?.username || t("topbar.adminRole")}
                  </span>
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>
                  <p className="font-semibold text-ink leading-tight">
                    {useAuthStore.getState().user?.full_name || useAuthStore.getState().user?.username || t("topbar.adminRole")}
                  </p>
                  <p className="text-[10px] text-ink-muted leading-tight font-normal">
                    {useAuthStore.getState().user?.email || useAuthStore.getState().user?.phone || useAuthStore.getState().user?.user_type}
                  </p>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link to="/profile" className="flex items-center gap-2 cursor-pointer">
                    <User className="h-3.5 w-3.5 text-primary" aria-hidden="true" />
                    <span>{t("topbar.profile", "Profile & Security")}</span>
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onSelect={onLogout}>
                  <LogOut className="h-3.5 w-3.5 text-rose-600" aria-hidden="true" />
                  <span>{t("topbar.signOut")}</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        <main id="main-content" className="flex-1 p-4 md:p-5">
          <div key={location.pathname} className="mx-auto max-w-6xl animate-page-enter">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
