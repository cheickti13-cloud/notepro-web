/** Tableau de bord personnalisé selon le profil (parent, élève, enseignant, administration). */
import Ionicons from '@expo/vector-icons/Ionicons';
import { useRouter } from 'expo-router';
import * as WebBrowser from 'expo-web-browser';
import { ReactNode } from 'react';
import { Pressable, RefreshControl, ScrollView, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { BoiteDate, COULEURS_ENFANTS, CoursLigne, couleurNote, SelecteurEnfant } from '@/components/metier';
import { Avatar, Badge, BandeauHorsLigne, BoutonIcone, Carte, Chargement, Erreur, NomIcone, Section, T, Vide } from '@/components/ui';
import { dateLongue, echeanceRelative, heure, isoJour, note, noteCourte, rang } from '@/lib/format';
import { routePourLien } from '@/lib/liens';
import { useAction, useDonnees } from '@/lib/requetes';
import { useSession } from '@/lib/session';
import type { Cours } from '@/lib/types';
import { police, rayon } from '@/theme/couleurs';
import { useTheme } from '@/theme/Theme';

export default function Accueil() {
  const { moi } = useSession();
  if (moi?.role === 'PARENT' || moi?.role === 'ELEVE') return <TableauFamille />;
  return <TableauPersonnel />;
}

function enCeMoment(cours: Cours[]) {
  const maintenant = new Date();
  const hm = `${String(maintenant.getHours()).padStart(2, '0')}:${String(maintenant.getMinutes()).padStart(2, '0')}`;
  const actifs = cours.filter((c) => c.statut !== 'annule');
  return { actuel: actifs.find((c) => c.debut <= hm && hm < c.fin), suivant: actifs.find((c) => c.debut > hm) };
}

function TableauFamille() {
  const { c } = useTheme();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { moi, eleve, etab } = useSession();
  const estEleve = moi?.role === 'ELEVE';
  const q = useDonnees(['accueil', eleve?.id], (a) => a.accueil(eleve!.id), { enabled: !!eleve });
  const notifs = useDonnees(['notifications'], (a) => a.notifications(), { refetchInterval: 30000 });
  const nbNotifs = notifs.data?.filter((n) => !n.lue).length ?? 0;
  const statut = useAction((a, v: { id: number; fait: boolean }) => a.statutDevoir(v.id, v.fait ? 'termine' : 'a_faire'), ['accueil', 'devoirs']);
  const d = q.data;
  const indexEnfant = Math.max(0, moi?.enfants.findIndex((e) => e.id === eleve?.id) ?? 0);
  const { actuel, suivant } = enCeMoment(d?.cours_du_jour ?? []);

  return (
    <View style={{ flex: 1, backgroundColor: c.fond }}>
      <ScrollView
        contentContainerStyle={{ paddingBottom: 32 }}
        refreshControl={<RefreshControl refreshing={q.isRefetching} onRefresh={() => q.refetch()} tintColor={c.accent} />}
      >
        <View style={{ backgroundColor: c.hero, paddingTop: insets.top + 14, paddingHorizontal: 20, paddingBottom: 24, borderBottomLeftRadius: 28, borderBottomRightRadius: 28, gap: 16 }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
            <View style={{ flex: 1 }}>
              <Text style={{ color: '#C9D7EE', fontFamily: police.semi, fontSize: 13 }}>{dateLongue(isoJour(new Date())).replace(/^./, (x) => x.toUpperCase())}</Text>
              <Text style={{ color: '#FFFFFF', fontFamily: police.extra, fontSize: 21 }} accessibilityRole="header">{estEleve ? 'Salut' : 'Bonjour'} {moi?.prenom}</Text>
            </View>
            <Pressable onPress={() => router.push('/notifications')} accessibilityRole="button" accessibilityLabel={`Notifications, ${nbNotifs} non lues`} style={{ width: 44, height: 44, borderRadius: 14, backgroundColor: 'rgba(255,255,255,0.1)', borderWidth: 1, borderColor: 'rgba(255,255,255,0.18)', alignItems: 'center', justifyContent: 'center' }}>
              <Ionicons name="notifications-outline" size={22} color="#FFFFFF" />
              {nbNotifs ? (
                <View style={{ position: 'absolute', top: -5, right: -5, minWidth: 18, height: 18, borderRadius: 9, backgroundColor: c.pastille, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 4 }}>
                  <Text style={{ color: '#FFF', fontSize: 10.5, fontFamily: police.extra }}>{nbNotifs}</Text>
                </View>
              ) : null}
            </Pressable>
          </View>
          <SelecteurEnfant surFond />
          {eleve ? (
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 14 }}>
              <View style={{ borderWidth: 3, borderColor: 'rgba(255,255,255,0.85)', borderRadius: 33 }}>
                <Avatar initiales={eleve.initiales} couleur={COULEURS_ENFANTS[indexEnfant % 4]} taille={60} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={{ color: '#FFFFFF', fontFamily: police.extra, fontSize: 18 }}>{eleve.prenom} {eleve.nom}</Text>
                <Text style={{ color: '#C9D7EE', fontFamily: police.semi, fontSize: 13 }} numberOfLines={1}>{eleve.classe ?? 'Sans classe'} · {moi?.etablissement.nom ?? etab.nom}</Text>
              </View>
            </View>
          ) : null}
          {estEleve && (actuel || suivant) ? (
            <Pressable onPress={() => router.push('/emploi-du-temps')} accessibilityRole="button" style={{ flexDirection: 'row', alignItems: 'center', gap: 12, padding: 12, borderRadius: 16, backgroundColor: 'rgba(255,255,255,0.1)' }}>
              <View style={{ width: 9, height: 9, borderRadius: 5, backgroundColor: '#4ADE80' }} />
              <View style={{ flex: 1 }}>
                <Text style={{ color: '#C9D7EE', fontFamily: police.gras, fontSize: 12 }}>{actuel ? `En ce moment · jusqu’à ${actuel.fin}` : `Prochain cours · ${suivant!.debut}`}</Text>
                <Text style={{ color: '#FFFFFF', fontFamily: police.extra }}>{(actuel ?? suivant)!.matiere} · Salle {(actuel ?? suivant)!.salle}</Text>
              </View>
            </Pressable>
          ) : null}
        </View>
        <BandeauHorsLigne />

        <View style={{ padding: 20, gap: 24 }}>
          {q.isPending && !d ? <Chargement lignes={4} /> : null}
          {q.isError && !d ? <Erreur erreur={q.error} reessayer={() => q.refetch()} /> : null}
          {!eleve && moi ? <Vide icone="people-outline" titre="Aucun élève associé" texte="Contactez l’établissement pour rattacher votre enfant à votre compte." /> : null}

          {d ? (
            <>
              <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 12 }}>
                <Carte onPress={() => router.push('/notes')} libelle={`Moyenne générale ${note(d.moyenne.valeur)}`} style={{ width: '100%', flexDirection: 'row', alignItems: 'center', gap: 12 }}>
                  <View style={{ flex: 1 }}>
                    <T v="petit" discret>Moyenne générale · {d.moyenne.periode}</T>
                    <View style={{ flexDirection: 'row', alignItems: 'baseline', gap: 8 }}>
                      <T v="chiffre" style={{ fontSize: 34 }}>{note(d.moyenne.valeur)}</T>
                      <T v="gras" discret>/20</T>
                      {d.moyenne.evolution != null ? <Badge texte={`${d.moyenne.evolution >= 0 ? '+' : '−'}${note(Math.abs(d.moyenne.evolution))} vs trim. préc.`} ton={d.moyenne.evolution >= 0 ? 'ok' : 'alerte'} /> : null}
                    </View>
                    <T v="petit" discret>Classe : {note(d.moyenne.classe)} · Rang {rang(d.moyenne.rang, d.moyenne.effectif)}</T>
                  </View>
                  <Ionicons name="chevron-forward" size={20} color={c.texte2} />
                </Carte>
                <Tuile titre="Prochaine échéance" onPress={() => d.prochaine_echeance && router.push(`/devoirs/${d.prochaine_echeance.id}`)}>
                  <T v="gras" numberOfLines={2}>{d.prochaine_echeance?.titre ?? 'Rien à rendre'}</T>
                  {d.prochaine_echeance ? <><T v="petit" discret numberOfLines={1}>{d.prochaine_echeance.matiere}</T><Badge texte={echeanceRelative(d.prochaine_echeance.pour_le)} ton="alerte" /></> : null}
                </Tuile>
                <Tuile titre="Absences · retards" onPress={() => router.push('/absences')}>
                  <T v="chiffre" style={{ fontSize: 24 }}>{d.absences.absences} · {d.absences.retards}</T>
                  <Badge texte={d.absences.a_justifier ? `${d.absences.a_justifier} à justifier` : 'Tout est justifié'} ton={d.absences.a_justifier ? 'danger' : 'ok'} />
                </Tuile>
                <Tuile titre="Devoirs à rendre" onPress={() => router.push('/devoirs')}>
                  <T v="chiffre" style={{ fontSize: 24 }}>{d.devoirs.a_rendre}</T>
                  <Badge texte={d.devoirs.urgents ? `${d.devoirs.urgents} pour demain` : 'Aucun urgent'} ton={d.devoirs.urgents ? 'danger' : 'info'} />
                </Tuile>
                <Tuile titre="Notifications" onPress={() => router.push('/notifications')}>
                  <T v="chiffre" style={{ fontSize: 24 }}>{nbNotifs}</T>
                  <Badge texte={`${d.notifications.length} importante${d.notifications.length > 1 ? 's' : ''}`} ton="info" />
                </Tuile>
              </View>

              {d.devoirs_urgents.length ? (
                <Section titre="Devoirs urgents" action="Tous les devoirs" onAction={() => router.push('/devoirs')}>
                  <Carte style={{ paddingVertical: 4 }}>
                    {d.devoirs_urgents.map((dv, i) => {
                      const fait = dv.statut === 'termine';
                      return (
                        <View key={dv.id} style={{ flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 12, borderTopWidth: i ? 1 : 0, borderColor: c.ligne }}>
                          {estEleve ? (
                            <Pressable
                              onPress={() => statut.mutate({ id: dv.id, fait: !fait })}
                              accessibilityRole="checkbox"
                              accessibilityState={{ checked: fait }}
                              accessibilityLabel={`${dv.titre} terminé`}
                              hitSlop={8}
                              style={{ width: 28, height: 28, borderRadius: 8, borderWidth: 2, borderColor: fait ? c.ok : c.ligne, backgroundColor: fait ? c.ok : 'transparent', alignItems: 'center', justifyContent: 'center' }}
                            >
                              {fait ? <Ionicons name="checkmark" size={18} color="#FFF" /> : null}
                            </Pressable>
                          ) : null}
                          <Pressable style={{ flex: 1 }} onPress={() => router.push(`/devoirs/${dv.id}`)} accessibilityRole="button">
                            <T v="gras" style={fait && { textDecorationLine: 'line-through', color: c.texte2 }}>{dv.titre}</T>
                            <T v="petit" discret>{dv.matiere}</T>
                          </Pressable>
                          <Badge texte={echeanceRelative(dv.pour_le)} ton={dv.statut === 'en_retard' ? 'danger' : 'alerte'} />
                        </View>
                      );
                    })}
                  </Carte>
                </Section>
              ) : null}

              <Section titre="Aujourd'hui" action="Emploi du temps" onAction={() => router.push('/emploi-du-temps')}>
                {d.cours_du_jour.length ? (
                  <Carte style={{ paddingVertical: 2 }}>
                    {d.cours_du_jour.map((k, i) => <CoursLigne key={k.id} cours={k} dernier={i === d.cours_du_jour.length - 1} />)}
                  </Carte>
                ) : (
                  <Vide icone="sunny-outline" titre="Pas de cours aujourd’hui" texte="Profitez-en pour avancer vos devoirs." />
                )}
              </Section>

              <Section titre="Dernières notes" action="Tout voir" onAction={() => router.push('/notes')}>
                {d.dernieres_notes.length ? (
                  <Carte style={{ paddingVertical: 2 }}>
                    {d.dernieres_notes.map((n, i) => (
                      <View key={n.id} style={{ flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 12, borderTopWidth: i ? 1 : 0, borderColor: c.ligne }}>
                        <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: n.couleur }} />
                        <View style={{ flex: 1 }}>
                          <T v="gras">{n.matiere}</T>
                          <T v="petit" discret numberOfLines={1}>{n.titre} · {echeanceRelative(n.date)}</T>
                        </View>
                        <T v="h2" couleur={couleurNote(n.sur20, c)}>{n.note == null ? n.statut.slice(0, 3) : `${noteCourte(n.note)}/${noteCourte(n.bareme)}`}</T>
                      </View>
                    ))}
                  </Carte>
                ) : <Vide icone="bar-chart-outline" titre="Pas encore de note" />}
              </Section>

              {d.notifications.length ? (
                <Section titre="Notifications importantes" action="Tout voir" onAction={() => router.push('/notifications')}>
                  {d.notifications.map((n) => (
                    <Carte key={n.id} onPress={() => router.push(routePourLien(n.lien) as any)} style={{ flexDirection: 'row', gap: 12, alignItems: 'center' }}>
                      <View style={{ width: 40, height: 40, borderRadius: 12, backgroundColor: n.priorite === 1 ? c.dangerDoux : c.alerteDoux, alignItems: 'center', justifyContent: 'center' }}>
                        <Ionicons name={n.categorie === 'absences' ? 'time-outline' : n.categorie === 'paiements' ? 'wallet-outline' : 'alert-circle-outline'} size={20} color={n.priorite === 1 ? c.danger : c.alerte} />
                      </View>
                      <View style={{ flex: 1 }}>
                        <T v="gras">{n.titre}</T>
                        <T v="petit" discret>{heure(n.date)}</T>
                      </View>
                    </Carte>
                  ))}
                </Section>
              ) : null}

              <Section titre="Accès rapide">
                <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                  <Raccourci icone="book-outline" titre="Devoirs" onPress={() => router.push('/devoirs')} />
                  <Raccourci icone="time-outline" titre="Absences" onPress={() => router.push('/absences')} />
                  <Raccourci icone="megaphone-outline" titre="Vie scolaire" onPress={() => router.push('/vie-scolaire')} />
                  {estEleve ? <Raccourci icone="notifications-outline" titre="Alertes" onPress={() => router.push('/notifications')} /> : <Raccourci icone="wallet-outline" titre="Frais" onPress={() => router.push('/frais')} />}
                </View>
              </Section>

              {d.evenements.length ? (
                <Section titre="À ne pas manquer" action="Vie scolaire" onAction={() => router.push('/vie-scolaire')}>
                  <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 12, paddingHorizontal: 20 }} style={{ marginHorizontal: -20 }}>
                    {d.evenements.map((e, i) => (
                      <Carte key={e.id} onPress={() => router.push('/vie-scolaire')} style={{ width: 236, padding: 0, overflow: 'hidden' }}>
                        <View style={{ height: 72, backgroundColor: ['#0B1F3A', '#1D5BD8', '#13803F'][i % 3], padding: 12, justifyContent: 'flex-end' }}>
                          <BoiteDate iso={e.debut} fond="#FFFFFF" texte="#0B1F3A" />
                        </View>
                        <View style={{ padding: 14, gap: 2 }}>
                          <T v="gras">{e.titre}</T>
                          <T v="petit" discret numberOfLines={2}>{e.lieu || e.description}</T>
                        </View>
                      </Carte>
                    ))}
                  </ScrollView>
                </Section>
              ) : null}
            </>
          ) : null}
        </View>
      </ScrollView>
    </View>
  );
}

