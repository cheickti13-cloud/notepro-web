/** Vie scolaire : actualités, événements, examens, vacances, documents. */
import Ionicons from '@expo/vector-icons/Ionicons';
import * as Calendar from 'expo-calendar';
import * as WebBrowser from 'expo-web-browser';
import { useState } from 'react';
import { Platform, Pressable, View } from 'react-native';

import { BoiteDate } from '@/components/metier';
import { Badge, Carte, Chargement, Ecran, EnTete, Erreur, NomIcone, Puce, Puces, T, useToast, Vide } from '@/components/ui';
import { dateLongue, dateMoyenne, heure } from '@/lib/format';
import { useDonnees } from '@/lib/requetes';
import { useSession } from '@/lib/session';
import type { Evenement } from '@/lib/types';
import { useTheme } from '@/theme/Theme';

type Onglet = 'actualites' | 'evenements' | 'examens' | 'vacances' | 'documents';
const TYPES: Record<Evenement['type'], [string, NomIcone]> = {
  REUNION: ['Réunion', 'people-outline'],
  EXAMEN: ['Examen', 'school-outline'],
  VACANCES: ['Vacances', 'sunny-outline'],
  SORTIE: ['Sortie', 'bus-outline'],
  CULTURE: ['Culture et sport', 'musical-notes-outline'],
  AUTRE: ['Événement', 'calendar-outline'],
};

async function ajouterAuCalendrier(e: Evenement) {
  const { status } = await Calendar.requestCalendarPermissionsAsync();
  if (status !== 'granted') throw new Error('Autorisez l’accès au calendrier.');
  const cal = Platform.OS === 'ios' ? await Calendar.getDefaultCalendarAsync() : (await Calendar.getCalendarsAsync(Calendar.EntityTypes.EVENT)).find((x) => x.allowsModifications);
  if (!cal) throw new Error('Aucun calendrier modifiable trouvé.');
  const debut = new Date(e.debut);
  await Calendar.createEventAsync(cal.id, {
    title: e.titre,
    startDate: debut,
    endDate: e.fin ? new Date(e.fin) : new Date(debut.getTime() + 2 * 3600 * 1000),
    location: e.lieu || undefined,
    notes: e.description,
  });
}

