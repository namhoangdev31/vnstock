import type { LoginFormProps } from './components/login-form';

import { useLocalSearchParams, useRouter } from 'expo-router';
import * as React from 'react';

import { showMessage } from 'react-native-flash-message';

import { FocusAwareStatusBar, View } from '@/components/ui';
import { client } from '@/lib/api';
import { LoginForm } from './components/login-form';
import { useAuthStore } from './use-auth-store';
import { useSocialAuth } from './use-social-auth';

export function LoginScreen() {
  const router = useRouter();
  const { mode } = useLocalSearchParams<{ mode?: 'signIn' | 'signUp' }>();
  const status = useAuthStore.use.status();
  const signIn = useAuthStore.use.signIn();
  const {
    loadingProvider,
    handleGoogleLogin,
    handleAppleLogin,
  } = useSocialAuth();

  React.useEffect(() => {
    if (status === 'signIn') {
      router.replace('/(app)');
    }
  }, [status, router]);

  const onSubmit: LoginFormProps['onSubmit'] = async (data) => {
    try {
      if (mode === 'signUp') {
        await client.post('/users/signup', {
          email: data.email,
          password: data.password,
          full_name: data.email.split('@')[0],
        });
      }

      const params = new URLSearchParams();
      params.append('username', data.email);
      params.append('password', data.password);

      const loginRes = await client.post<{ access_token: string }>('/login/access-token', params.toString(), {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });

      const accessToken = loginRes.data.access_token;
      const meRes = await client.get<{ email: string; full_name?: string | null }>('/users/me', {
        headers: { Authorization: `Bearer ${accessToken}` },
      });

      const userProfile = meRes.data;
      signIn(
        { access: accessToken, refresh: '' },
        {
          email: userProfile.email,
          name: userProfile.full_name || userProfile.email.split('@')[0],
          provider: 'email',
        },
      );
      router.replace('/(app)');
    }
    catch (err: any) {
      const detail = err.response?.data?.detail;
      const message = typeof detail === 'string'
        ? detail
        : (err instanceof Error ? err.message : 'Xác thực không thành công');

      showMessage({
        message: mode === 'signUp' ? 'Lỗi đăng ký tài khoản' : 'Lỗi đăng nhập',
        description: message,
        type: 'danger',
        duration: 4000,
      });
    }
  };

  const onCancel = () => {
    if (router.canGoBack()) {
      router.back();
    }
    else {
      router.replace('/onboarding');
    }
  };

  return (
    <View className="flex-1 bg-pure-white">
      <FocusAwareStatusBar />
      <LoginForm
        initialMode={mode === 'signUp' ? 'signUp' : 'signIn'}
        onSubmit={onSubmit}
        onCancel={onCancel}
        onGoogleSelect={handleGoogleLogin}
        onAppleSelect={handleAppleLogin}
        loadingProvider={loadingProvider}
      />
    </View>
  );
}
