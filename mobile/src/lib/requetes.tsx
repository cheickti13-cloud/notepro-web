/**
 * Données et cache.
 * - Les réponses sont mises en cache et sauvegardées sur le téléphone (AsyncStorage) :
 *   hors connexion, l'app affiche les dernières données synchronisées.
 * - Économie de données : pas de rechargement pendant 2 minutes, rechargement au
 *   retour dans l'app, rafraîchissement régulier seulement des messages/notifications.
 */
import AsyncStorage from '@react-native-async-storage/async-storage';
import NetInfo from '@react-native-community/netinfo';
import { createAsyncStoragePersister } from '@tanstack/query-async-storage-persister';
import { focusManager, onlineManager, QueryClient, useMutation, useQuery, useQueryClient, UseQueryOptions } from '@tanstack/react-query';
import { PersistQueryClientProvider } from '@tanstack/react-query-persist-client';
import { ReactNode, useEffect, useState } from 'react';
import { AppState, Platform } from 'react-native';

import type { ApiNotePro } from './api';
import { useSession } from './session';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 2 * 60 * 1000,
      gcTime: 7 * 24 * 60 * 60 * 1000,
      retry: (n, err: any) => !err?.statut && n < 2, // pas de nouvel essai sur 401/403/404
      networkMode: 'offlineFirst',
    },
    mutations: { networkMode: 'online' },
  },
});

const persister = createAsyncStoragePersister({ storage: AsyncStorage, key: 'np.cache', throttleTime: 2000 });

// Connexion réseau et retour au premier plan
onlineManager.setEventListener((setOnline) =>
  NetInfo.addEventListener((s) => setOnline(s.isConnected !== false && s.isInternetReachable !== false)),
);

export function RequetesProvider({ children }: { children: ReactNode }) {
  useEffect(() => {
    if (Platform.OS === 'web') return;
    const sub = AppState.addEventListener('change', (s) => focusManager.setFocused(s === 'active'));
    return () => sub.remove();
  }, []);
  return (
    <PersistQueryClientProvider client={queryClient} persistOptions={{ persister, maxAge: 7 * 24 * 60 * 60 * 1000, buster: 'v1' }}>
      {children}
    </PersistQueryClientProvider>
  );
}

export function useEnLigne() {
  const [enLigne, setEnLigne] = useState(onlineManager.isOnline());
  useEffect(() => onlineManager.subscribe(setEnLigne), []);
  return enLigne;
}

/**
 * Requête liée à la session : la clé inclut l'établissement et l'utilisateur pour
 * qu'aucune donnée d'un compte ne s'affiche jamais dans un autre.
 */
export function useDonnees<T>(
  cle: (string | number | null | undefined)[],
  fn: (api: ApiNotePro) => Promise<T>,
  options: Omit<UseQueryOptions<T, Error, T>, 'queryKey' | 'queryFn'> = {},
) {
  const { api, etab, moi } = useSession();
  return useQuery<T, Error, T>({
    queryKey: [etab.id, moi?.id ?? 0, ...cle],
    queryFn: () => fn(api),
    enabled: !!moi && (options.enabled ?? true),
    ...options,
  });
}

export function useAction<V, R>(fn: (api: ApiNotePro, v: V) => Promise<R>, invalider: string[] = []) {
  const { api } = useSession();
  const qc = useQueryClient();
  return useMutation<R, Error, V>({
    mutationFn: (v) => fn(api, v),
    onSuccess: () => {
      invalider.forEach((k) => qc.invalidateQueries({ predicate: (q) => q.queryKey.includes(k) }));
    },
  });
}
