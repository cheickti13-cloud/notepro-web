/** Palette NotePro : bleu nuit, bleu clair, blanc, vert pour le positif. Contrastes ≥ 4,5:1 sur le fond. */
export const clair = {
  sombre: false,
  fond: '#F3F6FB',
  surface: '#FFFFFF',
  surface2: '#E9EFF8',
  texte: '#0B1F3A',
  texte2: '#51627D',
  ligne: '#DCE4EF',
  primaire: '#0B1F3A',
  surPrimaire: '#FFFFFF',
  hero: '#0B1F3A',
  accent: '#1D5BD8',
  accentDoux: '#E3ECFD',
  ok: '#13803F',
  okDoux: '#E2F4E9',
  alerte: '#A8520A',
  alerteDoux: '#FDF0DF',
  danger: '#B42318',
  dangerDoux: '#FDE7E5',
  pastille: '#D92D20',
  ombre: '#0B1F3A',
};

export type Couleurs = typeof clair;

export const sombre: Couleurs = {
  sombre: true,
  fond: '#06111F',
  surface: '#0E1D31',
  surface2: '#162A47',
  texte: '#E8F0FB',
  texte2: '#9DB0CA',
  ligne: '#22385A',
  primaire: '#7FB0FF',
  surPrimaire: '#06111F',
  hero: '#133A73',
  accent: '#8DB8FF',
  accentDoux: '#17325C',
  ok: '#5BD98B',
  okDoux: '#0E3322',
  alerte: '#F5B94A',
  alerteDoux: '#3A2A0C',
  danger: '#FF8A80',
  dangerDoux: '#3D1614',
  pastille: '#D92D20',
  ombre: '#000000',
};

export const police = {
  normal: 'PlusJakartaSans_400Regular',
  moyen: 'PlusJakartaSans_500Medium',
  semi: 'PlusJakartaSans_600SemiBold',
  gras: 'PlusJakartaSans_700Bold',
  extra: 'PlusJakartaSans_800ExtraBold',
};

export const rayon = { s: 10, m: 14, l: 18, xl: 26 };
