import type { Post } from '../api';

import { Link } from 'expo-router';
import * as React from 'react';
import { StyleSheet, View } from 'react-native';

import { Image, Pressable, Text } from '@/components/ui';

const images = [
  'https://images.unsplash.com/photo-1489749798305-4fea3ae63d43?auto=format&fit=crop&w=800&q=80',
  'https://images.unsplash.com/photo-1564507004663-b6dfb3c824d5?auto=format&fit=crop&w=800&q=80',
  'https://images.unsplash.com/photo-1515386474292-47555758ef2e?auto=format&fit=crop&w=800&q=80',
  'https://plus.unsplash.com/premium_photo-1666815503002-5f07a44ac8fb?auto=format&fit=crop&w=800&q=80',
  'https://images.unsplash.com/photo-1587974928442-77dc3e0dba72?auto=format&fit=crop&w=800&q=80',
];

type Props = Post;

export function PostCard({ title, body, id }: Props) {
  // eslint-disable-next-line react-hooks/purity
  const imageUri = images[id % images.length];

  return (
    <Link href={`/feed/${id}`} asChild>
      <Pressable>
        {({ pressed }) => (
          <View style={[styles.card, pressed && styles.cardPressed]}>
            <Image
              style={styles.image}
              contentFit="cover"
              source={{ uri: imageUri }}
            />

            <View style={styles.content}>
              <View style={styles.tagRow}>
                <View style={styles.tag}>
                  <Text style={styles.tagText}>Phân tích</Text>
                </View>
              </View>
              <Text style={styles.title} numberOfLines={2}>{title}</Text>
              <Text style={styles.body} numberOfLines={3}>
                {body}
              </Text>
              <Text style={styles.readMore}>Đọc thêm →</Text>
            </View>
          </View>
        )}
      </Pressable>
    </Link>
  );
}

const styles = StyleSheet.create({
  card: {
    marginHorizontal: 16,
    marginVertical: 8,
    borderRadius: 16,
    overflow: 'hidden',
    backgroundColor: '#111827',
    borderWidth: 1,
    borderColor: '#1f2937',
  },
  cardPressed: {
    opacity: 0.85,
    transform: [{ scale: 0.98 }],
  },
  image: {
    height: 180,
    width: '100%',
  },
  content: {
    padding: 16,
    gap: 8,
  },
  tagRow: {
    flexDirection: 'row',
    gap: 6,
  },
  tag: {
    backgroundColor: 'rgba(255, 108, 0, 0.12)',
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  tagText: {
    color: '#FF8933',
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  title: {
    color: '#f5f5f5',
    fontSize: 17,
    fontWeight: '700',
    lineHeight: 24,
    letterSpacing: -0.2,
  },
  body: {
    color: '#737373',
    fontSize: 14,
    lineHeight: 21,
  },
  readMore: {
    color: '#FF6C00',
    fontSize: 13,
    fontWeight: '600',
  },
});
