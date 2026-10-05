/** Profil et paramètres : compte, enfants, notifications, sécurité, apparence, assistance. */
import { useRouter } from 'expo-router';
import { ReactNode, useEffect, useState } from 'react';
import { Alert, Linking, Platform, View } from 'react-native';

import { COULEURS_ENFANTS } from '@/components/metier';
import { Avatar, Badge, Bouton, Carte, Ecran, EnTete, Interrupteur, Ligne, Segments, Separateur, T, useToast } from '@/components/ui';
import { queryClient } from '@/lib/requetes';
import { useSession } from '@/lib/session';
import { prefs } from '@/lib/stockage';
import { ModeTheme, useTheme } from '@/theme/Theme';

const CATEGORIES: [string, string, string][] = [
  ['NOTE', 'Résultats scolaires', 'Nouvelles notes et bulletins'],
  ['ABSENCE', 'Absences et retards', 'Alerte immédiate en cas d’absence non prévue'],
  ['DEVOIR', 'Devoirs', 'Nouveaux devoirs et rappels'],
  ['EDT', 'Emploi du temps', 'Cours annulés, déplacés ou remplacés'],
  ['ANNONCE', 'Communications et paiements', 'Annonces, événements, échéances de frais'],
  ['MESSAGE', 'Messages', 'Nouveaux messages reçus'],
];

const ROLES: Record<string, string> = { PARENT: 'Parent', ELEVE: 'Élève', ENSEIGNANT: 'Enseignant', ADMIN: 'Administration' };

function confirmer(titre: string, message: string, action: () => void) {
  if (Platform.OS === 'web') {
    if (globalThis.confirm?.(`${titre}\n\n${message}`)) action();
    return;
  }
  Alert.alert(titre, message, [{ text: 'Annuler', style: 'cancel' }, { text: 'Confirmer', style: 'destructive', onPress: action }]);
}

