/** Messagerie : liste des conversations, recherche, filtres. */
import Ionicons from '@expo/vector-icons/Ionicons';
import { useRouter } from 'expo-router';
import { useMemo, useState } from 'react';
import { Pressable, TextInput, View } from 'react-native';

import { Avatar, BoutonIcone, Chargement, Ecran, EnTete, Erreur, Puce, Puces, T, Vide } from '@/components/ui';
import { quand } from '@/lib/format';
import { useDonnees } from '@/lib/requetes';
import { police, rayon } from '@/theme/couleurs';
import { useTheme } from '@/theme/Theme';

const COULEURS: Record<string, string> = { ENSEIGNANT: '#1D5BD8', ADMIN: '#0B1F3A', PARENT: '#7C3AED', ELEVE: '#13803F' };

export default function Messages() {
  const { c } = useTheme();
  const router = useRouter();
  const [recherche, setRecherche] = useState('');
  const [filtre, setFiltre] = useState<'tous' | 'non_lus' | 'enseignants'>('tous');
  const q = useDonnees(['conversations'], (a) => a.conversations(), { refetchInterval: 30000 });

  const liste = useMemo(() => {
    const t = recherche.trim().toLowerCase();
    return (q.data ?? [])
      .filter((x) => filtre === 'tous' || (filtre === 'non_lus' ? x.non_lu : x.interlocuteurs.some((i) => i.role === 'ENSEIGNANT')))
      .filter((x) => !t || [x.sujet, x.dernier_message?.texte ?? '', ...x.interlocuteurs.map((i) => i.nom + ' ' + i.detail)].join(' ').toLowerCase().includes(t));
  }, [q.data, recherche, filtre]);
  const nonLus = q.data?.filter((x) => x.non_lu).length ?? 0;

  return (
    <Ecran
      entete={<EnTete titre="Messagerie" retour={false} droite={<BoutonIcone icone="create-outline" libelle="Nouveau message" plein onPress={() => router.push('/nouveau-message')} />} />}
      rafraichir={() => q.refetch()}
      enRafraichissement={q.isRefetching}
    >
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10, height: 48, borderRadius: rayon.m, borderWidth: 1.5, borderColor: c.ligne, backgroundColor: c.surface, paddingHorizontal: 14 }}>
        <Ionicons name="search" size={20} color={c.texte2} />
        <TextInput
          value={recherche}
          onChangeText={setRecherche}
          placeholder="Rechercher un contact ou un message"
          placeholderTextColor={c.texte2}
          accessibilityLabel="Rechercher dans les conversations"
          style={{ flex: 1, color: c.texte, fontFamily: police.moyen, fontSize: 15 }}
          returnKeyType="search"
        />
        {recherche ? (
          <Pressable onPress={() => setRecherche('')} accessibilityLabel="Effacer la recherche" hitSlop={10}>
            <Ionicons name="close-circle" size={20} color={c.texte2} />
          </Pressable>
        ) : null}
      </View>
      <Puces>
        <Puce titre="Toutes" actif={filtre === 'tous'} onPress={() => setFiltre('tous')} />
        <Puce titre="Non lues" compte={nonLus} actif={filtre === 'non_lus'} onPress={() => setFiltre('non_lus')} />
        <Puce titre="Enseignants" actif={filtre === 'enseignants'} onPress={() => setFiltre('enseignants')} />
      </Puces>

      {q.isPending && !q.data ? <Chargement /> : null}
      {q.isError && !q.data ? <Erreur erreur={q.error} reessayer={() => q.refetch()} /> : null}
      {q.data && liste.length === 0 ? (
        recherche ? (
          <Vide icone="search-outline" titre="Aucun résultat" texte={`Aucune conversation ne contient « ${recherche} ».`} />
        ) : (
          <Vide icone="chatbubbles-outline" titre="Aucune conversation" texte="Écrivez à un enseignant ou à la vie scolaire." action="Nouveau message" onAction={() => router.push('/nouveau-message')} />
        )
      ) : null}

      <View style={{ marginHorizontal: -20 }}>
        {liste.map((x) => {
          const i = x.interlocuteurs[0];
          const titre = x.interlocuteurs.map((p) => p.nom).join(', ') || x.sujet;
          return (
            <Pressable
              key={x.id}
              onPress={() => router.push(`/conversation/${x.id}`)}
              accessibilityRole="button"
              accessibilityLabel={`${titre}${x.non_lu ? ', non lu' : ''}. ${x.dernier_message?.texte ?? ''}`}
              style={({ pressed }) => ({ flexDirection: 'row', gap: 12, paddingVertical: 12, paddingHorizontal: 20, alignItems: 'center', backgroundColor: pressed ? c.surface2 : 'transparent' })}
            >
              <Avatar initiales={i?.initiales ?? '?'} couleur={COULEURS[i?.role ?? 'ADMIN']} taille={48} />
              <View style={{ flex: 1, gap: 1 }}>
                <View style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 8 }}>
                  <T v="gras" numberOfLines={1} style={{ flex: 1 }}>{titre}</T>
                  <T v="petit" discret>{x.dernier_message ? quand(x.dernier_message.date) : ''}</T>
                </View>
                <T v="petit" discret numberOfLines={1}>{x.sujet}{i ? ` · ${i.detail}` : ''}</T>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                  <T numberOfLines={1} style={{ flex: 1, fontSize: 13.5, fontFamily: x.non_lu ? police.gras : police.normal }} discret={!x.non_lu}>
                    {x.dernier_message?.de_moi ? 'Vous : ' : ''}{x.dernier_message?.texte}
                  </T>
                  {x.non_lu ? <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: c.accent }} /> : null}
                </View>
              </View>
            </Pressable>
          );
        })}
      </View>
    </Ecran>
  );
}
