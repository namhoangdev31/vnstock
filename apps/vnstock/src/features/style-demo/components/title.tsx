import * as React from 'react';

import { Text, View } from '@/components/ui';

type Props = {
  text: string;
};
export function Title({ text }: Props) {
  return (
    <View className="flex-row items-center justify-center py-4 pb-2">
      <Text className="pr-2 text-2xl font-bold text-aave-paper">{text}</Text>
      <View className="h-px flex-1 bg-white/8" />
    </View>
  );
}
