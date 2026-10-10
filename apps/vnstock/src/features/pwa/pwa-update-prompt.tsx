import * as React from 'react';
import { Animated, Platform, Pressable, Text, View } from 'react-native';

import { usePWA } from '@/lib/hooks/use-pwa';

export function PWAUpdatePrompt() {
  const { hasUpdate, applyUpdate } = usePWA();
  const slideAnim = React.useRef(new Animated.Value(-80)).current;

  React.useEffect(() => {
    if (hasUpdate) {
      Animated.spring(slideAnim, {
        toValue: 0,
        useNativeDriver: true,
        tension: 80,
        friction: 12,
      }).start();
    }
  }, [hasUpdate, slideAnim]);

  if (Platform.OS !== 'web' || !hasUpdate) {
    return null;
  }

  return (
    <Animated.View
      style={{
        transform: [{ translateY: slideAnim }],
        position: 'absolute',
        bottom: 72,
        left: 16,
        right: 16,
        zIndex: 999,
      }}
    >
      <View
        style={{
          flexDirection: 'row',
          alignItems: 'center',
          paddingHorizontal: 16,
          paddingVertical: 14,
          backgroundColor: '#1a1f2e',
          borderRadius: 12,
          borderWidth: 1,
          borderColor: '#404040',
          gap: 12,
          shadowColor: '#000',
          shadowOffset: { width: 0, height: 4 },
          shadowOpacity: 0.3,
          shadowRadius: 8,
          elevation: 8,
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
            Có phiên bản mới
          </Text>
          <Text style={{ color: '#a3a3a3', fontSize: 12 }}>
            Tải lại để áp dụng cập nhật mới nhất
          </Text>
        </View>
        <Pressable
          onPress={applyUpdate}
          style={({ pressed }) => ({
            backgroundColor: pressed ? '#1a3a1a' : '#166534',
            paddingHorizontal: 14,
            paddingVertical: 8,
            borderRadius: 8,
          })}
        >
          <Text style={{ color: '#4ADE80', fontSize: 13, fontWeight: '700' }}>
            Cập nhật
          </Text>
        </Pressable>
      </View>
    </Animated.View>
  );
}
