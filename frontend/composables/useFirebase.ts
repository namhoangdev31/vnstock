import type { FirebaseApp } from "firebase/app"
import type { Auth } from "firebase/auth"
import { getApp, getApps, initializeApp } from "firebase/app"
import {
  GoogleAuthProvider,
  OAuthProvider,
  createUserWithEmailAndPassword,
  getAuth,
  signInWithPopup,
  updateProfile,
} from "firebase/auth"

export const useFirebase = () => {
  const config = useRuntimeConfig()

  const getFirebaseApp = (): FirebaseApp | null => {
    if (!process.client) return null
    if (!config.public.firebaseApiKey || !config.public.firebaseProjectId) {
      return null
    }

    if (getApps().length > 0) {
      return getApp()
    }

    return initializeApp({
      apiKey: config.public.firebaseApiKey as string,
      authDomain: config.public.firebaseAuthDomain as string,
      projectId: config.public.firebaseProjectId as string,
      storageBucket: config.public.firebaseStorageBucket as string,
      messagingSenderId: config.public.firebaseMessagingSenderId as string,
      appId: config.public.firebaseAppId as string,
      measurementId: config.public.firebaseMeasurementId as string,
    })
  }

  const getFirebaseAuth = (): Auth | null => {
    const app = getFirebaseApp()
    if (!app) return null
    return getAuth(app)
  }

  const registerWithEmailPassword = async (
    email: string,
    password: string,
    fullName?: string,
  ) => {
    const auth = getFirebaseAuth()
    if (!auth) return null

    try {
      const credential = await createUserWithEmailAndPassword(
        auth,
        email,
        password,
      )
      if (fullName && credential.user) {
        await updateProfile(credential.user, { displayName: fullName })
      }
      const idToken = await credential.user.getIdToken()
      return {
        idToken,
        email: credential.user.email ?? email,
        displayName: credential.user.displayName,
      }
    } catch (err: unknown) {
      console.warn("Tự động tạo tài khoản Firebase (Web):", err)
      return null
    }
  }

  const signInWithGoogle = async () => {
    const auth = getFirebaseAuth()
    if (!auth) {
      throw new Error(
        "Firebase chưa được cấu hình. Vui lòng kiểm tra file .env.",
      )
    }

    const provider = new GoogleAuthProvider()
    provider.addScope("email")
    provider.addScope("profile")

    const credential = await signInWithPopup(auth, provider)
    const user = credential.user
    const idToken = await user.getIdToken()

    if (!user.email) {
      throw new Error("Tài khoản Google không có email hợp lệ.")
    }

    return {
      idToken,
      email: user.email,
      displayName: user.displayName,
      photoURL: user.photoURL,
    }
  }

  const signInWithApple = async () => {
    const auth = getFirebaseAuth()
    if (!auth) {
      throw new Error(
        "Firebase chưa được cấu hình. Vui lòng kiểm tra file .env.",
      )
    }

    const provider = new OAuthProvider("apple.com")
    provider.addScope("email")
    provider.addScope("name")

    const credential = await signInWithPopup(auth, provider)
    const user = credential.user
    const idToken = await user.getIdToken()

    const email =
      user.email ||
      (
        credential as unknown as {
          _tokenResponse?: { email?: string }
        }
      )?._tokenResponse?.email

    if (!email) {
      throw new Error("Tài khoản Apple không trả về email hợp lệ.")
    }

    return {
      idToken,
      email,
      displayName: user.displayName,
      photoURL: user.photoURL,
    }
  }

  return {
    getFirebaseApp,
    getFirebaseAuth,
    registerWithEmailPassword,
    signInWithGoogle,
    signInWithApple,
  }
}

export default useFirebase
