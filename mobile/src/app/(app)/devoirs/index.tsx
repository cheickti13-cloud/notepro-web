/** Devoirs : section urgente, filtres par statut, matière et échéance, regroupement par date. */
import Ionicons from '@expo/vector-icons/Ionicons';
import { useRouter } from 'expo-router';
import { useMemo, useState } from 'react';
import { View } from 'react-native';

import { DevoirCarte, SelecteurEnfant } from '@/components/metier';
import { Carte, Chargement, Ecran, EnTete, Erreur, Puce, Puces, Segments, T, Vide } from '@/components/ui';
import { dateLongue, echeanceRelative, joursAvant } from '@/lib/format';
import { useDonnees } from '@/lib/requetes';
import { useSession } from '@/lib/session';
import type { StatutDevoir } from '@/lib/types';
import { useTheme } from '@/theme/Theme';

type FiltreStatut = 'tous' | StatutDevoir;

export default function Devoirs() {
  const { c } = useTheme();
  const router = useRouter();
  const { eleve } = useSession();
  const [statut, setStatut] = useState<FiltreStatut>('tous');
  const [matiere, setMatiere] = useState<string>('toutes');
  const [echeance, setEcheance] = useState<'toutes' | 'semaine' | 'plus_tard'>('toutes');
  const q = useDonnees(['devoirs', eleve?.id], (a) => a.devoirs(eleve!.id), { enabled: !!eleve });

  const tous = q.data ?? [];
  const matieres = useMemo(() => Array.from(new Set<string>(tous.map((d) => d.matiere))).sort(), [tous]);
  const urgents = tous.filter((d) => d.statut === 'en_retard' || (d.statut !== 'termine' && joursAvant(d.pour_le) <= 1));
  const parEcheance = tous
    .filter((d) => echeance === 'toutes' || (echeance === 'semaine' ? joursAvant(d.pour_le) <= 7 : joursAvant(d.pour_le) > 7))
    .filter((d) => matiere === 'toutes' || d.matiere === matiere);
  const liste = parEcheance.filter((d) => statut === 'tous' || d.statut === statut);
  const groupes = useMemo(() => {
    const g = new Map<string, typeof liste>();
    liste.forEach((d) => g.set(d.pour_le, [...(g.get(d.pour_le) ?? []), d]));
    return Array.from(g.entries());
  }, [liste]);
  const compte = (s: FiltreStatut) => parEcheance.filter((d) => s === 'tous' || d.statut === s).length;

  return (
    <Ecran entete={<EnTete titre="Devoirs" sousTitre={eleve ? `${eleve.prenom} · ${eleve.classe ?? ''}` : undefined} />} rafraichir={() => q.refetch()} enRafraichissement={q.isRefetching}>
      <SelecteurEnfant />
      {q.isPending && !q.data ? <Chargement /> : null}
      {q.isError && !q.data ? <Erreur erreur={q.error} reessayer={() => q.refetch()} /> : null}

      {urgents.length ? (
        <Carte fond={c.dangerDoux} style={{ gap: 6 }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
            <Ionicons name="alert-circle" size={18} color={c.danger} />
            <T v="h3" couleur={c.danger}>Urgent · {urgents.length} devoir{urgents.length > 1 ? 's' : ''}</T>
          </View>
          {urgents.map((d) => (
            <T key={d.id} v="petit" onPress={() => router.push(`/devoirs/${d.id}`)}>
              • {d.titre} — {d.matiere} ({d.statut === 'en_retard' ? 'en retard' : echeanceRelative(d.pour_le).toLowerCase()})
            </T>
          ))}
        </Carte>
      ) : null}

      <Segments options={[{ cle: 'toutes', titre: 'Toutes' }, { cle: 'semaine', titre: 'Cette semaine' }, { cle: 'plus_tard', titre: 'Plus tard' }]} valeur={echeance} onChange={setEcheance} />
      <Puces>
        {([['tous', 'Tous'], ['a_faire', 'À faire'], ['en_cours', 'En cours'], ['termine', 'Terminé'], ['en_retard', 'En retard']] as [FiltreStatut, string][]).map(([k, t]) => (
          <Puce key={k} titre={t} compte={compte(k)} actif={statut === k} onPress={() => setStatut(k)} />
        ))}
      </Puces>
      <Puces>
        <Puce titre="Toutes les matières" actif={matiere === 'toutes'} onPress={() => setMatiere('toutes')} />
        {matieres.map((m) => <Puce key={m} titre={m} actif={matiere === m} onPress={() => setMatiere(m)} />)}
      </Puces>

      {q.data && liste.length === 0 ? (
        <Vide icone="checkmark-done-outline" titre="Aucun devoir ne correspond" texte="Modifiez les filtres pour afficher d’autres devoirs." action="Réinitialiser les filtres" onAction={() => { setStatut('tous'); setMatiere('toutes'); setEcheance('toutes'); }} />
      ) : null}

      {groupes.map(([date, devoirs]) => (
        <View key={date} style={{ gap: 10 }}>
          <T v="legende" discret>{joursAvant(date) === 1 ? `Demain · ${dateLongue(date)}` : joursAvant(date) === 0 ? `Aujourd’hui · ${dateLongue(date)}` : dateLongue(date)}</T>
          {devoirs.map((d) => <DevoirCarte key={d.id} devoir={d} onPress={() => router.push(`/devoirs/${d.id}`)} />)}
        </View>
      ))}
    </Ecran>
  );
}
