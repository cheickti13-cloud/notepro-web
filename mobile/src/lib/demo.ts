/**
 * Mode démonstration : un établissement fictif complet, sans serveur.
 * Les dates sont calculées à partir d'aujourd'hui pour que l'app paraisse « vivante ».
 * Les actions (devoir terminé, message envoyé, paiement…) sont conservées en mémoire
 * le temps de la session.
 */
import type { ApiNotePro, Jetons } from './api';
import { ErreurApi } from './api';
import { ajouterJours, isoJour, lundiDe, versDate } from './format';
import type {
  Absences,
  Accueil,
  AbsenceItem,
  Contact,
  ConversationDetail,
  Cours,
  Devoir,
  EleveResume,
  Evenement,
  Frais,
  MatiereNotes,
  MessageItem,
  Moi,
  NotificationItem,
  Paiement,
  Releve,
  Role,
  Semaine,
} from './types';

const pause = (ms = 350) => new Promise((r) => setTimeout(r, ms));
const auj = () => new Date();
const jour = (n: number) => isoJour(ajouterJours(auj(), n));
const ilYa = (jours: number, h = 9, m = 0) => {
  const d = ajouterJours(auj(), -jours);
  d.setHours(h, m, 0, 0);
  return d.toISOString();
};

const COULEURS: Record<string, string> = {
  MATH: '#1D5BD8', FR: '#C2410C', ANG: '#0D9488', HG: '#7C3AED', SVT: '#13803F', PC: '#0369A1', EPS: '#B7791F', ESP: '#BE185D',
};
const NOMS: Record<string, string> = {
  MATH: 'Mathématiques', FR: 'Français', ANG: 'Anglais', HG: 'Histoire-Géographie', SVT: 'SVT', PC: 'Physique-Chimie', EPS: 'EPS', ESP: 'Espagnol',
};

const ENFANTS: EleveResume[] = [
  { id: 1, prenom: 'Aïcha', nom: 'Koné', initiales: 'AK', classe: '3e A' },
  { id: 2, prenom: 'Ibrahim', nom: 'Koné', initiales: 'IK', classe: '6e B' },
];

const PROFS: Record<number, Record<string, string>> = {
  1: { MATH: 'M. Kouassi', FR: 'Mme Diabaté', ANG: 'M. Adeyemi', HG: 'M. Traoré', SVT: 'Mme Bamba', PC: 'M. N’Guessan', EPS: 'M. Ouattara', ESP: 'Mme Sanogo' },
  2: { MATH: 'Mme Yao', FR: 'Mme Diabaté', ANG: 'Mme Achi', HG: 'M. Traoré', SVT: 'M. Konaté', PC: 'M. N’Guessan', EPS: 'M. Ouattara', ESP: 'Mme Sanogo' },
};

// ---------------------------------------------------------------------------
// Emploi du temps type (jour 0 = lundi)
// ---------------------------------------------------------------------------
type Modele = [string, string, string, string]; // début, fin, code, salle
const EDT: Record<number, Modele[][]> = {
  1: [
    [['07:30', '09:30', 'FR', 'A04'], ['09:45', '10:45', 'MATH', 'A04'], ['10:45', '12:15', 'PC', 'Labo 1'], ['15:00', '16:00', 'ESP', 'A07']],
    [['08:00', '09:00', 'SVT', 'Labo 2'], ['09:00', '10:00', 'MATH', 'A04'], ['10:15', '11:15', 'ANG', 'A07'], ['11:15', '12:15', 'HG', 'A04'], ['15:00', '17:00', 'EPS', 'Terrain']],
    [['07:30', '09:30', 'MATH', 'A04'], ['09:45', '11:45', 'FR', 'A04']],
    [['07:30', '08:30', 'ANG', 'A07'], ['08:30', '10:30', 'HG', 'A04'], ['10:45', '12:15', 'SVT', 'Labo 2'], ['15:00', '17:00', 'PC', 'Labo 1']],
    [['07:30', '09:30', 'FR', 'A04'], ['09:45', '10:45', 'ESP', 'A07'], ['10:45', '12:15', 'MATH', 'A04']],
    [],
  ],
  2: [
    [['08:00', '10:00', 'FR', 'C03'], ['10:15', '11:15', 'MATH', 'C05'], ['11:15', '12:15', 'SVT', 'Labo 1'], ['15:00', '16:00', 'ESP', 'C03']],
    [['07:30', '09:30', 'MATH', 'C05'], ['09:45', '11:45', 'HG', 'C03'], ['15:00', '17:00', 'EPS', 'Terrain']],
    [['07:30', '09:30', 'FR', 'C03'], ['09:45', '10:45', 'ANG', 'C04']],
    [['07:30', '09:30', 'PC', 'Labo 1'], ['09:45', '11:45', 'MATH', 'C05'], ['15:00', '16:00', 'ANG', 'C04']],
    [['07:30', '09:30', 'HG', 'C03'], ['09:45', '11:45', 'FR', 'C03']],
    [],
  ],
};

