import { Link as RouterLink, useRouterState } from "@tanstack/react-router"
import { ChevronRight, type LucideIcon } from "lucide-react"
import { useEffect, useState } from "react"

import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
  useSidebar,
} from "@/components/ui/sidebar"
import { cn } from "@/lib/utils"

export type SubItem = {
  title: string
  path: string
  icon?: LucideIcon
}

export type Item = {
  icon: LucideIcon
  title: string
  path?: string
  items?: SubItem[]
}

interface MainProps {
  items: Item[]
}

export function Main({ items }: MainProps) {
  const { isMobile, setOpenMobile, state } = useSidebar()
  const router = useRouterState()
  const currentPath = router.location.pathname

  const handleMenuClick = () => {
    if (isMobile) {
      setOpenMobile(false)
    }
  }

  return (
    <SidebarGroup>
      <SidebarGroupContent>
        <SidebarMenu>
          {items.map((item) => {
            if (item.items && item.items.length > 0) {
              return (
                <SidebarMenuItemWithSub
                  key={item.title}
                  item={item}
                  currentPath={currentPath}
                  isMobile={isMobile}
                  state={state}
                  onMenuClick={handleMenuClick}
                />
              )
            }

            const isActive = item.path ? currentPath === item.path : false

            return (
              <SidebarMenuItem key={item.title}>
                <SidebarMenuButton
                  tooltip={item.title}
                  isActive={isActive}
                  asChild
                >
                  <RouterLink to={item.path ?? "#"} onClick={handleMenuClick}>
                    <item.icon />
                    <span>{item.title}</span>
                  </RouterLink>
                </SidebarMenuButton>
              </SidebarMenuItem>
            )
          })}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  )
}

function SidebarMenuItemWithSub({
  item,
  currentPath,
  state,
  onMenuClick,
}: {
  item: Item
  currentPath: string
  isMobile: boolean
  state: "expanded" | "collapsed"
  onMenuClick: () => void
}) {
  const hasActiveChild = item.items?.some((sub) => currentPath === sub.path)
  const [open, setOpen] = useState(hasActiveChild || currentPath.startsWith("/trd"))

  useEffect(() => {
    if (hasActiveChild) {
      setOpen(true)
    }
  }, [hasActiveChild])

  return (
    <SidebarMenuItem>
      <SidebarMenuButton
        tooltip={item.title}
        isActive={hasActiveChild}
        onClick={() => setOpen((prev) => !prev)}
      >
        <item.icon />
        <span>{item.title}</span>
        <ChevronRight
          className={cn(
            "ml-auto size-4 transition-transform duration-200",
            open && "rotate-90",
            state === "collapsed" && "hidden",
          )}
        />
      </SidebarMenuButton>
      {open && state !== "collapsed" && item.items && (
        <SidebarMenuSub>
          {item.items.map((sub) => {
            const isSubActive = currentPath === sub.path

            return (
              <SidebarMenuSubItem key={sub.title}>
                <SidebarMenuSubButton isActive={isSubActive} asChild>
                  <RouterLink to={sub.path} onClick={onMenuClick}>
                    {sub.icon && <sub.icon />}
                    <span>{sub.title}</span>
                  </RouterLink>
                </SidebarMenuSubButton>
              </SidebarMenuSubItem>
            )
          })}
        </SidebarMenuSub>
      )}
    </SidebarMenuItem>
  )
}
