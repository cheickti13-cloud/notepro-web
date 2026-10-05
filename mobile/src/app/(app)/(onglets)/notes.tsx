/** Notes et résultats : moyennes, évolution, comparaison entre trimestres, bulletin PDF. */
import Ionicons from '@expo/vector-icons/Ionicons';
import { useRouter } from 'expo-router';
import * as WebBrowser from 'expo-web-browser';
import { useEffect, useState } from 'react';
import { Text, View } from 'react-native';

import { Barre, couleurNote, GraphiqueEvolution, SelecteurEnfant } from '@/components/metier';
import { Badge, Bouton, Carte, Chargement, Ecran, EnTete, Erreur, Section, Segments, T, useToast, Vide } from '@/components/ui';
import { note, rang } from '@/lib/format';
import { useDonnees } from '@/lib/requetes';
import { useSession } from '@/lib/session';
import { police } from '@/theme/couleurs';
import { useTheme } from '@/theme/Theme';

export default function Notes() {
  const { c } = useTheme();
  const router = useRouter();
  const toast = useToast();
  const { api, eleve } = useSession();
  const [periode, setPeriode] = useState<number | null>(null);
  const q = useDonnees(['notes', eleve?.id, periode], (a) => a.notes(eleve!.id, periode), { enabled: !!eleve });
  const r = q.data;

  // Première réponse : on retient la période courante choisie par le serveur
  useEffect(() => {
    if (r && periode == null && r.periode_id) setPeriode(r.periode_id);
  }, [r, periode]);

  const idx = r?.periodes.findIndex((p) => p.id === r.periode_id) ?? -1;
  const precedente = idx > 0 ? r!.periodes[idx - 1] : null;
  const qPrec = useDonnees(['notes', eleve?.id, precedente?.id], (a) => a.notes(eleve!.id, precedente!.id), { enabled: !!eleve && !!precedente });
  const prec = new Map<string, number | null>((qPrec.data?.matieres ?? []).map((m) => [m.code, m.moyenne] as [string, number | null]));
  const [telechargement, setTelechargement] = useState(false);

  async function bulletin() {
    if (!eleve || !r?.periode_id) return;
    setTelechargement(true);
    try {
      const url = await api.lien('bulletin', eleve.id, r.periode_id);
      if (url) await WebBrowser.openBrowserAsync(url);
      else toast('Bulletin PDF disponible avec le serveur de l’établissement (mode démo).');
    } catch (e: any) {
      toast(e.message);
    } finally {
      setTelechargement(false);
    }
  }

  return (
    <Ecran entete={<EnTete titre="Notes et résultats" sousTitre={eleve ? `${eleve.prenom} ${eleve.nom} · ${eleve.classe ?? ''}` : undefined} retour={false} />} rafraichir={() => q.refetch()} enRafraichissement={q.isRefetching}>
      <SelecteurEnfant />
      {r ? <Segments options={r.periodes.map((p) => ({ cle: p.id, titre: p.nom.replace('trimestre', 'trim.').replace('semestre', 'sem.') }))} valeur={r.periode_id ?? 0} onChange={(p) => setPeriode(p)} /> : null}
      {q.isPending && !r ? <Chargement lignes={4} /> : null}
      {q.isError && !r ? <Erreur erreur={q.error} reessayer={() => q.refetch()} /> : null}

      {r && r.matieres.length === 0 ? (
        <Vide icone="bar-chart-outline" titre="Pas encore de notes sur cette période" texte="Les notes apparaîtront ici dès leur publication. Vous serez notifié à chaque nouvelle note." />
      ) : null}

      {r && r.matieres.length > 0 ? (
        <>
          <Carte fond={c.hero} style={{ gap: 8 }}>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
              <View>
                <Text style={{ color: '#C9D7EE', fontFamily: police.gras, fontSize: 12.5 }}>Moyenne générale</Text>
                <Text style={{ color: '#FFFFFF', fontFamily: police.extra, fontSize: 40, letterSpacing: -0.8 }}>
                  {note(r.moyenne_generale)}<Text style={{ fontSize: 16, color: '#C9D7EE' }}>/20</Text>
                </Text>
              </View>
              {r.rang != null ? (
                <View style={{ alignItems: 'flex-end' }}>
                  <Text style={{ color: '#C9D7EE', fontFamily: police.gras, fontSize: 12.5 }}>Rang</Text>
                  <Text style={{ color: '#FFFFFF', fontFamily: police.extra, fontSize: 22 }}>{rang(r.rang, r.effectif)}</Text>
                </View>
              ) : null}
            </View>
            <View style={{ flexDirection: 'row', gap: 8, flexWrap: 'wrap' }}>
              <Text style={{ color: '#FFFFFF', backgroundColor: 'rgba(255,255,255,0.14)', borderRadius: 10, paddingHorizontal: 10, paddingVertical: 4, fontFamily: police.gras, fontSize: 12.5, overflow: 'hidden' }}>Classe : {note(r.moyenne_classe)}</Text>
              {qPrec.data?.moyenne_generale != null && r.moyenne_generale != null ? (
                <Text style={{ color: '#B9F5CF', backgroundColor: 'rgba(91,217,139,0.2)', borderRadius: 10, paddingHorizontal: 10, paddingVertical: 4, fontFamily: police.gras, fontSize: 12.5, overflow: 'hidden' }}>
                  {r.moyenne_generale >= qPrec.data.moyenne_generale ? '+' : '−'}{note(Math.abs(r.moyenne_generale - qPrec.data.moyenne_generale))} depuis le {precedente?.nom}
                </Text>
              ) : null}
            </View>
          </Carte>

          {r.evolution.length > 1 ? (
            <Section titre="Évolution de la moyenne">
              <Carte>
                <GraphiqueEvolution points={r.evolution.map((e) => ({ libelle: e.periode.replace(' trimestre', '').replace('er', 'er'), eleve: e.moyenne, classe: e.moyenne_classe }))} />
              </Carte>
            </Section>
          ) : null}

          <Section titre="Par matière">
            {r.matieres.map((m) => {
              const avant = prec.get(m.code);
              const delta = avant != null && m.moyenne != null ? m.moyenne - avant : null;
              return (
                <Carte key={m.id} onPress={() => router.push({ pathname: '/matiere/[id]', params: { id: String(m.id), periode: String(r.periode_id) } })} libelle={`${m.matiere}, moyenne ${note(m.moyenne)} sur 20, coefficient ${m.coefficient}`} style={{ gap: 10 }}>
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
                    <View style={{ width: 40, height: 40, borderRadius: 12, backgroundColor: m.couleur, alignItems: 'center', justifyContent: 'center' }}>
                      <Text style={{ color: '#FFF', fontFamily: police.extra, fontSize: 11 }}>{m.code.slice(0, 4)}</Text>
                    </View>
                    <View style={{ flex: 1 }}>
                      <T v="gras">{m.matiere}</T>
                      <T v="petit" discret>Coef. {String(m.coefficient).replace('.', ',')} · Classe {note(m.moyenne_classe)}</T>
                    </View>
                    <View style={{ alignItems: 'flex-end', gap: 2 }}>
                      <T v="h2" couleur={couleurNote(m.moyenne, c)} style={{ fontSize: 18 }}>{note(m.moyenne)}</T>
                      {delta != null ? <Badge texte={`${delta >= 0 ? '+' : '−'}${note(Math.abs(delta))}`} ton={delta >= 0 ? 'ok' : 'alerte'} /> : null}
                    </View>
                  </View>
                  {avant != null && m.moyenne != null ? (
                    <View style={{ gap: 4 }}>
                      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                        <T v="petit" discret style={{ width: 54 }}>{precedente?.nom.replace(' trimestre', ' trim.')}</T>
                        <Barre valeur={avant} max={20} couleur={c.texte2} hauteur={6} />
                        <T v="petit" discret style={{ width: 40, textAlign: 'right' }}>{note(avant)}</T>
                      </View>
                      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                        <T v="petit" discret style={{ width: 54 }}>Actuel</T>
                        <Barre valeur={m.moyenne} max={20} couleur={m.couleur} hauteur={6} />
                        <T v="petit" discret style={{ width: 40, textAlign: 'right' }}>{note(m.moyenne)}</T>
                      </View>
                    </View>
                  ) : null}
                  {m.appreciation ? <T v="petit" discret style={{ fontStyle: 'italic' }}>« {m.appreciation} »</T> : null}
                </Carte>
              );
            })}
          </Section>

          <Carte style={{ gap: 10 }}>
            <View style={{ flexDirection: 'row', gap: 10, alignItems: 'center' }}>
              <Ionicons name="document-text-outline" size={22} color={c.accent} />
              <T v="h3">Bulletin scolaire</T>
            </View>
            <T v="petit" discret>{r.bulletin_disponible ? 'Bulletin validé par le conseil de classe.' : 'Le bulletin sera disponible après le conseil de classe.'}</T>
            <Bouton titre={r.bulletin_disponible ? 'Télécharger le bulletin (PDF)' : 'Bulletin bientôt disponible'} icone="download-outline" desactive={!r.bulletin_disponible} charge={telechargement} onPress={bulletin} />
          </Carte>
        </>
      ) : null}
    </Ecran>
  );
}
