/** Détail d'une matière : moyenne, statistiques de classe, évaluations, appréciation. */
import Ionicons from '@expo/vector-icons/Ionicons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { Pressable, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Barre, couleurNote } from '@/components/metier';
import { Bouton, Carte, Chargement, Ecran, Erreur, Section, T, Vide } from '@/components/ui';
import { dateMoyenne, note, noteCourte } from '@/lib/format';
import { useDonnees } from '@/lib/requetes';
import { useSession } from '@/lib/session';
import { police } from '@/theme/couleurs';
import { useTheme } from '@/theme/Theme';

export default function DetailMatiere() {
  const { c } = useTheme();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { id, periode } = useLocalSearchParams<{ id: string; periode?: string }>();
  const { eleve } = useSession();
  const p = periode ? Number(periode) : null;
  const q = useDonnees(['notes', eleve?.id, p], (a) => a.notes(eleve!.id, p), { enabled: !!eleve });
  const m = q.data?.matieres.find((x) => String(x.id) === id);
  const [ouvert, setOuvert] = useState<number | null>(null);

  if (!m) {
    return (
      <Ecran>
        {q.isPending ? <Chargement /> : q.isError ? <Erreur erreur={q.error} reessayer={() => q.refetch()} /> : <Vide titre="Matière introuvable" action="Retour" onAction={() => router.back()} />}
      </Ecran>
    );
  }

  const nomPeriode = q.data?.periodes.find((x) => x.id === q.data?.periode_id)?.nom ?? '';
  return (
    <Ecran
      entete={
        <View style={{ backgroundColor: m.couleur, paddingTop: insets.top + 12, paddingHorizontal: 20, paddingBottom: 22, borderBottomLeftRadius: 28, borderBottomRightRadius: 28, gap: 6 }}>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
            <Pressable onPress={() => router.back()} accessibilityRole="button" accessibilityLabel="Retour" style={{ width: 44, height: 44, borderRadius: 14, backgroundColor: 'rgba(255,255,255,0.15)', alignItems: 'center', justifyContent: 'center' }}>
              <Ionicons name="chevron-back" size={22} color="#FFF" />
            </Pressable>
            <Text style={{ color: 'rgba(255,255,255,0.9)', fontFamily: police.gras, fontSize: 13 }}>{nomPeriode}</Text>
            <View style={{ width: 44 }} />
          </View>
          <Text style={{ color: '#FFF', fontFamily: police.extra, fontSize: 24, marginTop: 8 }} accessibilityRole="header">{m.matiere}</Text>
          <Text style={{ color: 'rgba(255,255,255,0.9)', fontFamily: police.semi, fontSize: 13 }}>{m.enseignant} · Coefficient {noteCourte(m.coefficient)}</Text>
          <View style={{ flexDirection: 'row', alignItems: 'flex-end', gap: 8, marginTop: 8 }}>
            <Text style={{ color: '#FFF', fontFamily: police.extra, fontSize: 44, lineHeight: 48 }}>{note(m.moyenne)}</Text>
            <Text style={{ color: 'rgba(255,255,255,0.85)', fontFamily: police.gras, fontSize: 16, paddingBottom: 6 }}>/20</Text>
          </View>
          <View style={{ flexDirection: 'row', gap: 8, marginTop: 8 }}>
            {[['Classe', note(m.moyenne_classe)], ['Min.', note(m.min)], ['Max.', note(m.max)]].map(([l, v]) => (
              <View key={l} style={{ flex: 1, backgroundColor: 'rgba(255,255,255,0.15)', borderRadius: 14, padding: 10, alignItems: 'center' }}>
                <Text style={{ color: '#FFF', fontFamily: police.extra, fontSize: 17 }}>{v}</Text>
                <Text style={{ color: 'rgba(255,255,255,0.85)', fontFamily: police.semi, fontSize: 11.5 }}>{l}</Text>
              </View>
            ))}
          </View>
        </View>
      }
      rafraichir={() => q.refetch()}
      enRafraichissement={q.isRefetching}
    >
      {m.appreciation ? (
        <Carte style={{ gap: 8 }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
            <Ionicons name="chatbox-ellipses-outline" size={20} color={c.accent} />
            <T v="h3">Appréciation de {m.enseignant}</T>
          </View>
          <T>{m.appreciation}</T>
        </Carte>
      ) : null}

      <Section titre={`Évaluations (${m.evaluations.length})`}>
        {m.evaluations.length === 0 ? (
          <Vide icone="document-outline" titre="Pas d’évaluation détaillée" texte="Le détail des notes est affiché pour la période en cours." />
        ) : (
          <Carte style={{ paddingVertical: 2 }}>
            {m.evaluations.map((e, i) => {
              const sur20 = e.note == null ? null : (e.note / e.bareme) * 20;
              const open = ouvert === e.id;
              return (
                <View key={e.id} style={{ borderTopWidth: i ? 1 : 0, borderColor: c.ligne }}>
                  <Pressable onPress={() => setOuvert(open ? null : e.id)} accessibilityRole="button" accessibilityState={{ expanded: open }} style={{ flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 12 }}>
                    <View style={{ flex: 1 }}>
                      <T v="gras">{e.titre}</T>
                      <T v="petit" discret>{dateMoyenne(e.date)} · coef. {noteCourte(e.coefficient)}</T>
                    </View>
                    <T v="h2" couleur={couleurNote(sur20, c)}>
                      {e.note == null ? (e.statut ?? '—').slice(0, 3) : noteCourte(e.note)}
                      <Text style={{ fontSize: 12, color: c.texte2 }}>/{noteCourte(e.bareme)}</Text>
                    </T>
                    <Ionicons name={open ? 'chevron-up' : 'chevron-down'} size={18} color={c.texte2} />
                  </Pressable>
                  {open ? (
                    <View style={{ paddingBottom: 14, gap: 8 }}>
                      {sur20 != null ? (
                        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                          <Barre valeur={sur20} max={20} couleur={m.couleur} />
                          <T v="petit" discret>{note(sur20)} / 20</T>
                        </View>
                      ) : null}
                      {e.commentaire ? <T v="petit" discret>« {e.commentaire} »</T> : <T v="petit" discret>Pas de commentaire.</T>}
                    </View>
                  ) : null}
                </View>
              );
            })}
          </Carte>
        )}
      </Section>

      <Bouton titre={`Écrire à ${m.enseignant}`} icone="chatbubble-outline" variante="secondaire" onPress={() => router.push({ pathname: '/nouveau-message', params: { a: String(m.enseignant_id), sujet: m.matiere } })} />
    </Ecran>
  );
}