function coursDuJour(eleve: number, date: Date): Cours[] {
  const j = (date.getDay() + 6) % 7;
  const modeles = EDT[eleve]?.[j] ?? [];
  const estAuj = isoJour(date) === isoJour(auj());
  const dans2 = isoJour(date) === jour(2);
  return modeles.map(([debut, fin, code, salle], i) => {
    let statut: Cours['statut'] = 'normal';
    let info = '';
    let s = salle;
    if (estAuj && i === 1) {
      statut = 'modifie';
      s = 'B12';
      info = `Changement de salle : B12 au lieu de ${salle}`;
    }
    if (estAuj && i === 3) {
      statut = 'annule';
      info = 'Cours annulé — enseignant absent';
    }
    if (dans2 && i === 2) {
      statut = 'modifie';
      info = 'Remplacement : M. Konaté';
    }
    return {
      id: eleve * 1000 + j * 10 + i,
      date: isoJour(date),
      debut,
      fin,
      matiere: NOMS[code],
      couleur: COULEURS[code],
      enseignant: statut === 'modifie' && info.startsWith('Remplacement') ? 'M. Konaté' : PROFS[eleve][code],
      salle: s,
      classe: ENFANTS.find((e) => e.id === eleve)?.classe ?? '',
      statut,
      info,
    };
  });
}

// ---------------------------------------------------------------------------
// Notes (T1 terminé, T2 en cours, T3 à venir)
// ---------------------------------------------------------------------------
type Ev = [string, number, number, number, number, string]; // titre, il y a (jours), note, barème, coef, commentaire
const COEFS: Record<string, number> = { MATH: 4, FR: 4, ANG: 2, HG: 2, SVT: 2, PC: 2, ESP: 1, EPS: 1 };
const NOTES_T2: Record<number, Record<string, { evals: Ev[]; app: string }>> = {
  1: {
    MATH: { evals: [['Équations du 1er degré', 1, 17, 20, 1, 'Très bien, méthode claire.'], ['Devoir surveillé n°4', 12, 14.5, 20, 2, 'Justifier chaque étape.'], ['Théorème de Thalès', 21, 8, 10, 1, 'Bonne maîtrise.'], ['DM n°2 — Statistiques', 32, 18, 20, 1, 'Excellent travail.']], app: 'Excellent travail ce trimestre. Peut viser plus haut en soignant les justifications en géométrie.' },
    FR: { evals: [['Dictée n°6', 4, 13, 20, 1, ''], ['Rédaction — Portrait', 15, 14.5, 20, 2, 'Belle expression.'], ['Questions sur texte', 28, 13, 20, 1, '']], app: 'Nets progrès à l’écrit, bravo.' },
    ANG: { evals: [['Oral — My hometown', 6, 16, 20, 1, 'Very good!'], ['Test Unit 5', 19, 15.5, 20, 2, '']], app: 'Very good work, keep it up.' },
    HG: { evals: [['Les régions de Côte d’Ivoire', 9, 13.5, 20, 1, ''], ['Contrôle — Indépendances', 24, 13.5, 20, 2, '']], app: 'Sérieuse et appliquée.' },
    SVT: { evals: [['TP — Digestion', 7, 15, 20, 1, ''], ['Interrogation — Nutrition', 22, 13.5, 20, 1, '']], app: 'Bonne progression.' },
    PC: { evals: [['TP — Circuits électriques', 5, 8.5, 10, 1, 'Rigoureuse.'], ['Contrôle — Électricité', 20, 13.5, 20, 2, '']], app: 'Rigoureuse en TP comme en cours.' },
    ESP: { evals: [['Vocabulario', 10, 12, 20, 1, ''], ['Expresión escrita', 26, 13.5, 20, 1, '']], app: 'Attention au vocabulaire, à revoir.' },
    EPS: { evals: [['Athlétisme — 80 m', 13, 16.5, 20, 1, '']], app: 'Excellente attitude.' },
  },
  2: {
    MATH: { evals: [['Devoir surveillé n°4', 2, 9, 20, 2, 'Revoir les fractions.'], ['Nombres décimaux', 16, 12, 20, 1, '']], app: 'Des efforts à fournir, ne pas hésiter à poser des questions.' },
    FR: { evals: [['Conjugaison', 5, 12.5, 20, 1, ''], ['Lecture suivie', 18, 13, 20, 1, '']], app: 'Ensemble correct.' },
    ANG: { evals: [['Oral — My family', 6, 15, 20, 1, 'Good job!']], app: 'Bonne participation.' },
    HG: { evals: [['Les fleuves d’Afrique', 11, 11, 20, 1, '']], app: 'Apprendre les leçons plus régulièrement.' },
    SVT: { evals: [['La cellule', 7, 12, 20, 1, '']], app: 'Correct.' },
    PC: { evals: [['Les états de la matière', 14, 10.5, 20, 1, '']], app: 'Peut mieux faire.' },
    ESP: { evals: [['Saludos', 9, 13, 20, 1, '']], app: 'Bien.' },
    EPS: { evals: [['Football', 12, 14, 20, 1, '']], app: 'Bon esprit d’équipe.' },
  },
};
const MOY_T1: Record<number, Record<string, number>> = {
  1: { MATH: 15.0, FR: 12.5, ANG: 15.0, HG: 12.31, SVT: 13.0, PC: 14.5, ESP: 13.5, EPS: 16.0 },
  2: { MATH: 11.5, FR: 12.0, ANG: 14.0, HG: 12.0, SVT: 12.5, PC: 11.0, ESP: 12.0, EPS: 14.5 },
};
const MOY_CLASSE: Record<string, number> = { MATH: 12.1, FR: 11.8, ANG: 12.9, HG: 11.2, SVT: 12.4, PC: 11.6, ESP: 12.2, EPS: 14.8 };

