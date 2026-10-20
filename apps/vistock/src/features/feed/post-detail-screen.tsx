import { Stack, useLocalSearchParams } from 'expo-router';
import * as React from 'react';

import {
  ActivityIndicator,
  FocusAwareStatusBar,
  Text,
  View,
} from '@/components/ui';
import { usePost } from './api';

export function PostDetailScreen() {
  const local = useLocalSearchParams<{ id: string }>();

  const { data, isPending, isError } = usePost({
    variables: { id: local.id },
  });

  if (isPending) {
    return (
      <View className="flex-1 justify-center bg-aave-inkwell p-4">
        <Stack.Screen options={{ title: 'Bài viết', headerBackTitle: 'Bảng Tin' }} />
        <FocusAwareStatusBar />
        <ActivityIndicator />
      </View>
    );
  }
  if (isError) {
    return (
      <View className="flex-1 justify-center bg-aave-inkwell p-4">
        <Stack.Screen options={{ title: 'Bài viết', headerBackTitle: 'Bảng Tin' }} />
        <FocusAwareStatusBar />
        <Text className="text-center text-aave-graphite">Không thể tải bài viết</Text>
      </View>
    );
  }

  return (
    <View className="flex-1 bg-aave-inkwell p-4">
      <Stack.Screen options={{ title: 'Bài viết', headerBackTitle: 'Bảng Tin' }} />
      <FocusAwareStatusBar />
      <View className="gap-3 rounded-2xl border border-white/6 bg-aave-obsidian p-5">
        <Text className="text-xl font-bold text-aave-paper">{data.title}</Text>
        <Text className="text-sm/6 text-aave-graphite">
          {data.body}
        </Text>
      </View>
    </View>
  );
}
