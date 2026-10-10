// biome-ignore assist/source/organizeImports: <explanation>
import { Link, Redirect, SplashScreen, Tabs } from 'expo-router';
import * as React from 'react';
import { useCallback, useEffect } from 'react';
import { Platform } from 'react-native';

import { Pressable, Text } from '@/components/ui';
import {
  Feed as FeedIcon,
  Settings as SettingsIcon,
  Style as StyleIcon,
} from '@/components/ui/icons';
import { PWAInstallBanner } from '@/features/pwa/pwa-install-banner';
import { PWAUpdatePrompt } from '@/features/pwa/pwa-update-prompt';
import { useAuthStore as useAuth } from '@/features/auth/use-auth-store';
import { useIsFirstTime } from '@/lib/hooks/use-is-first-time';

const isWeb = Platform.OS === 'web';

export default function TabLayout() {
  const status = useAuth.use.status();
  const [isFirstTime] = useIsFirstTime();
  const hideSplash = useCallback(async () => {
    await SplashScreen.hideAsync();
  }, []);
  useEffect(() => {
    if (status !== 'idle') {
      const timer = setTimeout(() => {
        hideSplash();
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [hideSplash, status]);

  if (isFirstTime) {
    return <Redirect href="/onboarding" />;
  }
  if (status === 'signOut') {
    return <Redirect href="/login" />;
  }
  return (
    <>
      {isWeb && <PWAUpdatePrompt />}
      {isWeb && <PWAInstallBanner />}
      <Tabs
        screenOptions={{
          tabBarStyle: {
            height: isWeb ? 60 : undefined,
            paddingBottom: isWeb ? 8 : undefined,
            paddingTop: isWeb ? 4 : undefined,
          },
          tabBarLabelStyle: {
            fontSize: 11,
            fontWeight: '600',
          },
        }}
      >
        <Tabs.Screen
          name="index"
          options={{
            title: 'Bảng Tin',
            tabBarIcon: ({ color }) => <FeedIcon color={color} />,
            headerTitle: 'Vnstock',
            headerRight: () => <CreateNewPostLink />,
            tabBarButtonTestID: 'feed-tab',
          }}
        />

        <Tabs.Screen
          name="style"
          options={{
            title: 'UI Kit',
            headerShown: false,
            tabBarIcon: ({ color }) => <StyleIcon color={color} />,
            tabBarButtonTestID: 'style-tab',
          }}
        />
        <Tabs.Screen
          name="settings"
          options={{
            title: 'Cài Đặt',
            headerShown: false,
            tabBarIcon: ({ color }) => <SettingsIcon color={color} />,
            tabBarButtonTestID: 'settings-tab',
          }}
        />
      </Tabs>
    </>
  );
}

function CreateNewPostLink() {
  return (
    <Link href="/feed/add-post" asChild>
      <Pressable>
        <Text className="px-3 text-primary-300">Tạo mới</Text>
      </Pressable>
    </Link>
  );
}
