/** Frais de scolarité : solde, échéancier, historique, reçus et paiement Mobile Money / carte. */
import Ionicons from '@expo/vector-icons/Ionicons';
import { useQueryClient } from '@tanstack/react-query';
import * as WebBrowser from 'expo-web-browser';
import { ReactNode, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Pressable, Text, View } from 'react-native';

import { SelecteurEnfant } from '@/components/metier';
import { Badge, Bouton, Carte, Champ, Chargement, Ecran, EnTete, Erreur, Feuille, Section, T, useToast } from '@/components/ui';
import { dateLongue, dateMoyenne, fcfa } from '@/lib/format';
import { useDonnees } from '@/lib/requetes';
import { useSession } from '@/lib/session';
import type { MoyenPaiement, Paiement, PaiementInitie } from '@/lib/types';
import { police, rayon } from '@/theme/couleurs';
import { useTheme } from '@/theme/Theme';

const MOYENS: { cle: MoyenPaiement; nom: string; sigle: string; fond: string; texte: string; detail: string; mobile: boolean }[] = [
  { cle: 'OM', nom: 'Orange Money', sigle: 'OM', fond: '#FF7900', texte: '#000000', detail: 'Validation par code secret', mobile: true },
  { cle: 'WAVE', nom: 'Wave', sigle: 'W', fond: '#1DC8F2', texte: '#000000', detail: 'Validation dans l’app Wave', mobile: true },
  { cle: 'MTN', nom: 'MTN MoMo', sigle: 'MTN', fond: '#FFCB05', texte: '#000000', detail: 'Validation par code secret', mobile: true },
  { cle: 'MOOV', nom: 'Moov Money', sigle: 'MV', fond: '#0057A8', texte: '#FFFFFF', detail: 'Validation par code secret', mobile: true },
  { cle: 'CB', nom: 'Carte bancaire', sigle: 'CB', fond: '#0B1F3A', texte: '#FFFFFF', detail: 'Visa, Mastercard · 3-D Secure', mobile: false },
];

