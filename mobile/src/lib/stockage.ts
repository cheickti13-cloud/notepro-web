/**
 * Stockage local.
 * - `secret` : jetons de connexion → trousseau chiffré du téléphone (Keychain iOS /
 *   Keystore Android via expo-secure-store). Sur le web, sessionStorage (effacé à la
 *   fermeture de l'onglet) : on ne garde jamais un jeton longue durée dans un navigateur.
 * - `prefs` : préférences non sensibles (thème, établissement choisi…) → AsyncStorage.
 */
import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

const web = Platform.OS === 'web';

export const secret = {
  async lire(cle: string): Promise<string | null> {
    try {
      if (web) return globalThis.sessionStorage?.getItem(cle) ?? null;
      return await SecureStore.getItemAsync(cle);
    } catch {
      return null;
    }
  },
  async ecrire(cle: string, valeur: string): Promise<void> {
    try {
      if (web) globalThis.sessionStorage?.setItem(cle, valeur);
      else await SecureStore.setItemAsync(cle, valeur, { keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY });
    } catch {
      // stockage indisponible : la session restera en mémoire uniquement
    }
  },
  async supprimer(cle: string): Promise<void> {
    try {
      if (web) globalThis.sessionStorage?.removeItem(cle);
      else await SecureStore.deleteItemAsync(cle);
    } catch {
      // rien à faire
    }
  },
};

export const prefs = {
  async lire<T>(cle: string, defaut: T): Promise<T> {
    try {
      const v = await AsyncStorage.getItem('np.' + cle);
      return v == null ? defaut : (JSON.parse(v) as T);
    } catch {
      return defaut;
    }
  },
  async ecrire(cle: string, valeur: unknown): Promise<void> {
    try {
      await AsyncStorage.setItem('np.' + cle, JSON.stringify(valeur));
    } catch {
      // ignoré
    }
  },
  async supprimer(cle: string): Promise<void> {
    try {
      await AsyncStorage.removeItem('np.' + cle);
    } catch {
      // ignoré
    }
  },
};
