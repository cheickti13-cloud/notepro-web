/** Centre de notifications : catégories, priorités, regroupement par date. */
import Ionicons from '@expo/vector-icons/Ionicons';
import { useRouter } from 'expo-router';
import { useMemo, useState } from 'react';
import { Pressable, View } from 'react-native';

import { Badge, Carte, Chargement, Ecran, EnTete, Erreur, Interrupteur, NomIcone, Puce, Puces, T, Vide } from '@/components/ui';
import { groupeDate, quand } from '@/lib/format';
import { routePourLien } from '@/lib/liens';
import { useAction, useDonnees } from '@/lib/requetes';
import type { NotificationItem } from '@/lib/types';
import { useTheme } from '@/theme/Theme';

const CATS: { cle: NotificationItem['categorie'] | 'toutes'; titre: string; icone: NomIcone }[] = [
  { cle: 'toutes', titre: 'Toutes', icone: 'notifications-outline' },
  { cle: 'resultats', titre: 'Résultats', icone: 'bar-chart-outline' },
  { cle: 'absences', titre: 'Absences', icone: 'time-outline' },
  { cle: 'devoirs', titre: 'Devoirs', icone: 'book-outline' },
  { cle: 'edt', titre: 'Emploi du temps', icone: 'calendar-outline' },
  { cle: 'administration', titre: 'Administration', icone: 'business-outline' },
  { cle: 'evenements', titre: 'Événements', icone: 'sparkles-outline' },
  { cle: 'paiements', titre: 'Paiements', icone: 'wallet-outline' },
  { cle: 'messages', titre: 'Messages', icone: 'chatbubble-outline' },
];
const PRIO: Record<number, [string, 'danger' | 'alerte' | 'info']> = { 1: ['Urgent', 'danger'], 2: ['Important', 'alerte'], 3: ['Info', 'info'] };

export default function Notifications() {
  const { c } = useTheme();
  const router = useRouter();
  const [cat, setCat] = useState<(typeof CATS)[number]['cle']>('toutes');
  const [prio, setPrio] = useState(false);
  const q = useDonnees(['notifications'], (a) => a.notifications(), { refetchInterval: 30000 });
  const lire = useAction((a, ids: number[] | 'tout') => a.lireNotifications(ids), ['notifications', 'accueil']);

  const groupes = useMemo(() => {
    let l = (q.data ?? []).filter((n) => cat === 'toutes' || n.categorie === cat);
    if (prio) l = [...l].sort((a, b) => a.priorite - b.priorite || (a.date < b.date ? 1 : -1));
    const g = new Map<string, NotificationItem[]>();
    l.forEach((n) => {
      const k = prio ? (n.priorite === 1 ? 'Urgent' : n.priorite === 2 ? 'Important' : 'Information') : groupeDate(n.date);
      g.set(k, [...(g.get(k) ?? []), n]);
    });
    return Array.from(g.entries());
  }, [q.data, cat, prio]);
  const nonLues = q.data?.filter((n) => !n.lue).length ?? 0;
  const presentes = new Set(q.data?.map((n) => n.categorie));

  return (
    <Ecran
      entete={<EnTete titre="Notifications" sousTitre={nonLues ? `${nonLues} non lue${nonLues > 1 ? 's' : ''}` : 'Tout est lu'} droite={nonLues ? <Pressable onPress={() => lire.mutate('tout')} accessibilityRole="button" hitSlop={8}><T v="gras" couleur={c.accent} style={{ fontSize: 13 }}>Tout lire</T></Pressable> : undefined} />}
      rafraichir={() => q.refetch()}
      enRafraichissement={q.isRefetching}
    >
      <Puces>
        {CATS.filter((x) => x.cle === 'toutes' || presentes.has(x.cle as NotificationItem['categorie'])).map((x) => (
          <Puce key={x.cle} titre={x.titre} actif={cat === x.cle} onPress={() => setCat(x.cle)} compte={q.data?.filter((n) => !n.lue && (x.cle === 'toutes' || n.categorie === x.cle)).length || undefined} />
        ))}
      </Puces>
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <T v="gras">Trier par priorité</T>
        <Interrupteur libelle="Trier par priorité" valeur={prio} onChange={setPrio} />
      </View>

      {q.isPending && !q.data ? <Chargement /> : null}
      {q.isError && !q.data ? <Erreur erreur={q.error} reessayer={() => q.refetch()} /> : null}
      {q.data && groupes.length === 0 ? <Vide icone="notifications-off-outline" titre="Rien de nouveau ici" texte="Vous serez prévenu dès qu’il se passe quelque chose." /> : null}

      {groupes.map(([titre, items]) => (
        <View key={titre} style={{ gap: 8 }}>
          <T v="legende" discret>{titre}</T>
          <Carte style={{ padding: 0, overflow: 'hidden' }}>
            {items.map((n, i) => {
              const icone = CATS.find((x) => x.cle === n.categorie)?.icone ?? 'notifications-outline';
              const ton = PRIO[n.priorite];
              return (
                <Pressable
                  key={n.id}
                  onPress={() => {
                    if (!n.lue) lire.mutate([n.id]);
                    router.push(routePourLien(n.lien) as any);
                  }}
                  accessibilityRole="button"
                  accessibilityLabel={`${ton[0]}, ${n.titre}${n.lue ? '' : ', non lue'}`}
                  style={({ pressed }) => ({ flexDirection: 'row', gap: 12, padding: 14, borderTopWidth: i ? 1 : 0, borderColor: c.ligne, backgroundColor: pressed ? c.surface2 : 'transparent' })}
                >
                  <View style={{ width: 42, height: 42, borderRadius: 13, backgroundColor: n.priorite === 1 ? c.dangerDoux : c.surface2, alignItems: 'center', justifyContent: 'center' }}>
                    <Ionicons name={icone} size={20} color={n.priorite === 1 ? c.danger : c.accent} />
                  </View>
                  <View style={{ flex: 1, gap: 3 }}>
                    <View style={{ flexDirection: 'row', gap: 6, alignItems: 'center' }}>
                      <Badge texte={ton[0]} ton={ton[1]} />
                      <T v="petit" discret>{quand(n.date)}</T>
                    </View>
                    <T v={n.lue ? 'corps' : 'gras'}>{n.titre}</T>
                  </View>
                  {!n.lue ? <View style={{ width: 9, height: 9, borderRadius: 5, backgroundColor: c.accent, marginTop: 6 }} /> : null}
                </Pressable>
              );
            })}
          </Carte>
        </View>
      ))}
    </Ecran>
  );
}
