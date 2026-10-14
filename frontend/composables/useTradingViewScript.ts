let scriptPromise: Promise<void> | null = null

export function loadTradingViewScript(): Promise<void> {
  if (typeof window === "undefined") {
    return Promise.resolve()
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  if ((window as any).TradingView?.widget) {
    return Promise.resolve()
  }

  if (scriptPromise) {
    return scriptPromise
  }

  scriptPromise = new Promise<void>((resolve, reject) => {
    const src = "/charting_library/charting_library.standalone.js"
    const existing = document.querySelector(`script[src="${src}"]`)
    if (existing) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      if ((window as any).TradingView?.widget) {
        resolve()
        return
      }
      existing.addEventListener("load", () => resolve())
      existing.addEventListener("error", (e) => reject(e))
      return
    }

    const script = document.createElement("script")
    script.src = src
    script.type = "text/javascript"
    script.async = true
    script.onload = () => resolve()
    script.onerror = () => {
      scriptPromise = null
      reject(new Error(`Không thể nạp tệp thư viện TradingView: ${src}`))
    }
    document.head.appendChild(script)
  })

  return scriptPromise
}
