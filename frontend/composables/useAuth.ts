import type {
  Body_login_login_access_token as AccessToken,
  UserPublic,
  UserRegister,
} from "~/client"
import { LoginService, UsersService } from "~/client"

export const useAuth = () => {
  const router = useRouter()
  const { showErrorToast, showSuccessToast } = useCustomToast()

  const user = useState<UserPublic | null>("auth_user", () => null)
  const token = useState<string | null>("auth_token", () => null)
  const isLoading = useState<boolean>("auth_loading", () => false)

  const initToken = () => {
    if (process.client && !token.value) {
      token.value = localStorage.getItem("access_token")
    }
    return token.value
  }

  const isLoggedIn = computed(() => {
    return !!token.value
  })

  const fetchUser = async (): Promise<UserPublic | null> => {
    if (!token.value && process.client) {
      token.value = localStorage.getItem("access_token")
    }
    if (!token.value) {
      user.value = null
      return null
    }

    try {
      isLoading.value = true
      const response = await UsersService.readUserMe()
      user.value = response.data
      return user.value
    } catch (err: unknown) {
      const error = err as { status?: number; response?: { status?: number } }
      if (error?.status === 401 || error?.response?.status === 401) {
        logout()
      }
      return null
    } finally {
      isLoading.value = false
    }
  }

  const login = async (credentials: AccessToken) => {
    try {
      isLoading.value = true
      const response = await LoginService.loginAccessToken({
        body: credentials,
      })

      const accessToken = response.data.access_token
      if (process.client) {
        localStorage.setItem("access_token", accessToken)
      }
      token.value = accessToken

      await fetchUser()
      showSuccessToast("Đăng nhập thành công!", "Chào mừng bạn quay trở lại.")
      const route = useRoute()
      const defaultTarget = user.value?.is_superuser ? "/admin" : "/app"
      const rawTarget = (route.query.redirect as string) || defaultTarget
      const redirectTarget =
        !user.value?.is_superuser && rawTarget.startsWith("/admin")
          ? "/app"
          : rawTarget
      await router.push(redirectTarget)
    } catch (err: unknown) {
      const error = err as { body?: { detail?: string }; message?: string }
      const message =
        error?.body?.detail ||
        error?.message ||
        "Đăng nhập thất bại. Vui lòng kiểm tra email và mật khẩu."
      showErrorToast("Lỗi đăng nhập", message)
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const signup = async (data: UserRegister) => {
    try {
      isLoading.value = true
      await UsersService.registerUser({ body: data })
      showSuccessToast(
        "Đăng ký thành công!",
        "Tài khoản của bạn đã được tạo. Vui lòng đăng nhập.",
      )
      await router.push("/login")
    } catch (err: unknown) {
      const error = err as { body?: { detail?: string }; message?: string }
      const message =
        error?.body?.detail ||
        error?.message ||
        "Đăng ký thất bại. Email có thể đã được sử dụng."
      showErrorToast("Lỗi đăng ký", message)
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const logout = () => {
    if (process.client) {
      localStorage.removeItem("access_token")
    }
    token.value = null
    user.value = null
    router.push("/login")
  }

  return {
    user,
    token,
    isLoading,
    isLoggedIn,
    initToken,
    fetchUser,
    login,
    signup,
    logout,
  }
}

export default useAuth
