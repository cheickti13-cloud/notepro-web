/**
 * Session utilisateur : établissement choisi, jetons, profil, enfant sélectionné,
 * verrouillage biométrique.
 */
import { useQueryClient } from '@tanstack/react-query';
import * as LocalAuthentication from 'expo-local-authentication';
import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { Platform } from 'react-native';

import { ApiNotePro, ClientServeur, ErreurApi, Jetons } from './api';
import { apiDemo, demoRole } from './demo';
import { DEMO } from './etablissements';
import { obtenirJetonPush } from './push';
import { prefs, secret } from './stockage';
import type { EleveResume, Etablissement, Moi, Role } from './types';

type Statut = 'chargement' | 'reprise' | 'deconnecte' | 'verrouille' | 'connecte';

interface Session {
  statut: Statut;
  etab: Etablissement;
  api: ApiNotePro;
  moi: Moi | null;
  eleve: EleveResume | null;
  choisirEleve: (id: number) => void;
  choisirEtab: (e: Etablissement) => void;
  connexion: (identifiant: string, motDePasse: string, souvenir: boolean, role: Role) => Promise<void>;
  deconnexion: () => Promise<void>;
  deverrouiller: () => Promise<boolean>;
  rafraichirProfil: () => Promise<void>;
  biometrie: { dispo: boolean; active: boolean; activer: (v: boolean) => Promise<void> };
  messageSession: string | null;
}

const Ctx = createContext<Session | null>(null);

export async function biometrieDisponible(): Promise<boolean> {
  if (Platform.OS === 'web') return false;
  try {
    return (await LocalAuthentication.hasHardwareAsync()) && (await LocalAuthentication.isEnrolledAsync());
  } catch {
    return false;
  }
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const [statut, setStatut] = useState<Statut>('chargement');
  const [etab, setEtab] = useState<Etablissement>(DEMO);
  const [moi, setMoi] = useState<Moi | null>(null);
  const [eleveId, setEleveId] = useState<number | null>(null);
  const [bioDispo, setBioDispo] = useState(false);
  const [bioActive, setBioActive] = useState(false);
  const [messageSession, setMessageSession] = useState<string | null>(null);
  const jetons = useRef<Jetons | null>(null);
  const souvenir = useRef(true);

  const terminerLocalement = useCallback(async (message: string | null) => {
    jetons.current = null;
    await secret.supprimer('jetons');
    await prefs.supprimer('moi');
    qc.clear();
    setMoi(null);
    setMessageSession(message);
    setStatut('deconnecte');
  }, [qc]);

  const api = useMemo<ApiNotePro>(() => {
    if (etab.api === 'demo') return apiDemo;
    return new ClientServeur(etab, {
      jetons: () => jetons.current,
      majJetons: (j) => {
        jetons.current = j;
        if (souvenir.current) secret.ecrire('jetons', JSON.stringify(j));
      },
      expiree: () => {
        terminerLocalement('Votre session a expiré. Reconnectez-vous.');
      },
    });
  }, [etab, terminerLocalement]);

  const appliquerMoi = useCallback(async (m: Moi) => {
    setMoi(m);
    await prefs.ecrire('moi', m);
    const memorise = await prefs.lire<number | null>('eleve', null);
    const id = m.enfants.find((e) => e.id === memorise)?.id ?? m.enfants[0]?.id ?? null;
    setEleveId(id);
  }, []);

  const enregistrerPush = useCallback(async (a: ApiNotePro) => {
    const jeton = await obtenirJetonPush();
    if (jeton) a.enregistrerAppareil(jeton, Platform.OS).catch(() => undefined);
  }, []);

  /** Charge le profil ; hors connexion, reprend le dernier profil connu. */
  const chargerProfil = useCallback(async (a: ApiNotePro) => {
    try {
      await appliquerMoi(await a.moi());
    } catch (e) {
      const cache = await prefs.lire<Moi | null>('moi', null);
      if (e instanceof ErreurApi && e.horsLigne && cache) await appliquerMoi(cache);
      else throw e;
    }
  }, [appliquerMoi]);

  // Démarrage : reprise de la session mémorisée
  useEffect(() => {
    (async () => {
      setBioDispo(await biometrieDisponible());
      const bio = await prefs.lire('biometrie', false);
      setBioActive(bio);
      const e = await prefs.lire<Etablissement>('etab', DEMO);
      setEtab(e);
      if (e.api === 'demo') demoRole(await prefs.lire<Role>('demoRole', 'PARENT'));
      const brut = await secret.lire('jetons');
      if (!brut) return setStatut('deconnecte');
      jetons.current = JSON.parse(brut);
      setStatut(bio ? 'verrouille' : 'reprise');
    })();
  }, []);

  // Session reprise sans biométrie : on charge le profil dès que l'API correspondante est prête
  useEffect(() => {
    if (statut === 'reprise' && jetons.current) {
      chargerProfil(api)
        .then(() => {
          setStatut('connecte');
          enregistrerPush(api);
        })
        .catch(() => terminerLocalement(null));
    }
  }, [statut, api, chargerProfil, enregistrerPush, terminerLocalement]);

  const valeur: Session = {
    statut,
    etab,
    api,
    moi,
    eleve: moi?.enfants.find((e) => e.id === eleveId) ?? null,
    choisirEleve: (id) => {
      setEleveId(id);
      prefs.ecrire('eleve', id);
    },
    choisirEtab: (e) => {
      setEtab(e);
      prefs.ecrire('etab', e);
    },
    messageSession,
    async connexion(identifiant, motDePasse, garder, role) {
      setMessageSession(null);
      souvenir.current = garder;
      if (etab.api === 'demo') {
        demoRole(role);
        await prefs.ecrire('demoRole', role);
      }
      const j = await api.connexion(identifiant, motDePasse);
      jetons.current = j;
      if (garder) await secret.ecrire('jetons', JSON.stringify(j));
      else await secret.supprimer('jetons');
      await prefs.ecrire('etab', etab);
      await chargerProfil(api);
      setStatut('connecte');
      enregistrerPush(api);
    },
    async deconnexion() {
      await api.deconnexion().catch(() => undefined);
      await terminerLocalement(null);
    },
    async deverrouiller() {
      const r = await LocalAuthentication.authenticateAsync({
        promptMessage: 'Déverrouiller NotePro',
        cancelLabel: 'Annuler',
        fallbackLabel: 'Utiliser le code',
      });
      if (!r.success) return false;
      setStatut('reprise');
      return true;
    },
    async rafraichirProfil() {
      await chargerProfil(api);
    },
    biometrie: {
      dispo: bioDispo,
      active: bioActive,
      async activer(v) {
        if (v) {
          const r = await LocalAuthentication.authenticateAsync({ promptMessage: 'Activer la connexion biométrique' });
          if (!r.success) return;
        }
        setBioActive(v);
        await prefs.ecrire('biometrie', v);
      },
    },
  };

  return <Ctx.Provider value={valeur}>{children}</Ctx.Provider>;
}

export function useSession(): Session {
  const s = useContext(Ctx);
  if (!s) throw new Error('useSession doit être utilisé dans <SessionProvider>');
  return s;
}
