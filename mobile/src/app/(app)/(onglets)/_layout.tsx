/** Barre de navigation inférieure : Accueil, Emploi du temps, Notes, Messagerie, Profil. */
import Ionicons from '@expo/vector-icons/Ionicons';
import { Tabs } from 'expo-router';
import { Platform } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { NomIcone } from '@/components/ui';
import { useDonnees } from '@/lib/requetes';
import { useSession } from '@/lib/session';
import { police } from '@/theme/couleurs';
import { useTheme } from '@/theme/Theme';

const icone = (actif: NomIcone, inactif: NomIcone) =>
  ({ color, focused }: { color: string; focused: boolean }) => <Ionicons name={focused ? actif : inactif} size={23} color={color} />;

export default function Onglets() {
  const { c } = useTheme();
  const insets = useSafeAreaInsets();
  const { moi } = useSession();
  const famille = moi?.role === 'PARENT' || moi?.role === 'ELEVE';
  // Rafraîchissement régulier (30 s) uniquement pour la messagerie, quand l'app est ouverte
  const conv = useDonnees(['conversations'], (a) => a.conversations(), { refetchInterval: 30000 });
  const nonLus = conv.data?.filter((x) => x.non_lu).length ?? 0;

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: c.accent,
        tabBarInactiveTintColor: c.texte2,
        tabBarLabelStyle: { fontFamily: police.gras, fontSize: 10.5 },
        tabBarStyle: {
          backgroundColor: c.surface,
          borderTopColor: c.ligne,
          height: 62 + (Platform.OS === 'web' ? 8 : insets.bottom),
          paddingTop: 6,
          paddingBottom: Platform.OS === 'web' ? 8 : Math.max(insets.bottom, 8),
        },
        tabBarBadgeStyle: { backgroundColor: c.pastille, fontFamily: police.extra, fontSize: 10 },
      }}
    >
      <Tabs.Screen name="accueil" options={{ title: 'Accueil', tabBarIcon: icone('home', 'home-outline') }} />
      <Tabs.Screen
        name="emploi-du-temps"
        options={{ title: 'Emploi du temps', tabBarIcon: icone('calendar', 'calendar-outline'), href: famille ? undefined : null }}
      />
      <Tabs.Screen name="notes" options={{ title: 'Notes', tabBarIcon: icone('bar-chart', 'bar-chart-outline'), href: famille ? undefined : null }} />
      <Tabs.Screen
        name="messages"
        options={{ title: 'Messages', tabBarIcon: icone('chatbubble', 'chatbubble-outline'), tabBarBadge: nonLus || undefined }}
      />
      <Tabs.Screen name="profil" options={{ title: 'Profil', tabBarIcon: icone('person', 'person-outline') }} />
    </Tabs>
  );
}
