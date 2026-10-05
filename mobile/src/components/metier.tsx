/** Composants propres à la vie scolaire, réutilisés par plusieurs écrans. */
import Ionicons from '@expo/vector-icons/Ionicons';
import { Pressable, ScrollView, Text, View } from 'react-native';
import Svg, { Circle, Line, Polyline, Text as SvgText } from 'react-native-svg';

import { echeanceRelative, jourMois, note as fmtNote } from '@/lib/format';
import { useSession } from '@/lib/session';
import type { AbsenceItem, Cours, Devoir, StatutAbsence, StatutDevoir } from '@/lib/types';
import { police, rayon } from '@/theme/couleurs';
import { useTheme } from '@/theme/Theme';

import { Avatar, Badge, Carte, T } from './ui';

export const COULEURS_ENFANTS = ['#1D5BD8', '#13803F', '#7C3AED', '#C2410C'];

/** Sélecteur d'enfant (parents de plusieurs élèves). `sombre` : version pour bandeau bleu nuit. */
export function SelecteurEnfant({ surFond = false }: { surFond?: boolean }) {
  const { moi, eleve, choisirEleve } = useSession();
  const { c } = useTheme();
  if (!moi || moi.enfants.length < 2) return null;
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }} accessibilityRole="tablist" accessibilityLabel="Choisir l'enfant">
      {moi.enfants.map((e, i) => {
        const actif = e.id === eleve?.id;
        const texte = surFond ? (actif ? '#0B1F3A' : '#FFFFFF') : actif ? c.surPrimaire : c.texte;
        return (
          <Pressable
            key={e.id}
            onPress={() => choisirEleve(e.id)}
            accessibilityRole="tab"
            accessibilityState={{ selected: actif }}
            accessibilityLabel={`${e.prenom}, ${e.classe ?? ''}`}
            style={{
              height: 44, paddingLeft: 6, paddingRight: 14, borderRadius: 22, flexDirection: 'row', alignItems: 'center', gap: 8,
              backgroundColor: actif ? (surFond ? '#FFFFFF' : c.primaire) : 'transparent',
              borderWidth: 1, borderColor: surFond ? (actif ? '#FFFFFF' : 'rgba(255,255,255,0.3)') : actif ? c.primaire : c.ligne,
            }}
          >
            <Avatar initiales={e.initiales} couleur={COULEURS_ENFANTS[i % 4]} taille={32} />
            <Text style={{ color: texte, fontFamily: police.gras, fontSize: 13 }}>{e.prenom}</Text>
          </Pressable>
        );
      })}
    </ScrollView>
  );
}

export function CoursLigne({ cours, dernier }: { cours: Cours; dernier?: boolean }) {
  const { c } = useTheme();
  const annule = cours.statut === 'annule';
  return (
    <View
      accessible
      accessibilityLabel={`${cours.matiere} de ${cours.debut} à ${cours.fin}, ${cours.enseignant}, salle ${cours.salle}${cours.info ? ', ' + cours.info : ''}`}
      style={{ flexDirection: 'row', gap: 12, paddingVertical: 12, borderBottomWidth: dernier ? 0 : 1, borderColor: c.ligne }}
    >
      <View style={{ width: 50 }}>
        <T v="gras" style={{ fontSize: 13 }}>{cours.debut}</T>
        <T v="petit" discret>{cours.fin}</T>
      </View>
      <View style={{ width: 4, borderRadius: 2, backgroundColor: cours.couleur }} />
      <View style={{ flex: 1, opacity: annule ? 0.6 : 1, gap: 2 }}>
        <T v="gras" style={annule && { textDecorationLine: 'line-through' }}>{cours.matiere}</T>
        <T v="petit" discret>{cours.enseignant} · Salle {cours.salle || '—'}</T>
        {cours.statut !== 'normal' ? <Badge texte={cours.info} ton={annule ? 'danger' : 'alerte'} /> : null}
      </View>
    </View>
  );
}

const STATUTS_DEVOIR: Record<StatutDevoir, [string, 'info' | 'alerte' | 'ok' | 'danger']> = {
  a_faire: ['À faire', 'info'],
  en_cours: ['En cours', 'alerte'],
  termine: ['Terminé', 'ok'],
  en_retard: ['En retard', 'danger'],
};
export const libelleStatutDevoir = (s: StatutDevoir) => STATUTS_DEVOIR[s][0];
export const BadgeDevoir = ({ statut }: { statut: StatutDevoir }) => <Badge texte={STATUTS_DEVOIR[statut][0]} ton={STATUTS_DEVOIR[statut][1]} />;

export function DevoirCarte({ devoir, onPress }: { devoir: Devoir; onPress: () => void }) {
  const { c } = useTheme();
  return (
    <Carte onPress={onPress} libelle={`${devoir.matiere} : ${devoir.titre}, pour ${echeanceRelative(devoir.pour_le)}, ${libelleStatutDevoir(devoir.statut)}`} style={{ paddingVertical: 14 }}>
      <View style={{ flexDirection: 'row', gap: 12 }}>
        <View style={{ width: 6, borderRadius: 3, backgroundColor: devoir.couleur }} />
        <View style={{ flex: 1, gap: 2 }}>
          <T v="petit" discret>{devoir.matiere} · {devoir.enseignant}</T>
          <T v="gras" style={[{ fontSize: 15 }, devoir.statut === 'termine' && { textDecorationLine: 'line-through', color: c.texte2 }]}>{devoir.titre}</T>
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 2 }}>
            <Ionicons name="time-outline" size={14} color={c.texte2} />
            <T v="petit" discret>Pour {echeanceRelative(devoir.pour_le).toLowerCase()}</T>
            {devoir.piece_jointe ? <Ionicons name="attach" size={15} color={c.texte2} /> : null}
          </View>
        </View>
        <BadgeDevoir statut={devoir.statut} />
      </View>
    </Carte>
  );
}

