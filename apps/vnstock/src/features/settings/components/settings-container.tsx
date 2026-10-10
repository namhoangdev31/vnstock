import type { TxKeyPath } from '@/lib/i18n';

import * as React from 'react';
import { Text, View } from '@/components/ui';

type Props = {
  children: React.ReactNode;
  title?: TxKeyPath;
};

export function SettingsContainer({ children, title }: Props) {
  return (
    <>
      {title && <Text className="pt-4 pb-2 text-base font-semibold text-aave-paper" tx={title} />}
      <View className="rounded-xl border border-neutral-200 bg-white dark:border-white/6 dark:bg-aave-obsidian">
        {children}
      </View>
    </>
  );
}