function Tuile({ titre, onPress, children }: { titre: string; onPress: () => void; children: ReactNode }) {
  return (
    <Carte onPress={onPress} libelle={titre} style={{ width: '48%', flexGrow: 1, gap: 4, minHeight: 112 }}>
      <T v="petit" discret>{titre}</T>
      {children}
    </Carte>
  );
}

function Raccourci({ icone, titre, onPress }: { icone: NomIcone; titre: string; onPress: () => void }) {
  const { c } = useTheme();
  return (
    <Pressable onPress={onPress} accessibilityRole="button" style={{ alignItems: 'center', gap: 6, width: 76 }}>
      <View style={{ width: 54, height: 54, borderRadius: 16, backgroundColor: c.surface, alignItems: 'center', justifyContent: 'center', shadowColor: c.ombre, shadowOpacity: 0.07, shadowRadius: 10, elevation: 2 }}>
        <Ionicons name={icone} size={24} color={c.accent} />
      </View>
      <T v="petit" style={{ textAlign: 'center' }}>{titre}</T>
    </Pressable>
  );
}

/** Enseignants et administration : l'essentiel mobile ; la saisie complète se fait sur l'espace web. */
function TableauPersonnel() {
  const { c } = useTheme();
  const router = useRouter();
  const { moi, etab } = useSession();
  const notifs = useDonnees(['notifications'], (a) => a.notifications());
  const conv = useDonnees(['conversations'], (a) => a.conversations());
  const vie = useDonnees(['vie'], (a) => a.vieScolaire());
  const nonLues = notifs.data?.filter((n) => !n.lue).length ?? 0;
  const nonLus = conv.data?.filter((x) => x.non_lu).length ?? 0;
  const insets = useSafeAreaInsets();
  return (
    <View style={{ flex: 1, backgroundColor: c.fond }}>
      <ScrollView contentContainerStyle={{ padding: 20, paddingTop: insets.top + 18, gap: 22 }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
          <Avatar initiales={moi?.initiales ?? ''} couleur="#0B1F3A" taille={52} />
          <View style={{ flex: 1 }}>
            <T v="petit" discret>{moi?.role === 'ADMIN' ? 'Administration' : 'Enseignant'} · {moi?.etablissement.nom}</T>
            <T v="h1">Bonjour {moi?.prenom}</T>
          </View>
          <BoutonIcone icone="notifications-outline" libelle="Notifications" pastille={nonLues} onPress={() => router.push('/notifications')} />
        </View>
        <View style={{ flexDirection: 'row', gap: 12 }}>
          <Carte onPress={() => router.push('/messages')} style={{ flex: 1 }} libelle="Messages non lus">
            <T v="petit" discret>Messages non lus</T>
            <T v="chiffre">{nonLus}</T>
          </Carte>
          <Carte onPress={() => router.push('/notifications')} style={{ flex: 1 }} libelle="Notifications">
            <T v="petit" discret>Notifications</T>
            <T v="chiffre">{nonLues}</T>
          </Carte>
        </View>
        <Carte style={{ gap: 10, backgroundColor: c.accentDoux }}>
          <T v="h3" couleur={c.accent}>{moi?.role === 'ADMIN' ? 'Gestion de l’établissement' : 'Appel, notes et cahier de texte'}</T>
          <T discret>La saisie complète ({moi?.role === 'ADMIN' ? 'comptes, emplois du temps, bulletins, paiements' : 'appel, évaluations, devoirs, appréciations'}) est disponible sur l’espace web NotePro, optimisé pour ordinateur et tablette.</T>
          {etab.api !== 'demo' ? (
            <Text onPress={() => WebBrowser.openBrowserAsync(etab.api)} style={{ color: c.accent, fontFamily: police.gras }} accessibilityRole="link">Ouvrir l’espace web →</Text>
          ) : null}
        </Carte>
        <Section titre="Informations récentes" action="Vie scolaire" onAction={() => router.push('/vie-scolaire')}>
          {vie.data?.annonces.slice(0, 3).map((a) => (
            <Carte key={a.id} style={{ gap: 4, borderRadius: rayon.l }}>
              {a.importante ? <Badge texte="Important" ton="danger" /> : null}
              <T v="gras">{a.titre}</T>
              <T v="petit" discret numberOfLines={2}>{a.contenu}</T>
            </Carte>
          )) ?? <Chargement lignes={2} />}
        </Section>
      </ScrollView>
    </View>
  );
}
