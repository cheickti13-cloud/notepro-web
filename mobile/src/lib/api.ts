/**
 * Client de l'API NotePro.
 *
 * Deux implémentations du même contrat `ApiNotePro` :
 * - `ClientServeur` : un vrai serveur Django (JWT, renouvellement automatique du jeton)
 * - `apiDemo` (demo.ts) : données fictives en mémoire, pour essayer l'app sans serveur
 */
import type {
  Absences,
  Accueil,
  Contact,
  ConversationDetail,
  ConversationResume,
  Devoir,
  Etablissement,
  FichierJoint,
  Frais,
  MessageItem,
  Moi,
  MoyenPaiement,
  NotificationItem,
  Paiement,
  PaiementInitie,
  Releve,
  Semaine,
  StatutDevoir,
  VieScolaire,
} from './types';

export interface Jetons {
  access: string;
  refresh: string;
}

export interface ApiNotePro {
  connexion(identifiant: string, motDePasse: string): Promise<Jetons>;
  deconnexion(): Promise<void>;
  moi(): Promise<Moi>;
  changerMotDePasse(ancien: string, nouveau: string): Promise<void>;
  preferencesPush(p: Record<string, boolean>): Promise<void>;
  enregistrerAppareil(jeton: string, plateforme: string): Promise<void>;
  accueil(eleve: number): Promise<Accueil>;
  edt(eleve: number, semaine: string): Promise<Semaine>;
  notes(eleve: number, periode?: number | null): Promise<Releve>;
  devoirs(eleve: number): Promise<Devoir[]>;
  statutDevoir(devoir: number, statut: Exclude<StatutDevoir, 'en_retard'>): Promise<void>;
  absences(eleve: number): Promise<Absences>;
  justifier(absence: number, motif: string, fichier?: FichierJoint | null): Promise<void>;
  declarerAbsence(eleve: number, d: { date: string; motif: string; commentaire: string }, fichier?: FichierJoint | null): Promise<void>;
  conversations(): Promise<ConversationResume[]>;
  conversation(id: number): Promise<ConversationDetail>;
  envoyerMessage(id: number, texte: string, fichier?: FichierJoint | null): Promise<MessageItem>;
  nouvelleConversation(destinataires: number[], sujet: string, texte: string): Promise<{ id: number }>;
  contacts(): Promise<Contact[]>;
  notifications(): Promise<NotificationItem[]>;
  lireNotifications(ids: number[] | 'tout'): Promise<void>;
  vieScolaire(): Promise<VieScolaire>;
  frais(eleve: number): Promise<Frais>;
  payer(eleve: number, frais: number, moyen: MoyenPaiement, telephone: string): Promise<PaiementInitie>;
  paiement(id: number): Promise<Paiement>;
  /** Lien de téléchargement temporaire (bulletin, reçu, document…), ou null en démo. */
  lien(type: 'bulletin' | 'recu' | 'document' | 'devoir' | 'message' | 'justificatif', id: number, periode?: number): Promise<string | null>;
}

export class ErreurApi extends Error {
  constructor(message: string, public statut = 0, public horsLigne = false) {
    super(message);
  }
}

/** Messages d'erreur clairs pour l'utilisateur, selon le code HTTP. */
function messagePour(statut: number, detail?: string): string {
  if (detail) return detail;
  if (statut === 400) return 'Les informations envoyées sont incomplètes ou invalides.';
  if (statut === 401) return 'Votre session a expiré. Reconnectez-vous.';
  if (statut === 403) return "Vous n'avez pas accès à cette information.";
  if (statut === 404) return 'Élément introuvable.';
  if (statut === 429) return 'Trop de tentatives. Réessayez dans quelques minutes.';
  if (statut >= 500) return 'Le serveur de l’établissement rencontre un problème. Réessayez plus tard.';
  return 'Une erreur est survenue.';
}

type Corps = Record<string, unknown> | FormData | undefined;

export class ClientServeur implements ApiNotePro {
  private base: string;

  constructor(
    etab: Etablissement,
    private session: {
      jetons: () => Jetons | null;
      majJetons: (j: Jetons) => void;
      expiree: () => void;
    },
  ) {
    this.base = etab.api.replace(/\/+$/, '') + '/api';
  }

  private enCours: Promise<boolean> | null = null;

