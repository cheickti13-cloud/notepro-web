/** Espace connecté : redirige vers la connexion si la session n'est pas ouverte. */
import { Redirect, Stack } from 'expo-router';

import { useSession } from '@/lib/session';
import { useTheme } from '@/theme/Theme';

export default function EspaceConnecte() {
  const { statut, moi } = useSession();
  const { c } = useTheme();
  if (statut !== 'connecte' || !moi) return <Redirect href="/" />;
  // Premier accès : changement du mot de passe initial obligatoire
  if (moi.doit_changer_mdp) return <Redirect href="/mot-de-passe" />;
  return <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: c.fond }, animation: 'slide_from_right' }} />;
}
