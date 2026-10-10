import { useRouter } from 'expo-router';
import * as React from 'react';
import { Animated, Platform, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Button, FocusAwareStatusBar, Text } from '@/components/ui';
import { useIsFirstTime } from '@/lib/hooks';
import { usePWA } from '@/lib/hooks/use-pwa';

const features = [
  { icon: '📊', label: 'Phân tích định lượng 3 Engine' },
  { icon: '⚡', label: 'Dự báo ATC & T+1 thời gian thực' },
  { icon: '📈', label: 'Theo dõi VN30F1M toàn phiên' },
  { icon: '🛡️', label: 'Paper trading an toàn, không rủi ro' },
];

function FeatureRow({ icon, label, delay }: { icon: string; label: string; delay: number }) {
  const fadeAnim = React.useRef(new Animated.Value(0)).current;
  const slideAnim = React.useRef(new Animated.Value(20)).current;

  React.useEffect(() => {
    const timer = setTimeout(() => {
      Animated.parallel([
        Animated.timing(fadeAnim, { toValue: 1, duration: 400, useNativeDriver: true }),
        Animated.spring(slideAnim, { toValue: 0, useNativeDriver: true, tension: 80, friction: 12 }),
      ]).start();
    }, delay);
    return () => clearTimeout(timer);
  }, [fadeAnim, slideAnim, delay]);

  return (
    <Animated.View
      style={[styles.featureRow, { opacity: fadeAnim, transform: [{ translateY: slideAnim }] }]}
    >
      <View style={styles.featureIcon}>
        <Text style={styles.featureIconText}>{icon}</Text>
      </View>
      <Text style={styles.featureLabel}>{label}</Text>
    </Animated.View>
  );
}

export function OnboardingScreen() {
  const [_, setIsFirstTime] = useIsFirstTime();
  const { canInstall, installPWA } = usePWA();
  const router = useRouter();
  const isWeb = Platform.OS === 'web';

  const titleAnim = React.useRef(new Animated.Value(0)).current;
  const subtitleAnim = React.useRef(new Animated.Value(0)).current;

  React.useEffect(() => {
    Animated.sequence([
      Animated.timing(titleAnim, { toValue: 1, duration: 600, useNativeDriver: true }),
      Animated.timing(subtitleAnim, { toValue: 1, duration: 400, useNativeDriver: true }),
    ]).start();
  }, [titleAnim, subtitleAnim]);

  const handleStart = React.useCallback(() => {
    setIsFirstTime(false);
    router.replace('/login');
  }, [setIsFirstTime, router]);

  const handleInstallAndStart = React.useCallback(async () => {
    await installPWA();
    setIsFirstTime(false);
    router.replace('/login');
  }, [installPWA, setIsFirstTime, router]);

  return (
    <View style={styles.container}>
      <FocusAwareStatusBar />

      {/* Background accent */}
      <View style={styles.bgAccent} />

      <SafeAreaView style={styles.safeArea}>
        {/* Header brand */}
        <Animated.View style={[styles.header, { opacity: titleAnim }]}>
          <View style={styles.logoContainer}>
            <Text style={styles.logoText}>V</Text>
          </View>
          <View>
            <Text style={styles.brandName}>Vnstock Terminal</Text>
            <Text style={styles.brandTagline}>Phân tích thị trường Việt Nam</Text>
          </View>
        </Animated.View>

        {/* Hero section */}
        <View style={styles.hero}>
          <Animated.View style={{ opacity: titleAnim }}>
            <Text style={styles.heroTitle}>
              {`Nắm bắt thị trường\n`}
              <Text style={styles.heroTitleAccent}>
                trong tầm tay
              </Text>
            </Text>
          </Animated.View>

          <Animated.View style={{ opacity: subtitleAnim }}>
            <Text style={styles.heroSubtitle}>
              Hệ thống nghiên cứu định lượng 24/7 — dự báo ATC, tối ưu phái sinh VN30F1M và lựa chọn cổ phiếu alpha.
            </Text>
          </Animated.View>
        </View>

        {/* Feature list */}
        <View style={styles.featureList}>
          {features.map((f, i) => (
            <FeatureRow key={f.label} icon={f.icon} label={f.label} delay={300 + i * 100} />
          ))}
        </View>

        {/* CTA */}
        <View style={styles.ctaContainer}>
          {isWeb && canInstall
            ? (
                <>
                  <Button
                    label="Cài đặt & Bắt đầu"
                    onPress={handleInstallAndStart}
                    variant="default"
                  />
                  <Button
                    label="Tiếp tục trên trình duyệt"
                    onPress={handleStart}
                    variant="ghost"
                  />
                </>
              )
            : (
                <Button
                  label="Bắt đầu ngay"
                  onPress={handleStart}
                  variant="default"
                />
              )}
          <Text style={styles.disclaimer}>
            Chỉ phân tích thông tin — không tự động khớp lệnh thật
          </Text>
        </View>
      </SafeAreaView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0B0E14',
  },
  bgAccent: {
    position: 'absolute',
    top: -120,
    right: -80,
    width: 320,
    height: 320,
    borderRadius: 160,
    backgroundColor: 'rgba(255, 108, 0, 0.08)',
  },
  safeArea: {
    flex: 1,
    paddingHorizontal: 24,
    paddingBottom: 16,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingTop: 12,
    marginBottom: 40,
  },
  logoContainer: {
    width: 44,
    height: 44,
    borderRadius: 12,
    backgroundColor: '#FF6C00',
    alignItems: 'center',
    justifyContent: 'center',
  },
  logoText: {
    color: '#fff',
    fontSize: 22,
    fontWeight: '800',
  },
  brandName: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '700',
  },
  brandTagline: {
    color: '#737373',
    fontSize: 12,
    marginTop: 1,
  },
  hero: {
    flex: 1,
    justifyContent: 'center',
    gap: 16,
  },
  heroTitle: {
    color: '#ffffff',
    fontSize: 38,
    fontWeight: '800',
    lineHeight: 46,
    letterSpacing: -0.5,
  },
  heroTitleAccent: {
    color: '#FF6C00',
  },
  heroSubtitle: {
    color: '#a3a3a3',
    fontSize: 15,
    lineHeight: 24,
  },
  featureList: {
    gap: 12,
    marginBottom: 32,
  },
  featureRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
  },
  featureIcon: {
    width: 36,
    height: 36,
    borderRadius: 10,
    backgroundColor: 'rgba(255, 108, 0, 0.12)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  featureIconText: {
    fontSize: 18,
  },
  featureLabel: {
    color: '#e5e5e5',
    fontSize: 14,
    fontWeight: '500',
  },
  ctaContainer: {
    gap: 8,
  },
  disclaimer: {
    color: '#525252',
    fontSize: 11,
    textAlign: 'center',
    marginTop: 8,
  },
});
