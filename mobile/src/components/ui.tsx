/**
 * Composants d'interface communs à tous les écrans (cohérence visuelle).
 * Cibles tactiles ≥ 44 pt, libellés d'accessibilité, mode sombre automatique.
 */
import Ionicons from '@expo/vector-icons/Ionicons';
import * as Haptics from 'expo-haptics';
import { useRouter } from 'expo-router';
import { ComponentProps, createContext, ReactNode, useCallback, useContext, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Animated,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleProp,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  TextInputProps,
  TextStyle,
  View,
  ViewStyle,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useEnLigne } from '@/lib/requetes';
import { police, rayon } from '@/theme/couleurs';
import { useTheme } from '@/theme/Theme';

export type NomIcone = ComponentProps<typeof Ionicons>['name'];

export const Icone = ({ nom, taille = 22, couleur }: { nom: NomIcone; taille?: number; couleur?: string }) => {
  const { c } = useTheme();
  return <Ionicons name={nom} size={taille} color={couleur ?? c.texte} />;
};

// ---------------------------------------------------------------------------
// Texte
// ---------------------------------------------------------------------------
type Variante = 'titre' | 'h1' | 'h2' | 'h3' | 'corps' | 'gras' | 'petit' | 'legende' | 'chiffre';
const TAILLES: Record<Variante, TextStyle> = {
  titre: { fontSize: 26, fontFamily: police.extra, letterSpacing: -0.4 },
  h1: { fontSize: 23, fontFamily: police.extra, letterSpacing: -0.3 },
  h2: { fontSize: 17, fontFamily: police.extra },
  h3: { fontSize: 15, fontFamily: police.gras },
  corps: { fontSize: 14.5, fontFamily: police.normal, lineHeight: 21 },
  gras: { fontSize: 14.5, fontFamily: police.gras },
  petit: { fontSize: 12.5, fontFamily: police.semi },
  legende: { fontSize: 11.5, fontFamily: police.gras, textTransform: 'uppercase', letterSpacing: 0.6 },
  chiffre: { fontSize: 30, fontFamily: police.extra, letterSpacing: -0.6 },
};

export function T({ v = 'corps', discret, couleur, style, children, ...p }: {
  v?: Variante; discret?: boolean; couleur?: string; style?: StyleProp<TextStyle>; children: ReactNode; numberOfLines?: number; accessibilityRole?: 'header' | 'text' | 'link'; onPress?: () => void;
}) {
  const { c } = useTheme();
  return (
    <Text style={[TAILLES[v], { color: couleur ?? (discret ? c.texte2 : c.texte) }, style]} {...p}>
      {children}
    </Text>
  );
}

// ---------------------------------------------------------------------------
// Mise en page
// ---------------------------------------------------------------------------
export function Ecran({ children, rafraichir, enRafraichissement = false, entete, pied, defile = true, fond }: {
  children: ReactNode; rafraichir?: () => void; enRafraichissement?: boolean; entete?: ReactNode; pied?: ReactNode; defile?: boolean; fond?: string;
}) {
  const { c } = useTheme();
  const insets = useSafeAreaInsets();
  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: fond ?? c.fond }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <View style={{ paddingTop: entete ? 0 : insets.top }} />
      {entete}
      <BandeauHorsLigne />
      {defile ? (
        <ScrollView
          contentContainerStyle={{ paddingHorizontal: 20, paddingTop: 12, paddingBottom: 32, gap: 20 }}
          refreshControl={rafraichir ? <RefreshControl refreshing={enRafraichissement} onRefresh={rafraichir} tintColor={c.accent} /> : undefined}
          keyboardShouldPersistTaps="handled"
        >
          {children}
        </ScrollView>
      ) : (
        <View style={{ flex: 1 }}>{children}</View>
      )}
      {pied ? <View style={{ padding: 16, paddingBottom: 16 + insets.bottom, borderTopWidth: 1, borderColor: c.ligne, backgroundColor: c.fond }}>{pied}</View> : null}
    </KeyboardAvoidingView>
  );
}