const STATUTS_ABSENCE: Record<StatutAbsence, [string, 'danger' | 'alerte' | 'ok']> = {
  NON_JUSTIFIEE: ['Non justifiée', 'danger'],
  EN_ATTENTE: ['En attente', 'alerte'],
  JUSTIFIEE: ['Justifiée', 'ok'],
  REFUSEE: ['Refusée', 'danger'],
};
export const BadgeAbsence = ({ a }: { a: AbsenceItem }) => <Badge texte={STATUTS_ABSENCE[a.statut][0]} ton={STATUTS_ABSENCE[a.statut][1]} />;

export function BoiteDate({ iso, fond, texte }: { iso: string; fond?: string; texte?: string }) {
  const { c } = useTheme();
  const d = jourMois(iso.slice(0, 10));
  return (
    <View style={{ width: 50, height: 54, borderRadius: 14, backgroundColor: fond ?? c.surface2, alignItems: 'center', justifyContent: 'center' }}>
      <Text style={{ fontFamily: police.extra, fontSize: 18, color: texte ?? c.texte }}>{d.jour}</Text>
      <Text style={{ fontFamily: police.extra, fontSize: 10, color: texte ?? c.texte }}>{d.mois}</Text>
    </View>
  );
}

/** Courbe d'évolution de la moyenne (élève vs classe), échelle 0–20 resserrée automatiquement. */
export function GraphiqueEvolution({ points }: { points: { libelle: string; eleve: number; classe: number | null }[] }) {
  const { c } = useTheme();
  if (points.length === 0) return null;
  const L = 320;
  const H = 160;
  const valeurs = points.flatMap((p) => [p.eleve, p.classe ?? p.eleve]);
  const min = Math.max(0, Math.floor(Math.min(...valeurs) - 1));
  const max = Math.min(20, Math.ceil(Math.max(...valeurs) + 1));
  const X = (i: number) => (points.length === 1 ? L / 2 : 36 + (i * (L - 60)) / (points.length - 1));
  const Y = (v: number) => 14 + ((max - v) / Math.max(1, max - min)) * (H - 40);
  const graduations = [max, (max + min) / 2, min];
  const desc = points.map((p) => `${p.libelle} : ${fmtNote(p.eleve)}`).join(', ');
  return (
    <View accessible accessibilityLabel={`Évolution de la moyenne. ${desc}`}>
      <Svg width="100%" height={H} viewBox={`0 0 ${L} ${H}`}>
        {graduations.map((g) => (
          <Line key={g} x1={30} x2={L - 8} y1={Y(g)} y2={Y(g)} stroke={c.ligne} strokeWidth={1} />
        ))}
        {graduations.map((g) => (
          <SvgText key={'t' + g} x={0} y={Y(g) + 4} fontSize={11} fill={c.texte2}>{String(Math.round(g * 10) / 10).replace('.', ',')}</SvgText>
        ))}
        {points.some((p) => p.classe != null) ? (
          <Polyline points={points.map((p, i) => `${X(i)},${Y(p.classe ?? p.eleve)}`).join(' ')} fill="none" stroke={c.texte2} strokeWidth={2} strokeDasharray="5 5" />
        ) : null}
        <Polyline points={points.map((p, i) => `${X(i)},${Y(p.eleve)}`).join(' ')} fill="none" stroke={c.accent} strokeWidth={3} strokeLinejoin="round" strokeLinecap="round" />
        {points.map((p, i) => (
          <Circle key={i} cx={X(i)} cy={Y(p.eleve)} r={5} fill={c.surface} stroke={c.accent} strokeWidth={2.5} />
        ))}
        {points.map((p, i) => (
          <SvgText key={'l' + i} x={X(i)} y={H - 4} fontSize={11} fill={c.texte2} textAnchor="middle">{p.libelle}</SvgText>
        ))}
        {points.map((p, i) => (
          <SvgText key={'v' + i} x={X(i)} y={Y(p.eleve) - 10} fontSize={12} fontWeight="bold" fill={c.accent} textAnchor="middle">{fmtNote(p.eleve)}</SvgText>
        ))}
      </Svg>
      <View style={{ flexDirection: 'row', gap: 16, marginTop: 4 }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
          <View style={{ width: 16, height: 3, borderRadius: 2, backgroundColor: c.accent }} />
          <T v="petit" discret>Élève</T>
        </View>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
          <View style={{ width: 16, height: 0, borderTopWidth: 2, borderStyle: 'dashed', borderColor: c.texte2 }} />
          <T v="petit" discret>Moyenne de la classe</T>
        </View>
      </View>
    </View>
  );
}

/** Barre horizontale simple (comparaisons, récapitulatifs). */
export function Barre({ valeur, max, couleur, hauteur = 8 }: { valeur: number; max: number; couleur: string; hauteur?: number }) {
  const { c } = useTheme();
  return (
    <View style={{ height: hauteur, borderRadius: hauteur / 2, backgroundColor: c.surface2, overflow: 'hidden', flex: 1 }}>
      <View style={{ height: '100%', width: `${Math.max(0, Math.min(100, (valeur / max) * 100))}%`, backgroundColor: couleur, borderRadius: hauteur / 2 }} />
    </View>
  );
}

export function couleurNote(v: number | null | undefined, c: { ok: string; danger: string; texte: string }) {
  if (v == null) return c.texte;
  return v >= 14 ? c.ok : v < 10 ? c.danger : c.texte;
}

export const styleCarteListe = { paddingVertical: 4, borderRadius: rayon.l };
