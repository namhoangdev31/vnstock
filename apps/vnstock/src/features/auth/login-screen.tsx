import type { LoginFormProps } from './components/login-form';

import { useLocalSearchParams, useRouter } from 'expo-router';
import * as React from 'react';

import { FocusAwareStatusBar, View } from '@/components/ui';
import { LoginForm } from './components/login-form';
import { useAuthStore } from './use-auth-store';

export function LoginScreen() {
  const router = useRouter();
  const { mode } = useLocalSearchParams<{ mode?: 'signIn' | 'signUp' }>();
  const status = useAuthStore.use.status();
  const signIn = useAuthStore.use.signIn();

  React.useEffect(() => {
    if (status === 'signIn') {
      router.replace('/(app)');
    }
  }, [status, router]);

  const onSubmit: LoginFormProps['onSubmit'] = (data) => {
    console.log(data);
    signIn({ access: 'access-token', refresh: 'refresh-token' });
    router.replace('/(app)');
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
      />
    </View>
  );
}
