/** Conversation : bulles de messages, accusés de lecture, pièces jointes, envoi. */
import Ionicons from '@expo/vector-icons/Ionicons';
import { useQueryClient } from '@tanstack/react-query';
import * as DocumentPicker from 'expo-document-picker';
import { useLocalSearchParams, useRouter } from 'expo-router';
import * as WebBrowser from 'expo-web-browser';
import { useRef, useState } from 'react';
import { ActivityIndicator, FlatList, KeyboardAvoidingView, Platform, Pressable, Text, TextInput, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Avatar, Chargement, Erreur, T, useToast } from '@/components/ui';
import { dateLongue, heure, isoJour } from '@/lib/format';
import { useDonnees } from '@/lib/requetes';
import { useSession } from '@/lib/session';
import type { FichierJoint, MessageItem } from '@/lib/types';
import { police, rayon } from '@/theme/couleurs';
import { useTheme } from '@/theme/Theme';

export default function Conversation() {
  const { c } = useTheme();
  const router = useRouter();
  const toast = useToast();
  const insets = useSafeAreaInsets();
  const qc = useQueryClient();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { api } = useSession();
  const q = useDonnees(['conversation', id], (a) => a.conversation(Number(id)), { refetchInterval: 15000 });
  const [texte, setTexte] = useState('');
  const [fichier, setFichier] = useState<FichierJoint | null>(null);
  const [envoi, setEnvoi] = useState(false);
  const liste = useRef<FlatList<MessageItem>>(null);
  const conv = q.data;
  const autre = conv?.interlocuteurs[0];

  async function joindre() {
    const r = await DocumentPicker.getDocumentAsync({ type: ['application/pdf', 'image/jpeg', 'image/png'], copyToCacheDirectory: true });
    if (!r.canceled) {
      const a = r.assets[0];
      if ((a.size ?? 0) > 5 * 1024 * 1024) return toast('Fichier trop volumineux (5 Mo maximum).');
      setFichier({ uri: a.uri, name: a.name, mimeType: a.mimeType ?? 'application/octet-stream', file: a.file });
    }
  }

  async function envoyer() {
    if ((!texte.trim() && !fichier) || envoi) return;
    setEnvoi(true);
    try {
      await api.envoyerMessage(Number(id), texte.trim(), fichier);
      setTexte('');
      setFichier(null);
      await q.refetch();
      qc.invalidateQueries({ predicate: (x) => x.queryKey.includes('conversations') });
      setTimeout(() => liste.current?.scrollToEnd({ animated: true }), 100);
    } catch (e: any) {
      toast(e.message);
    } finally {
      setEnvoi(false);
    }
  }

  async function ouvrirPieceJointe(m: MessageItem) {
    const url = await api.lien('message', m.id).catch(() => null);
    if (url) WebBrowser.openBrowserAsync(url);
    else toast('Pièce jointe disponible avec le serveur de l’établissement (mode démo).');
  }

  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: c.fond }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <View style={{ paddingTop: insets.top + 8, paddingBottom: 10, paddingHorizontal: 16, flexDirection: 'row', alignItems: 'center', gap: 12, backgroundColor: c.surface, borderBottomWidth: 1, borderColor: c.ligne }}>
        <Pressable onPress={() => router.back()} accessibilityRole="button" accessibilityLabel="Retour aux conversations" style={{ width: 44, height: 44, alignItems: 'center', justifyContent: 'center' }}>
          <Ionicons name="chevron-back" size={24} color={c.texte} />
        </Pressable>
        <Avatar initiales={autre?.initiales ?? '?'} couleur={autre?.role === 'ADMIN' ? '#0B1F3A' : '#1D5BD8'} taille={42} />
        <View style={{ flex: 1 }}>
          <T v="gras" numberOfLines={1}>{conv?.interlocuteurs.map((i) => i.nom).join(', ') ?? 'Conversation'}</T>
          <T v="petit" discret numberOfLines={1}>{conv?.sujet}{autre ? ` · ${autre.detail}` : ''}</T>
        </View>
      </View>

      {q.isPending && !conv ? <View style={{ padding: 20 }}><Chargement /></View> : null}
      {q.isError && !conv ? <View style={{ padding: 20 }}><Erreur erreur={q.error} reessayer={() => q.refetch()} /></View> : null}

      {conv ? (
        <FlatList
          ref={liste}
          data={conv.messages}
          keyExtractor={(m) => String(m.id)}
          contentContainerStyle={{ padding: 16, gap: 10 }}
          onContentSizeChange={() => liste.current?.scrollToEnd({ animated: false })}
          renderItem={({ item: m, index }) => {
            const nouveauJour = index === 0 || isoJour(new Date(conv.messages[index - 1].date)) !== isoJour(new Date(m.date));
            return (
              <View style={{ gap: 4 }}>
                {nouveauJour ? <T v="petit" discret style={{ textAlign: 'center', marginVertical: 6 }}>{dateLongue(isoJour(new Date(m.date)))}</T> : null}
                <View style={{ alignSelf: m.de_moi ? 'flex-end' : 'flex-start', maxWidth: '84%' }}>
                  <View
                    accessible
                    accessibilityLabel={`${m.de_moi ? 'Vous' : m.auteur}, ${heure(m.date)} : ${m.texte}`}
                    style={{
                      backgroundColor: m.de_moi ? c.primaire : c.surface,
                      borderRadius: 18,
                      borderBottomRightRadius: m.de_moi ? 6 : 18,
                      borderBottomLeftRadius: m.de_moi ? 18 : 6,
                      paddingHorizontal: 14,
                      paddingVertical: 10,
                      gap: 8,
                    }}
                  >
                    <Text style={{ color: m.de_moi ? c.surPrimaire : c.texte, fontFamily: police.normal, fontSize: 15, lineHeight: 21 }}>{m.texte}</Text>
                    {m.piece_jointe ? (
                      <Pressable onPress={() => ouvrirPieceJointe(m)} accessibilityRole="button" accessibilityLabel={`Ouvrir ${m.piece_jointe}`} style={{ flexDirection: 'row', alignItems: 'center', gap: 8, padding: 8, borderRadius: 12, backgroundColor: 'rgba(127,140,160,0.18)' }}>
                        <Ionicons name="attach" size={18} color={m.de_moi ? c.surPrimaire : c.texte} />
                        <Text style={{ color: m.de_moi ? c.surPrimaire : c.texte, fontFamily: police.gras, fontSize: 13, flexShrink: 1 }} numberOfLines={1}>{m.piece_jointe}</Text>
                      </Pressable>
                    ) : null}
                  </View>
                  <View style={{ flexDirection: 'row', gap: 4, alignSelf: m.de_moi ? 'flex-end' : 'flex-start', alignItems: 'center', marginTop: 2 }}>
                    <T v="petit" discret style={{ fontSize: 11 }}>{heure(m.date)}</T>
                    {m.de_moi ? (
                      <>
                        <Ionicons name={m.lu ? 'checkmark-done' : 'checkmark'} size={14} color={m.lu ? c.accent : c.texte2} />
                        <T v="petit" discret style={{ fontSize: 11 }}>{m.lu ? 'Lu' : 'Envoyé'}</T>
                      </>
                    ) : null}
                  </View>
                </View>
              </View>
            );
          }}
        />
      ) : <View style={{ flex: 1 }} />}

      <View style={{ paddingHorizontal: 12, paddingTop: 10, paddingBottom: 10 + insets.bottom, backgroundColor: c.surface, borderTopWidth: 1, borderColor: c.ligne, gap: 8 }}>
        {fichier ? (
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, padding: 8, borderRadius: rayon.s, backgroundColor: c.surface2 }}>
            <Ionicons name="document-attach-outline" size={18} color={c.accent} />
            <T v="petit" style={{ flex: 1 }} numberOfLines={1}>{fichier.name}</T>
            <Pressable onPress={() => setFichier(null)} accessibilityLabel="Retirer la pièce jointe" hitSlop={8}><Ionicons name="close" size={18} color={c.texte2} /></Pressable>
          </View>
        ) : null}
        <View style={{ flexDirection: 'row', alignItems: 'flex-end', gap: 8 }}>
          <Pressable onPress={joindre} accessibilityRole="button" accessibilityLabel="Joindre un fichier" style={{ width: 44, height: 44, borderRadius: 14, borderWidth: 1, borderColor: c.ligne, alignItems: 'center', justifyContent: 'center' }}>
            <Ionicons name="attach" size={22} color={c.texte} />
          </Pressable>
          <TextInput
            value={texte}
            onChangeText={setTexte}
            placeholder="Écrire un message…"
            placeholderTextColor={c.texte2}
            multiline
            maxLength={5000}
            accessibilityLabel="Votre message"
            style={{ flex: 1, minHeight: 44, maxHeight: 120, borderRadius: 22, borderWidth: 1.5, borderColor: c.ligne, backgroundColor: c.fond, color: c.texte, paddingHorizontal: 16, paddingTop: 11, paddingBottom: 11, fontFamily: police.moyen, fontSize: 15 }}
          />
          <Pressable onPress={envoyer} disabled={envoi} accessibilityRole="button" accessibilityLabel="Envoyer" style={{ width: 44, height: 44, borderRadius: 22, backgroundColor: c.primaire, alignItems: 'center', justifyContent: 'center', opacity: !texte.trim() && !fichier ? 0.5 : 1 }}>
            {envoi ? <ActivityIndicator color={c.surPrimaire} /> : <Ionicons name="send" size={19} color={c.surPrimaire} />}
          </Pressable>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}