const arrondi = (v: number) => Math.round(v * 100) / 100;
function moyenneMatiere(evals: Ev[]) {
  let t = 0;
  let p = 0;
  evals.forEach(([, , n, b, c]) => {
    t += (n / b) * 20 * c;
    p += c;
  });
  return p ? arrondi(t / p) : null;
}
function generale(moys: Record<string, number | null>) {
  let t = 0;
  let p = 0;
  Object.entries(moys).forEach(([k, v]) => {
    if (v != null) {
      t += v * COEFS[k];
      p += COEFS[k];
    }
  });
  return p ? arrondi(t / p) : null;
}

function releve(eleve: number, periode: number): Releve {
  const periodes = [
    { id: 1, nom: '1er trimestre', courante: false },
    { id: 2, nom: '2e trimestre', courante: true },
    { id: 3, nom: '3e trimestre', courante: false },
  ];
  const g1 = generale(MOY_T1[eleve]);
  const m2: Record<string, number | null> = {};
  Object.entries(NOTES_T2[eleve]).forEach(([k, v]) => (m2[k] = moyenneMatiere(v.evals)));
  const g2 = generale(m2);
  const evolution = [
    { periode: '1er trimestre', moyenne: g1 ?? 0, moyenne_classe: 11.95 },
    { periode: '2e trimestre', moyenne: g2 ?? 0, moyenne_classe: 12.1 },
  ];
  if (periode === 3) {
    return { periodes, periode_id: 3, moyenne_generale: null, moyenne_classe: null, rang: null, effectif: 42, matieres: [], evolution, bulletin_disponible: false };
  }
  const matieres: MatiereNotes[] = Object.keys(COEFS).map((code, i) => {
    const t2 = NOTES_T2[eleve][code];
    const evals = periode === 2 ? t2.evals : [];
    const moyenne = periode === 2 ? m2[code] : MOY_T1[eleve][code];
    return {
      id: eleve * 100 + i,
      matiere: NOMS[code],
      code,
      couleur: COULEURS[code],
      enseignant: PROFS[eleve][code],
      enseignant_id: 100 + i,
      coefficient: COEFS[code],
      moyenne,
      moyenne_classe: MOY_CLASSE[code],
      min: arrondi(MOY_CLASSE[code] - 6.3),
      max: arrondi(Math.min(19.5, MOY_CLASSE[code] + 5.8)),
      appreciation: periode === 2 ? t2.app : 'Bon trimestre.',
      evaluations: evals.map(([titre, ilya, n, b, c, com], k) => ({
        id: eleve * 10000 + i * 100 + k,
        titre,
        date: jour(-ilya),
        bareme: b,
        coefficient: c,
        note: n,
        statut: 'NOTEE',
        commentaire: com,
      })),
    };
  });
  return {
    periodes,
    periode_id: periode,
    moyenne_generale: periode === 2 ? g2 : g1,
    moyenne_classe: periode === 2 ? 12.1 : 11.95,
    rang: eleve === 1 ? (periode === 2 ? 7 : 9) : periode === 2 ? 21 : 18,
    effectif: eleve === 1 ? 42 : 45,
    matieres,
    evolution,
    bulletin_disponible: periode === 1,
  };
}

// ---------------------------------------------------------------------------
// État modifiable de la démo
// ---------------------------------------------------------------------------
const etat = {
  role: 'PARENT' as Role,
  statutsDevoirs: {} as Record<number, 'a_faire' | 'en_cours' | 'termine'>,
  justifiees: {} as Record<number, string>,
  declarees: [] as AbsenceItem[],
  messages: {} as Record<number, MessageItem[]>,
  lues: new Set<number>(),
  convLues: new Set<number>(),
  paiements: [] as Paiement[],
  nouvellesConv: [] as { id: number; sujet: string; dest: Contact[]; texte: string }[],
};

export function demoRole(r: Role) {
  etat.role = r;
}

