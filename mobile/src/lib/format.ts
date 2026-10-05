/** Formats français : dates, nombres, montants. */
const JOURS = ['dimanche', 'lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi'];
const JOURS_COURTS = ['Dim.', 'Lun.', 'Mar.', 'Mer.', 'Jeu.', 'Ven.', 'Sam.'];
const MOIS = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre'];
const MOIS_COURTS = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.'];

/** "2027-03-16" -> Date locale (sans décalage de fuseau). */
export function versDate(iso: string): Date {
  if (/^\d{4}-\d{2}-\d{2}$/.test(iso)) {
    const [a, m, j] = iso.split('-').map(Number);
    return new Date(a, m - 1, j);
  }
  return new Date(iso);
}

export function isoJour(d: Date): string {
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

export function lundiDe(d: Date): Date {
  const r = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const j = (r.getDay() + 6) % 7;
  r.setDate(r.getDate() - j);
  return r;
}

export function ajouterJours(d: Date, n: number): Date {
  const r = new Date(d);
  r.setDate(r.getDate() + n);
  return r;
}

export const dateLongue = (iso: string) => {
  const d = versDate(iso);
  return `${JOURS[d.getDay()]} ${d.getDate() === 1 ? '1er' : d.getDate()} ${MOIS[d.getMonth()]} ${d.getFullYear()}`;
};
export const dateMoyenne = (iso: string) => {
  const d = versDate(iso);
  return `${JOURS_COURTS[d.getDay()]} ${d.getDate()} ${MOIS_COURTS[d.getMonth()]}`;
};
export const jourMois = (iso: string) => {
  const d = versDate(iso);
  return { jour: String(d.getDate()).padStart(2, '0'), mois: MOIS_COURTS[d.getMonth()].replace('.', '').toUpperCase() };
};
export const heure = (iso: string) => {
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
};

/** "Aujourd'hui", "Hier", "Lun. 15 mars"… pour les listes de messages et notifications. */
export function quand(iso: string): string {
  const d = new Date(iso);
  const auj = new Date();
  const diff = Math.round((lundiDe(auj).getTime() - lundiDe(d).getTime()) / 86400000);
  if (isoJour(d) === isoJour(auj)) return heure(iso);
  if (isoJour(d) === isoJour(ajouterJours(auj, -1))) return 'Hier';
  if (diff === 0) return JOURS_COURTS[d.getDay()];
  return `${d.getDate()} ${MOIS_COURTS[d.getMonth()]}`;
}

export function groupeDate(iso: string): string {
  const d = new Date(iso);
  const auj = new Date();
  if (isoJour(d) === isoJour(auj)) return "Aujourd'hui";
  if (isoJour(d) === isoJour(ajouterJours(auj, -1))) return 'Hier';
  if (lundiDe(d).getTime() === lundiDe(auj).getTime()) return 'Cette semaine';
  return 'Plus ancien';
}

/** Écart en jours entre aujourd'hui et une date AAAA-MM-JJ (positif = futur). */
export function joursAvant(iso: string): number {
  const auj = versDate(isoJour(new Date()));
  return Math.round((versDate(iso).getTime() - auj.getTime()) / 86400000);
}

export function echeanceRelative(iso: string): string {
  const n = joursAvant(iso);
  if (n < 0) return n === -1 ? 'Hier' : `Il y a ${-n} j`;
  if (n === 0) return "Aujourd'hui";
  if (n === 1) return 'Demain';
  if (n < 7) return dateMoyenne(iso);
  return dateMoyenne(iso);
}

/** 14.62 -> "14,62" ; null -> "—" */
export const note = (v: number | null | undefined, dec = 2) =>
  v == null ? '—' : v.toFixed(dec).replace('.', ',');

export const noteCourte = (v: number | null | undefined) => (v == null ? '—' : String(Math.round(v * 100) / 100).replace('.', ','));

export const fcfa = (n: number) => n.toLocaleString('fr-FR').replace(/ | /g, ' ') + ' FCFA';

export const rang = (r: number | null, effectif: number) => (r == null ? '—' : `${r}${r === 1 ? 'er' : 'e'} / ${effectif}`);
