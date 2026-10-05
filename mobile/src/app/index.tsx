/** Écran de démarrage (splash) : oriente vers la connexion, le verrouillage ou l'accueil. */
import Ionicons from '@expo/vector-icons/Ionicons';
import { Redirect } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Animated, Pressable, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Logo } from '@/components/Logo';
import { useSession } from '@/lib/session';
import { police } from '@/theme/couleurs';

export default function Demarrage() {
  const { statut, deverrouiller, deconnexion } = useSession();
  const insets = useSafeAreaInsets();
  const echelle = useRef(new Animated.Value(0.85)).current;
  const [echec, setEchec] = useState(false);

  useEffect(() => {
    Animated.spring(echelle, { toValue: 1, useNativeDriver: true, friction: 6 }).start();
  }, [echelle]);

  useEffect(() => {
    if (statut === 'verrouille') deverrouiller().then((ok) => setEchec(!ok));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statut]);

  if (statut === 'deconnecte') return <Redirect href="/connexion" />;
  if (statut === 'connecte') return <Redirect href="/accueil" />;

  return (
    <View style={{ flex: 1, backgroundColor: '#0B1F3A', alignItems: 'center', justifyContent: 'center', paddingBottom: insets.bottom }}>
      <Animated.View style={{ transform: [{ scale: echelle }], alignItems: 'center', gap: 18 }}>
        <Logo taille={96} inverse />
        <Text style={{ color: '#FFFFFF', fontFamily: police.extra, fontSize: 36, letterSpacing: -0.6 }}>
          Note<Text style={{ color: '#7FB0FF' }}>Pro</Text>
        </Text>
        <Text style={{ color: '#C9D7EE', fontFamily: police.moyen, fontSize: 16 }}>Votre école, toujours avec vous</Text>
      </Animated.View>
      <View style={{ position: 'absolute', bottom: 60 + insets.bottom, alignItems: 'center', gap: 14, paddingHorizontal: 32, alignSelf: 'stretch' }}>
        {statut === 'verrouille' && echec ? (
          <>
            <Pressable
              onPress={() => deverrouiller().then((ok) => setEchec(!ok))}
              accessibilityRole="button"
              style={{ height: 54, alignSelf: 'stretch', borderRadius: 16, backgroundColor: '#FFFFFF', flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center' }}
            >
              <Ionicons name="finger-print" size={22} color="#0B1F3A" />
              <Text style={{ color: '#0B1F3A', fontFamily: police.gras, fontSize: 15 }}>Déverrouiller</Text>
            </Pressable>
            <Pressable onPress={deconnexion} accessibilityRole="button" hitSlop={10}>
              <Text style={{ color: '#C9D7EE', fontFamily: police.semi }}>Se connecter avec le mot de passe</Text>
            </Pressable>
          </>
        ) : (
          <ActivityIndicator color="#7FB0FF" accessibilityLabel="Chargement" />
        )}
      </View>
    </View>
  );
}