function devoirs(eleve: number): Devoir[] {
  const p = PROFS[eleve];
  const base: [number, string, string, number, number, string, boolean][] = eleve === 1
    ? [
        [11, 'SVT', 'Compte rendu TP — Digestion', -8, -1, 'Rédiger le compte rendu du TP en suivant le plan donné en classe.', false],
        [12, 'PC', 'Exercices 4 à 7 p. 112', -1, 1, 'Exercices sur la loi d’Ohm. Calculatrice autorisée.', false],
        [13, 'ANG', 'Apprendre le vocabulaire Unit 6', -4, 1, 'Liste de vocabulaire p. 84.', true],
        [14, 'MATH', 'DM n°3 — Fonctions affines', -4, 2, 'Faire les exercices 1 à 4 de la fiche jointe. Tracer chaque représentation graphique dans un repère orthonormé (unité 1 cm). Exercice 4 : rédiger la démonstration en justifiant chaque étape.', true],
        [15, 'HG', 'Carte : les régions de Côte d’Ivoire', -5, 3, 'Compléter le fond de carte avec la légende.', true],
        [16, 'FR', 'Fiche de lecture — L’Enfant noir', -15, 6, 'Fiche de lecture complète (auteur, résumé, personnages, avis argumenté).', true],
        [17, 'ESP', 'Rédaction « Mi ciudad »', 0, 7, '10 lignes minimum.', false],
        [18, 'MATH', 'Fiche de révision — Compositions', 0, 10, 'Révisions des chapitres 1 à 6.', true],
      ]
    : [
        [21, 'HG', 'Exposé — Les fleuves d’Afrique', -6, 3, 'Exposé de 5 minutes en binôme.', false],
        [22, 'MATH', 'Exercices 12 à 15 p. 58', -1, 1, 'Fractions et nombres décimaux.', false],
        [23, 'FR', 'Conjugaison : le passé simple', -2, 2, 'Apprendre les verbes du 1er et 2e groupe.', false],
      ];
  const initial: Record<number, 'en_cours' | 'termine'> = { 13: 'termine', 14: 'en_cours', 16: 'en_cours' };
  return base.map(([id, code, titre, donne, pour, desc, pj]) => {
    const choisi = etat.statutsDevoirs[id] ?? initial[id] ?? 'a_faire';
    const pourLe = jour(pour);
    const statut = choisi === 'termine' ? 'termine' : pour < 0 ? 'en_retard' : choisi;
    return {
      id, matiere: NOMS[code], couleur: COULEURS[code], enseignant: p[code], enseignant_id: 100, titre,
      description: desc, donne_le: jour(donne), pour_le: pourLe, duree_estimee: code === 'MATH' ? 90 : 30, piece_jointe: pj, statut,
    };
  });
}

function absences(eleve: number): Absences {
  const base: AbsenceItem[] = eleve === 1
    ? [
        { id: 31, date: jour(0), horaire: '08:00 – 09:00', cours: 'SVT', type: 'ABSENCE', minutes: null, statut: 'NON_JUSTIFIEE', motif: '', justificatif: false, commentaire_admin: '', justifiable: true },
        { id: 32, date: jour(-5), horaire: '07:30', cours: 'Français', type: 'RETARD', minutes: 10, statut: 'JUSTIFIEE', motif: 'Problème de transport', justificatif: false, commentaire_admin: '', justifiable: false },
        { id: 33, date: jour(-11), horaire: 'Journée', cours: 'Tous les cours', type: 'ABSENCE', minutes: null, statut: 'JUSTIFIEE', motif: 'Raison médicale · certificat fourni', justificatif: true, commentaire_admin: '', justifiable: false },
        { id: 34, date: jour(-15), horaire: '07:30', cours: 'Français', type: 'RETARD', minutes: 5, statut: 'NON_JUSTIFIEE', motif: '', justificatif: false, commentaire_admin: '', justifiable: true },
        { id: 35, date: jour(-22), horaire: '15:00 – 17:00', cours: 'Espagnol, EPS', type: 'ABSENCE', minutes: null, statut: 'EN_ATTENTE', motif: 'Rendez-vous administratif', justificatif: true, commentaire_admin: '', justifiable: false },
      ]
    : [{ id: 41, date: jour(0), horaire: '08:00', cours: 'Français', type: 'RETARD', minutes: 10, statut: 'JUSTIFIEE', motif: 'Enregistré par la vie scolaire', justificatif: false, commentaire_admin: '', justifiable: false }];
  const items = [...etat.declarees.filter((a) => a.id % 2 === eleve % 2), ...base].map((a) =>
    etat.justifiees[a.id] ? { ...a, statut: 'EN_ATTENTE' as const, motif: etat.justifiees[a.id], justifiable: false } : a,
  );
  const abs = items.filter((a) => a.type === 'ABSENCE');
  const ret = items.filter((a) => a.type === 'RETARD');
  const d = auj();
  const mensuel = Array.from({ length: 7 }, (_, i) => {
    const m = new Date(d.getFullYear(), d.getMonth() - 6 + i, 1);
    const nom = m.toLocaleDateString('fr-FR', { month: 'short', year: 'numeric' });
    const dans = items.filter((a) => versDate(a.date).getMonth() === m.getMonth() && versDate(a.date).getFullYear() === m.getFullYear());
    const extra = eleve === 1 && i === 2 ? 1 : 0;
    return { mois: nom, absences: dans.filter((a) => a.type === 'ABSENCE').length + extra, retards: dans.filter((a) => a.type === 'RETARD').length };
  });
  return {
    stats: {
      absences: abs.length,
      retards: ret.length,
      non_justifiees: items.filter((a) => a.statut === 'NON_JUSTIFIEE' || a.statut === 'REFUSEE').length,
      en_attente: items.filter((a) => a.statut === 'EN_ATTENTE').length,
      minutes_retard: ret.reduce((t, a) => t + (a.minutes ?? 0), 0),
    },
    items,
    mensuel,
  };
}