export function EnTete({ titre, sousTitre, retour = true, droite }: { titre: string; sousTitre?: string; retour?: boolean; droite?: ReactNode }) {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { c } = useTheme();
  return (
    <View style={{ paddingTop: insets.top + 10, paddingHorizontal: 20, paddingBottom: 6, flexDirection: 'row', alignItems: 'center', gap: 12, backgroundColor: c.fond }}>
      {retour ? <BoutonIcone icone="chevron-back" libelle="Retour" onPress={() => (router.canGoBack() ? router.back() : router.replace('/'))} /> : null}
      <View style={{ flex: 1 }}>
        <T v="h1" accessibilityRole="header" numberOfLines={1}>{titre}</T>
        {sousTitre ? <T v="petit" discret numberOfLines={1}>{sousTitre}</T> : null}
      </View>
      {droite}
    </View>
  );
}

export function Carte({ children, onPress, style, libelle, fond }: { children: ReactNode; onPress?: () => void; style?: StyleProp<ViewStyle>; libelle?: string; fond?: string }) {
  const { c } = useTheme();
  const base: ViewStyle = {
    backgroundColor: fond ?? c.surface,
    borderRadius: rayon.l,
    padding: 16,
    shadowColor: c.ombre,
    shadowOpacity: c.sombre ? 0.4 : 0.07,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
    elevation: 2,
  };
  if (!onPress) return <View style={[base, style]}>{children}</View>;
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel={libelle} style={({ pressed }) => [base, style, pressed && { opacity: 0.85, transform: [{ scale: 0.99 }] }]}>
      {children}
    </Pressable>
  );
}

export function Section({ titre, action, onAction, children }: { titre: string; action?: string; onAction?: () => void; children: ReactNode }) {
  const { c } = useTheme();
  return (
    <View style={{ gap: 10 }}>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <T v="h2" accessibilityRole="header">{titre}</T>
        {action ? (
          <Pressable onPress={onAction} hitSlop={12} accessibilityRole="link">
            <Text style={{ color: c.accent, fontFamily: police.gras, fontSize: 13 }}>{action}</Text>
          </Pressable>
        ) : null}
      </View>
      {children}
    </View>
  );
}

export const Separateur = () => {
  const { c } = useTheme();
  return <View style={{ height: StyleSheet.hairlineWidth, backgroundColor: c.ligne }} />;
};

// ---------------------------------------------------------------------------
// Boutons et contrôles
// ---------------------------------------------------------------------------
export function Bouton({ titre, onPress, variante = 'primaire', icone, charge, desactive, style }: {
  titre: string; onPress?: () => void; variante?: 'primaire' | 'secondaire' | 'danger' | 'contour'; icone?: NomIcone; charge?: boolean; desactive?: boolean; style?: StyleProp<ViewStyle>;
}) {
  const { c } = useTheme();
  const fond = { primaire: c.primaire, secondaire: c.surface2, danger: c.danger, contour: 'transparent' }[variante];
  const texte = { primaire: c.surPrimaire, secondaire: c.texte, danger: '#FFFFFF', contour: c.accent }[variante];
  const inactif = desactive || charge;
  return (
    <Pressable
      onPress={() => {
        if (inactif) return;
        Haptics.selectionAsync().catch(() => undefined);
        onPress?.();
      }}
      accessibilityRole="button"
      accessibilityState={{ disabled: !!inactif, busy: !!charge }}
      style={({ pressed }) => [
        { height: 52, borderRadius: rayon.m, backgroundColor: inactif && variante === 'primaire' ? c.surface2 : fond, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, paddingHorizontal: 18 },
        variante === 'contour' && { borderWidth: 1.5, borderColor: c.accent },
        pressed && { opacity: 0.85 },
        style,
      ]}
    >
      {charge ? <ActivityIndicator color={texte} /> : icone ? <Ionicons name={icone} size={20} color={inactif && variante === 'primaire' ? c.texte2 : texte} /> : null}
      <Text style={{ color: inactif && variante === 'primaire' ? c.texte2 : texte, fontFamily: police.gras, fontSize: 15 }}>{titre}</Text>
    </Pressable>
  );
}

