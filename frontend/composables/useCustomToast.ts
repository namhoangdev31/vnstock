export const useCustomToast = () => {
  const toast = useToast()

  const showSuccessToast = (message: string, description?: string) => {
    toast.add({
      title: message,
      description,
      color: "green",
      icon: "i-heroicons-check-circle",
    })
  }

  const showErrorToast = (message: string, description?: string) => {
    toast.add({
      title: message,
      description,
      color: "red",
      icon: "i-heroicons-exclamation-circle",
    })
  }

  const showInfoToast = (message: string, description?: string) => {
    toast.add({
      title: message,
      description,
      color: "blue",
      icon: "i-heroicons-information-circle",
    })
  }

  return {
    showSuccessToast,
    showErrorToast,
    showInfoToast,
  }
}

export default useCustomToast