const CONTACTS: Contact[] = [
  { id: 101, nom: 'Mme Diabaté', initiales: 'FD', role: 'ENSEIGNANT', detail: 'Professeure principale · Français' },
  { id: 102, nom: 'M. Kouassi', initiales: 'YK', role: 'ENSEIGNANT', detail: 'Mathématiques' },
  { id: 103, nom: 'M. Adeyemi', initiales: 'TA', role: 'ENSEIGNANT', detail: 'Anglais' },
  { id: 104, nom: 'Vie scolaire', initiales: 'VS', role: 'ADMIN', detail: 'Administration' },
  { id: 105, nom: 'Comptabilité', initiales: 'CP', role: 'ADMIN', detail: 'Frais de scolarité' },
  { id: 106, nom: 'Mme Yao', initiales: 'AY', role: 'ENSEIGNANT', detail: 'Mathématiques · 6e B' },
];

function conversationsBase(): ConversationDetail[] {
  const c = (id: number) => CONTACTS.find((x) => x.id === id)!;
  return [
    { id: 1, sujet: 'Réunion parents-professeurs', interlocuteurs: [c(101)], messages: [
      { id: 11, auteur: 'Mme Diabaté', de_moi: false, texte: 'Bonjour Madame Koné, je souhaiterais vous rencontrer lors de la réunion de samedi pour faire le point sur le trimestre d’Aïcha.', date: ilYa(1, 17, 40), lu: true, piece_jointe: null },
      { id: 12, auteur: 'Mariam Koné', de_moi: true, texte: 'Bonjour Madame, avec plaisir. Je serai présente à partir de 9h.', date: ilYa(1, 18, 5), lu: true, piece_jointe: null },
      { id: 13, auteur: 'Mme Diabaté', de_moi: false, texte: 'Parfait. Voici la fiche de suivi pour préparer l’échange.', date: ilYa(0, 9, 12), lu: false, piece_jointe: 'Fiche_suivi_Aicha.pdf' },
    ] },
    { id: 2, sujet: 'Absence de ce matin', interlocuteurs: [c(104)], messages: [
      { id: 21, auteur: 'Vie scolaire', de_moi: false, texte: 'Bonjour, Aïcha est absente depuis 8h en SVT. Merci de nous indiquer le motif ou de déposer un justificatif depuis l’application.', date: ilYa(0, 8, 14), lu: false, piece_jointe: null },
    ] },
    { id: 3, sujet: 'Calculatrice pour le DM', interlocuteurs: [c(102)], messages: [
      { id: 31, auteur: 'Mariam Koné', de_moi: true, texte: 'Bonjour Monsieur, Aïcha a-t-elle besoin d’une calculatrice particulière pour le DM n°3 ?', date: ilYa(2, 19, 2), lu: true, piece_jointe: null },
      { id: 32, auteur: 'M. Kouassi', de_moi: false, texte: 'Bonsoir, une calculatrice collège suffit. Merci pour votre retour.', date: ilYa(2, 20, 15), lu: true, piece_jointe: null },
    ] },
    { id: 4, sujet: 'Reçu de paiement', interlocuteurs: [c(105)], messages: [
      { id: 41, auteur: 'Comptabilité', de_moi: false, texte: 'Votre paiement de 150 000 FCFA (2e tranche) a bien été reçu. Le reçu est disponible dans la rubrique Frais.', date: ilYa(8, 10, 30), lu: true, piece_jointe: 'Recu_2027-0142.pdf' },
    ] },
    { id: 5, sujet: 'Oral d’anglais', interlocuteurs: [c(103)], messages: [
      { id: 51, auteur: 'M. Adeyemi', de_moi: false, texte: 'Good news: Aïcha’s oral presentation was excellent!', date: ilYa(4, 14, 22), lu: true, piece_jointe: null },
    ] },
  ];
}

function toutesConversations(): ConversationDetail[] {
  const base = conversationsBase().map((c) => ({ ...c, messages: [...c.messages, ...(etat.messages[c.id] ?? [])] }));
  const nouvelles = etat.nouvellesConv.map((n) => ({
    id: n.id,
    sujet: n.sujet,
    interlocuteurs: n.dest,
    messages: [{ id: n.id * 10, auteur: 'Moi', de_moi: true, texte: n.texte, date: new Date().toISOString(), lu: false, piece_jointe: null }, ...(etat.messages[n.id] ?? [])],
  }));
  return [...nouvelles, ...base];
}

