/** Thème clair / sombre : suit le téléphone par défaut, modifiable dans le profil. */
import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from 'react';
import { useColorScheme } from 'react-native';

import { prefs } from '@/lib/stockage';

import { clair, Couleurs, sombre } from './couleurs';

export type ModeTheme = 'systeme' | 'clair' | 'sombre';

interface ValeurTheme {
  c: Couleurs;
  mode: ModeTheme;
  setMode: (m: ModeTheme) => void;
}

const Ctx = createContext<ValeurTheme>({ c: clair, mode: 'systeme', setMode: () => {} });

export function ThemeProvider({ children }: { children: ReactNode }) {
  const systeme = useColorScheme();
  const [mode, setModeState] = useState<ModeTheme>('systeme');

  useEffect(() => {
    prefs.lire<ModeTheme>('theme', 'systeme').then(setModeState);
  }, []);

  const valeur = useMemo<ValeurTheme>(() => {
    const estSombre = mode === 'sombre' || (mode === 'systeme' && systeme === 'dark');
    return {
      c: estSombre ? sombre : clair,
      mode,
      setMode: (m) => {
        setModeState(m);
        prefs.ecrire('theme', m);
      },
    };
  }, [mode, systeme]);

  return <Ctx.Provider value={valeur}>{children}</Ctx.Provider>;
}

export const useTheme = () => useContext(Ctx);
