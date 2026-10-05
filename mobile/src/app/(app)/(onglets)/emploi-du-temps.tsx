/** Emploi du temps : vue jour / semaine, cours annulés ou modifiés, synchronisation avec le calendrier. */
import Ionicons from '@expo/vector-icons/Ionicons';
import * as Calendar from 'expo-calendar';
import { useMemo, useState } from 'react';
import { Alert, Platform, Pressable, ScrollView, Text, View } from 'react-native';

import { CoursLigne, SelecteurEnfant } from '@/components/metier';
import { BoutonIcone, Carte, Chargement, Ecran, EnTete, Erreur, Segments, T, useToast, Vide } from '@/components/ui';
import { ajouterJours, isoJour, lundiDe, versDate } from '@/lib/format';
import { useDonnees } from '@/lib/requetes';
import { useSession } from '@/lib/session';
import type { Cours, Semaine } from '@/lib/types';
import { police, rayon } from '@/theme/couleurs';
import { useTheme } from '@/theme/Theme';

const MOIS = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.'];

/** Ajoute les cours (non annulés) de la semaine dans un calendrier « NotePro » du téléphone. */
async function synchroniserCalendrier(semaine: Semaine, eleve: string): Promise<number> {
  const { status } = await Calendar.requestCalendarPermissionsAsync();
  if (status !== 'granted') throw new Error('Autorisez l’accès au calendrier dans les réglages du téléphone.');
  const calendriers = await Calendar.getCalendarsAsync(Calendar.EntityTypes.EVENT);
  let cal = calendriers.find((x) => x.title === 'NotePro');
  let id = cal?.id;
  if (!id) {
    const source = Platform.OS === 'ios'
      ? (await Calendar.getDefaultCalendarAsync()).source
      : { isLocalAccount: true, name: 'NotePro', type: Calendar.SourceType.LOCAL as string };
    id = await Calendar.createCalendarAsync({
      title: 'NotePro', color: '#1D5BD8', entityType: Calendar.EntityTypes.EVENT, name: 'notepro',
      ownerAccount: 'personal', accessLevel: Calendar.CalendarAccessLevel.OWNER,
      sourceId: (source as any).id, source: source as any,
    });
  }
  const debutSemaine = versDate(semaine.lundi);
  const existants = await Calendar.getEventsAsync([id], debutSemaine, ajouterJours(debutSemaine, 7));
  await Promise.all(existants.map((e) => Calendar.deleteEventAsync(e.id).catch(() => undefined)));
  let n = 0;
  for (const j of semaine.jours) {
    for (const k of j.cours.filter((x) => x.statut !== 'annule')) {
      const [h1, m1] = k.debut.split(':').map(Number);
      const [h2, m2] = k.fin.split(':').map(Number);
      const d = versDate(k.date);
      await Calendar.createEventAsync(id, {
        title: `${k.matiere} (${eleve})`,
        startDate: new Date(d.getFullYear(), d.getMonth(), d.getDate(), h1, m1),
        endDate: new Date(d.getFullYear(), d.getMonth(), d.getDate(), h2, m2),
        location: k.salle ? `Salle ${k.salle}` : undefined,
        notes: [k.enseignant, k.info].filter(Boolean).join(' — '),
      });
      n += 1;
    }
  }
  return n;
}