function notifications(): NotificationItem[] {
  const n: NotificationItem[] = [
    { id: 1, type: 'ABSENCE', categorie: 'absences', priorite: 1, titre: 'Absence non prévue d’Aïcha en SVT (8h–9h)', lien: '/absences', lue: false, date: ilYa(0, 8, 12) },
    { id: 2, type: 'EDT', categorie: 'edt', priorite: 2, titre: 'Histoire-Géographie annulé aujourd’hui à 11h15', lien: '/emploi-du-temps', lue: false, date: ilYa(0, 7, 5) },
    { id: 3, type: 'EDT', categorie: 'edt', priorite: 3, titre: 'Mathématiques : salle B12 au lieu de A04', lien: '/emploi-du-temps', lue: false, date: ilYa(0, 7, 1) },
    { id: 4, type: 'NOTE', categorie: 'resultats', priorite: 3, titre: 'Nouvelle note en Mathématiques : Équations du 1er degré', lien: '/notes', lue: false, date: ilYa(1, 18, 30) },
    { id: 5, type: 'DEVOIR', categorie: 'devoirs', priorite: 2, titre: 'Nouveau devoir en Physique-Chimie pour demain', lien: '/devoirs', lue: true, date: ilYa(1, 16, 10) },
    { id: 6, type: 'ANNONCE', categorie: 'paiements', priorite: 2, titre: 'Rappel : 3e tranche à régler avant l’échéance', lien: '/frais', lue: true, date: ilYa(2, 9, 0) },
    { id: 7, type: 'ANNONCE', categorie: 'evenements', priorite: 3, titre: 'Réunion parents-professeurs samedi', lien: '/vie-scolaire', lue: true, date: ilYa(3, 10, 0) },
    { id: 8, type: 'ANNONCE', categorie: 'administration', priorite: 3, titre: 'Calendrier des compositions publié', lien: '/vie-scolaire', lue: true, date: ilYa(3, 9, 0) },
  ];
  return n.map((x) => (etat.lues.has(x.id) ? { ...x, lue: true } : x));
}

function evenements(): Evenement[] {
  const iso = (n: number, h = 9) => {
    const d = ajouterJours(auj(), n);
    d.setHours(h, 0, 0, 0);
    return d.toISOString();
  };
  return [
    { id: 1, titre: 'Réunion parents-professeurs', type: 'REUNION', debut: iso(4), fin: iso(4, 12), lieu: 'Salle polyvalente', description: 'Classes de 3e, de 9h à 12h.' },
    { id: 2, titre: 'Journée culturelle', type: 'CULTURE', debut: iso(10, 8), fin: null, lieu: 'Cour principale', description: 'Défilé, danses et gastronomie. Tenue traditionnelle bienvenue.' },
    { id: 3, titre: 'Compositions du trimestre', type: 'EXAMEN', debut: iso(13, 7), fin: iso(17, 12), lieu: 'Salles de classe', description: 'Calendrier détaillé dans les documents.' },
    { id: 4, titre: 'Vacances scolaires', type: 'VACANCES', debut: iso(18, 0), fin: iso(33, 0), lieu: '', description: 'Reprise des cours le lundi suivant.' },
    { id: 5, titre: 'Finale régionale de mathématiques', type: 'SORTIE', debut: iso(25, 6), fin: null, lieu: 'Yamoussoukro', description: 'Départ en car à 6h. Autorisation parentale requise.' },
  ];
}

function frais(eleve: number): Frais {
  const payes = etat.paiements.filter((p) => p.statut === 'CONFIRME');
  if (eleve === 2) {
    return {
      total: 390000, paye: 390000, reste: 0,
      echeances: [{ id: 21, libelle: 'Scolarité annuelle', categorie: 'SCOLARITE', montant: 390000, reste: 0, echeance: jour(-200), statut: 'payee' }],
      paiements: [{ id: 201, frais: 'Scolarité annuelle', montant: 390000, moyen: 'CB', moyen_libelle: 'Carte bancaire', statut: 'CONFIRME', reference: 'NP-8F2A91C0D3E1', numero_recu: '2026-0215', date: ilYa(200) }],
    };
  }
  const t3 = payes.some((p) => p.frais === '3e tranche de scolarité');
  const tr = payes.some((p) => p.frais === 'Transport scolaire');
  const echeances: Frais['echeances'] = [
    { id: 11, libelle: '1re tranche de scolarité', categorie: 'SCOLARITE', montant: 150000, reste: 0, echeance: jour(-185), statut: 'payee' },
    { id: 12, libelle: '2e tranche de scolarité', categorie: 'SCOLARITE', montant: 150000, reste: 0, echeance: jour(-60), statut: 'payee' },
    { id: 13, libelle: '3e tranche de scolarité', categorie: 'SCOLARITE', montant: 150000, reste: t3 ? 0 : 150000, echeance: jour(30), statut: t3 ? 'payee' : 'a_venir' },
    { id: 14, libelle: 'Transport scolaire', categorie: 'TRANSPORT', montant: 15000, reste: tr ? 0 : 15000, echeance: jour(14), statut: tr ? 'payee' : 'a_venir' },
  ];
  const total = echeances.reduce((t, e) => t + e.montant, 0);
  const reste = echeances.reduce((t, e) => t + e.reste, 0);
  return {
    total, paye: total - reste, reste, echeances,
    paiements: [
      ...etat.paiements.filter((p) => p.statut === 'CONFIRME'),
      { id: 102, frais: '2e tranche de scolarité', montant: 150000, moyen: 'WAVE', moyen_libelle: 'Wave', statut: 'CONFIRME', reference: 'NP-1C77AB09E2F4', numero_recu: '2027-0142', date: ilYa(60) },
      { id: 101, frais: '1re tranche de scolarité', montant: 150000, moyen: 'OM', moyen_libelle: 'Orange Money', statut: 'CONFIRME', reference: 'NP-55D0E3A1B7C2', numero_recu: '2026-0381', date: ilYa(185) },
    ],
  };
}

