import type { Post } from './api';
import { FlashList } from '@shopify/flash-list';

import * as React from 'react';
import { StyleSheet, View } from 'react-native';

import { EmptyList, FocusAwareStatusBar, Text } from '@/components/ui';
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
      <View style={styles.errorContainer}>
        <Text style={styles.errorIcon}>⚠️</Text>
        <Text style={styles.errorTitle}>Không thể tải dữ liệu</Text>
        <Text style={styles.errorSub}>Kiểm tra kết nối mạng và thử lại</Text>
      </View>
    );
  }
  return (
    <View style={styles.container}>
      <FocusAwareStatusBar />
      <FlashList
        data={data}
        renderItem={renderItem}
        keyExtractor={(_, index) => `item-${index}`}
        ListEmptyComponent={<EmptyList isLoading={isPending} />}
        contentContainerStyle={styles.listContent}
        showsVerticalScrollIndicator={false}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0B0E14',
  },
  listContent: {
    paddingTop: 8,
    paddingBottom: 16,
  },
  errorContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    backgroundColor: '#0B0E14',
    padding: 32,
  },
  errorIcon: {
    fontSize: 40,
    marginBottom: 8,
  },
  errorTitle: {
    color: '#f5f5f5',
    fontSize: 18,
    fontWeight: '700',
  },
  errorSub: {
    color: '#737373',
    fontSize: 14,
    textAlign: 'center',
  },
});
