import { client } from "~/client/client.gen"

export default defineNuxtPlugin(() => {
  const config = useRuntimeConfig()
  // In dev mode, route through Nuxt Nitro proxy to eliminate browser CORS issues
  const baseURL = import.meta.dev
    ? ""
    : ((config.public.apiUrl as string) || "").replace(/\/+$/, "")

  client.setConfig({
    baseURL,
    auth: () => {
      if (process.client) {
        return localStorage.getItem("access_token") || ""
      }
      return ""
    },
  })
})
