/** Changement du mot de passe (obligatoire à la première connexion, ou depuis le profil). */
import { Redirect, useRouter } from 'expo-router';
import { useState } from 'react';

import { Bouton, Champ, Ecran, EnTete, T, useToast } from '@/components/ui';
import { useSession } from '@/lib/session';

export default function MotDePasse() {
  const router = useRouter();
  const toast = useToast();
  const { api, moi, statut, rafraichirProfil } = useSession();
  const [ancien, setAncien] = useState('');
  const [nouveau, setNouveau] = useState('');
  const [confirme, setConfirme] = useState('');
  const [erreur, setErreur] = useState<string | undefined>();
  const [charge, setCharge] = useState(false);
  if (statut !== 'connecte') return <Redirect href="/" />;
  const oblige = !!moi?.doit_changer_mdp;

  async function valider() {
    setErreur(undefined);
    if (nouveau.length < 10) return setErreur('Au moins 10 caractères.');
    if (nouveau !== confirme) return setErreur('Les deux mots de passe ne correspondent pas.');
    setCharge(true);
    try {
      await api.changerMotDePasse(ancien, nouveau);
      await rafraichirProfil();
      toast('Mot de passe modifié');
      router.replace('/accueil');
    } catch (e: any) {
      setErreur(e.message);
    } finally {
      setCharge(false);
    }
  }

  return (
    <Ecran entete={<EnTete titre="Mot de passe" retour={!oblige} sousTitre={oblige ? 'Première connexion' : undefined} />} pied={<Bouton titre="Enregistrer" onPress={valider} charge={charge} />}>
      {oblige ? <T discret>Pour votre sécurité, remplacez le mot de passe provisoire remis par l’établissement par un mot de passe personnel.</T> : null}
      <Champ libelle="Mot de passe actuel" secureTextEntry value={ancien} onChangeText={setAncien} autoComplete="password" />
      <Champ libelle="Nouveau mot de passe" secureTextEntry value={nouveau} onChangeText={setNouveau} autoComplete="new-password" aide="10 caractères minimum, évitez les mots trop simples." />
      <Champ libelle="Confirmer le nouveau mot de passe" secureTextEntry value={confirme} onChangeText={setConfirme} erreur={erreur} />
    </Ecran>
  );
}