function moi(): Moi {
  const base = { email: '', doit_changer_mdp: false, etablissement: { nom: 'Groupe Scolaire Les Lauréats (démo)', annee: '2026-2027' }, preferences_push: {} };
  if (etat.role === 'ELEVE') {
    return { ...base, id: 2, username: 'aicha.kone', prenom: 'Aïcha', nom: 'Koné', initiales: 'AK', role: 'ELEVE', telephone_masque: '', enfants: [ENFANTS[0]] };
  }
  if (etat.role === 'ENSEIGNANT') {
    return { ...base, id: 3, username: 'y.kouassi', prenom: 'Yao', nom: 'Kouassi', initiales: 'YK', role: 'ENSEIGNANT', telephone_masque: '+225 07 •• •• 33 21', enfants: [] };
  }
  if (etat.role === 'ADMIN') {
    return { ...base, id: 4, username: 'direction', prenom: 'Awa', nom: 'Direction', initiales: 'AD', role: 'ADMIN', telephone_masque: '', enfants: [] };
  }
  return { ...base, id: 1, username: 'm.kone', prenom: 'Mariam', nom: 'Koné', initiales: 'MK', role: 'PARENT', telephone_masque: '+225 07 •• •• 18 90', enfants: ENFANTS };
}

function eleveValide(e: number) {
  const m = moi();
  if (!m.enfants.some((x) => x.id === e)) throw new ErreurApi("Vous n'avez pas accès à cette information.", 403);
}

