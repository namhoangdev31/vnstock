import type { FirebaseApp } from 'firebase/app';
import type { Auth } from 'firebase/auth';
import Env from 'env';
import { getApp, getApps, initializeApp } from 'firebase/app';
import {
  createUserWithEmailAndPassword,
  getAuth,
  GoogleAuthProvider,
  OAuthProvider,
  signInWithPopup,
  updateProfile,
} from 'firebase/auth';

export type FirebaseConfig = {
  apiKey?: string;
  authDomain?: string;
  projectId?: string;
  storageBucket?: string;
  messagingSenderId?: string;
  appId?: string;
  measurementId?: string;
  databaseURL?: string;
};

export const firebaseConfig: FirebaseConfig = {
  apiKey: Env.EXPO_PUBLIC_FIREBASE_API_KEY,
  authDomain: Env.EXPO_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: Env.EXPO_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: Env.EXPO_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: Env.EXPO_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: Env.EXPO_PUBLIC_FIREBASE_APP_ID,
  measurementId: Env.EXPO_PUBLIC_FIREBASE_MEASUREMENT_ID,
  databaseURL: Env.EXPO_PUBLIC_FIREBASE_DATABASE_URL,
};

export function isFirebaseConfigured(): boolean {
  return Boolean(firebaseConfig.apiKey && firebaseConfig.projectId);
}

export function getFirebaseApp(): FirebaseApp | null {
  if (!isFirebaseConfigured()) {
    return null;
  }

  if (getApps().length > 0) {
    return getApp();
  }

  return initializeApp({
    apiKey: firebaseConfig.apiKey!,
    authDomain: firebaseConfig.authDomain,
    projectId: firebaseConfig.projectId!,
    storageBucket: firebaseConfig.storageBucket,
    messagingSenderId: firebaseConfig.messagingSenderId,
    appId: firebaseConfig.appId,
    measurementId: firebaseConfig.measurementId,
    databaseURL: firebaseConfig.databaseURL,
  });
}

export function getFirebaseAuth(): Auth | null {
  const app = getFirebaseApp();
  if (!app) {
    return null;
  }
  return getAuth(app);
}

export async function signInWithFirebaseGoogle(): Promise<{
  idToken: string;
  email: string;
  displayName: string | null;
  photoURL: string | null;
}> {
  const auth = getFirebaseAuth();
  if (!auth) {
    throw new Error('Firebase chưa được cấu hình. Vui lòng thêm cấu hình Firebase vào file .env.');
  }

  const provider = new GoogleAuthProvider();
  provider.addScope('email');
  provider.addScope('profile');

  const result = await signInWithPopup(auth, provider);
  const user = result.user;
  const idToken = await user.getIdToken();

  if (!user.email) {
    throw new Error('Tài khoản Google không có email');
  }

  return {
    idToken,
    email: user.email,
    displayName: user.displayName,
    photoURL: user.photoURL,
  };
}

export async function signInWithFirebaseApple(): Promise<{
  idToken: string;
  email: string;
  displayName: string | null;
  photoURL: string | null;
}> {
  const auth = getFirebaseAuth();
  if (!auth) {
    throw new Error('Firebase chưa được cấu hình. Vui lòng thêm cấu hình Firebase vào file .env.');
  }

  const provider = new OAuthProvider('apple.com');
  provider.addScope('email');
  provider.addScope('name');

  const result = await signInWithPopup(auth, provider);
  const user = result.user;
  const idToken = await user.getIdToken();

  const email = user.email || (result as { _tokenResponse?: { email?: string } })?._tokenResponse?.email;
  if (!email) {
    throw new Error('Tài khoản Apple không trả về email.');
  }

  return {
    idToken,
    email,
    displayName: user.displayName,
    photoURL: user.photoURL,
  };
}

export async function registerWithFirebaseEmail(
  email: string,
  password: string,
  fullName?: string,
): Promise<{ idToken: string; email: string } | null> {
  const auth = getFirebaseAuth();
  if (!auth) {
    return null;
  }

  try {
    const result = await createUserWithEmailAndPassword(auth, email, password);
    if (fullName && result.user) {
      await updateProfile(result.user, { displayName: fullName });
    }
    const idToken = await result.user.getIdToken();
    return {
      idToken,
      email: result.user.email ?? email,
    };
  }
  catch (err: unknown) {
    console.warn('Tự động tạo tài khoản Firebase (Mobile):', err);
    return null;
  }
}
