import {
  Briefcase,
  Clock,
  Cpu,
  FileText,
  History,
  Home,
  Layers,
  LineChart,
  TrendingUp,
  Users,
} from "lucide-react"

import { SidebarAppearance } from "@/components/Common/Appearance"
import { Logo } from "@/components/Common/Logo"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
} from "@/components/ui/sidebar"
import useAuth from "@/hooks/useAuth"
import { type Item, Main } from "./Main"
import { User } from "./User"

const baseItems: Item[] = [
  { icon: Home, title: "Dashboard", path: "/" },
  { icon: TrendingUp, title: "Stock Market", path: "/stock" },
  {
    icon: FileText,
    title: "TRD",
    items: [
      { icon: FileText, title: "Phase 1: Nền tảng", path: "/trd/phase-1" },
      { icon: Cpu, title: "Phase 2: Tri-Engine", path: "/trd/phase-2" },
      { icon: Clock, title: "Phase 3: Daemon 24/7", path: "/trd/phase-3" },
      { icon: Layers, title: "Phase 4: Paper & T+2", path: "/trd/phase-4" },
      { icon: History, title: "Phase 5: Forecast Journal", path: "/trd/phase-5" },
      { icon: LineChart, title: "Phase 6: Dashboards", path: "/trd/phase-6" },
    ],
  },
  { icon: Briefcase, title: "Items", path: "/items" },
]

export function AppSidebar() {
  const { user: currentUser } = useAuth()

  const items = currentUser?.is_superuser
    ? [...baseItems, { icon: Users, title: "Admin", path: "/admin" }]
    : baseItems

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="px-4 py-6 group-data-[collapsible=icon]:px-0 group-data-[collapsible=icon]:items-center">
        <Logo variant="responsive" />
      </SidebarHeader>
      <SidebarContent>
        <Main items={items} />
      </SidebarContent>
      <SidebarFooter>
        <SidebarAppearance />
        <User user={currentUser} />
      </SidebarFooter>
    </Sidebar>
  )
}

export default AppSidebar
