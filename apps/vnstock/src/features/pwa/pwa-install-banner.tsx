import * as React from 'react';
import { Animated, Platform } from 'react-native';

import { Pressable, Text, View } from '@/components/ui';
import { usePWA } from '@/lib/hooks/use-pwa';

export function PWAInstallBanner() {
  const { canInstall, isInstalled, installPWA } = usePWA();
  const [dismissed, setDismissed] = React.useState(false);
  const slideAnim = React.useRef(new Animated.Value(-80)).current;
  const opacityAnim = React.useRef(new Animated.Value(0)).current;

  const shouldShow = Platform.OS === 'web' && canInstall && !isInstalled && !dismissed;

  React.useEffect(() => {
    if (shouldShow) {
      Animated.parallel([
        Animated.spring(slideAnim, { toValue: 0, useNativeDriver: true, tension: 80, friction: 12 }),
        Animated.timing(opacityAnim, { toValue: 1, duration: 300, useNativeDriver: true }),
      ]).start();
    }
  }, [shouldShow, slideAnim, opacityAnim]);

  const handleDismiss = React.useCallback(() => {
    Animated.parallel([
      Animated.timing(slideAnim, { toValue: -80, duration: 200, useNativeDriver: true }),
      Animated.timing(opacityAnim, { toValue: 0, duration: 200, useNativeDriver: true }),
    ]).start(() => setDismissed(true));
  }, [slideAnim, opacityAnim]);

  const handleInstall = React.useCallback(async () => {
    await installPWA();
    setDismissed(true);
  }, [installPWA]);

  if (!shouldShow) {
    return null;
  }

  return (
    <Animated.View
      className="absolute inset-x-0 top-0 z-999"
      style={{ transform: [{ translateY: slideAnim }], opacity: opacityAnim }}
    >
      <View className="flex-row items-center gap-3 border-b border-white/6 bg-aave-obsidian px-4 py-3">
        <View className="flex-1">
          <Text className="mb-0.5 text-[13px] font-bold text-aave-paper">Cài đặt Vistock</Text>
          <Text className="text-xs text-aave-graphite">Trải nghiệm mượt mà hơn trên màn hình chính</Text>
        </View>
        <Pressable
          onPress={handleInstall}
          className="rounded-lg bg-aave-violet px-3.5 py-2 active:opacity-90"
        >
          <Text className="text-[13px] font-bold text-aave-charcoal">Cài đặt</Text>
        </Pressable>
        <Pressable onPress={handleDismiss} hitSlop={10} className="p-1">
          <Text className="text-lg/4.5 text-aave-graphite">✕</Text>
        </Pressable>
      </View>
    </Animated.View>
  );
}
