/** Absences et retards : historique, récapitulatif mensuel, justification et déclaration par le parent. */
import Ionicons from '@expo/vector-icons/Ionicons';
import * as DocumentPicker from 'expo-document-picker';
import * as ImagePicker from 'expo-image-picker';
import { useState } from 'react';
import { Pressable, View } from 'react-native';

import { BadgeAbsence, Barre, BoiteDate, SelecteurEnfant } from '@/components/metier';
import { Bouton, Carte, Champ, Chargement, Ecran, EnTete, Erreur, Feuille, Puce, Puces, Segments, T, useToast, Vide } from '@/components/ui';
import { ajouterJours, dateLongue, dateMoyenne, isoJour } from '@/lib/format';
import { useAction, useDonnees } from '@/lib/requetes';
import { useSession } from '@/lib/session';
import type { AbsenceItem, FichierJoint } from '@/lib/types';
import { rayon } from '@/theme/couleurs';
import { useTheme } from '@/theme/Theme';

const MOTIFS = ['Raison médicale', 'Rendez-vous médical', 'Raison familiale', 'Problème de transport', 'Autre'];

export default function Absences() {
  const { c } = useTheme();
  const toast = useToast();
  const { eleve, moi } = useSession();
  const parent = moi?.role === 'PARENT';
  const [onglet, setOnglet] = useState<'historique' | 'mensuel'>('historique');
  const [feuille, setFeuille] = useState<{ mode: 'justifier'; absence: AbsenceItem } | { mode: 'declarer' } | null>(null);
  const q = useDonnees(['absences', eleve?.id], (a) => a.absences(eleve!.id), { enabled: !!eleve });
  const d = q.data;
  const nonPrevue = d?.items.find((a) => a.date === isoJour(new Date()) && a.type === 'ABSENCE' && a.statut === 'NON_JUSTIFIEE');
  const maxMois = Math.max(1, ...(d?.mensuel.map((m) => m.absences + m.retards) ?? [1]));

  return (
    <Ecran
      entete={<EnTete titre="Absences et retards" sousTitre={eleve ? `${eleve.prenom} · période en cours` : undefined} />}
      rafraichir={() => q.refetch()}
      enRafraichissement={q.isRefetching}
      pied={parent ? <Bouton titre="Déclarer une absence" icone="add" onPress={() => setFeuille({ mode: 'declarer' })} /> : undefined}
    >
      <SelecteurEnfant />
      {q.isPending && !d ? <Chargement /> : null}
      {q.isError && !d ? <Erreur erreur={q.error} reessayer={() => q.refetch()} /> : null}

      {nonPrevue ? (
        <Carte fond={c.dangerDoux} style={{ flexDirection: 'row', gap: 12 }}>
          <View style={{ width: 40, height: 40, borderRadius: 12, backgroundColor: c.danger, alignItems: 'center', justifyContent: 'center' }}>
            <Ionicons name="warning" size={20} color="#FFF" />
          </View>
          <View style={{ flex: 1, gap: 6 }}>
            <T v="h3" couleur={c.danger}>Absence non prévue aujourd’hui</T>
            <T v="petit">{nonPrevue.cours}, {nonPrevue.horaire}. Vous avez été prévenu automatiquement.</T>
            {parent ? <Bouton titre="Justifier maintenant" variante="danger" onPress={() => setFeuille({ mode: 'justifier', absence: nonPrevue })} style={{ height: 42 }} /> : null}
          </View>
        </Carte>
      ) : null}

      {d ? (
        <>
          <View style={{ flexDirection: 'row', gap: 10 }}>
            <Stat valeur={d.stats.absences} libelle="Absences" />
            <Stat valeur={d.stats.retards} libelle="Retards" detail={`${d.stats.minutes_retard} min`} />
            <Stat valeur={d.stats.non_justifiees} libelle="À justifier" couleur={d.stats.non_justifiees ? c.danger : c.ok} />
          </View>
          <Segments options={[{ cle: 'historique', titre: 'Historique' }, { cle: 'mensuel', titre: 'Récapitulatif mensuel' }]} valeur={onglet} onChange={setOnglet} />

          {onglet === 'historique' ? (
            d.items.length ? (
              d.items.map((a) => (
                <Carte key={a.id} style={{ flexDirection: 'row', gap: 12 }}>
                  <BoiteDate iso={a.date} fond={a.statut === 'NON_JUSTIFIEE' ? c.dangerDoux : undefined} texte={a.statut === 'NON_JUSTIFIEE' ? c.danger : undefined} />
                  <View style={{ flex: 1, gap: 3 }}>
                    <View style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 8 }}>
                      <T v="gras">{a.type === 'RETARD' ? `Retard · ${a.minutes ?? '?'} min` : 'Absence'}</T>
                      <BadgeAbsence a={a} />
                    </View>
                    <T v="petit" discret>{dateMoyenne(a.date)} · {a.horaire} · {a.cours}</T>
                    <T v="petit">Motif : <T v="petit" discret>{a.motif || 'Non renseigné'}</T></T>
                    {a.commentaire_admin ? <T v="petit" discret>Vie scolaire : {a.commentaire_admin}</T> : null}
                    {parent && a.justifiable ? (
                      <Pressable onPress={() => setFeuille({ mode: 'justifier', absence: a })} accessibilityRole="button" style={{ marginTop: 6, alignSelf: 'flex-start', borderWidth: 1.5, borderColor: c.accent, borderRadius: 10, paddingHorizontal: 12, height: 38, justifyContent: 'center' }}>
                        <T v="gras" couleur={c.accent} style={{ fontSize: 13 }}>Transmettre un justificatif</T>
                      </Pressable>
                    ) : null}
                  </View>
                </Carte>
              ))
            ) : (
              <Vide icone="happy-outline" titre="Aucune absence ni retard" texte="Bravo pour cette assiduité !" />
            )
          ) : (
            <Carte style={{ gap: 12 }}>
              {d.mensuel.map((m) => (
                <View key={m.mois} style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }} accessible accessibilityLabel={`${m.mois} : ${m.absences} absences, ${m.retards} retards`}>
                  <T v="petit" style={{ width: 76 }}>{m.mois}</T>
                  <View style={{ flex: 1, flexDirection: 'row', gap: 4 }}>
                    {m.absences + m.retards === 0 ? <T v="petit" couleur={c.ok}>Aucune</T> : (
                      <>
                        {m.absences ? <View style={{ flex: m.absences / maxMois }}><Barre valeur={1} max={1} couleur={c.danger} hauteur={14} /></View> : null}
                        {m.retards ? <View style={{ flex: m.retards / maxMois }}><Barre valeur={1} max={1} couleur={c.alerte} hauteur={14} /></View> : null}
                        <View style={{ flex: Math.max(0, 1 - (m.absences + m.retards) / maxMois) }} />
                      </>
                    )}
                  </View>
                  <T v="gras" style={{ width: 44, textAlign: 'right', fontSize: 13 }}>{m.absences} · {m.retards}</T>
                </View>
              ))}
              <View style={{ flexDirection: 'row', gap: 16 }}>
                <Legende couleur={c.danger} texte="Absences" />
                <Legende couleur={c.alerte} texte="Retards" />
              </View>
            </Carte>
          )}
        </>
      ) : null}

      <FeuilleJustification feuille={feuille} onClose={() => setFeuille(null)} onSucces={(m) => { setFeuille(null); toast(m); }} />
    </Ecran>
  );
}

