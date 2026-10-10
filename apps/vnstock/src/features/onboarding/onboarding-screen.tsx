import type { ImageSource } from 'expo-image';
import type { NativeScrollEvent, NativeSyntheticEvent } from 'react-native';
import { useRouter } from 'expo-router';
import * as React from 'react';
import { Platform, useWindowDimensions } from 'react-native';

import {
  FocusAwareStatusBar,
  Image,
  Pressable,
  SafeAreaView,
  ScrollView,
  Text,
  View,
} from '@/components/ui';
import { useAuthStore } from '@/features/auth/use-auth-store';
import { useIsFirstTime } from '@/lib/hooks';
import { usePWA } from '@/lib/hooks/use-pwa';

type OnboardingSlide = {
  id: string;
  type: 'welcome' | 'feature';
  title: string;
  subtitle?: string;
  image?: ImageSource | number | string;
};

const SLIDES: OnboardingSlide[] = [
  {
    id: 'welcome',
    type: 'welcome',
    title: 'Welcome to\nViStock',
    subtitle: 'Nền tảng nghiên cứu định lượng & dự báo thị trường chứng khoán chuyên sâu.',
  },
  {
    id: 'derivatives',
    type: 'feature',
    title: 'Giao dịch phái sinh &\ncổ phiếu thông minh',
    subtitle: 'Nắm bắt nhịp đập VN30F1M và danh mục cổ phiếu tối ưu với chiến lược định lượng chuyên sâu.',
    image: require('../../../assets/onboarding/card-rewards.png'),
  },
  {
    id: 'security',
    type: 'feature',
    title: 'Quản trị rủi ro &\nbảo mật chuẩn tổ chức',
    subtitle: 'Bảo vệ danh mục đầu tư với hệ thống quản trị rủi ro đa tầng và cơ chế giả lập Paper Trading an toàn.',
    image: require('../../../assets/onboarding/secure-vault.png'),
  },
  {
    id: 'atc',
    type: 'feature',
    title: 'Dự báo phiên ATC &\nxu hướng T+1',
    subtitle: 'Mô hình xác suất đa kịch bản giúp dự phóng chính xác bước giá đóng cửa và cơ hội phiên kế tiếp.',
    image: require('../../../assets/onboarding/atc-forecasting.png'),
  },
  {
    id: 'tri-engine',
    type: 'feature',
    title: 'Sức mạnh từ\nTri-Engine Analytics',
    subtitle: 'Đồng bộ liên tục giữa hành vi giá, dòng vốn tổ chức và mô hình máy học định lượng 24/7.',
    image: require('../../../assets/onboarding/tri-engine.png'),
  },
];

function OnboardingHeader({
  activeIndex,
  onBack,
  onSignIn,
}: {
  activeIndex: number;
  onBack: () => void;
  onSignIn: () => void;
}) {
  return (
    <View className="h-14 w-full flex-row items-center justify-between px-6">
      <View className="min-w-20 items-start">
        {activeIndex > 0 && (
          <Pressable
            hitSlop={8}
            className="h-10 justify-center py-2 active:opacity-60"
            onPress={onBack}
          >
            <Text className="text-sm font-medium text-slate">Quay lại</Text>
          </Pressable>
        )}
      </View>

      <View className="items-center justify-center">
        {activeIndex > 0 && (
          <Image
            source={require('../../../assets/vistock-logo-blue.png')}
            className="h-7 w-8"
            contentFit="contain"
            placeholder={null}
          />
        )}
      </View>

      <View className="min-w-20 items-end">
        <Pressable
          hitSlop={8}
          className="py-2 active:opacity-70"
          onPress={onSignIn}
        >
          <Text className="text-base font-semibold text-coinbase-blue">
            Sign in
          </Text>
        </Pressable>
      </View>
    </View>
  );
}

function WelcomeSlide({ slide }: { slide: OnboardingSlide }) {
  return (
    <View className="flex-1 justify-center pb-8">
      <Image
        source={require('../../../assets/vistock-logo-blue.png')}
        className="mb-8 h-32 w-36"
        contentFit="contain"
        placeholder={null}
      />
      <Text className="text-[40px] leading-[46px] font-bold tracking-tight text-midnight">
        {slide.title}
      </Text>
      {slide.subtitle && (
        <Text className="mt-4 text-base/6 text-slate">
          {slide.subtitle}
        </Text>
      )}
    </View>
  );
}

function FeatureSlide({ slide }: { slide: OnboardingSlide }) {
  return (
    <View className="flex-1 items-center justify-center pb-8">
      <View className="mb-8 h-60 w-full items-center justify-center">
        <Image
          source={slide.image}
          className="h-56 w-72"
          contentFit="contain"
          placeholder={null}
        />
      </View>
      <Text className="text-center text-heading-lg/8 font-bold tracking-tight text-midnight">
        {slide.title}
      </Text>
      {slide.subtitle && (
        <Text className="mt-3 px-4 text-center text-body/6 text-slate">
          {slide.subtitle}
        </Text>
      )}
    </View>
  );
}

function PaginationDots({
  activeIndex,
  onSelect,
}: {
  activeIndex: number;
  onSelect: (index: number) => void;
}) {
  return (
    <View className="flex-row items-center justify-center gap-2 py-4">
      {SLIDES.map((slide, index) => {
        const isActive = activeIndex === index;
        return (
          <Pressable
            key={slide.id}
            hitSlop={8}
            onPress={() => onSelect(index)}
            className={`size-2 rounded-full ${isActive ? 'bg-midnight' : 'bg-pewter'}`}
          />
        );
      })}
    </View>
  );
}

