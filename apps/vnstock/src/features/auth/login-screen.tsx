import type { LoginFormProps } from './components/login-form';

import { useRouter } from 'expo-router';

import { FocusAwareStatusBar, View } from '@/components/ui';
import { LoginForm } from './components/login-form';
import { useAuthStore } from './use-auth-store';

export function LoginScreen() {
  const router = useRouter();
  const signIn = useAuthStore.use.signIn();

  const onSubmit: LoginFormProps['onSubmit'] = (data) => {
    console.log(data);
    signIn({ access: 'access-token', refresh: 'refresh-token' });
    router.push('/');
  };

  return (
    <View className="flex-1">
      <FocusAwareStatusBar />
      <LoginForm onSubmit={onSubmit} />
    </View>
  );
}
