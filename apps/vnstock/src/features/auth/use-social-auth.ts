import type { UserProfile } from '@/lib/auth/utils';
import { useRouter } from 'expo-router';
import * as React from 'react';
import { Platform } from 'react-native';
import { showMessage } from 'react-native-flash-message';
import { client } from '@/lib/api';
import { isFirebaseConfigured, signInWithFirebaseGoogle } from '@/lib/firebase';
import { useAuthStore } from './use-auth-store';

export type SocialProvider = 'google' | 'apple' | 'passkey';

type GoogleUserInfo = {
  sub: string;
  email: string;
  name?: string;
  picture?: string;
};

export type ExchangePayload = {
  provider: 'google' | 'apple';
  token: string;
  email: string;
  fullName?: string;
};

export async function fetchGoogleProfile(accessToken: string): Promise<GoogleUserInfo> {
  const response = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) {
    throw new Error('Không thể tải thông tin tài khoản từ Google');
  }
  return response.json();
}

export async function exchangeSocialToken(
  payload: ExchangePayload,
): Promise<{ accessToken: string; user: UserProfile }> {
  const res = await client.post<{ access_token: string }>('/login/social', {
    provider: payload.provider,
    token: payload.token,
    email: payload.email,
    full_name: payload.fullName,
  });

  return {
    accessToken: res.data.access_token,
    user: {
      email: payload.email,
      name: payload.fullName || payload.email.split('@')[0],
      provider: payload.provider,
    },
  };
}

function showConfigWarning(providerName: string, envVarName: string) {
  showMessage({
    message: `Chưa cấu hình ${providerName} Client ID`,
    description: `Vui lòng thêm biến môi trường ${envVarName} vào file .env để đăng nhập bằng ${providerName}.`,
    type: 'warning',
    duration: 5000,
  });
}

function useOAuthCallback(
  setLoadingProvider: (provider: SocialProvider | null) => void,
  signIn: (token: { access: string; refresh: string }, user: UserProfile) => void,
  router: ReturnType<typeof useRouter>,
) {
  React.useEffect(() => {
    if (Platform.OS !== 'web' || typeof window === 'undefined' || !window.location.hash) {
      return;
    }

    const hashParams = new URLSearchParams(window.location.hash.substring(1));
    const googleAccessToken = hashParams.get('access_token');
    if (!googleAccessToken) {
      return;
    }

    let isMounted = true;
    async function processHash() {
      try {
        setLoadingProvider('google');
        const googleUser = await fetchGoogleProfile(googleAccessToken!);
        const { accessToken, user } = await exchangeSocialToken({
          provider: 'google',
          token: googleAccessToken!,
          email: googleUser.email,
          fullName: googleUser.name,
        });

        if (!isMounted) {
          return;
        }
        user.avatar = googleUser.picture;
        signIn({ access: accessToken, refresh: '' }, user);
        window.history.replaceState(null, '', window.location.pathname);
        showMessage({
          message: 'Đăng nhập Google thành công',
          description: `Chào mừng ${user.name}`,
          type: 'success',
          duration: 3000,
        });
        router.replace('/(app)');
      }
      catch (err: unknown) {
        if (!isMounted) {
          return;
        }
        showMessage({
          message: 'Lỗi xác thực Google',
          description: err instanceof Error ? err.message : 'Không thể hoàn tất đăng nhập Google.',
          type: 'danger',
          duration: 4000,
        });
      }
      finally {
        if (isMounted) {
          setLoadingProvider(null);
        }
      }
    }

    processHash();
    return () => {
      isMounted = false;
    };
  }, [setLoadingProvider, signIn, router]);
}

async function authenticateWithFirebaseGoogle(
  signIn: (token: { access: string; refresh: string }, user: UserProfile) => void,
  router: ReturnType<typeof useRouter>,
) {
  const firebaseResult = await signInWithFirebaseGoogle();
  const { accessToken, user } = await exchangeSocialToken({
    provider: 'google',
    token: firebaseResult.idToken,
    email: firebaseResult.email,
    fullName: firebaseResult.displayName ?? undefined,
  });

  if (firebaseResult.photoURL) {
    user.avatar = firebaseResult.photoURL;
  }

  signIn({ access: accessToken, refresh: '' }, user);
  showMessage({
    message: 'Đăng nhập Google thành công',
    description: `Chào mừng ${user.name}`,
    type: 'success',
    duration: 3000,
  });
  router.replace('/(app)');
}