export const apiDemo: ApiNotePro = {
  async connexion(identifiant: string, mdp: string): Promise<Jetons> {
    await pause(600);
    if (!identifiant.trim() || !mdp) throw new ErreurApi('Saisissez votre identifiant et votre mot de passe.', 400);
    return { access: 'demo', refresh: 'demo' };
  },
  async deconnexion() {},
  async moi() {
    await pause(200);
    return moi();
  },
  async changerMotDePasse(ancien: string, nouveau: string) {
    await pause();
    if (nouveau.length < 10) throw new ErreurApi('Le mot de passe doit contenir au moins 10 caractères.', 400);
  },
  async preferencesPush() {},
  async enregistrerAppareil() {},
  async accueil(eleve: number): Promise<Accueil> {
    await pause();
    eleveValide(eleve);
    const r = releve(eleve, 2);
    const dv = devoirs(eleve);
    const aRendre = dv.filter((d) => d.statut !== 'termine');
    const urgents = aRendre.filter((d) => d.pour_le <= jour(1));
    const ab = absences(eleve);
    const evo = r.evolution;
    return {
      eleve: ENFANTS.find((e) => e.id === eleve)!,
      moyenne: { valeur: r.moyenne_generale, classe: r.moyenne_classe, rang: r.rang, effectif: r.effectif, periode: '2e trimestre', evolution: arrondi(evo[1].moyenne - evo[0].moyenne) },
      prochaine_echeance: aRendre.find((d) => d.statut !== 'en_retard') ?? null,
      absences: { absences: ab.stats.absences, retards: ab.stats.retards, a_justifier: ab.stats.non_justifiees },
      devoirs: { a_rendre: aRendre.length, urgents: urgents.length },
      devoirs_urgents: urgents,
      dernieres_notes: r.matieres
        .flatMap((m) => m.evaluations.map((e) => ({ id: e.id, matiere: m.matiere, couleur: m.couleur, titre: e.titre, date: e.date, note: e.note, bareme: e.bareme, statut: 'NOTEE', sur20: e.note == null ? null : (e.note / e.bareme) * 20 })))
        .sort((a, b) => (a.date < b.date ? 1 : -1))
        .slice(0, 4),
      cours_du_jour: coursDuJour(eleve, auj()),
      notifications: notifications().filter((n) => !n.lue && n.priorite <= 2).slice(0, 3),
      evenements: evenements().slice(0, 3),
    };
  },
  async edt(eleve: number, semaine: string): Promise<Semaine> {
    await pause();
    eleveValide(eleve);
    const lundi = lundiDe(versDate(semaine));
    const noms = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi'];
    return {
      lundi: isoJour(lundi),
      jours: noms.slice(0, 5).map((nom, i) => {
        const d = ajouterJours(lundi, i);
        return { date: isoJour(d), nom, cours: coursDuJour(eleve, d) };
      }),
    };
  },
  async notes(eleve: number, periode?: number | null) {
    await pause();
    eleveValide(eleve);
    return releve(eleve, periode ?? 2);
  },
  async devoirs(eleve: number) {
    await pause();
    eleveValide(eleve);
    return devoirs(eleve);
  },
  async statutDevoir(devoir: number, statut) {
    await pause(200);
    etat.statutsDevoirs[devoir] = statut;
  },
  async absences(eleve: number) {
    await pause();
    eleveValide(eleve);
    return absences(eleve);
  },
  async justifier(absence: number, motif: string) {
    await pause(700);
    etat.justifiees[absence] = motif + ' · justificatif transmis';
  },
  async declarerAbsence(eleve: number, d) {
    await pause(700);
    etat.declarees.unshift({
      id: 900 + etat.declarees.length * 2 + (eleve % 2), date: d.date, horaire: 'Journée', cours: 'Tous les cours', type: 'ABSENCE',
      minutes: null, statut: 'EN_ATTENTE', motif: d.motif, justificatif: false, commentaire_admin: '', justifiable: false,
    });
  },
  async conversations() {
    await pause();
    return toutesConversations().map((c) => {
      const dernier = c.messages[c.messages.length - 1];
      return {
        id: c.id,
        sujet: c.sujet,
        interlocuteurs: c.interlocuteurs,
        dernier_message: dernier ? { texte: dernier.texte, date: dernier.date, de_moi: dernier.de_moi } : null,
        non_lu: !etat.convLues.has(c.id) && c.messages.some((m) => !m.de_moi && !m.lu),
      };
    }).sort((a, b) => ((a.dernier_message?.date ?? '') < (b.dernier_message?.date ?? '') ? 1 : -1));
  },
  async conversation(id: number) {
    await pause();
    etat.convLues.add(id);
    const c = toutesConversations().find((x) => x.id === id);
    if (!c) throw new ErreurApi('Conversation introuvable.', 404);
    return c;
  },
  async envoyerMessage(id: number, texte: string, fichier) {
    await pause(400);
    const m: MessageItem = { id: Date.now(), auteur: 'Moi', de_moi: true, texte: texte || 'Pièce jointe', date: new Date().toISOString(), lu: false, piece_jointe: fichier?.name ?? null };
    etat.messages[id] = [...(etat.messages[id] ?? []), m];
    return m;
  },
  async nouvelleConversation(destinataires: number[], sujet: string, texte: string) {
    await pause(500);
    const id = 100 + etat.nouvellesConv.length;
    etat.nouvellesConv.unshift({ id, sujet, texte, dest: CONTACTS.filter((c) => destinataires.includes(c.id)) });
    etat.convLues.add(id);
    return { id };
  },
  async contacts() {
    await pause(200);
    return CONTACTS;
  },
  async notifications() {
    await pause();
    return notifications();
  },
  async lireNotifications(ids) {
    (ids === 'tout' ? notifications().map((n) => n.id) : ids).forEach((i) => etat.lues.add(i));
  },
  async vieScolaire() {
    await pause();
    return {
      annonces: [
        { id: 1, titre: 'Nos élèves de 3e qualifiés pour la finale régionale de maths', contenu: 'Quatre élèves représenteront l’établissement à Yamoussoukro. Félicitations à toute l’équipe !', date: ilYa(4), importante: true },
        { id: 2, titre: 'Nouvelle bibliothèque numérique', contenu: '1 200 livres accessibles gratuitement depuis l’application.', date: ilYa(6), importante: false },
        { id: 3, titre: 'Campagne de vaccination', contenu: 'En partenariat avec le centre de santé de Cocody. Autorisation parentale requise.', date: ilYa(12), importante: false },
      ],
      evenements: evenements(),
      documents: [
        { id: 1, titre: 'Règlement intérieur 2026-2027', date: ilYa(190) },
        { id: 2, titre: 'Calendrier des compositions', date: ilYa(3) },
        { id: 3, titre: 'Liste des fournitures — 3e', date: ilYa(200) },
        { id: 4, titre: 'Autorisation parentale — sortie', date: ilYa(5) },
        { id: 5, titre: 'Menu de la cantine du mois', date: ilYa(10) },
      ],
    };
  },
  async frais(eleve: number) {
    await pause();
    eleveValide(eleve);
    return frais(eleve);
  },
  async payer(eleve: number, fraisId: number, moyen, telephone: string) {
    await pause(800);
    const f = frais(eleve).echeances.find((e) => e.id === fraisId);
    if (!f || f.reste === 0) throw new ErreurApi('Ces frais sont déjà réglés.', 400);
    const libelles: Record<string, string> = { OM: 'Orange Money', WAVE: 'Wave', MTN: 'MTN MoMo', MOOV: 'Moov Money', CB: 'Carte bancaire', ESPECES: 'Espèces' };
    const p: Paiement = {
      id: 300 + etat.paiements.length, frais: f.libelle, montant: f.reste, moyen, moyen_libelle: libelles[moyen], statut: 'EN_ATTENTE',
      reference: 'NP-DEMO' + Math.floor(Math.random() * 1e6), numero_recu: '', date: new Date().toISOString(),
    };
    etat.paiements.unshift(p);
    return {
      paiement: p,
      instructions: moyen === 'CB'
        ? { type: 'redirection', message: 'Vous allez être redirigé vers la page sécurisée 3-D Secure (simulation).' }
        : { type: 'validation_telephone', message: `Une demande de ${f.reste.toLocaleString('fr-FR')} FCFA a été envoyée au ${telephone}. Validez-la avec votre code secret ${libelles[moyen]} (simulation).` },
    };
  },
  async paiement(id: number) {
    await pause(1200);
    const p = etat.paiements.find((x) => x.id === id);
    if (!p) throw new ErreurApi('Paiement introuvable.', 404);
    p.statut = 'CONFIRME';
    p.numero_recu = p.numero_recu || '2027-0' + (198 + etat.paiements.length);
    return { ...p };
  },
  async lien() {
    return null;
  },
};
