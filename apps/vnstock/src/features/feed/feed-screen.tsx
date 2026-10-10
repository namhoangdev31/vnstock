import type { Post } from './api';
import { FlashList } from '@shopify/flash-list';

import * as React from 'react';

import { EmptyList, FocusAwareStatusBar, Text, View } from '@/components/ui';
import { usePosts } from './api';
import { PostCard } from './components/post-card';

export function FeedScreen() {
  const { data, isPending, isError } = usePosts();
  const renderItem = React.useCallback(
    ({ item }: { item: Post }) => <PostCard {...item} />,
    [],
  );

  if (isError) {
    return (
      <View className="flex-1 items-center justify-center gap-2 bg-aave-inkwell p-8">
        <Text className="text-lg font-bold text-aave-paper">Không thể tải dữ liệu</Text>
        <Text className="text-center text-sm text-aave-graphite">Kiểm tra kết nối mạng và thử lại</Text>
      </View>
    );
  }
  return (
    <View className="flex-1 bg-aave-inkwell">
      <FocusAwareStatusBar />
      <FlashList
        data={data}
        renderItem={renderItem}
        keyExtractor={(_, index) => `item-${index}`}
        ListEmptyComponent={<EmptyList isLoading={isPending} />}
        contentContainerStyle={{ paddingTop: 8, paddingBottom: 16 }}
        showsVerticalScrollIndicator={false}
      />
    </View>
  );
}
