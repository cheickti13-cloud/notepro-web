/**
 * Établissements disponibles dans l'écran de choix.
 * Architecture multi-établissements : chaque établissement a son propre serveur
 * NotePro (ses données restent séparées). L'app peut en mémoriser plusieurs.
 */
import { prefs } from './stockage';
import type { Etablissement } from './types';

export const DEMO: Etablissement = {
  id: 'demo',
  nom: 'Groupe Scolaire Les Lauréats',
  ville: 'Cocody, Abidjan · démonstration',
  api: 'demo',
};

/** Serveur défini à la compilation (fichier .env : EXPO_PUBLIC_API_URL). */
const SERVEUR_ENV: Etablissement | null = process.env.EXPO_PUBLIC_API_URL
  ? { id: 'env', nom: 'Mon établissement', ville: process.env.EXPO_PUBLIC_API_URL, api: process.env.EXPO_PUBLIC_API_URL }
  : null;

export async function listerEtablissements(): Promise<Etablissement[]> {
  const perso = await prefs.lire<Etablissement[]>('etablissements', []);
  return [DEMO, ...(SERVEUR_ENV ? [SERVEUR_ENV] : []), ...perso];
}

export async function ajouterEtablissement(nom: string, url: string): Promise<Etablissement> {
  let propre = url.trim().replace(/\/+$/, '');
  if (!/^https?:\/\//.test(propre)) propre = 'https://' + propre;
  const e: Etablissement = { id: 'u' + Date.now(), nom: nom.trim() || 'Établissement', ville: propre.replace(/^https?:\/\//, ''), api: propre };
  const perso = await prefs.lire<Etablissement[]>('etablissements', []);
  await prefs.ecrire('etablissements', [...perso, e]);
  return e;
}

export async function retirerEtablissement(id: string) {
  const perso = await prefs.lire<Etablissement[]>('etablissements', []);
  await prefs.ecrire('etablissements', perso.filter((e) => e.id !== id));
}
