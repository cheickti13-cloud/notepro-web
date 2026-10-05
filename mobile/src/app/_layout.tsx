/** Racine de l'application : polices, thème, cache, session, navigation. */
import {
  PlusJakartaSans_400Regular,
  PlusJakartaSans_500Medium,
  PlusJakartaSans_600SemiBold,
  PlusJakartaSans_700Bold,
  PlusJakartaSans_800ExtraBold,
  useFonts,
} from '@expo-google-fonts/plus-jakarta-sans';
import * as Notifications from 'expo-notifications';
import { Stack, useRouter } from 'expo-router';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { useEffect } from 'react';
import { Platform } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { ToastProvider } from '@/components/ui';
import { routePourLien } from '@/lib/liens';
import { queryClient, RequetesProvider } from '@/lib/requetes';
import { SessionProvider } from '@/lib/session';
import { ThemeProvider, useTheme } from '@/theme/Theme';

SplashScreen.preventAutoHideAsync().catch(() => undefined);

function Navigation() {
  const { c } = useTheme();
  const router = useRouter();

  // Toucher une notification push ouvre l'écran correspondant ; à la réception, on rafraîchit les données
  useEffect(() => {
    if (Platform.OS === 'web') return;
    const recue = Notifications.addNotificationReceivedListener(() => queryClient.invalidateQueries());
    const touchee = Notifications.addNotificationResponseReceivedListener((r) => {
      const lien = (r.notification.request.content.data as any)?.lien ?? '';
      router.push(routePourLien(lien) as any);
    });
    return () => {
      recue.remove();
      touchee.remove();
    };
  }, [router]);

  return (
    <>
      <StatusBar style={c.sombre ? 'light' : 'dark'} />
      <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: c.fond }, animation: 'slide_from_right' }} />
    </>
  );
}

export default function RootLayout() {
  const [polices] = useFonts({
    PlusJakartaSans_400Regular,
    PlusJakartaSans_500Medium,
    PlusJakartaSans_600SemiBold,
    PlusJakartaSans_700Bold,
    PlusJakartaSans_800ExtraBold,
  });

  useEffect(() => {
    if (polices) SplashScreen.hideAsync().catch(() => undefined);
  }, [polices]);

  if (!polices) return null;

  return (
    <SafeAreaProvider>
      <ThemeProvider>
        <RequetesProvider>
          <SessionProvider>
            <ToastProvider>
              <Navigation />
            </ToastProvider>
          </SessionProvider>
        </RequetesProvider>
      </ThemeProvider>
    </SafeAreaProvider>
  );
}