  /** Renouvelle le jeton d'accès (une seule requête à la fois). */
  private rafraichir(): Promise<boolean> {
    if (!this.enCours) {
      this.enCours = (async () => {
        const j = this.session.jetons();
        if (!j) return false;
        try {
          const r = await fetch(this.base + '/auth/rafraichir/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh: j.refresh }),
          });
          if (!r.ok) return false;
          const d = await r.json();
          this.session.majJetons({ access: d.access, refresh: d.refresh ?? j.refresh });
          return true;
        } catch {
          return false;
        } finally {
          setTimeout(() => (this.enCours = null), 0);
        }
      })();
    }
    return this.enCours;
  }

  private async req<T>(methode: string, chemin: string, corps?: Corps, auth = true, essai = 0): Promise<T> {
    const headers: Record<string, string> = { Accept: 'application/json' };
    const j = this.session.jetons();
    if (auth && j) headers.Authorization = `Bearer ${j.access}`;
    let body: BodyInit | undefined;
    if (corps instanceof FormData) body = corps;
    else if (corps) {
      headers['Content-Type'] = 'application/json';
      body = JSON.stringify(corps);
    }
    let r: Response;
    try {
      const ctrl = new AbortController();
      const minuteur = setTimeout(() => ctrl.abort(), 20000);
      r = await fetch(this.base + chemin, { method: methode, headers, body, signal: ctrl.signal });
      clearTimeout(minuteur);
    } catch {
      throw new ErreurApi('Connexion impossible. Vérifiez votre accès à Internet.', 0, true);
    }
    if (r.status === 401 && auth && essai === 0 && (await this.rafraichir())) {
      return this.req<T>(methode, chemin, corps, auth, 1);
    }
    if (r.status === 401 && auth) this.session.expiree();
    if (r.status === 204) return undefined as T;
    let donnees: any = null;
    try {
      donnees = await r.json();
    } catch {
      // réponse sans corps JSON
    }
    if (!r.ok) throw new ErreurApi(messagePour(r.status, donnees?.detail), r.status);
    return donnees as T;
  }

  private formulaire(champs: Record<string, string>, nomFichier: string, fichier?: FichierJoint | null): FormData {
    const f = new FormData();
    Object.entries(champs).forEach(([k, v]) => f.append(k, v));
    if (fichier) {
      if (fichier.file) f.append(nomFichier, fichier.file, fichier.name);
      else f.append(nomFichier, { uri: fichier.uri, name: fichier.name, type: fichier.mimeType } as unknown as Blob);
    }
    return f;
  }

  connexion = (identifiant: string, motDePasse: string) =>
    this.req<Jetons>('POST', '/auth/connexion/', { username: identifiant.trim(), password: motDePasse }, false);
  deconnexion = async () => {
    const j = this.session.jetons();
    if (j) await this.req('POST', '/auth/deconnexion/', { refresh: j.refresh }).catch(() => undefined);
  };
  moi = () => this.req<Moi>('GET', '/moi/');
  changerMotDePasse = (ancien: string, nouveau: string) => this.req<void>('POST', '/auth/mot-de-passe/', { ancien, nouveau });
  preferencesPush = (p: Record<string, boolean>) => this.req<void>('PUT', '/moi/preferences-push/', p);
  enregistrerAppareil = (jeton: string, plateforme: string) => this.req<void>('POST', '/appareils/', { jeton, plateforme });
  accueil = (e: number) => this.req<Accueil>('GET', `/eleves/${e}/accueil/`);
  edt = (e: number, semaine: string) => this.req<Semaine>('GET', `/eleves/${e}/emploi-du-temps/?semaine=${semaine}`);
  notes = (e: number, p?: number | null) => this.req<Releve>('GET', `/eleves/${e}/notes/${p ? `?periode=${p}` : ''}`);
  devoirs = (e: number) => this.req<Devoir[]>('GET', `/eleves/${e}/devoirs/`);
  statutDevoir = (d: number, statut: string) => this.req<void>('POST', `/devoirs/${d}/statut/`, { statut });
  absences = (e: number) => this.req<Absences>('GET', `/eleves/${e}/absences/`);
  justifier = (a: number, motif: string, fichier?: FichierJoint | null) =>
    this.req<void>('POST', `/absences/${a}/justifier/`, this.formulaire({ motif }, 'justificatif', fichier));
  declarerAbsence = (e: number, d: { date: string; motif: string; commentaire: string }, fichier?: FichierJoint | null) =>
    this.req<void>('POST', `/eleves/${e}/absences/declarer/`, this.formulaire(d, 'justificatif', fichier));
  conversations = () => this.req<ConversationResume[]>('GET', '/conversations/');
  conversation = (id: number) => this.req<ConversationDetail>('GET', `/conversations/${id}/`);
  envoyerMessage = (id: number, texte: string, fichier?: FichierJoint | null) =>
    this.req<MessageItem>('POST', `/conversations/${id}/`, this.formulaire({ texte }, 'piece_jointe', fichier));
  nouvelleConversation = (destinataires: number[], sujet: string, texte: string) =>
    this.req<{ id: number }>('POST', '/conversations/', { destinataires, sujet, texte });
  contacts = () => this.req<Contact[]>('GET', '/contacts/');
  notifications = () => this.req<NotificationItem[]>('GET', '/notifications/');
  lireNotifications = (ids: number[] | 'tout') =>
    this.req<void>('POST', '/notifications/lire/', ids === 'tout' ? { tout: true } : { ids });
  vieScolaire = () => this.req<VieScolaire>('GET', '/vie-scolaire/');
  frais = (e: number) => this.req<Frais>('GET', `/eleves/${e}/frais/`);
  payer = (e: number, frais: number, moyen: MoyenPaiement, telephone: string) =>
    this.req<PaiementInitie>('POST', `/eleves/${e}/paiements/`, { frais_id: frais, moyen, telephone });
  paiement = (id: number) => this.req<Paiement>('GET', `/paiements/${id}/`);
  lien = async (type: string, id: number, periode?: number) =>
    (await this.req<{ url: string }>('GET', `/liens/?type=${type}&id=${id}${periode ? `&periode=${periode}` : ''}`)).url;
}