export default function EmploiDuTemps() {
  const { c } = useTheme();
  const toast = useToast();
  const { eleve } = useSession();
  const [vue, setVue] = useState<'jour' | 'semaine'>('jour');
  const [lundi, setLundi] = useState(() => lundiDe(new Date()));
  const [jourSel, setJourSel] = useState(() => Math.min(4, (new Date().getDay() + 6) % 7));
  const [sync, setSync] = useState(false);
  const iso = isoJour(lundi);
  const q = useDonnees(['edt', eleve?.id, iso], (a) => a.edt(eleve!.id, iso), { enabled: !!eleve });

  const jours = q.data?.jours ?? [];
  const jour = jours[jourSel];
  const nbModifs = useMemo(() => jours.reduce((t, j) => t + j.cours.filter((k) => k.statut !== 'normal').length, 0), [jours]);
  const finSemaine = ajouterJours(lundi, 4);
  const titreSemaine = `Du ${lundi.getDate()} ${MOIS[lundi.getMonth()]} au ${finSemaine.getDate()} ${MOIS[finSemaine.getMonth()]}`;
  const aujourdHui = isoJour(new Date());

  async function synchroniser() {
    if (Platform.OS === 'web') return toast('La synchronisation est disponible dans l’application mobile.');
    if (!q.data || !eleve) return;
    setSync(true);
    try {
      const n = await synchroniserCalendrier(q.data, eleve.prenom);
      toast(`${n} cours ajoutés au calendrier « NotePro »`);
    } catch (e: any) {
      Alert.alert('Calendrier', e?.message ?? 'Synchronisation impossible.');
    } finally {
      setSync(false);
    }
  }

  return (
    <Ecran
      entete={<EnTete titre="Emploi du temps" sousTitre={eleve ? `${eleve.prenom} ${eleve.nom} · ${eleve.classe ?? ''}` : undefined} retour={false} droite={<BoutonIcone icone={sync ? 'sync' : 'calendar-outline'} libelle="Synchroniser avec le calendrier du téléphone" onPress={synchroniser} />} />}
      rafraichir={() => q.refetch()}
      enRafraichissement={q.isRefetching}
    >
      <SelecteurEnfant />
      <Segments options={[{ cle: 'jour', titre: 'Jour' }, { cle: 'semaine', titre: 'Semaine' }]} valeur={vue} onChange={setVue} />
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <BoutonIcone icone="chevron-back" libelle="Semaine précédente" onPress={() => setLundi(ajouterJours(lundi, -7))} />
        <Pressable onPress={() => { setLundi(lundiDe(new Date())); setJourSel(Math.min(4, (new Date().getDay() + 6) % 7)); }} accessibilityRole="button" accessibilityHint="Revenir à la semaine en cours">
          <T v="gras">{titreSemaine}</T>
        </Pressable>
        <BoutonIcone icone="chevron-forward" libelle="Semaine suivante" onPress={() => setLundi(ajouterJours(lundi, 7))} />
      </View>
      {nbModifs ? (
        <View accessibilityRole="alert" style={{ backgroundColor: c.alerteDoux, borderRadius: rayon.m, padding: 12, flexDirection: 'row', gap: 10, alignItems: 'center' }}>
          <Ionicons name="warning-outline" size={18} color={c.alerte} />
          <T v="petit" couleur={c.alerte} style={{ flex: 1 }}>{nbModifs} modification{nbModifs > 1 ? 's' : ''} cette semaine — mises à jour automatiquement</T>
        </View>
      ) : null}

      {q.isPending && !q.data ? <Chargement /> : null}
      {q.isError && !q.data ? <Erreur erreur={q.error} reessayer={() => q.refetch()} /> : null}

      {q.data && vue === 'jour' ? (
        <>
          <View style={{ flexDirection: 'row', gap: 6 }} accessibilityRole="tablist">
            {jours.map((j, i) => {
              const actif = i === jourSel;
              const d = versDate(j.date);
              return (
                <Pressable
                  key={j.date}
                  onPress={() => setJourSel(i)}
                  accessibilityRole="tab"
                  accessibilityState={{ selected: actif }}
                  accessibilityLabel={`${j.nom} ${d.getDate()}`}
                  style={{ flex: 1, height: 64, borderRadius: 16, backgroundColor: actif ? c.primaire : c.surface, alignItems: 'center', justifyContent: 'center', borderWidth: j.date === aujourdHui && !actif ? 1.5 : 0, borderColor: c.accent }}
                >
                  <Text style={{ color: actif ? c.surPrimaire : c.texte2, fontFamily: police.gras, fontSize: 11 }}>{j.nom.slice(0, 3)}</Text>
                  <Text style={{ color: actif ? c.surPrimaire : c.texte, fontFamily: police.extra, fontSize: 18 }}>{d.getDate()}</Text>
                  {j.cours.some((k) => k.statut !== 'normal') ? <View style={{ position: 'absolute', bottom: 7, width: 5, height: 5, borderRadius: 3, backgroundColor: '#E8590C' }} /> : null}
                </Pressable>
              );
            })}
          </View>
          {jour?.cours.length ? (
            <Carte style={{ paddingVertical: 2 }}>
              {jour.cours.map((k, i) => <CoursLigne key={k.id} cours={k} dernier={i === jour.cours.length - 1} />)}
            </Carte>
          ) : (
            <Vide icone="sunny-outline" titre="Pas de cours ce jour-là" />
          )}
        </>
      ) : null}

      {q.data && vue === 'semaine' ? <VueSemaine jours={jours} onChoisir={(i) => { setJourSel(i); setVue('jour'); }} aujourdHui={aujourdHui} /> : null}
    </Ecran>
  );
}

