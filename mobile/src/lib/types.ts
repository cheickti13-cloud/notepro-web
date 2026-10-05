/**
 * Types des données échangées avec l'API Django (`api/donnees.py`, `api/views.py`).
 * Toute modification d'un côté doit être reportée de l'autre.
 */

export type Role = 'ELEVE' | 'PARENT' | 'ENSEIGNANT' | 'ADMIN';

export interface Etablissement {
  id: string;
  nom: string;
  ville: string;
  /** URL du serveur NotePro, ou "demo" pour le mode démonstration intégré */
  api: string;
}

export interface EleveResume {
  id: number;
  prenom: string;
  nom: string;
  initiales: string;
  classe: string | null;
}

export interface Moi {
  id: number;
  username: string;
  prenom: string;
  nom: string;
  initiales: string;
  role: Role;
  email: string;
  telephone_masque: string;
  doit_changer_mdp: boolean;
  etablissement: { nom: string; annee: string };
  enfants: EleveResume[];
  preferences_push: Record<string, boolean>;
}

export type StatutCours = 'normal' | 'annule' | 'modifie';

export interface Cours {
  id: number;
  date: string; // AAAA-MM-JJ
  debut: string; // HH:MM
  fin: string;
  matiere: string;
  couleur: string;
  enseignant: string;
  salle: string;
  classe: string;
  statut: StatutCours;
  info: string;
}

export interface Semaine {
  lundi: string;
  jours: { date: string; nom: string; cours: Cours[] }[];
}

export interface NoteRecente {
  id: number;
  matiere: string;
  couleur: string;
  titre: string;
  date: string;
  note: number | null;
  bareme: number;
  statut: string;
  sur20: number | null;
}

export type StatutDevoir = 'a_faire' | 'en_cours' | 'termine' | 'en_retard';

export interface Devoir {
  id: number;
  matiere: string;
  couleur: string;
  enseignant: string;
  enseignant_id: number;
  titre: string;
  description: string;
  donne_le: string;
  pour_le: string;
  duree_estimee: number | null;
  piece_jointe: boolean;
  statut: StatutDevoir;
}

export interface NotificationItem {
  id: number;
  type: string;
  categorie: 'resultats' | 'absences' | 'devoirs' | 'edt' | 'administration' | 'evenements' | 'paiements' | 'messages';
  priorite: 1 | 2 | 3;
  titre: string;
  lien: string;
  lue: boolean;
  date: string;
}

export interface Evenement {
  id: number;
  titre: string;
  type: 'REUNION' | 'EXAMEN' | 'VACANCES' | 'SORTIE' | 'CULTURE' | 'AUTRE';
  debut: string; // ISO
  fin: string | null;
  lieu: string;
  description: string;
}

export interface Accueil {
  eleve: EleveResume;
  moyenne: { valeur: number | null; classe: number | null; rang: number | null; effectif: number; periode: string; evolution: number | null };
  prochaine_echeance: Devoir | null;
  absences: { absences: number; retards: number; a_justifier: number };
  devoirs: { a_rendre: number; urgents: number };
  devoirs_urgents: Devoir[];
  dernieres_notes: NoteRecente[];
  cours_du_jour: Cours[];
  notifications: NotificationItem[];
  evenements: Evenement[];
}

export interface Evaluation {
  id: number;
  titre: string;
  date: string;
  bareme: number;
  coefficient: number;
  note: number | null;
  statut: string | null;
  commentaire: string;
}

export interface MatiereNotes {
  id: number;
  matiere: string;
  code: string;
  couleur: string;
  enseignant: string;
  enseignant_id: number;
  coefficient: number;
  moyenne: number | null;
  moyenne_classe: number | null;
  min: number | null;
  max: number | null;
  appreciation: string;
  evaluations: Evaluation[];
}

export interface Releve {
  periodes: { id: number; nom: string; courante: boolean }[];
  periode_id: number | null;
  moyenne_generale: number | null;
  moyenne_classe: number | null;
  rang: number | null;
  effectif: number;
  matieres: MatiereNotes[];
  evolution: { periode: string; moyenne: number; moyenne_classe: number | null }[];
  bulletin_disponible?: boolean;
}

export type StatutAbsence = 'NON_JUSTIFIEE' | 'EN_ATTENTE' | 'JUSTIFIEE' | 'REFUSEE';

export interface AbsenceItem {
  id: number;
  date: string;
  horaire: string;
  cours: string;
  type: 'ABSENCE' | 'RETARD';
  minutes: number | null;
  statut: StatutAbsence;
  motif: string;
  justificatif: boolean;
  commentaire_admin: string;
  justifiable: boolean;
}

export interface Absences {
  stats: { absences: number; retards: number; non_justifiees: number; en_attente: number; minutes_retard: number };
  items: AbsenceItem[];
  mensuel: { mois: string; absences: number; retards: number }[];
}

export interface Contact {
  id: number;
  nom: string;
  initiales: string;
  role: Role;
  detail: string;
}

export interface ConversationResume {
  id: number;
  sujet: string;
  interlocuteurs: Contact[];
  dernier_message: { texte: string; date: string; de_moi: boolean } | null;
  non_lu: boolean;
}

export interface MessageItem {
  id: number;
  auteur: string;
  de_moi: boolean;
  texte: string;
  date: string;
  lu: boolean;
  piece_jointe: string | null;
}

export interface ConversationDetail {
  id: number;
  sujet: string;
  interlocuteurs: Contact[];
  messages: MessageItem[];
}

export interface VieScolaire {
  annonces: { id: number; titre: string; contenu: string; date: string; importante: boolean }[];
  evenements: Evenement[];
  documents: { id: number; titre: string; date: string }[];
}

export type MoyenPaiement = 'OM' | 'WAVE' | 'MTN' | 'MOOV' | 'CB' | 'ESPECES';

export interface Paiement {
  id: number;
  frais: string;
  montant: number;
  moyen: MoyenPaiement;
  moyen_libelle: string;
  statut: 'EN_ATTENTE' | 'CONFIRME' | 'ECHOUE' | 'ANNULE';
  reference: string;
  numero_recu: string;
  date: string;
}

export interface Frais {
  total: number;
  paye: number;
  reste: number;
  echeances: { id: number; libelle: string; categorie: string; montant: number; reste: number; echeance: string; statut: 'payee' | 'a_venir' | 'en_retard' }[];
  paiements: Paiement[];
}

export interface PaiementInitie {
  paiement: Paiement;
  instructions: { type: 'validation_telephone' | 'redirection'; message: string };
}

export interface FichierJoint {
  uri: string;
  name: string;
  mimeType: string;
  /** Sur le web, l'objet File fourni par le navigateur */
  file?: Blob;
}
