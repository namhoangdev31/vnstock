export default defineNuxtPlugin((nuxtApp) => {
  if (typeof window === "undefined" || !("IntersectionObserver" in window)) {
    return
  }

  // Đánh dấu client sẵn sàng kích hoạt animation
  document.documentElement.classList.add("reveal-init")

  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          const target = entry.target as HTMLElement
          target.classList.add("is-revealed")

          // Kích hoạt theo chuỗi nếu là container chứa các phần tử con
          const cascadeChildren =
            target.querySelectorAll<HTMLElement>(".reveal-cascade")
          cascadeChildren.forEach((child, index) => {
            if (!child.style.getPropertyValue("--reveal-delay")) {
              child.style.setProperty("--reveal-delay", `${index * 90}ms`)
            }
            child.classList.add("is-revealed")
          })

          observer.unobserve(target)
        }
      }
    },
    {
      root: null,
      threshold: 0.08,
      rootMargin: "0px 0px -30px 0px",
    },
  )

  const observeElements = () => {
    const targets = document.querySelectorAll<HTMLElement>(
      ".reveal-item, .reveal-scale, .reveal-left, .reveal-right, .reveal-container",
    )
    for (const target of targets) {
      if (!target.classList.contains("is-revealed")) {
        observer.observe(target)
      }
    }
  }

  // Directive v-reveal="{ delay: 120 }"
  nuxtApp.vueApp.directive("reveal", {
    mounted(el: HTMLElement, binding) {
      if (binding.value?.delay) {
        el.style.setProperty("--reveal-delay", `${binding.value.delay}ms`)
      }
      observer.observe(el)
    },
    unmounted(el: HTMLElement) {
      observer.unobserve(el)
    },
  })

  // Tự động quét khi chuyển trang hoàn tất
  nuxtApp.hook("page:finish", () => {
    nextTick(() => {
      observeElements()
    })
  })

  // Quét sau khi DOM khởi tạo
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      observeElements()
    })
  } else {
    setTimeout(observeElements, 50)
  }
})
