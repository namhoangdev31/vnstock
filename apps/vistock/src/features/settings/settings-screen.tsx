import Env from 'env';
import { useUniwind } from 'uniwind';

import {
  colors,
  FocusAwareStatusBar,
  ScrollView,
  Text,
  View,
} from '@/components/ui';
import { Github, Rate, Share, Support, Website } from '@/components/ui/icons';
import { useAuthStore as useAuth } from '@/features/auth/use-auth-store';
import { translate } from '@/lib/i18n';
import { LanguageItem } from './components/language-item';
import { SettingsContainer } from './components/settings-container';
import { SettingsItem } from './components/settings-item';
import { ThemeItem } from './components/theme-item';

function UserProfileBanner() {
  const user = useAuth.use.user();
  if (!user) {
    return null;
  }

  const providerLabel = {
    google: 'Google SSO',
    apple: 'Apple ID',
    passkey: 'Passkey',
    email: 'Email Account',
    guest: 'Guest Session',
  }[user.provider ?? 'email'];

  return (
    <View className="mb-6 rounded-2xl border border-pewter bg-frost p-4 dark:border-white/10 dark:bg-charcoal">
      <View className="flex-row items-center gap-3">
        <View className="size-11 items-center justify-center rounded-full bg-coinbase-blue">
          <Text className="text-base font-bold text-pure-white">
            {user.name ? user.name.charAt(0).toUpperCase() : 'U'}
          </Text>
        </View>
        <View className="flex-1">
          <Text className="text-base font-semibold text-midnight dark:text-pure-white">
            {user.name}
          </Text>
          <Text className="text-sm text-slate">
            {user.email}
          </Text>
        </View>
        <View className="rounded-full bg-cloud px-2.5 py-1 dark:bg-white/10">
          <Text className="text-xs font-medium text-slate dark:text-ash">
            {providerLabel}
          </Text>
        </View>
      </View>
    </View>
  );
}

export function SettingsScreen() {
  const signOut = useAuth.use.signOut();
  const { theme } = useUniwind();
  const iconColor
    = theme === 'dark' ? colors.aave.graphite : colors.aave.iron;
  return (
    <>
      <FocusAwareStatusBar />

      <ScrollView>
        <View className="flex-1 px-4 pt-16">
          <Text className="mb-4 text-xl font-bold text-aave-obsidian dark:text-aave-paper">
            {translate('settings.title')}
          </Text>
          <UserProfileBanner />
          <SettingsContainer title="settings.generale">
            <LanguageItem />
            <ThemeItem />
          </SettingsContainer>

          <SettingsContainer title="settings.about">
            <SettingsItem
              text="settings.app_name"
              value={Env.EXPO_PUBLIC_NAME}
            />
            <SettingsItem
              text="settings.version"
              value={Env.EXPO_PUBLIC_VERSION}
            />
          </SettingsContainer>

          <SettingsContainer title="settings.support_us">
            <SettingsItem
              text="settings.share"
              icon={<Share color={iconColor} />}
              onPress={() => {}}
            />
            <SettingsItem
              text="settings.rate"
              icon={<Rate color={iconColor} />}
              onPress={() => {}}
            />
            <SettingsItem
              text="settings.support"
              icon={<Support color={iconColor} />}
              onPress={() => {}}
            />
          </SettingsContainer>

          <SettingsContainer title="settings.links">
            <SettingsItem text="settings.privacy" onPress={() => {}} />
            <SettingsItem text="settings.terms" onPress={() => {}} />
            <SettingsItem
              text="settings.github"
              icon={<Github color={iconColor} />}
              onPress={() => {}}
            />
            <SettingsItem
              text="settings.website"
              icon={<Website color={iconColor} />}
              onPress={() => {}}
            />
          </SettingsContainer>

          <View className="my-8">
            <SettingsContainer>
              <SettingsItem text="settings.logout" onPress={signOut} />
            </SettingsContainer>
          </View>
        </View>
      </ScrollView>
    </>
  );
}
