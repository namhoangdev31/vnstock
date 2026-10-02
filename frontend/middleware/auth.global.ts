export default defineNuxtRouteMiddleware(async (to) => {
  // Only execute client-side or during navigation
  if (process.server) return

  const { token, user, initToken, fetchUser } = useAuth()
  initToken()

  const publicRoutes = [
    "/",
    "/login",
    "/signup",
    "/recover-password",
    "/reset-password",
  ]

  const isPublicRoute = publicRoutes.some((route) => to.path === route)
  const isAuthPage = [
    "/login",
    "/signup",
    "/recover-password",
    "/reset-password",
  ].includes(to.path)

  // If user is logged in and trying to access auth pages, redirect to admin cockpit
  if (token.value && isAuthPage) {
    return navigateTo("/admin")
  }

  // If route is public, allow access
  if (isPublicRoute) {
    return
  }

  // All other routes (including /admin and sub-routes) require login
  if (!token.value) {
    return navigateTo(`/login?redirect=${encodeURIComponent(to.fullPath)}`)
  }

  // Ensure user data is loaded for authenticated routes
  if (!user.value) {
    await fetchUser()
  }

  // If visiting /admin/users (RBAC), ensure user is superuser
  if (to.path.startsWith("/admin/users") && !user.value?.is_superuser) {
    return navigateTo("/admin")
  }
})

