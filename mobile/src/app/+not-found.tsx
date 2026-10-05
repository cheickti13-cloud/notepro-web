import { useRouter } from 'expo-router';

import { Ecran, Vide } from '@/components/ui';

export default function Introuvable() {
  const router = useRouter();
  return (
    <Ecran>
      <Vide icone="compass-outline" titre="Page introuvable" texte="Cet écran n’existe pas ou a été déplacé." action="Retour à l’accueil" onAction={() => router.replace('/')} />
    </Ecran>
  );
}
