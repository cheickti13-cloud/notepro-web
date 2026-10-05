import Svg, { Circle, Path, Rect } from 'react-native-svg';

/** Logo NotePro : livre ouvert + point vert (progression). */
export function Logo({ taille = 64, inverse = false }: { taille?: number; inverse?: boolean }) {
  const fond = inverse ? '#FFFFFF' : '#0B1F3A';
  const trait = inverse ? '#0B1F3A' : '#FFFFFF';
  return (
    <Svg width={taille} height={taille} viewBox="0 0 48 48" accessibilityLabel="Logo NotePro">
      <Rect width={48} height={48} rx={14} fill={fond} />
      <Path d="M12 16c4-2 8-2 12 1 4-3 8-3 12-1v17c-4-2-8-2-12 1-4-3-8-3-12-1z" fill="none" stroke={trait} strokeWidth={2.6} strokeLinejoin="round" />
      <Path d="M24 17v17" stroke={trait} strokeWidth={2.6} />
      <Circle cx={37} cy={12} r={5} fill="#22C55E" />
    </Svg>
  );
}