export function BoutonIcone({ icone, libelle, onPress, pastille, plein }: { icone: NomIcone; libelle: string; onPress?: () => void; pastille?: number; plein?: boolean }) {
  const { c } = useTheme();
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={pastille ? `${libelle}, ${pastille} non lu${pastille > 1 ? 's' : ''}` : libelle}
      hitSlop={6}
      style={({ pressed }) => ({
        width: 44, height: 44, borderRadius: rayon.m, alignItems: 'center', justifyContent: 'center',
        backgroundColor: plein ? c.primaire : c.surface, borderWidth: plein ? 0 : 1, borderColor: c.ligne, opacity: pressed ? 0.7 : 1,
      })}
    >
      <Ionicons name={icone} size={22} color={plein ? c.surPrimaire : c.texte} />
      {pastille ? <Pastille n={pastille} style={{ position: 'absolute', top: -5, right: -5 }} /> : null}
    </Pressable>
  );
}

export function Pastille({ n, style }: { n: number; style?: StyleProp<ViewStyle> }) {
  const { c } = useTheme();
  return (
    <View style={[{ minWidth: 18, height: 18, borderRadius: 9, backgroundColor: c.pastille, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 5 }, style]}>
      <Text style={{ color: '#FFFFFF', fontSize: 10.5, fontFamily: police.extra }}>{n > 99 ? '99+' : n}</Text>
    </View>
  );
}

type Ton = 'ok' | 'alerte' | 'danger' | 'info' | 'neutre';
export function Badge({ texte, ton = 'info' }: { texte: string; ton?: Ton }) {
  const { c } = useTheme();
  const t = {
    ok: [c.okDoux, c.ok], alerte: [c.alerteDoux, c.alerte], danger: [c.dangerDoux, c.danger], info: [c.accentDoux, c.accent], neutre: [c.surface2, c.texte],
  }[ton];
  return (
    <View style={{ alignSelf: 'flex-start', backgroundColor: t[0], borderRadius: 11, paddingHorizontal: 8, height: 22, justifyContent: 'center' }}>
      <Text style={{ color: t[1], fontSize: 11.5, fontFamily: police.gras }}>{texte}</Text>
    </View>
  );
}

export function Puce({ titre, actif, onPress, compte }: { titre: string; actif: boolean; onPress: () => void; compte?: number }) {
  const { c } = useTheme();
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityState={{ selected: actif }}
      style={{ height: 38, paddingHorizontal: 14, borderRadius: 19, borderWidth: 1, borderColor: actif ? c.primaire : c.ligne, backgroundColor: actif ? c.primaire : c.surface, flexDirection: 'row', alignItems: 'center', gap: 6 }}
    >
      <Text style={{ color: actif ? c.surPrimaire : c.texte, fontFamily: police.semi, fontSize: 13 }}>{titre}</Text>
      {compte ? <Text style={{ color: actif ? c.surPrimaire : c.texte2, fontFamily: police.semi, fontSize: 12, opacity: 0.8 }}>{compte}</Text> : null}
    </Pressable>
  );
}

export function Puces({ children }: { children: ReactNode }) {
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8, paddingHorizontal: 20 }} style={{ marginHorizontal: -20, flexGrow: 0 }}>
      {children}
    </ScrollView>
  );
}