export default function Profil() {
  const { c, mode, setMode } = useTheme();
  const router = useRouter();
  const toast = useToast();
  const { moi, etab, api, deconnexion, biometrie, rafraichirProfil } = useSession();
  const [push, setPush] = useState<Record<string, boolean>>(moi?.preferences_push ?? {});
  const [economie, setEconomie] = useState(false);

  useEffect(() => {
    prefs.lire('economieDonnees', false).then(setEconomie);
  }, []);

  if (!moi) return null;

  async function basculerPush(cle: string, v: boolean) {
    const p = { ...push, [cle]: v };
    setPush(p);
    try {
      await api.preferencesPush(p);
      rafraichirProfil().catch(() => undefined);
    } catch (e: any) {
      toast(e.message);
    }
  }

  return (
    <Ecran entete={<EnTete titre="Profil" retour={false} />}>
      <Carte style={{ flexDirection: 'row', alignItems: 'center', gap: 14 }}>
        <Avatar initiales={moi.initiales} couleur="#0B1F3A" taille={64} />
        <View style={{ flex: 1, gap: 2 }}>
          <T v="h2">{moi.prenom} {moi.nom}</T>
          <T v="petit" discret>{ROLES[moi.role]}{moi.telephone_masque ? ` · ${moi.telephone_masque}` : ''}</T>
          <Badge texte="Compte vérifié" ton="ok" />
        </View>
      </Carte>

      <Groupe titre="Établissement">
        <Ligne icone="business-outline" titre={moi.etablissement.nom} detail={`Année ${moi.etablissement.annee}`} />
        <Separateur />
        <Ligne
          icone="swap-horizontal-outline"
          titre="Changer d’établissement"
          detail="Vous serez déconnecté de cet espace"
          onPress={() => confirmer('Changer d’établissement', 'Vous allez être déconnecté.', async () => { await deconnexion(); router.replace('/etablissement'); })}
        />
      </Groupe>

      {moi.role === 'PARENT' ? (
        <Groupe titre="Mes enfants">
          {moi.enfants.map((e, i) => (
            <View key={e.id}>
              {i ? <Separateur /> : null}
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 10 }}>
                <Avatar initiales={e.initiales} couleur={COULEURS_ENFANTS[i % 4]} taille={38} />
                <View style={{ flex: 1 }}>
                  <T v="gras">{e.prenom} {e.nom}</T>
                  <T v="petit" discret>{e.classe ?? 'Sans classe'}</T>
                </View>
              </View>
            </View>
          ))}
          <Separateur />
          <Ligne icone="add-circle-outline" titre="Rattacher un enfant" detail="Avec le code remis par l’établissement" onPress={() => toast('Présentez-vous au secrétariat avec le code de rattachement.')} />
        </Groupe>
      ) : null}

      <Groupe titre="Notifications push">
        {CATEGORIES.map(([cle, titre, detail], i) => (
          <View key={cle}>
            {i ? <Separateur /> : null}
            <Ligne titre={titre} detail={detail} droite={<Interrupteur libelle={`Notifications : ${titre}`} valeur={push[cle] !== false} onChange={(v) => basculerPush(cle, v)} />} />
          </View>
        ))}
      </Groupe>

      <Groupe titre="Sécurité">
        {biometrie.dispo ? (
          <>
            <Ligne icone="finger-print" titre="Connexion biométrique" detail="Empreinte ou Face ID à l’ouverture" droite={<Interrupteur libelle="Connexion biométrique" valeur={biometrie.active} onChange={(v) => biometrie.activer(v)} />} />
            <Separateur />
          </>
        ) : null}
        <Ligne icone="key-outline" titre="Modifier le mot de passe" onPress={() => router.push('/mot-de-passe')} />
        <Separateur />
        <Ligne icone="shield-checkmark-outline" titre="Mes données personnelles" detail="Copie de vos données (RGPD) depuis l’espace web" onPress={() => (etab.api === 'demo' ? toast('Disponible sur l’espace web de l’établissement.') : Linking.openURL(etab.api + '/compte/'))} />
      </Groupe>

      <Groupe titre="Application">
        <View style={{ paddingVertical: 10, gap: 8 }}>
          <T v="gras">Apparence</T>
          <Segments<ModeTheme> options={[{ cle: 'systeme', titre: 'Automatique' }, { cle: 'clair', titre: 'Clair' }, { cle: 'sombre', titre: 'Sombre' }]} valeur={mode} onChange={setMode} />
        </View>
        <Separateur />
        <Ligne icone="language-outline" titre="Langue" detail="Français" droite={<Badge texte="English bientôt" ton="neutre" />} />
        <Separateur />
        <Ligne
          icone="cellular-outline"
          titre="Économiseur de données"
          detail="Moins de rafraîchissements automatiques"
          droite={<Interrupteur libelle="Économiseur de données" valeur={economie} onChange={(v) => { setEconomie(v); prefs.ecrire('economieDonnees', v); }} />}
        />
        <Separateur />
        <Ligne icone="cloud-download-outline" titre="Données hors connexion" detail="Les dernières données consultées restent disponibles sans Internet" />
        <Separateur />
        <Ligne icone="trash-outline" titre="Vider le cache" onPress={() => { queryClient.clear(); toast('Cache vidé. Les données seront rechargées.'); }} />
      </Groupe>

      <Groupe titre="Assistance">
        <Ligne icone="help-circle-outline" titre="Centre d’aide" detail="Questions fréquentes" onPress={() => toast('Centre d’aide : bientôt disponible dans l’application.')} />
        <Separateur />
        <Ligne icone="chatbubbles-outline" titre="Contacter l’établissement" detail="Via la messagerie sécurisée" onPress={() => router.push('/nouveau-message')} />
      </Groupe>

      <Bouton titre="Se déconnecter" variante="contour" icone="log-out-outline" onPress={() => confirmer('Déconnexion', 'Voulez-vous vous déconnecter ?', async () => { await deconnexion(); router.replace('/connexion'); })} />
      <T v="petit" discret style={{ textAlign: 'center' }}>NotePro 1.0.0{etab.api === 'demo' ? ' · mode démonstration' : ''}</T>
    </Ecran>
  );
}

function Groupe({ titre, children }: { titre: string; children: ReactNode }) {
  return (
    <View style={{ gap: 8 }}>
      <T v="legende" discret>{titre}</T>
      <Carte style={{ paddingVertical: 4 }}>{children}</Carte>
    </View>
  );
}
