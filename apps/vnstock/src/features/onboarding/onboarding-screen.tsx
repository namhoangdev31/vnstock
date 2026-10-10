import { useRouter } from 'expo-router';
import * as React from 'react';
import { Animated, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { Button, FocusAwareStatusBar, Text, View } from '@/components/ui';
import { useIsFirstTime } from '@/lib/hooks';
import { usePWA } from '@/lib/hooks/use-pwa';

const features = [
  { step: '01', label: 'Phân tích định lượng 3 Engine' },
  { step: '02', label: 'Dự báo ATC và T+1 thời gian thực' },
  { step: '03', label: 'Theo dõi VN30F1M toàn phiên' },
  { step: '04', label: 'Paper trading an toàn không rủi ro' },
];

function FeatureRow({ step, label, delay }: { step: string; label: string; delay: number }) {
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
      className="flex-row items-center gap-3.5"
      style={{ opacity: fadeAnim, transform: [{ translateY: slideAnim }] }}
    >
      <View className="size-9 items-center justify-center rounded-[10px] border border-aave-violet/30 bg-aave-violet/15">
        <Text className="font-mono text-xs font-bold text-aave-violet">{step}</Text>
      </View>
      <Text className="text-sm font-medium text-aave-bone">{label}</Text>
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
    <View className="relative flex-1 bg-aave-inkwell">
      <FocusAwareStatusBar />

      {/* Background accent */}
      <View className="absolute -top-30 -right-20 size-80 rounded-full bg-aave-violet/6" />

      <SafeAreaView className="flex-1 px-6 pb-4">
        {/* Header brand */}
        <Animated.View className="mb-10 flex-row items-center gap-3 pt-3" style={{ opacity: titleAnim }}>
          <View className="size-11 items-center justify-center rounded-xl bg-aave-violet">
            <Text className="text-[22px] font-extrabold text-aave-charcoal">V</Text>
          </View>
          <View>
            <Text className="text-base font-bold text-aave-paper">Vnstock Terminal</Text>
            <Text className="mt-0.5 text-xs text-aave-graphite">Phân tích thị trường Việt Nam</Text>
          </View>
        </Animated.View>

        {/* Hero section */}
        <View className="flex-1 justify-center gap-4">
          <Animated.View style={{ opacity: titleAnim }}>
            <Text className="text-[38px]/11.5 font-extrabold tracking-tight text-aave-paper">
              {`Nắm bắt thị trường\n`}
              <Text className="text-aave-violet">
                trong tầm tay
              </Text>
            </Text>
          </Animated.View>

          <Animated.View style={{ opacity: subtitleAnim }}>
            <Text className="text-[15px]/6 text-aave-graphite">
              Hệ thống nghiên cứu định lượng 24/7 — dự báo ATC, tối ưu phái sinh VN30F1M và lựa chọn cổ phiếu alpha.
            </Text>
          </Animated.View>
        </View>

        {/* Feature list */}
        <View className="mb-8 gap-3">
          {features.map((f, i) => (
            <FeatureRow key={f.step} step={f.step} label={f.label} delay={300 + i * 100} />
          ))}
        </View>

        {/* CTA */}
        <View className="gap-2">
          {isWeb && canInstall
            ? (
                <>
                  <Button
                    label="Cài đặt và Bắt đầu"
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
          <Text className="mt-2 text-center text-[11px] text-aave-iron">
            Chỉ phân tích thông tin — không tự động khớp lệnh thật
          </Text>
        </View>
      </SafeAreaView>
    </View>
  );
}
