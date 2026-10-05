/** Nouveau message : choix des destinataires autorisés, sujet, message. */
import Ionicons from '@expo/vector-icons/Ionicons';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useEffect, useMemo, useState } from 'react';
import { Pressable, TextInput, View } from 'react-native';

import { Avatar, Bouton, Carte, Champ, Chargement, Ecran, EnTete, Erreur, T, useToast } from '@/components/ui';
import { useAction, useDonnees } from '@/lib/requetes';
import { police, rayon } from '@/theme/couleurs';
import { useTheme } from '@/theme/Theme';

export default function NouveauMessage() {
  const { c } = useTheme();
  const router = useRouter();
  const toast = useToast();
  const params = useLocalSearchParams<{ a?: string; sujet?: string }>();
  const q = useDonnees(['contacts'], (a) => a.contacts());
  const [choisis, setChoisis] = useState<number[]>([]);
  const [filtre, setFiltre] = useState('');
  const [sujet, setSujet] = useState(params.sujet ?? '');
  const [texte, setTexte] = useState('');
  const [erreur, setErreur] = useState<string | undefined>();
  const envoyer = useAction((a, _v: void) => a.nouvelleConversation(choisis, sujet.trim(), texte.trim()), ['conversations']);

  useEffect(() => {
    if (params.a && q.data?.some((x) => String(x.id) === params.a)) setChoisis([Number(params.a)]);
  }, [params.a, q.data]);

  const contacts = useMemo(() => {
    const t = filtre.trim().toLowerCase();
    return (q.data ?? []).filter((x) => !t || `${x.nom} ${x.detail}`.toLowerCase().includes(t));
  }, [q.data, filtre]);

  function valider() {
    setErreur(undefined);
    if (!choisis.length) return setErreur('Choisissez au moins un destinataire.');
    if (!sujet.trim() || !texte.trim()) return setErreur('Le sujet et le message sont obligatoires.');
    envoyer.mutate(undefined, {
      onSuccess: (r) => {
        toast('Message envoyé');
        router.replace(`/conversation/${r.id}`);
      },
      onError: (e) => setErreur(e.message),
    });
  }

  return (
    <Ecran entete={<EnTete titre="Nouveau message" />} pied={<Bouton titre="Envoyer" icone="send" onPress={valider} charge={envoyer.isPending} />}>
      <View style={{ gap: 8 }}>
        <T v="petit" style={{ fontFamily: police.gras }}>Destinataires</T>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10, height: 46, borderRadius: rayon.m, borderWidth: 1.5, borderColor: c.ligne, backgroundColor: c.surface, paddingHorizontal: 12 }}>
          <Ionicons name="search" size={18} color={c.texte2} />
          <TextInput value={filtre} onChangeText={setFiltre} placeholder="Rechercher un enseignant, la vie scolaire…" placeholderTextColor={c.texte2} accessibilityLabel="Rechercher un destinataire" style={{ flex: 1, color: c.texte, fontFamily: police.moyen, fontSize: 14.5 }} />
        </View>
        {q.isPending ? <Chargement lignes={2} /> : null}
        {q.isError ? <Erreur erreur={q.error} reessayer={() => q.refetch()} /> : null}
        <Carte style={{ paddingVertical: 2, maxHeight: 280 }}>
          {contacts.map((x, i) => {
            const actif = choisis.includes(x.id);
            return (
              <Pressable
                key={x.id}
                onPress={() => setChoisis(actif ? choisis.filter((y) => y !== x.id) : [...choisis, x.id])}
                accessibilityRole="checkbox"
                accessibilityState={{ checked: actif }}
                style={{ flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 10, borderTopWidth: i ? 1 : 0, borderColor: c.ligne }}
              >
                <Avatar initiales={x.initiales} couleur={x.role === 'ADMIN' ? '#0B1F3A' : '#1D5BD8'} taille={38} />
                <View style={{ flex: 1 }}>
                  <T v="gras">{x.nom}</T>
                  <T v="petit" discret>{x.detail}</T>
                </View>
                <View style={{ width: 24, height: 24, borderRadius: 7, borderWidth: 2, borderColor: actif ? c.accent : c.ligne, backgroundColor: actif ? c.accent : 'transparent', alignItems: 'center', justifyContent: 'center' }}>
                  {actif ? <Ionicons name="checkmark" size={16} color="#FFF" /> : null}
                </View>
              </Pressable>
            );
          })}
        </Carte>
        <T v="petit" discret>Seuls les interlocuteurs autorisés par l’établissement apparaissent ici.</T>
      </View>
      <Champ libelle="Sujet" value={sujet} onChangeText={setSujet} maxLength={150} placeholder="ex. Rendez-vous, question sur un devoir…" />
      <Champ libelle="Message" value={texte} onChangeText={setTexte} multiline maxLength={5000} placeholder="Votre message" erreur={erreur} />
    </Ecran>
  );
}
