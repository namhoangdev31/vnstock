import {
  useDocumentVisibility,
  useIntervalFn,
  useNow,
  useOnline,
} from "@vueuse/core"

export type TradingPhase = "ACTIVE" | "INTERMISSION" | "OVERNIGHT"

export function useTradingPhase(): ComputedRef<TradingPhase> {
  const now = useNow()
  return computed(() => {
    const local = new Date(
      now.value.toLocaleString("en-US", { timeZone: "Asia/Ho_Chi_Minh" }),
    )
    const value = local.getHours() * 100 + local.getMinutes()
    if ((value >= 845 && value < 1130) || (value >= 1300 && value < 1445))
      return "ACTIVE"
    if ((value >= 1130 && value < 1300) || (value >= 1445 && value < 1500))
      return "INTERMISSION"
    return "OVERNIGHT"
  })
}

export function useTradingPolling(fetcher: () => Promise<void>) {
  const phase = useTradingPhase()
  const online = useOnline()
  const visibility = useDocumentVisibility()
  const visible = computed(() => visibility.value === "visible")
  const loading = shallowRef(false)
  const refreshing = shallowRef(false)
  const stale = shallowRef(false)
  const error = shallowRef<string | null>(null)
  const lastUpdated = shallowRef<string | null>(null)
  let failureCount = 0

  const refresh = async () => {
    if (!online.value || !visible.value || refreshing.value) return
    refreshing.value = true
    try {
      await fetcher()
      failureCount = 0
      error.value = null
      stale.value = false
      lastUpdated.value = new Date().toISOString()
    } catch (cause) {
      failureCount += 1
      stale.value = true
      error.value =
        cause instanceof Error ? cause.message : "Không thể cập nhật dữ liệu"
    } finally {
      refreshing.value = false
      loading.value = false
    }
  }

  const interval = computed(() => (phase.value === "ACTIVE" ? 1000 : 5000))
  const { pause, resume } = useIntervalFn(refresh, interval, {
    immediate: false,
  })

  watch(
    [phase, visible, online],
    () => {
      if (online.value && visible.value) resume()
      else pause()
    },
    { immediate: true },
  )

  onMounted(() => {
    loading.value = true
    void refresh()
  })

  onUnmounted(() => pause())

  return {
    phase,
    online,
    visible,
    loading,
    refreshing,
    stale,
    error,
    lastUpdated,
    failureCount,
    refresh,
    pause,
    resume,
  }
}
