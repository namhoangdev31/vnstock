import type { BottomSheetModal } from '@gorhom/bottom-sheet';
import type { PressableProps } from 'react-native';
import type { SvgProps } from 'react-native-svg';
import {
  BottomSheetFlatList,

} from '@gorhom/bottom-sheet';
import { FlashList } from '@shopify/flash-list';
import * as React from 'react';
import { Platform, Pressable, View } from 'react-native';
import Svg, { Path } from 'react-native-svg';
import { tv } from 'tailwind-variants';

import { useUniwind } from 'uniwind';
import colors from '@/components/ui/colors';

import { CaretDown } from '@/components/ui/icons';
import { Modal, useModal } from './modal';
import { Text } from './text';

const selectTv = tv({
  slots: {
    container: 'mb-4',
    label: 'mb-1 text-sm font-medium text-aave-graphite dark:text-aave-graphite',
    input:
      'mt-0 flex-row items-center justify-center rounded-xl border border-neutral-300 bg-neutral-100 p-3 dark:border-white/8 dark:bg-aave-obsidian',
    inputValue: 'text-aave-obsidian dark:text-aave-paper',
  },

  variants: {
    focused: {
      true: {
        input: 'border-aave-violet dark:border-aave-violet',
      },
    },
    error: {
      true: {
        input: 'border-tv-bear dark:border-tv-bear',
        label: 'text-tv-bear dark:text-tv-bear',
        inputValue: 'text-tv-bear',
      },
    },
    disabled: {
      true: {
        input: 'bg-neutral-200 opacity-60 dark:bg-aave-obsidian/50',
      },
    },
  },
  defaultVariants: {
    error: false,
    disabled: false,
  },
});

const List = Platform.OS === 'web' ? FlashList : BottomSheetFlatList;

export type OptionType = { label: string; value: string | number };

type OptionsProps = {
  options: OptionType[];
  onSelect: (option: OptionType) => void;
  value?: string | number;
  testID?: string;
};

function keyExtractor(item: OptionType) {
  return `select-item-${item.value}`;
}

export function Options({ ref, options, onSelect, value, testID }: OptionsProps & { ref?: React.RefObject<BottomSheetModal | null> }) {
  const height = options.length * 70 + 100;
  const snapPoints = React.useMemo(() => [height], [height]);
  const { theme } = useUniwind();
  const isDark = theme === 'dark';

  const renderSelectItem = React.useCallback(
    ({ item }: { item: OptionType }) => (
      <Option
        key={`select-item-${item.value}`}
        label={item.label}
        selected={value === item.value}
        onPress={() => onSelect(item)}
        testID={testID ? `${testID}-item-${item.value}` : undefined}
      />
    ),
    [onSelect, value, testID],
  );

  return (
    <Modal
      ref={ref}
      index={0}
      snapPoints={snapPoints}
      backgroundStyle={{
        backgroundColor: isDark ? colors.aave.obsidian : colors.surface.canvas,
      }}
    >
      <List
        data={options}
        keyExtractor={keyExtractor}
        renderItem={renderSelectItem}
        testID={testID ? `${testID}-modal` : undefined}
        estimatedItemSize={52}
      />
    </Modal>
  );
}

const Option = React.memo(
  ({
    label,
    selected = false,
    ...props
  }: PressableProps & {
    selected?: boolean;
    label: string;
  }) => {
    return (
      <Pressable
        className="flex-row items-center border-b border-neutral-200 bg-white p-3 dark:border-white/6 dark:bg-aave-obsidian"
        {...props}
      >
        <Text className="flex-1 text-aave-obsidian dark:text-aave-paper">{label}</Text>
        {selected && <Check />}
      </Pressable>
    );
  },
);

export type SelectProps = {
  value?: string | number;
  label?: string;
  disabled?: boolean;
  error?: string;
  options?: OptionType[];
  onSelect?: (value: string | number) => void;
  placeholder?: string;
  testID?: string;
};

export function Select(props: SelectProps) {
  const {
    label,
    value,
    error,
    options = [],
    placeholder = 'select...',
    disabled = false,
    onSelect,
    testID,
  } = props;
  const modal = useModal();

  const onSelectOption = React.useCallback(
    (option: OptionType) => {
      onSelect?.(option.value);
      modal.dismiss();
    },
    [modal, onSelect],
  );

  const styles = React.useMemo(
    () =>
      selectTv({
        error: Boolean(error),
        disabled,
      }),
    [error, disabled],
  );

  const textValue = React.useMemo(
    () =>
      value !== undefined
        ? (options?.filter(t => t.value === value)?.[0]?.label ?? placeholder)
        : placeholder,
    [value, options, placeholder],
  );

  return (
    <>
      <View className={styles.container()}>
        {label && (
          <Text
            testID={testID ? `${testID}-label` : undefined}
            className={styles.label()}
          >
            {label}
          </Text>
        )}
        <Pressable
          className={styles.input()}
          disabled={disabled}
          onPress={modal.present}
          testID={testID ? `${testID}-trigger` : undefined}
        >
          <View className="flex-1">
            <Text className={styles.inputValue()}>{textValue}</Text>
          </View>
          <CaretDown />
        </Pressable>
        {error && (
          <Text
            testID={`${testID}-error`}
            className="text-sm text-danger-300 dark:text-danger-600"
          >
            {error}
          </Text>
        )}
      </View>
      <Options
        testID={testID}
        ref={modal.ref}
        options={options}
        onSelect={onSelectOption}
      />
    </>
  );
}

function Check({ ...props }: SvgProps) {
  return (
    <Svg
      width={25}
      height={24}
      fill="none"
      viewBox="0 0 25 24"
      {...props}
      className="stroke-black dark:stroke-white"
    >
      <Path
        d="m20.256 6.75-10.5 10.5L4.506 12"
        strokeWidth={2.438}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </Svg>
  );
}