function OnboardingActions({
  onCreateAccount,
  onBrowseAssets,
  canInstall,
  installPWA,
  isWeb,
}: {
  onCreateAccount: () => void;
  onBrowseAssets: () => void;
  canInstall: boolean;
  installPWA: () => Promise<boolean> | Promise<void>;
  isWeb: boolean;
}) {
  return (
    <View className="w-full gap-2 px-6 pb-2">
      <Pressable
        testID="create-account-btn"
        className="h-10 w-full items-center justify-center rounded-full bg-coinbase-blue active:opacity-85"
        onPress={onCreateAccount}
      >
        <Text className="text-[17px] font-semibold text-pure-white">
          Create free account
        </Text>
      </Pressable>

      <Pressable
        testID="browse-assets-btn"
        className="h-10 w-full items-center justify-center active:opacity-70"
        onPress={onBrowseAssets}
      >
        <Text className="text-[17px] font-semibold text-coinbase-blue">
          Browse assets
        </Text>
      </Pressable>

      {isWeb && canInstall && (
        <Pressable
          className="mt-1 h-10 w-full items-center justify-center rounded-full border border-pewter bg-frost active:opacity-80"
          onPress={installPWA}
        >
          <Text className="text-xs font-medium text-slate">
            Cài đặt ứng dụng PWA
          </Text>
        </Pressable>
      )}

      <Text className="mt-1 text-center text-[11px] text-ash">
        Nghiên cứu định lượng và mô phỏng — Không phải tư vấn đầu tư
      </Text>
    </View>
  );
}

function useOnboardingCarousel(slideWidth: number) {
  const [activeIndex, setActiveIndex] = React.useState(0);
  const scrollViewRef = React.useRef<ScrollView>(null);

  const handleScroll = React.useCallback(
    (event: NativeSyntheticEvent<NativeScrollEvent>) => {
      const offsetX = event.nativeEvent.contentOffset.x;
      const index = Math.round(offsetX / slideWidth);
      if (index >= 0 && index < SLIDES.length && index !== activeIndex) {
        setActiveIndex(index);
      }
    },
    [slideWidth, activeIndex],
  );

  const scrollToSlide = React.useCallback(
    (index: number) => {
      scrollViewRef.current?.scrollTo({
        x: index * slideWidth,
        animated: true,
      });
      setActiveIndex(index);
    },
    [slideWidth],
  );

  return { activeIndex, scrollViewRef, handleScroll, scrollToSlide };
}

export function OnboardingScreen() {
  const [_, setIsFirstTime] = useIsFirstTime();
  const { canInstall, installPWA } = usePWA();
  const status = useAuthStore.use.status();
  const signIn = useAuthStore.use.signIn();
  const router = useRouter();
  const isWeb = Platform.OS === 'web';
  const { width } = useWindowDimensions();

  const slideWidth = React.useMemo(() => Math.min(width, 480), [width]);
  const { activeIndex, scrollViewRef, handleScroll, scrollToSlide } = useOnboardingCarousel(slideWidth);

  React.useEffect(() => {
    if (status === 'signIn') {
      router.replace('/(app)');
    }
  }, [status, router]);

  const handleStartLogin = React.useCallback(
    (mode: 'signIn' | 'signUp' = 'signIn') => {
      setIsFirstTime(false);
      router.replace({ pathname: '/login', params: { mode } });
    },
    [setIsFirstTime, router],
  );

  const handleBrowseAssets = React.useCallback(() => {
    setIsFirstTime(false);
    signIn({ access: 'guest-preview-token', refresh: 'guest-preview-token' });
    router.replace('/(app)');
  }, [setIsFirstTime, router, signIn]);

  return (
    <View className="flex-1 bg-pure-white">
      <FocusAwareStatusBar />
      <SafeAreaView className="flex-1" edges={['top', 'bottom']}>
        <OnboardingHeader
          activeIndex={activeIndex}
          onBack={() => scrollToSlide(activeIndex - 1)}
          onSignIn={() => handleStartLogin('signIn')}
        />

        <View className="flex-1">
          <ScrollView
            ref={scrollViewRef}
            horizontal
            pagingEnabled
            showsHorizontalScrollIndicator={false}
            onScroll={handleScroll}
            scrollEventThrottle={16}
            className="flex-1"
          >
            {SLIDES.map(slide => (
              <View
                key={slide.id}
                style={{ width: slideWidth }}
                className="flex-1 justify-center px-6"
              >
                {slide.type === 'welcome'
                  ? (
                      <WelcomeSlide slide={slide} />
                    )
                  : (
                      <FeatureSlide slide={slide} />
                    )}
              </View>
            ))}
          </ScrollView>
        </View>

        <PaginationDots
          activeIndex={activeIndex}
          onSelect={scrollToSlide}
        />

        <OnboardingActions
          onCreateAccount={() => handleStartLogin('signUp')}
          onBrowseAssets={handleBrowseAssets}
          canInstall={canInstall}
          installPWA={installPWA}
          isWeb={isWeb}
        />
      </SafeAreaView>
    </View>
  );
}