export default function VieScolaire() {
  const { c } = useTheme();
  const toast = useToast();
  const { api } = useSession();
  const [onglet, setOnglet] = useState<Onglet>('actualites');
  const [ajoutes, setAjoutes] = useState<Set<number>>(new Set());
  const q = useDonnees(['vie'], (a) => a.vieScolaire());
  const d = q.data;
  const maintenant = new Date().toISOString();

  const evts = (d?.evenements ?? []).filter((e) => (onglet === 'examens' ? e.type === 'EXAMEN' : onglet === 'vacances' ? e.type === 'VACANCES' : !['EXAMEN', 'VACANCES'].includes(e.type)));

  async function agenda(e: Evenement) {
    if (Platform.OS === 'web') return toast('Disponible dans l’application mobile.');
    try {
      await ajouterAuCalendrier(e);
      setAjoutes(new Set(ajoutes).add(e.id));
      toast('Ajouté à votre calendrier');
    } catch (err: any) {
      toast(err.message);
    }
  }

  async function ouvrirDocument(id: number) {
    const url = await api.lien('document', id).catch(() => null);
    if (url) WebBrowser.openBrowserAsync(url);
    else toast('Document disponible avec le serveur de l’établissement (mode démo).');
  }

  return (
    <Ecran entete={<EnTete titre="Vie scolaire" sousTitre="Informations de l’établissement" />} rafraichir={() => q.refetch()} enRafraichissement={q.isRefetching}>
      <Puces>
        {([['actualites', 'Actualités'], ['evenements', 'Événements'], ['examens', 'Examens'], ['vacances', 'Vacances'], ['documents', 'Documents']] as [Onglet, string][]).map(([k, t]) => (
          <Puce key={k} titre={t} actif={onglet === k} onPress={() => setOnglet(k)} />
        ))}
      </Puces>
      {q.isPending && !d ? <Chargement /> : null}
      {q.isError && !d ? <Erreur erreur={q.error} reessayer={() => q.refetch()} /> : null}

      {d && onglet === 'actualites' ? (
        d.annonces.length ? d.annonces.map((a, i) => (
          <Carte key={a.id} style={{ padding: 0, overflow: 'hidden' }}>
            {i === 0 ? (
              <View style={{ height: 110, backgroundColor: '#0B1F3A', padding: 14, justifyContent: 'flex-end', overflow: 'hidden' }}>
                <View style={{ position: 'absolute', width: 200, height: 200, borderRadius: 100, borderWidth: 26, borderColor: 'rgba(127,176,255,0.18)', right: -60, top: -70 }} />
                <View style={{ position: 'absolute', width: 110, height: 110, borderRadius: 55, backgroundColor: 'rgba(34,197,94,0.25)', right: 60, bottom: -50 }} />
                <View style={{ alignSelf: 'flex-start', backgroundColor: '#FFF', borderRadius: 11, paddingHorizontal: 8, paddingVertical: 3 }}>
                  <T v="petit" couleur="#0B1F3A">À la une</T>
                </View>
              </View>
            ) : null}
            <View style={{ padding: 16, gap: 4 }}>
              <View style={{ flexDirection: 'row', gap: 8, alignItems: 'center' }}>
                <T v="petit" discret>{dateMoyenne(a.date.slice(0, 10))}</T>
                {a.importante ? <Badge texte="Important" ton="danger" /> : null}
              </View>
              <T v="h3">{a.titre}</T>
              <T discret>{a.contenu}</T>
            </View>
          </Carte>
        )) : <Vide icone="newspaper-outline" titre="Aucune actualité" />
      ) : null}

      {d && ['evenements', 'examens', 'vacances'].includes(onglet) ? (
        evts.length ? evts.map((e) => {
          const passe = (e.fin ?? e.debut) < maintenant;
          const [type, icone] = TYPES[e.type];
          return (
            <Carte key={e.id} style={{ gap: 10, opacity: passe ? 0.6 : 1 }}>
              <View style={{ flexDirection: 'row', gap: 14 }}>
                <BoiteDate iso={e.debut} fond={e.type === 'EXAMEN' ? c.primaire : e.type === 'VACANCES' ? c.okDoux : c.surface2} texte={e.type === 'EXAMEN' ? c.surPrimaire : e.type === 'VACANCES' ? c.ok : c.texte} />
                <View style={{ flex: 1, gap: 3 }}>
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                    <Ionicons name={icone} size={15} color={c.texte2} />
                    <T v="petit" discret>{type}{passe ? ' · terminé' : ''}</T>
                  </View>
                  <T v="h3">{e.titre}</T>
                  <T v="petit" discret>
                    {e.type === 'VACANCES' && e.fin ? `Du ${dateLongue(e.debut.slice(0, 10))} au ${dateLongue(e.fin.slice(0, 10))}` : `${dateLongue(e.debut.slice(0, 10))} à ${heure(e.debut)}`}
                    {e.lieu ? ` · ${e.lieu}` : ''}
                  </T>
                  {e.description ? <T v="petit">{e.description}</T> : null}
                </View>
              </View>
              {!passe ? (
                <Pressable onPress={() => agenda(e)} accessibilityRole="button" style={{ alignSelf: 'flex-end', flexDirection: 'row', gap: 6, alignItems: 'center', borderWidth: 1.5, borderColor: ajoutes.has(e.id) ? c.ok : c.ligne, backgroundColor: ajoutes.has(e.id) ? c.okDoux : 'transparent', borderRadius: 10, paddingHorizontal: 12, height: 38 }}>
                  <Ionicons name={ajoutes.has(e.id) ? 'checkmark' : 'add'} size={16} color={ajoutes.has(e.id) ? c.ok : c.texte} />
                  <T v="gras" couleur={ajoutes.has(e.id) ? c.ok : undefined} style={{ fontSize: 13 }}>{ajoutes.has(e.id) ? 'Dans mon agenda' : 'Ajouter à mon agenda'}</T>
                </Pressable>
              ) : null}
            </Carte>
          );
        }) : <Vide icone="calendar-outline" titre="Rien de prévu pour le moment" />
      ) : null}

      {d && onglet === 'documents' ? (
        d.documents.length ? d.documents.map((doc) => (
          <Carte key={doc.id} onPress={() => ouvrirDocument(doc.id)} libelle={`Télécharger ${doc.titre}`} style={{ flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 12 }}>
            <View style={{ width: 44, height: 44, borderRadius: 12, backgroundColor: c.dangerDoux, alignItems: 'center', justifyContent: 'center' }}>
              <Ionicons name="document-text-outline" size={22} color={c.danger} />
            </View>
            <View style={{ flex: 1 }}>
              <T v="gras">{doc.titre}</T>
              <T v="petit" discret>Publié le {dateMoyenne(doc.date.slice(0, 10))}</T>
            </View>
            <Ionicons name="download-outline" size={20} color={c.texte} />
          </Carte>
        )) : <Vide icone="folder-open-outline" titre="Aucun document" />
      ) : null}
    </Ecran>
  );
}
