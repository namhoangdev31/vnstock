import * as React from 'react';
import { Text, View } from '@/components/ui';
import colors from '@/components/ui/colors';

import { Title } from './title';

type ColorName = keyof typeof colors;

export function Colors() {
  return (
    <>
      <Title text="Colors" />
      {(Object.keys(colors) as ColorName[]).map(name => (
        <Color name={name} key={name} />
      ))}
    </>
  );
}

function Color({ name }: { name: ColorName }) {
  if (typeof colors[name] === 'string')
    return null;
  return (
    <View className="pt-2">
      <Text className="font-medium text-aave-paper">{name.toUpperCase()}</Text>
      <View className="flex-row flex-wrap content-between justify-around">
        {Object.entries(colors[name]).map(([key, value]) => {
          return (
            <ColorCard
              key={`${name}-${key}`}
              value={key}
              color={value}
            />
          );
        })}
      </View>
    </View>
  );
}

function ColorCard({ color, value }: { value: string; color: string }) {
  return (
    <View className="m-1 min-w-[70px] flex-1">
      <View
        className="h-14 w-full rounded-md border border-white/8"
        style={{ backgroundColor: color }}
      />
      <Text className="mt-1 text-xs text-aave-graphite">{value}</Text>
    </View>
  );
}
