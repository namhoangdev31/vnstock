import type { SvgProps } from 'react-native-svg';
import Svg, { Path } from 'react-native-svg';

export function Passkey({
  size = 20,
  color = '#000000',
  ...props
}: SvgProps & { size?: number; color?: string }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill={color} {...props}>
      <Path d="M12 2a5 5 0 1 0 5 5 5 5 0 0 0-5-5zm0 8a3 3 0 1 1 3-3 3 3 0 0 1-3 3zm9 11v-1a7 7 0 0 0-7-7h-4a7 7 0 0 0-7 7v1h2v-1a5 5 0 0 1 5-5h4a5 5 0 0 1 5 5v1z" />
      <Path d="M19 12h-2v2h2v2h2v-2h2v-2h-2v-2h-2z" />
    </Svg>
  );
}