function VueSemaine({ jours, onChoisir, aujourdHui }: { jours: Semaine['jours']; onChoisir: (i: number) => void; aujourdHui: string }) {
  const { c } = useTheme();
  const fond = (k: Cours) => (k.statut === 'annule' ? c.dangerDoux : k.statut === 'modifie' ? c.alerteDoux : c.surface);
  return (
    <View style={{ gap: 12 }}>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 6 }}>
        {jours.map((j, i) => (
          <View key={j.date} style={{ width: 92, gap: 6 }}>
            <View style={{ paddingVertical: 6, borderRadius: 10, backgroundColor: j.date === aujourdHui ? c.primaire : c.surface2, alignItems: 'center' }}>
              <Text style={{ fontFamily: police.extra, fontSize: 12, color: j.date === aujourdHui ? c.surPrimaire : c.texte }}>{j.nom.slice(0, 3)} {versDate(j.date).getDate()}</Text>
            </View>
            {j.cours.map((k) => (
              <Pressable
                key={k.id}
                onPress={() => onChoisir(i)}
                accessibilityLabel={`${k.matiere}, ${j.nom} de ${k.debut} à ${k.fin}${k.info ? ', ' + k.info : ''}`}
                style={{ minHeight: 62, borderRadius: 8, padding: 6, backgroundColor: fond(k), borderTopWidth: 3, borderTopColor: k.couleur, opacity: k.statut === 'annule' ? 0.7 : 1 }}
              >
                <T v="petit" discret style={{ fontSize: 10.5 }}>{k.debut}</T>
                <T v="gras" style={[{ fontSize: 12 }, k.statut === 'annule' && { textDecorationLine: 'line-through' }]} numberOfLines={2}>{k.matiere}</T>
                <T v="petit" discret style={{ fontSize: 10.5 }}>{k.salle}</T>
              </Pressable>
            ))}
          </View>
        ))}
      </ScrollView>
      <View style={{ flexDirection: 'row', gap: 16, flexWrap: 'wrap' }}>
        <Legende couleur={c.dangerDoux} bord={c.danger} texte="Annulé" />
        <Legende couleur={c.alerteDoux} bord={c.alerte} texte="Modifié / remplacé" />
        <T v="petit" discret>Touchez un cours pour le détail du jour</T>
      </View>
    </View>
  );
}

const Legende = ({ couleur, bord, texte }: { couleur: string; bord: string; texte: string }) => (
  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
    <View style={{ width: 12, height: 12, borderRadius: 3, backgroundColor: couleur, borderWidth: 1, borderColor: bord }} />
    <T v="petit" discret>{texte}</T>
  </View>
);
