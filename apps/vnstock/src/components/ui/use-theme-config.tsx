import type { Theme } from '@react-navigation/native';
import {
  DarkTheme as _DarkTheme,
  DefaultTheme,
} from '@react-navigation/native';
import { useUniwind } from 'uniwind';

import colors from '@/components/ui/colors';

const DarkTheme: Theme = {
  ..._DarkTheme,
  colors: {
    ..._DarkTheme.colors,
    primary: colors.aave.violet,
    background: colors.aave.inkwell,
    text: colors.aave.paper,
    border: 'rgba(255, 255, 255, 0.06)',
    card: colors.aave.obsidian,
  },
};

const LightTheme: Theme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    primary: colors.aave.violet,
    background: colors.surface.canvas,
    text: colors.aave.charcoal,
    border: 'rgba(34, 29, 29, 0.06)',
    card: colors.surface.card,
  },
};

export function useThemeConfig() {
  const { theme } = useUniwind();

  if (theme === 'dark')
    return DarkTheme;

  return LightTheme;
}
