/** Écran de connexion : établissement, profil, identifiant ou téléphone, mot de passe, biométrie. */
import Ionicons from '@expo/vector-icons/Ionicons';
import { Redirect, useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, Switch, Text, TextInput, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Logo } from '@/components/Logo';
import { Bouton, Champ, Feuille, T } from '@/components/ui';
import { prefs } from '@/lib/stockage';
import { useSession } from '@/lib/session';
import type { Role } from '@/lib/types';
import { police, rayon } from '@/theme/couleurs';
import { useTheme } from '@/theme/Theme';

const PROFILS: { cle: Role; titre: string; icone: 'people' | 'school' | 'easel' | 'business' }[] = [
  { cle: 'PARENT', titre: 'Parent', icone: 'people' },
  { cle: 'ELEVE', titre: 'Élève', icone: 'school' },
  { cle: 'ENSEIGNANT', titre: 'Enseignant', icone: 'easel' },
  { cle: 'ADMIN', titre: 'Admin.', icone: 'business' },
];

export default function Connexion() {
  const { c } = useTheme();
  const insets = useSafeAreaInsets();
  const router = useRouter();
  const { etab, connexion, statut, messageSession, biometrie } = useSession();
  const [role, setRole] = useState<Role>('PARENT');
  const [identifiant, setIdentifiant] = useState('');
  const [mdp, setMdp] = useState('');
  const [voir, setVoir] = useState(false);
  const [souvenir, setSouvenir] = useState(true);
  const [charge, setCharge] = useState(false);
  const [erreur, setErreur] = useState<string | null>(messageSession);
  const [oubli, setOubli] = useState(false);
  const [codeEnvoye, setCodeEnvoye] = useState(false);
  const demo = etab.api === 'demo';

  useEffect(() => {
    prefs.lire<string>('dernierIdentifiant', '').then((v) => v && setIdentifiant(v));
    prefs.lire<Role>('dernierRole', 'PARENT').then(setRole);
  }, []);

  if (statut === 'connecte') return <Redirect href="/accueil" />;

  async function valider() {
    setErreur(null);
    if (!identifiant.trim() || !mdp) {
      setErreur('Saisissez votre identifiant (ou numéro) et votre mot de passe.');
      return;
    }
    setCharge(true);
    try {
      await connexion(identifiant, mdp, souvenir, role);
      await prefs.ecrire('dernierIdentifiant', souvenir ? identifiant : '');
      await prefs.ecrire('dernierRole', role);
      router.replace('/accueil');
    } catch (e: any) {
      setErreur(e?.message ?? 'Connexion impossible.');
    } finally {
      setCharge(false);
    }
  }

  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: c.fond }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={{ padding: 24, paddingTop: insets.top + 24, paddingBottom: insets.bottom + 32, gap: 20 }} keyboardShouldPersistTaps="handled">
        <View style={{ alignItems: 'center', gap: 12 }}>
          <Logo taille={64} />
          <T v="titre" style={{ textAlign: 'center' }} accessibilityRole="header">Bienvenue sur NotePro</T>
          <T discret style={{ textAlign: 'center', fontSize: 15 }}>Votre école, toujours avec vous</T>
        </View>

        <Pressable
          onPress={() => router.push('/etablissement')}
          accessibilityRole="button"
          accessibilityLabel={`Établissement : ${etab.nom}. Changer d'établissement`}
          style={{ flexDirection: 'row', alignItems: 'center', gap: 12, padding: 12, borderRadius: rayon.m, backgroundColor: c.surface, borderWidth: 1, borderColor: c.ligne }}
        >
          <View style={{ width: 40, height: 40, borderRadius: 12, backgroundColor: c.surface2, alignItems: 'center', justifyContent: 'center' }}>
            <Ionicons name="business-outline" size={20} color={c.accent} />
          </View>
          <View style={{ flex: 1 }}>
            <T v="gras" numberOfLines={1}>{etab.nom}</T>
            <T v="petit" discret numberOfLines={1}>{etab.ville}</T>
          </View>
          <Text style={{ color: c.accent, fontFamily: police.gras, fontSize: 13 }}>Changer</Text>
        </Pressable>

        <View style={{ gap: 8 }}>
          <T v="petit" style={{ fontFamily: police.gras }}>Je me connecte en tant que</T>
          <View style={{ flexDirection: 'row', gap: 6 }} accessibilityRole="radiogroup">
            {PROFILS.map((p) => {
              const actif = role === p.cle;
              return (
                <Pressable
                  key={p.cle}
                  onPress={() => setRole(p.cle)}
                  accessibilityRole="radio"
                  accessibilityState={{ checked: actif }}
                  style={{ flex: 1, height: 64, borderRadius: rayon.m, borderWidth: 1, borderColor: actif ? c.primaire : c.ligne, backgroundColor: actif ? c.primaire : c.surface, alignItems: 'center', justifyContent: 'center', gap: 4 }}
                >
                  <Ionicons name={p.icone} size={18} color={actif ? c.surPrimaire : c.texte} />
                  <Text style={{ color: actif ? c.surPrimaire : c.texte, fontFamily: police.gras, fontSize: 12 }}>{p.titre}</Text>
                </Pressable>
              );
            })}
          </View>
        </View>

        <Champ
          libelle="Identifiant ou numéro de téléphone"
          value={identifiant}
          onChangeText={setIdentifiant}
          autoCapitalize="none"
          autoCorrect={false}
          autoComplete="username"
          textContentType="username"
          placeholder={demo ? 'Démo : saisissez n’importe quel identifiant' : 'ex. m.kone ou +225 07 12 34 56 78'}
          returnKeyType="next"
        />
        <View style={{ gap: 6 }}>
          <T v="petit" style={{ fontFamily: police.gras }}>Mot de passe</T>
          <View>
            <TextInput
              value={mdp}
              onChangeText={setMdp}
              secureTextEntry={!voir}
              autoComplete="password"
              textContentType="password"
              accessibilityLabel="Mot de passe"
              placeholder={demo ? 'Démo : n’importe quel mot de passe' : ''}
              placeholderTextColor={c.texte2}
              onSubmitEditing={valider}
              returnKeyType="go"
              style={{ height: 52, borderRadius: rayon.m, borderWidth: 1.5, borderColor: c.ligne, backgroundColor: c.surface, color: c.texte, paddingHorizontal: 14, paddingRight: 56, fontFamily: police.moyen, fontSize: 15 }}
            />
            <Pressable onPress={() => setVoir(!voir)} accessibilityRole="button" accessibilityLabel={voir ? 'Masquer le mot de passe' : 'Afficher le mot de passe'} style={{ position: 'absolute', right: 4, top: 4, width: 44, height: 44, alignItems: 'center', justifyContent: 'center' }}>
              <Ionicons name={voir ? 'eye-off-outline' : 'eye-outline'} size={22} color={c.texte2} />
            </Pressable>
          </View>
        </View>

        <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
          <Pressable onPress={() => setSouvenir(!souvenir)} style={{ flexDirection: 'row', alignItems: 'center', gap: 10, minHeight: 44 }} accessibilityRole="switch" accessibilityState={{ checked: souvenir }}>
            <Switch value={souvenir} onValueChange={setSouvenir} trackColor={{ false: c.ligne, true: c.ok }} thumbColor="#FFFFFF" accessibilityLabel="Se souvenir de moi" />
            <T v="gras">Se souvenir de moi</T>
          </Pressable>
          <Pressable onPress={() => { setCodeEnvoye(false); setOubli(true); }} hitSlop={10} accessibilityRole="button">
            <Text style={{ color: c.accent, fontFamily: police.gras, fontSize: 13.5 }}>Mot de passe oublié ?</Text>
          </Pressable>
        </View>

        {erreur ? (
          <View accessibilityRole="alert" style={{ backgroundColor: c.dangerDoux, borderRadius: rayon.m, padding: 12, flexDirection: 'row', gap: 8 }}>
            <Ionicons name="alert-circle" size={18} color={c.danger} />
            <T v="petit" couleur={c.danger} style={{ flex: 1 }}>{erreur}</T>
          </View>
        ) : null}

        <Bouton titre="Se connecter" onPress={valider} charge={charge} />

        {biometrie.dispo && !biometrie.active ? (
          <View style={{ flexDirection: 'row', gap: 8, alignItems: 'center', justifyContent: 'center' }}>
            <Ionicons name="finger-print" size={18} color={c.texte2} />
            <T v="petit" discret style={{ textAlign: 'center', flexShrink: 1 }}>Après cette connexion, activez l’empreinte ou Face ID dans votre profil pour ouvrir l’app en un geste.</T>
          </View>
        ) : null}

        <T v="petit" discret style={{ textAlign: 'center' }}>Vos données scolaires sont chiffrées et protégées.</T>
      </ScrollView>

      <Feuille visible={oubli} onClose={() => setOubli(false)} titre={codeEnvoye ? 'Demande envoyée' : 'Mot de passe oublié'}>
        {codeEnvoye ? (
          <>
            <T discret>Si ce numéro correspond à un compte, l’administration de l’établissement vous enverra un nouveau mot de passe temporaire par SMS.</T>
            <Bouton titre="J'ai compris" onPress={() => setOubli(false)} />
          </>
        ) : (
          <>
            <T discret>Saisissez le numéro de téléphone enregistré auprès de l’établissement.</T>
            <Champ libelle="Numéro de téléphone" keyboardType="phone-pad" placeholder="+225 07 00 00 00 00" />
            <Bouton titre="Envoyer la demande" onPress={() => setCodeEnvoye(true)} />
            <Bouton titre="Annuler" variante="secondaire" onPress={() => setOubli(false)} />
          </>
        )}
      </Feuille>
    </KeyboardAvoidingView>
  );
}
