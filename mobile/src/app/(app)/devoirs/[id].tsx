/** Détail d'un devoir : consignes, pièces jointes, avancement, rappel. */
import Ionicons from '@expo/vector-icons/Ionicons';
import * as Notifications from 'expo-notifications';
import { useLocalSearchParams, useRouter } from 'expo-router';
import * as WebBrowser from 'expo-web-browser';
import { useState } from 'react';
import { Platform, Pressable, View } from 'react-native';

import { BadgeDevoir } from '@/components/metier';
import { Bouton, Carte, Chargement, Ecran, EnTete, Interrupteur, Ligne, Segments, T, useToast, Vide } from '@/components/ui';
import { dateLongue, echeanceRelative, joursAvant, versDate } from '@/lib/format';
import { useAction, useDonnees } from '@/lib/requetes';
import { useSession } from '@/lib/session';
import { rayon } from '@/theme/couleurs';
import { useTheme } from '@/theme/Theme';

type Avancement = 'a_faire' | 'en_cours' | 'termine';

export default function DetailDevoir() {
  const { c } = useTheme();
  const router = useRouter();
  const toast = useToast();
  const { id } = useLocalSearchParams<{ id: string }>();
  const { eleve, moi, api } = useSession();
  const q = useDonnees(['devoirs', eleve?.id], (a) => a.devoirs(eleve!.id), { enabled: !!eleve });
  const d = q.data?.find((x) => String(x.id) === id);
  const changer = useAction((a, s: Avancement) => a.statutDevoir(Number(id), s), ['devoirs', 'accueil']);
  const [rappel, setRappel] = useState(false);
  const estEleve = moi?.role === 'ELEVE';

  if (!d) return <Ecran entete={<EnTete titre="Devoir" />}>{q.isPending ? <Chargement /> : <Vide titre="Devoir introuvable" />}</Ecran>;

  const avancement: Avancement = d.statut === 'en_retard' ? 'a_faire' : d.statut;
  const restant = joursAvant(d.pour_le);

  async function programmerRappel(v: boolean) {
    setRappel(v);
    if (!v || Platform.OS === 'web') return;
    const { status } = await Notifications.requestPermissionsAsync();
    if (status !== 'granted') return toast('Autorisez les notifications pour recevoir le rappel.');
    const veille = versDate(d!.pour_le);
    veille.setDate(veille.getDate() - 1);
    veille.setHours(18, 0, 0, 0);
    if (veille.getTime() <= Date.now()) return toast('L’échéance est trop proche pour programmer un rappel.');
    await Notifications.scheduleNotificationAsync({
      content: { title: 'Devoir pour demain', body: `${d!.matiere} : ${d!.titre}`, data: { lien: '/devoirs' } },
      trigger: { type: Notifications.SchedulableTriggerInputTypes.DATE, date: veille },
    });
    toast('Rappel programmé la veille à 18h');
  }

  async function ouvrirPieceJointe() {
    const url = await api.lien('devoir', d!.id).catch(() => null);
    if (url) WebBrowser.openBrowserAsync(url);
    else toast('Pièce jointe disponible avec le serveur de l’établissement (mode démo).');
  }

  return (
    <Ecran
      entete={<EnTete titre="Devoir" droite={<BadgeDevoir statut={d.statut} />} />}
      pied={estEleve ? (
        <Bouton titre={d.statut === 'termine' ? 'Devoir terminé' : 'Marquer comme terminé'} icone="checkmark-circle-outline" desactive={d.statut === 'termine'} charge={changer.isPending} onPress={() => changer.mutate('termine', { onSuccess: () => toast('Bravo ! Devoir terminé.') })} />
      ) : (
        <Bouton titre={`Écrire à ${d.enseignant}`} icone="chatbubble-outline" variante="secondaire" onPress={() => router.push({ pathname: '/nouveau-message', params: { a: String(d.enseignant_id), sujet: d.titre } })} />
      )}
    >
      <View style={{ gap: 6 }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
          <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: d.couleur }} />
          <T v="gras" couleur={d.couleur}>{d.matiere}</T>
        </View>
        <T v="h1" accessibilityRole="header">{d.titre}</T>
      </View>

      <Carte style={{ flexDirection: 'row', flexWrap: 'wrap', rowGap: 14 }}>
        {[
          ['Enseignant', d.enseignant],
          ['Publié le', dateLongue(d.donne_le)],
          ['À rendre', dateLongue(d.pour_le)],
          ['Temps restant', restant < 0 ? 'Échéance dépassée' : restant === 0 ? 'Aujourd’hui' : `${restant} jour${restant > 1 ? 's' : ''}`],
        ].map(([l, v]) => (
          <View key={l} style={{ width: '50%', paddingRight: 8 }}>
            <T v="petit" discret>{l}</T>
            <T v="gras" couleur={l === 'Temps restant' && restant <= 1 ? c.alerte : undefined}>{v}</T>
          </View>
        ))}
        {d.duree_estimee ? <T v="petit" discret>Durée estimée : environ {d.duree_estimee} min</T> : null}
      </Carte>

      <View style={{ gap: 8 }}>
        <T v="h2">Consignes</T>
        <Carte><T>{d.description || 'Pas de consigne supplémentaire.'}</T></Carte>
      </View>

      {d.piece_jointe ? (
        <View style={{ gap: 8 }}>
          <T v="h2">Pièce jointe</T>
          <Pressable onPress={ouvrirPieceJointe} accessibilityRole="button" accessibilityLabel="Ouvrir la pièce jointe" style={{ flexDirection: 'row', alignItems: 'center', gap: 12, padding: 12, borderRadius: rayon.m, borderWidth: 1, borderColor: c.ligne, backgroundColor: c.surface }}>
            <View style={{ width: 40, height: 40, borderRadius: 10, backgroundColor: c.dangerDoux, alignItems: 'center', justifyContent: 'center' }}>
              <Ionicons name="document-attach-outline" size={20} color={c.danger} />
            </View>
            <View style={{ flex: 1 }}>
              <T v="gras">Énoncé du devoir</T>
              <T v="petit" discret>Ouvrir ou télécharger</T>
            </View>
            <Ionicons name="download-outline" size={20} color={c.texte} />
          </Pressable>
        </View>
      ) : null}

      {estEleve ? (
        <View style={{ gap: 8 }}>
          <T v="h2">Mon avancement</T>
          <Segments<Avancement> options={[{ cle: 'a_faire', titre: 'À faire' }, { cle: 'en_cours', titre: 'En cours' }, { cle: 'termine', titre: 'Terminé' }]} valeur={avancement} onChange={(s) => changer.mutate(s)} />
        </View>
      ) : null}

      <Carte style={{ paddingVertical: 4 }}>
        <Ligne icone="alarm-outline" titre="Me rappeler la veille" detail={`À 18h, ${echeanceRelative(d.pour_le) === 'Demain' ? 'aujourd’hui' : 'la veille de l’échéance'}`} droite={<Interrupteur libelle="Rappel la veille" valeur={rappel} onChange={programmerRappel} />} />
      </Carte>
    </Ecran>
  );
}
