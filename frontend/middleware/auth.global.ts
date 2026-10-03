export default defineNuxtRouteMiddleware(async (to) => {
  if (process.server) return

  const { token, user, initToken, fetchUser } = useAuth()
  initToken()

  const publicRoutes = [
    "/",
    "/iboard",
    "/login",
    "/signup",
    "/recover-password",
    "/reset-password",
  ]

  const isPublicRoute =
    publicRoutes.some((route) => to.path === route || to.path === `${route}/`) ||
    to.path.startsWith("/iboard/")
  const isAuthPage = [
    "/login",
    "/signup",
    "/recover-password",
    "/reset-password",
  ].includes(to.path)

  if (token.value && isAuthPage) {
    return navigateTo("/admin")
  }

  if (isPublicRoute) {
    return
  }

  if (!token.value) {
    return navigateTo(`/login?redirect=${encodeURIComponent(to.fullPath)}`)
  }

  if (!user.value) {
    await fetchUser()
  }

  if (to.path.startsWith("/admin/users") && !user.value?.is_superuser) {
    return navigateTo("/admin")
  }
})
