import { Link, Redirect, SplashScreen, Tabs } from 'expo-router';
import { useCallback, useEffect } from 'react';
import { Platform } from 'react-native';
import { useUniwind } from 'uniwind';

import { colors, Pressable, Text } from '@/components/ui';
import {
  Feed as FeedIcon,
  Settings as SettingsIcon,
  Style as StyleIcon,
} from '@/components/ui/icons';
import { useAuthStore as useAuth } from '@/features/auth/use-auth-store';
import { PWAInstallBanner } from '@/features/pwa/pwa-install-banner';
import { PWAUpdatePrompt } from '@/features/pwa/pwa-update-prompt';
import { useIsFirstTime } from '@/lib/hooks/use-is-first-time';

const isWeb = Platform.OS === 'web';

export default function TabLayout() {
  const { theme } = useUniwind();
  const isDark = theme === 'dark';
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
            backgroundColor: isDark ? colors.aave.obsidian : colors.surface.canvas,
            borderTopColor: isDark ? 'rgba(255, 255, 255, 0.06)' : 'rgba(34, 29, 29, 0.06)',
          },
          tabBarActiveTintColor: colors.aave.violet,
          tabBarInactiveTintColor: isDark ? colors.aave.graphite : colors.aave.pewter,
          headerStyle: {
            backgroundColor: isDark ? colors.aave.obsidian : colors.surface.canvas,
          },
          headerTitleStyle: {
            color: isDark ? colors.aave.paper : colors.aave.charcoal,
          },
          headerShadowVisible: false,
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
        <Text className="px-3 font-semibold text-aave-violet">Tạo mới</Text>
      </Pressable>
    </Link>
  );
}