function Stat({ valeur, libelle, detail, couleur }: { valeur: number; libelle: string; detail?: string; couleur?: string }) {
  return (
    <Carte style={{ flex: 1, alignItems: 'center', padding: 12 }}>
      <T v="chiffre" style={{ fontSize: 26 }} couleur={couleur}>{valeur}</T>
      <T v="petit" discret>{libelle}</T>
      {detail ? <T v="petit" discret style={{ fontSize: 11 }}>{detail}</T> : null}
    </Carte>
  );
}

const Legende = ({ couleur, texte }: { couleur: string; texte: string }) => (
  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
    <View style={{ width: 12, height: 12, borderRadius: 3, backgroundColor: couleur }} />
    <T v="petit" discret>{texte}</T>
  </View>
);

function FeuilleJustification({ feuille, onClose, onSucces }: {
  feuille: { mode: 'justifier'; absence: AbsenceItem } | { mode: 'declarer' } | null; onClose: () => void; onSucces: (m: string) => void;
}) {
  const { c } = useTheme();
  const { eleve } = useSession();
  const [motif, setMotif] = useState(MOTIFS[0]);
  const [commentaire, setCommentaire] = useState('');
  const [jour, setJour] = useState(1);
  const [fichier, setFichier] = useState<FichierJoint | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const action = useAction(async (a, _v: void) => {
    if (!feuille || !eleve) return;
    const texte = commentaire.trim() ? `${motif} — ${commentaire.trim()}` : motif;
    if (feuille.mode === 'justifier') await a.justifier(feuille.absence.id, texte, fichier);
    else await a.declarerAbsence(eleve.id, { date: isoJour(ajouterJours(new Date(), jour)), motif, commentaire }, fichier);
  }, ['absences', 'accueil']);

  async function photo(camera: boolean) {
    const fn = camera ? ImagePicker.launchCameraAsync : ImagePicker.launchImageLibraryAsync;
    if (camera) {
      const p = await ImagePicker.requestCameraPermissionsAsync();
      if (!p.granted) return setErreur('Autorisez l’appareil photo dans les réglages.');
    }
    const r = await fn({ mediaTypes: ['images'], quality: 0.6 });
    if (!r.canceled) {
      const a = r.assets[0];
      setFichier({ uri: a.uri, name: a.fileName ?? 'justificatif.jpg', mimeType: a.mimeType ?? 'image/jpeg', file: (a as any).file });
    }
  }
  async function document() {
    const r = await DocumentPicker.getDocumentAsync({ type: ['application/pdf', 'image/jpeg', 'image/png'], copyToCacheDirectory: true });
    if (!r.canceled) {
      const a = r.assets[0];
      if ((a.size ?? 0) > 5 * 1024 * 1024) return setErreur('Fichier trop volumineux (5 Mo maximum).');
      setFichier({ uri: a.uri, name: a.name, mimeType: a.mimeType ?? 'application/pdf', file: a.file });
    }
  }

  const fermer = () => {
    setFichier(null);
    setCommentaire('');
    setErreur(null);
    onClose();
  };

  return (
    <Feuille visible={!!feuille} onClose={fermer} titre={feuille?.mode === 'declarer' ? 'Déclarer une absence à venir' : 'Justifier l’absence'}>
      {feuille?.mode === 'justifier' ? (
        <T discret>{feuille.absence.type === 'RETARD' ? 'Retard' : 'Absence'} du {dateLongue(feuille.absence.date)} ({feuille.absence.horaire}, {feuille.absence.cours}).</T>
      ) : (
        <>
          <T discret>Prévenez l’établissement avant l’absence de {eleve?.prenom}.</T>
          <T v="petit" style={{ fontWeight: '700' }}>Date</T>
          <Puces>
            {[0, 1, 2, 3, 4, 5, 6].map((n) => (
              <Puce key={n} titre={n === 0 ? 'Aujourd’hui' : n === 1 ? 'Demain' : dateMoyenne(isoJour(ajouterJours(new Date(), n)))} actif={jour === n} onPress={() => setJour(n)} />
            ))}
          </Puces>
        </>
      )}
      <T v="petit" style={{ fontWeight: '700' }}>Motif</T>
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
        {MOTIFS.map((m) => <Puce key={m} titre={m} actif={motif === m} onPress={() => setMotif(m)} />)}
      </View>
      <Champ libelle="Commentaire (facultatif)" value={commentaire} onChangeText={setCommentaire} multiline maxLength={400} placeholder="Informations utiles, sans détail médical." />
      <T v="petit" style={{ fontWeight: '700' }}>Justificatif (facultatif)</T>
      {fichier ? (
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10, borderWidth: 1.5, borderColor: c.ok, borderRadius: rayon.m, padding: 12 }}>
          <Ionicons name="checkmark-circle" size={20} color={c.ok} />
          <T v="gras" style={{ flex: 1 }} numberOfLines={1}>{fichier.name}</T>
          <Pressable onPress={() => setFichier(null)} hitSlop={8} accessibilityRole="button"><T v="gras" couleur={c.danger}>Retirer</T></Pressable>
        </View>
      ) : (
        <View style={{ flexDirection: 'row', gap: 8 }}>
          <Bouton titre="Photo" icone="camera-outline" variante="secondaire" onPress={() => photo(true)} style={{ flex: 1, height: 48 }} />
          <Bouton titre="Galerie" icone="images-outline" variante="secondaire" onPress={() => photo(false)} style={{ flex: 1, height: 48 }} />
          <Bouton titre="PDF" icone="document-outline" variante="secondaire" onPress={document} style={{ flex: 1, height: 48 }} />
        </View>
      )}
      <T v="petit" discret>Les informations transmises sont chiffrées et visibles uniquement par vous et la vie scolaire.</T>
      {erreur || action.error ? <T v="petit" couleur={c.danger}>{erreur ?? action.error?.message}</T> : null}
      <Bouton
        titre="Envoyer à la vie scolaire"
        charge={action.isPending}
        onPress={() => action.mutate(undefined, { onSuccess: () => { fermer(); onSucces('Envoyé. Vous serez notifié de la validation.'); } })}
      />
    </Feuille>
  );
}