export default function Frais() {
  const { c } = useTheme();
  const toast = useToast();
  const { eleve, moi, api } = useSession();
  const parent = moi?.role === 'PARENT';
  const q = useDonnees(['frais', eleve?.id], (a) => a.frais(eleve!.id), { enabled: !!eleve });
  const [payer, setPayer] = useState(false);
  const d = q.data;
  const pct = d && d.total ? Math.round((d.paye / d.total) * 100) : 0;

  async function recu(p: Paiement) {
    const url = await api.lien('recu', p.id).catch(() => null);
    if (url) WebBrowser.openBrowserAsync(url);
    else toast(`Reçu n°${p.numero_recu} : disponible avec le serveur de l’établissement (mode démo).`);
  }

  return (
    <Ecran entete={<EnTete titre="Frais de scolarité" sousTitre={moi?.etablissement.annee ? `Année ${moi.etablissement.annee}` : undefined} />} rafraichir={() => q.refetch()} enRafraichissement={q.isRefetching}>
      <SelecteurEnfant />
      {q.isPending && !d ? <Chargement /> : null}
      {q.isError && !d ? <Erreur erreur={q.error} reessayer={() => q.refetch()} /> : null}

      {d ? (
        <>
          <Carte fond={c.hero} style={{ gap: 10 }}>
            <Text style={{ color: '#C9D7EE', fontFamily: police.gras, fontSize: 12.5 }}>Reste à payer · {eleve?.prenom}</Text>
            <Text style={{ color: '#FFF', fontFamily: police.extra, fontSize: 32, letterSpacing: -0.6 }}>{fcfa(d.reste)}</Text>
            <View accessibilityRole="progressbar" accessibilityValue={{ min: 0, max: 100, now: pct }} accessibilityLabel="Part des frais payée" style={{ height: 10, borderRadius: 5, backgroundColor: 'rgba(255,255,255,0.18)', overflow: 'hidden' }}>
              <View style={{ height: '100%', width: `${pct}%`, backgroundColor: '#4ADE80', borderRadius: 5 }} />
            </View>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
              <Text style={{ color: '#C9D7EE', fontFamily: police.semi, fontSize: 12.5 }}>Payé : <Text style={{ color: '#FFF', fontFamily: police.gras }}>{fcfa(d.paye)}</Text></Text>
              <Text style={{ color: '#C9D7EE', fontFamily: police.semi, fontSize: 12.5 }}>Total : {fcfa(d.total)}</Text>
            </View>
            {d.reste > 0 && parent ? (
              <Pressable onPress={() => setPayer(true)} accessibilityRole="button" style={{ height: 50, borderRadius: rayon.m, backgroundColor: '#FFF', alignItems: 'center', justifyContent: 'center', marginTop: 4 }}>
                <Text style={{ color: '#0B1F3A', fontFamily: police.extra, fontSize: 15 }}>Payer maintenant</Text>
              </Pressable>
            ) : d.reste === 0 ? (
              <View style={{ padding: 12, borderRadius: 12, backgroundColor: 'rgba(74,222,128,0.18)' }}>
                <Text style={{ color: '#B9F5CF', fontFamily: police.gras, textAlign: 'center' }}>Scolarité entièrement réglée. Merci !</Text>
              </View>
            ) : null}
          </Carte>

          <Section titre="Échéancier">
            <Carte style={{ paddingVertical: 2 }}>
              {d.echeances.map((e, i) => (
                <View key={e.id} style={{ flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 12, borderTopWidth: i ? 1 : 0, borderColor: c.ligne }}>
                  <View style={{ width: 36, height: 36, borderRadius: 18, backgroundColor: e.statut === 'payee' ? c.okDoux : e.statut === 'en_retard' ? c.dangerDoux : c.alerteDoux, alignItems: 'center', justifyContent: 'center' }}>
                    <Ionicons name={e.statut === 'payee' ? 'checkmark' : 'time-outline'} size={18} color={e.statut === 'payee' ? c.ok : e.statut === 'en_retard' ? c.danger : c.alerte} />
                  </View>
                  <View style={{ flex: 1 }}>
                    <T v="gras">{e.libelle}</T>
                    <T v="petit" discret>{e.statut === 'payee' ? 'Réglé' : `Avant le ${dateLongue(e.echeance)}`}</T>
                  </View>
                  <View style={{ alignItems: 'flex-end', gap: 3 }}>
                    <T v="gras">{fcfa(e.montant)}</T>
                    <Badge texte={e.statut === 'payee' ? 'Payée' : e.statut === 'en_retard' ? 'En retard' : 'À venir'} ton={e.statut === 'payee' ? 'ok' : e.statut === 'en_retard' ? 'danger' : 'alerte'} />
                  </View>
                </View>
              ))}
            </Carte>
            {d.reste > 0 ? (
              <View style={{ flexDirection: 'row', gap: 10, padding: 12, borderRadius: rayon.m, backgroundColor: c.alerteDoux }}>
                <Ionicons name="notifications-outline" size={18} color={c.alerte} />
                <T v="petit" couleur={c.alerte} style={{ flex: 1 }}>Rappel automatique 7 jours puis 2 jours avant chaque échéance.</T>
              </View>
            ) : null}
          </Section>

          <Section titre="Historique des paiements">
            <Carte style={{ paddingVertical: 2 }}>
              {d.paiements.length === 0 ? <T discret style={{ paddingVertical: 12 }}>Aucun paiement enregistré.</T> : null}
              {d.paiements.map((p, i) => {
                const m = MOYENS.find((x) => x.cle === p.moyen);
                return (
                  <View key={p.id} style={{ flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 12, borderTopWidth: i ? 1 : 0, borderColor: c.ligne }}>
                    <View style={{ width: 40, height: 40, borderRadius: 12, backgroundColor: m?.fond ?? c.surface2, alignItems: 'center', justifyContent: 'center' }}>
                      <Text style={{ color: m?.texte ?? c.texte, fontFamily: police.extra, fontSize: 11 }}>{m?.sigle ?? '€'}</Text>
                    </View>
                    <View style={{ flex: 1 }}>
                      <T v="gras">{p.frais}</T>
                      <T v="petit" discret>{dateMoyenne(p.date.slice(0, 10))} · {p.moyen_libelle}</T>
                    </View>
                    <View style={{ alignItems: 'flex-end' }}>
                      <T v="gras">{fcfa(p.montant)}</T>
                      {p.statut === 'CONFIRME' ? (
                        <Pressable onPress={() => recu(p)} accessibilityRole="button" accessibilityLabel={`Télécharger le reçu ${p.numero_recu}`} hitSlop={8}>
                          <T v="petit" couleur={c.accent}>Reçu PDF</T>
                        </Pressable>
                      ) : <Badge texte="En attente" ton="alerte" />}
                    </View>
                  </View>
                );
              })}
            </Carte>
          </Section>
        </>
      ) : null}

      {d ? <FeuillePaiement visible={payer} onClose={() => setPayer(false)} echeances={d.echeances.filter((e) => e.reste > 0)} /> : null}
    </Ecran>
  );
}

