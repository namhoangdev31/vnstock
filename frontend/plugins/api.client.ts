import { client } from "~/client/client.gen"

export default defineNuxtPlugin(() => {
  const config = useRuntimeConfig()
  const baseURL = ((config.public.apiUrl as string) || "").replace(/\/+$/, "")

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
