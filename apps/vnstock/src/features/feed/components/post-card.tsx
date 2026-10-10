import type { Post } from '../api';

import { Link } from 'expo-router';
import * as React from 'react';

import { Image, Pressable, Text, View } from '@/components/ui';

const images = [
  'https://images.unsplash.com/photo-1489749798305-4fea3ae63d43?auto=format&fit=crop&w=800&q=80',
  'https://images.unsplash.com/photo-1564507004663-b6dfb3c824d5?auto=format&fit=crop&w=800&q=80',
  'https://images.unsplash.com/photo-1515386474292-47555758ef2e?auto=format&fit=crop&w=800&q=80',
  'https://plus.unsplash.com/premium_photo-1666815503002-5f07a44ac8fb?auto=format&fit=crop&w=800&q=80',
  'https://images.unsplash.com/photo-1587974928442-77dc3e0dba72?auto=format&fit=crop&w=800&q=80',
];

type Props = Post;

export function PostCard({ title, body, id }: Props) {
  const imageUri = images[id % images.length];

  return (
    <Link href={`/feed/${id}`} asChild>
      <Pressable>
        {({ pressed }) => (
          <View
            className={`mx-4 my-2 overflow-hidden rounded-2xl border border-white/6 bg-aave-obsidian ${
              pressed ? 'scale-[0.98] opacity-85' : ''
            }`}
          >
            <Image
              className="h-[180px] w-full"
              contentFit="cover"
              source={{ uri: imageUri }}
            />

            <View className="gap-2 p-4">
              <View className="flex-row gap-1.5">
                <View className="rounded-md bg-aave-violet/15 px-2 py-0.5">
                  <Text className="text-[11px] font-bold tracking-wider text-aave-violet">Phân tích</Text>
                </View>
              </View>
              <Text className="text-[17px]/6 font-bold tracking-tight text-aave-paper" numberOfLines={2}>
                {title}
              </Text>
              <Text className="text-sm leading-[21px] text-aave-graphite" numberOfLines={3}>
                {body}
              </Text>
              <Text className="text-[13px] font-semibold text-aave-violet">Đọc thêm →</Text>
            </View>
          </View>
        )}
      </Pressable>
    </Link>
  );
}