function redirectToGoogleOAuth() {
  const googleClientId = process.env.EXPO_PUBLIC_GOOGLE_CLIENT_ID;
  if (!googleClientId) {
    showConfigWarning('Google', 'EXPO_PUBLIC_GOOGLE_CLIENT_ID');
    return;
  }

  if (Platform.OS === 'web' && typeof window !== 'undefined') {
    const redirectUri = `${window.location.origin}/login`;
    const authUrl = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${googleClientId}&redirect_uri=${encodeURIComponent(
      redirectUri,
    )}&response_type=token&scope=openid%20email%20profile`;

    window.location.href = authUrl;
  }
}

function redirectToAppleOAuth() {
  const appleClientId = process.env.EXPO_PUBLIC_APPLE_CLIENT_ID;
  if (!appleClientId) {
    showConfigWarning('Apple ID', 'EXPO_PUBLIC_APPLE_CLIENT_ID');
    return;
  }

  if (Platform.OS === 'web' && typeof window !== 'undefined') {
    const redirectUri = `${window.location.origin}/login`;
    const authUrl = `https://appleid.apple.com/auth/authorize?client_id=${appleClientId}&redirect_uri=${encodeURIComponent(
      redirectUri,
    )}&response_type=code%20id_token&scope=name%20email&response_mode=fragment`;

    window.location.href = authUrl;
  }
}

async function authenticatePasskey() {
  if (typeof window === 'undefined' || !window.PublicKeyCredential) {
    showMessage({
      message: 'Passkey không khả dụng',
      description: 'Trình duyệt hoặc thiết bị của bạn không hỗ trợ WebAuthn / Passkey.',
      type: 'warning',
      duration: 4000,
    });
    return;
  }

  const challenge = new Uint8Array(32);
  window.crypto.getRandomValues(challenge);

  const credential = await navigator.credentials.get({
    publicKey: {
      challenge,
      timeout: 60000,
      userVerification: 'preferred',
    },
  });

  if (!credential) {
    throw new Error('Không nhận được thông tin xác thực từ Passkey');
  }
}

export function useSocialAuth() {
  const [loadingProvider, setLoadingProvider] = React.useState<SocialProvider | null>(null);
  const signIn = useAuthStore.use.signIn();
  const router = useRouter();

  useOAuthCallback(setLoadingProvider, signIn, router);

  const handleGoogleLogin = React.useCallback(async () => {
    try {
      setLoadingProvider('google');

      if (isFirebaseConfigured() && Platform.OS === 'web') {
        await authenticateWithFirebaseGoogle(signIn, router);
        return;
      }

      redirectToGoogleOAuth();
    }
    catch (err: unknown) {
      const errorMsg = err instanceof Error ? err.message : 'Đăng nhập Google thất bại';
      if (!errorMsg.includes('auth/popup-closed-by-user')) {
        showMessage({
          message: 'Đăng nhập Google thất bại',
          description: errorMsg,
          type: 'danger',
          duration: 4000,
        });
      }
    }
    finally {
      setLoadingProvider(null);
    }
  }, [signIn, router]);

  const handleAppleLogin = React.useCallback(async () => {
    redirectToAppleOAuth();
  }, []);

  const handlePasskeyLogin = React.useCallback(async () => {
    try {
      setLoadingProvider('passkey');
      await authenticatePasskey();
    }
    catch (err: unknown) {
      showMessage({
        message: 'Xác thực Passkey thất bại',
        description: err instanceof Error ? err.message : 'Thao tác Passkey bị từ chối hoặc đã huỷ.',
        type: 'danger',
        duration: 4000,
      });
    }
    finally {
      setLoadingProvider(null);
    }
  }, []);

  return {
    loadingProvider,
    handleGoogleLogin,
    handleAppleLogin,
    handlePasskeyLogin,
  };
}
