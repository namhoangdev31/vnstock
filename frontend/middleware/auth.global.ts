export default defineNuxtRouteMiddleware(async (to) => {
  // Only execute client-side or during navigation
  if (process.server) return

  const { token, user, initToken, fetchUser } = useAuth()
  initToken()

  const publicRoutes = [
    "/login",
    "/signup",
    "/recover-password",
    "/reset-password",
  ]

  const isPublicRoute = publicRoutes.some((route) => to.path === route)
  const isTrdRoute = to.path.startsWith("/trd")

  // If user is logged in and trying to access auth pages, redirect to dashboard
  if (token.value && isPublicRoute) {
    return navigateTo("/")
  }

  // If route is public or TRD, allow access
  if (isPublicRoute || isTrdRoute) {
    return
  }

  // If not logged in, redirect to login
  if (!token.value) {
    return navigateTo(`/login?redirect=${encodeURIComponent(to.fullPath)}`)
  }

  // Ensure user data is loaded for authenticated routes
  if (!user.value) {
    await fetchUser()
  }

  // If visiting /admin, ensure user is superuser
  if (to.path.startsWith("/admin") && !user.value?.is_superuser) {
    return navigateTo("/")
  }
})