function FeuillePaiement({ visible, onClose, echeances }: { visible: boolean; onClose: () => void; echeances: { id: number; libelle: string; reste: number; echeance: string }[] }) {
  const { c } = useTheme();
  const qc = useQueryClient();
  const toast = useToast();
  const { api, eleve } = useSession();
  const [frais, setFrais] = useState<number | null>(null);
  const [moyen, setMoyen] = useState<MoyenPaiement>('OM');
  const [tel, setTel] = useState('');
  const [etape, setEtape] = useState<'choix' | 'attente' | 'succes'>('choix');
  const [initie, setInitie] = useState<PaiementInitie | null>(null);
  const [final, setFinal] = useState<Paiement | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [charge, setCharge] = useState(false);
  const actif = useRef(true);
  const choix = echeances.find((e) => e.id === frais) ?? echeances[0];
  const m = MOYENS.find((x) => x.cle === moyen)!;

  useEffect(() => {
    if (visible) {
      setEtape('choix');
      setErreur(null);
      setFrais(echeances[0]?.id ?? null);
    }
    actif.current = visible;
  }, [visible, echeances]);

  async function lancer() {
    if (!eleve || !choix) return;
    if (m.mobile && tel.replace(/\D/g, '').length < 8) return setErreur('Saisissez le numéro du compte qui va payer.');
    setErreur(null);
    setCharge(true);
    try {
      const r = await api.payer(eleve.id, choix.id, moyen, tel);
      setInitie(r);
      setEtape('attente');
      // Vérification régulière du statut auprès du serveur (le serveur fait foi, via le prestataire)
      for (let i = 0; i < 40 && actif.current; i++) {
        await new Promise((res) => setTimeout(res, i === 0 ? 1500 : 3000));
        const p = await api.paiement(r.paiement.id);
        if (p.statut === 'CONFIRME') {
          setFinal(p);
          setEtape('succes');
          qc.invalidateQueries({ predicate: (x) => x.queryKey.includes('frais') });
          return;
        }
        if (p.statut === 'ECHOUE' || p.statut === 'ANNULE') {
          setEtape('choix');
          return setErreur('Le paiement n’a pas abouti. Aucun montant n’a été débité.');
        }
      }
    } catch (e: any) {
      setErreur(e.message);
      setEtape('choix');
    } finally {
      setCharge(false);
    }
  }

  return (
    <Feuille visible={visible} onClose={onClose} titre={etape === 'succes' ? undefined : etape === 'attente' ? undefined : `Payer pour ${eleve?.prenom}`}>
      {etape === 'choix' ? (
        <>
          <T v="petit" style={{ fontFamily: police.gras }}>Ce que vous réglez</T>
          {echeances.map((e) => (
            <Option key={e.id} actif={choix?.id === e.id} onPress={() => setFrais(e.id)}>
              <View style={{ flex: 1 }}>
                <T v="gras">{e.libelle}</T>
                <T v="petit" discret>Avant le {dateLongue(e.echeance)}</T>
              </View>
              <T v="gras">{fcfa(e.reste)}</T>
            </Option>
          ))}
          <T v="petit" style={{ fontFamily: police.gras }}>Moyen de paiement</T>
          {MOYENS.map((x) => (
            <Option key={x.cle} actif={moyen === x.cle} onPress={() => setMoyen(x.cle)}>
              <View style={{ width: 40, height: 40, borderRadius: 12, backgroundColor: x.fond, alignItems: 'center', justifyContent: 'center' }}>
                <Text style={{ color: x.texte, fontFamily: police.extra, fontSize: 12 }}>{x.sigle}</Text>
              </View>
              <View style={{ flex: 1 }}>
                <T v="gras">{x.nom}</T>
                <T v="petit" discret>{x.detail}</T>
              </View>
            </Option>
          ))}
          {m.mobile ? <Champ libelle={`Numéro ${m.nom}`} keyboardType="phone-pad" value={tel} onChangeText={setTel} placeholder="+225 07 00 00 00 00" /> : null}
          {erreur ? <T v="petit" couleur={c.danger}>{erreur}</T> : null}
          <Bouton titre={choix ? `Payer ${fcfa(choix.reste)}` : 'Payer'} onPress={lancer} charge={charge} desactive={!choix} />
          <T v="petit" discret style={{ textAlign: 'center' }}>Paiement sécurisé via le prestataire agréé de l’établissement. NotePro ne conserve aucune donnée bancaire.</T>
        </>
      ) : null}

      {etape === 'attente' ? (
        <View style={{ alignItems: 'center', gap: 12, paddingVertical: 12 }}>
          <ActivityIndicator size="large" color={c.accent} />
          <T v="h2" style={{ textAlign: 'center' }}>{m.mobile ? 'Validez sur votre téléphone' : 'Paiement en cours'}</T>
          <T discret style={{ textAlign: 'center' }}>{initie?.instructions.message}</T>
          <Bouton titre="Annuler" variante="secondaire" onPress={onClose} style={{ alignSelf: 'stretch' }} />
        </View>
      ) : null}

      {etape === 'succes' && final ? (
        <View style={{ alignItems: 'center', gap: 10, paddingVertical: 8 }}>
          <View style={{ width: 72, height: 72, borderRadius: 36, backgroundColor: c.okDoux, alignItems: 'center', justifyContent: 'center' }}>
            <Ionicons name="checkmark" size={38} color={c.ok} />
          </View>
          <T v="h2">Paiement confirmé</T>
          <T discret style={{ textAlign: 'center' }}>{fcfa(final.montant)} réglés via {final.moyen_libelle}.{'\n'}Reçu n°{final.numero_recu} · Réf. {final.reference}</T>
          <Bouton titre="Terminer" onPress={() => { onClose(); toast('Merci ! Le reçu est disponible dans l’historique.'); }} style={{ alignSelf: 'stretch' }} />
        </View>
      ) : null}
    </Feuille>
  );
}

function Option({ actif, onPress, children }: { actif: boolean; onPress: () => void; children: ReactNode }) {
  const { c } = useTheme();
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="radio"
      accessibilityState={{ checked: actif }}
      style={{ flexDirection: 'row', alignItems: 'center', gap: 12, padding: 12, borderRadius: rayon.m, borderWidth: 2, borderColor: actif ? c.accent : c.ligne, backgroundColor: actif ? c.accentDoux : c.surface, minHeight: 60 }}
    >
      {children}
      <View style={{ width: 22, height: 22, borderRadius: 11, borderWidth: 2, borderColor: actif ? c.accent : c.ligne, alignItems: 'center', justifyContent: 'center' }}>
        {actif ? <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: c.accent }} /> : null}
      </View>
    </Pressable>
  );
}
