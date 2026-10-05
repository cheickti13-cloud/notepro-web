/** Convertit les liens des notifications (chemins du site web) en écrans de l'app. */
export function routePourLien(lien: string): string {
  if (!lien) return '/notifications';
  const conv = lien.match(/^\/messagerie\/(\d+)\/?$/);
  if (conv) return `/conversation/${conv[1]}`;
  if (lien.startsWith('/absences')) return '/absences';
  if (lien.startsWith('/notes') || lien.startsWith('/bulletins')) return '/notes';
  if (lien.startsWith('/emploi-du-temps')) return '/emploi-du-temps';
  if (lien.startsWith('/cahier-de-texte') || lien.startsWith('/devoirs')) return '/devoirs';
  if (lien.startsWith('/frais')) return '/frais';
  if (lien.startsWith('/messagerie/annonces') || lien.startsWith('/vie-scolaire')) return '/vie-scolaire';
  if (lien.startsWith('/messagerie')) return '/messages';
  return '/notifications';
}
