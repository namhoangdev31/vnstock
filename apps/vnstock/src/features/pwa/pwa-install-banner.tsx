import * as React from 'react';
import { Animated, Platform, Pressable, Text, View } from 'react-native';

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
        Animated.spring(slideAnim, {
          toValue: 0,
          useNativeDriver: true,
          tension: 80,
          friction: 12,
        }),
        Animated.timing(opacityAnim, {
          toValue: 1,
          duration: 300,
          useNativeDriver: true,
        }),
      ]).start();
    }
  }, [shouldShow, slideAnim, opacityAnim]);

  const handleDismiss = React.useCallback(() => {
    Animated.parallel([
      Animated.timing(slideAnim, {
        toValue: -80,
        duration: 200,
        useNativeDriver: true,
      }),
      Animated.timing(opacityAnim, {
        toValue: 0,
        duration: 200,
        useNativeDriver: true,
      }),
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
      style={{
        transform: [{ translateY: slideAnim }],
        opacity: opacityAnim,
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 999,
      }}
    >
      <View
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          paddingHorizontal: 16,
          paddingVertical: 12,
          backgroundColor: '#1a1f2e',
          borderBottomWidth: 1,
          borderBottomColor: '#FF6C00',
          gap: 12,
        }}
      >
        <View style={{ flex: 1 }}>
          <Text
            style={{
              color: '#ffffff',
              fontSize: 13,
              fontWeight: '700',
              marginBottom: 2,
            }}
          >
            Cài đặt Vnstock
          </Text>
          <Text style={{ color: '#a3a3a3', fontSize: 12 }}>
            Trải nghiệm mượt mà hơn trên màn hình chính
          </Text>
        </View>
        <Pressable
          onPress={handleInstall}
          style={({ pressed }) => ({
            backgroundColor: pressed ? '#E56100' : '#FF6C00',
            paddingHorizontal: 14,
            paddingVertical: 8,
            borderRadius: 8,
          })}
        >
          <Text style={{ color: '#ffffff', fontSize: 13, fontWeight: '700' }}>
            Cài đặt
          </Text>
        </Pressable>
        <Pressable
          onPress={handleDismiss}
          hitSlop={{ top: 10, right: 10, bottom: 10, left: 10 }}
          style={{ padding: 4 }}
        >
          <Text style={{ color: '#737373', fontSize: 18, lineHeight: 18 }}>
            ✕
          </Text>
        </Pressable>
      </View>
    </Animated.View>
  );
}
