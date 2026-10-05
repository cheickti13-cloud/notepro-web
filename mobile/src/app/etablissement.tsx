/** Choix de l'établissement (multi-établissements) et ajout d'un nouvel établissement par adresse. */
import Ionicons from '@expo/vector-icons/Ionicons';
import { useRouter } from 'expo-router';
import { useEffect, useState } from 'react';
import { Pressable, View } from 'react-native';

import { Bouton, Carte, Champ, Ecran, EnTete, Feuille, T, useToast } from '@/components/ui';
import { ajouterEtablissement, listerEtablissements, retirerEtablissement } from '@/lib/etablissements';
import { useSession } from '@/lib/session';
import type { Etablissement } from '@/lib/types';
import { police, rayon } from '@/theme/couleurs';
import { useTheme } from '@/theme/Theme';

export default function ChoixEtablissement() {
  const { c } = useTheme();
  const router = useRouter();
  const toast = useToast();
  const { etab, choisirEtab } = useSession();
  const [liste, setListe] = useState<Etablissement[]>([]);
  const [choix, setChoix] = useState(etab.id);
  const [ajout, setAjout] = useState(false);
  const [nom, setNom] = useState('');
  const [url, setUrl] = useState('');
  const [verif, setVerif] = useState(false);
  const [erreur, setErreur] = useState<string | undefined>();

  const charger = () => listerEtablissements().then(setListe);
  useEffect(() => {
    charger();
  }, []);

  async function ajouter() {
    setErreur(undefined);
    if (!url.trim()) return setErreur('Indiquez l’adresse communiquée par l’établissement.');
    setVerif(true);
    const e = await ajouterEtablissement(nom, url);
    try {
      // Vérifie que l'adresse répond bien comme un serveur NotePro
      const r = await fetch(e.api + '/api/moi/');
      if (r.status !== 401 && r.status !== 200) throw new Error();
    } catch {
      await retirerEtablissement(e.id);
      setVerif(false);
      return setErreur('Aucun serveur NotePro ne répond à cette adresse. Vérifiez-la et votre connexion.');
    }
    setVerif(false);
    setAjout(false);
    setNom('');
    setUrl('');
    await charger();
    setChoix(e.id);
    toast('Établissement ajouté');
  }

  return (
    <Ecran
      entete={<EnTete titre="Établissement" sousTitre="Choisissez votre école" />}
      pied={
        <Bouton
          titre="Continuer"
          onPress={() => {
            const e = liste.find((x) => x.id === choix);
            if (e) choisirEtab(e);
            router.back();
          }}
        />
      }
    >
      <T discret>Votre compte peut être rattaché à plusieurs établissements. Chaque établissement possède son propre espace sécurisé.</T>
      <View style={{ gap: 10 }} accessibilityRole="radiogroup">
        {liste.map((e) => {
          const actif = e.id === choix;
          return (
            <Pressable
              key={e.id}
              onPress={() => setChoix(e.id)}
              accessibilityRole="radio"
              accessibilityState={{ checked: actif }}
              style={{ flexDirection: 'row', alignItems: 'center', gap: 12, padding: 14, borderRadius: rayon.l, borderWidth: 2, borderColor: actif ? c.accent : c.ligne, backgroundColor: actif ? c.accentDoux : c.surface }}
            >
              <View style={{ width: 46, height: 46, borderRadius: 14, backgroundColor: c.surface2, alignItems: 'center', justifyContent: 'center' }}>
                <T v="gras" style={{ fontSize: 13 }}>{e.nom.split(' ').filter((m) => m.length > 2).slice(0, 3).map((m) => m[0]).join('').toUpperCase()}</T>
              </View>
              <View style={{ flex: 1 }}>
                <T v="gras">{e.nom}</T>
                <T v="petit" discret numberOfLines={1}>{e.ville}</T>
              </View>
              {e.id.startsWith('u') ? (
                <Pressable onPress={async () => { await retirerEtablissement(e.id); charger(); }} accessibilityLabel={`Retirer ${e.nom}`} hitSlop={8} style={{ padding: 8 }}>
                  <Ionicons name="trash-outline" size={20} color={c.texte2} />
                </Pressable>
              ) : null}
              <View style={{ width: 22, height: 22, borderRadius: 11, borderWidth: 2, borderColor: actif ? c.accent : c.ligne, alignItems: 'center', justifyContent: 'center' }}>
                {actif ? <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: c.accent }} /> : null}
              </View>
            </Pressable>
          );
        })}
      </View>
      <Carte onPress={() => setAjout(true)} libelle="Ajouter un établissement" style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
        <Ionicons name="add-circle-outline" size={24} color={c.accent} />
        <T v="gras" couleur={c.accent} style={{ fontFamily: police.gras }}>Ajouter un établissement</T>
      </Carte>

      <Feuille visible={ajout} onClose={() => setAjout(false)} titre="Ajouter un établissement">
        <T discret>Saisissez l’adresse fournie par votre établissement (sur la circulaire de rentrée ou par SMS).</T>
        <Champ libelle="Nom (facultatif)" value={nom} onChangeText={setNom} placeholder="ex. Lycée moderne de Bouaké" />
        <Champ libelle="Adresse du serveur" value={url} onChangeText={setUrl} autoCapitalize="none" autoCorrect={false} keyboardType="url" placeholder="notepro.mon-ecole.ci" erreur={erreur} />
        <Bouton titre="Ajouter" onPress={ajouter} charge={verif} />
      </Feuille>
    </Ecran>
  );
}
