export default defineNuxtRouteMiddleware(async (to) => {
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

  const isPublicRoute = publicRoutes.some(
    (route) => to.path === route || to.path === `${route}/`,
  )
  const isAuthPage = [
    "/login",
    "/signup",
    "/recover-password",
    "/reset-password",
  ].includes(to.path)

  if (token.value && isAuthPage) {
    if (!user.value) {
      await fetchUser()
    }
    return navigateTo(user.value?.is_superuser ? "/admin" : "/app")
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

  // /admin is strictly for admin / superuser only. Normal users go to /app
  if (to.path.startsWith("/admin") && !user.value?.is_superuser) {
    return navigateTo("/app")
  }
})