export function Segments<K extends string | number>({ options, valeur, onChange }: { options: { cle: K; titre: string }[]; valeur: K; onChange: (k: K) => void }) {
  const { c } = useTheme();
  return (
    <View accessibilityRole="tablist" style={{ flexDirection: 'row', backgroundColor: c.surface2, borderRadius: rayon.m, padding: 4, gap: 4 }}>
      {options.map((o) => {
        const actif = o.cle === valeur;
        return (
          <Pressable
            key={String(o.cle)}
            onPress={() => onChange(o.cle)}
            accessibilityRole="tab"
            accessibilityState={{ selected: actif }}
            style={{ flex: 1, height: 40, borderRadius: 10, alignItems: 'center', justifyContent: 'center', backgroundColor: actif ? c.surface : 'transparent' }}
          >
            <Text style={{ color: actif ? c.texte : c.texte2, fontFamily: police.gras, fontSize: 13.5 }} numberOfLines={1}>{o.titre}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

export function Interrupteur({ valeur, onChange, libelle }: { valeur: boolean; onChange: (v: boolean) => void; libelle: string }) {
  const { c } = useTheme();
  return (
    <Switch
      value={valeur}
      onValueChange={(v) => {
        Haptics.selectionAsync().catch(() => undefined);
        onChange(v);
      }}
      accessibilityLabel={libelle}
      trackColor={{ false: c.ligne, true: c.ok }}
      thumbColor="#FFFFFF"
      ios_backgroundColor={c.ligne}
    />
  );
}

export function Champ({ libelle, aide, erreur, ...p }: TextInputProps & { libelle: string; aide?: string; erreur?: string }) {
  const { c } = useTheme();
  const [focus, setFocus] = useState(false);
  return (
    <View style={{ gap: 6 }}>
      <T v="petit" style={{ fontFamily: police.gras }}>{libelle}</T>
      <TextInput
        placeholderTextColor={c.texte2}
        accessibilityLabel={libelle}
        onFocus={() => setFocus(true)}
        onBlur={() => setFocus(false)}
        style={[{
          minHeight: 52, borderRadius: rayon.m, borderWidth: 1.5, borderColor: erreur ? c.danger : focus ? c.accent : c.ligne,
          backgroundColor: c.surface, color: c.texte, paddingHorizontal: 14, fontFamily: police.moyen, fontSize: 15,
        }, p.multiline && { minHeight: 90, paddingTop: 12, textAlignVertical: 'top' }]}
        {...p}
      />
      {erreur ? <T v="petit" couleur={c.danger}>{erreur}</T> : aide ? <T v="petit" discret>{aide}</T> : null}
    </View>
  );
}

export function Avatar({ initiales, couleur, taille = 44 }: { initiales: string; couleur?: string; taille?: number }) {
  return (
    <View style={{ width: taille, height: taille, borderRadius: taille / 2, backgroundColor: couleur ?? '#1D5BD8', alignItems: 'center', justifyContent: 'center' }} accessibilityElementsHidden importantForAccessibility="no">
      <Text style={{ color: '#FFFFFF', fontFamily: police.extra, fontSize: taille * 0.34 }}>{initiales}</Text>
    </View>
  );
}

export function Ligne({ titre, detail, icone, droite, onPress, couleurTitre }: { titre: string; detail?: string; icone?: NomIcone; droite?: ReactNode; onPress?: () => void; couleurTitre?: string }) {
  const { c } = useTheme();
  const contenu = (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12, minHeight: 60, paddingVertical: 10 }}>
      {icone ? (
        <View style={{ width: 38, height: 38, borderRadius: 12, backgroundColor: c.surface2, alignItems: 'center', justifyContent: 'center' }}>
          <Ionicons name={icone} size={20} color={couleurTitre ?? c.accent} />
        </View>
      ) : null}
      <View style={{ flex: 1 }}>
        <T v="gras" couleur={couleurTitre}>{titre}</T>
        {detail ? <T v="petit" discret>{detail}</T> : null}
      </View>
      {droite ?? (onPress ? <Ionicons name="chevron-forward" size={20} color={c.texte2} /> : null)}
    </View>
  );
  return onPress ? <Pressable onPress={onPress} accessibilityRole="button" style={({ pressed }) => pressed && { opacity: 0.7 }}>{contenu}</Pressable> : contenu;
}

// ---------------------------------------------------------------------------
// États : chargement, vide, erreur, hors connexion
// ---------------------------------------------------------------------------
export function Squelette({ hauteur = 80, style }: { hauteur?: number; style?: StyleProp<ViewStyle> }) {
  const { c } = useTheme();
  const op = useRef(new Animated.Value(0.5)).current;
  useEffect(() => {
    const a = Animated.loop(Animated.sequence([
      Animated.timing(op, { toValue: 1, duration: 700, useNativeDriver: true }),
      Animated.timing(op, { toValue: 0.5, duration: 700, useNativeDriver: true }),
    ]));
    a.start();
    return () => a.stop();
  }, [op]);
  return <Animated.View accessibilityLabel="Chargement" style={[{ height: hauteur, borderRadius: rayon.l, backgroundColor: c.surface2, opacity: op }, style]} />;
}

export function Chargement({ lignes = 3 }: { lignes?: number }) {
  return (
    <View style={{ gap: 12 }}>
      {Array.from({ length: lignes }, (_, i) => <Squelette key={i} hauteur={i === 0 ? 120 : 76} />)}
    </View>
  );
}

export function Vide({ icone = 'sparkles-outline', titre, texte, action, onAction }: { icone?: NomIcone; titre: string; texte?: string; action?: string; onAction?: () => void }) {
  const { c } = useTheme();
  return (
    <Carte style={{ alignItems: 'center', paddingVertical: 32, gap: 8 }}>
      <View style={{ width: 64, height: 64, borderRadius: 20, backgroundColor: c.accentDoux, alignItems: 'center', justifyContent: 'center' }}>
        <Ionicons name={icone} size={30} color={c.accent} />
      </View>
      <T v="h3" style={{ textAlign: 'center' }}>{titre}</T>
      {texte ? <T discret style={{ textAlign: 'center' }}>{texte}</T> : null}
      {action ? <Bouton titre={action} onPress={onAction} variante="secondaire" style={{ marginTop: 8, alignSelf: 'stretch' }} /> : null}
    </Carte>
  );
}

export function Erreur({ erreur, reessayer }: { erreur: Error | null; reessayer?: () => void }) {
  const horsLigne = (erreur as any)?.horsLigne;
  return (
    <Vide
      icone={horsLigne ? 'cloud-offline-outline' : 'alert-circle-outline'}
      titre={horsLigne ? 'Pas de connexion' : 'Impossible de charger'}
      texte={erreur?.message ?? 'Une erreur est survenue.'}
      action={reessayer ? 'Réessayer' : undefined}
      onAction={reessayer}
    />
  );
}

export function BandeauHorsLigne() {
  const enLigne = useEnLigne();
  const { c } = useTheme();
  if (enLigne) return null;
  return (
    <View accessibilityRole="alert" style={{ backgroundColor: c.alerteDoux, paddingVertical: 8, paddingHorizontal: 20, flexDirection: 'row', gap: 8, alignItems: 'center' }}>
      <Ionicons name="cloud-offline-outline" size={16} color={c.alerte} />
      <Text style={{ color: c.alerte, fontFamily: police.semi, fontSize: 12.5, flex: 1 }}>Hors connexion — affichage des dernières données synchronisées</Text>
    </View>
  );
}

// ---------------------------------------------------------------------------
// Feuille modale (bas d'écran) et messages éphémères
// ---------------------------------------------------------------------------
export function Feuille({ visible, onClose, titre, children }: { visible: boolean; onClose: () => void; titre?: string; children: ReactNode }) {
  const { c } = useTheme();
  const insets = useSafeAreaInsets();
  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose} statusBarTranslucent>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1, justifyContent: 'flex-end' }}>
        <Pressable style={StyleSheet.absoluteFill} onPress={onClose} accessibilityLabel="Fermer">
          <View style={{ flex: 1, backgroundColor: 'rgba(6,17,31,0.55)' }} />
        </Pressable>
        <View style={{ backgroundColor: c.surface, borderTopLeftRadius: rayon.xl, borderTopRightRadius: rayon.xl, paddingHorizontal: 20, paddingTop: 10, paddingBottom: 24 + insets.bottom, maxHeight: '92%' }}>
          <View style={{ width: 40, height: 5, borderRadius: 3, backgroundColor: c.ligne, alignSelf: 'center', marginBottom: 14 }} />
          {titre ? <T v="h1" style={{ fontSize: 20, marginBottom: 12 }} accessibilityRole="header">{titre}</T> : null}
          <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{ gap: 14 }}>{children}</ScrollView>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const ToastCtx = createContext<(m: string) => void>(() => {});
export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [msg, setMsg] = useState<string | null>(null);
  const insets = useSafeAreaInsets();
  const { c } = useTheme();
  const t = useRef<ReturnType<typeof setTimeout> | null>(null);
  const afficher = useCallback((m: string) => {
    setMsg(m);
    if (t.current) clearTimeout(t.current);
    t.current = setTimeout(() => setMsg(null), 3200);
  }, []);
  return (
    <ToastCtx.Provider value={afficher}>
      {children}
      {msg ? (
        <View pointerEvents="none" accessibilityLiveRegion="polite" accessibilityRole="alert" style={{ position: 'absolute', left: 16, right: 16, bottom: 96 + insets.bottom, backgroundColor: c.texte, borderRadius: rayon.m, padding: 14, flexDirection: 'row', gap: 10, alignItems: 'center' }}>
          <Ionicons name="checkmark-circle" size={20} color={c.fond} />
          <Text style={{ color: c.fond, fontFamily: police.semi, flex: 1 }}>{msg}</Text>
        </View>
      ) : null}
    </ToastCtx.Provider>
  );
}
