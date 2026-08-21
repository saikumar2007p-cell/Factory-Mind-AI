/**
 * frontend/src/firebase/auth.js
 *
 * Firebase Authentication service for FactoryMind AI.
 * Provides login, logout, token management, and auth state listener.
 */

import {
  signInWithEmailAndPassword,
  signOut as firebaseSignOut,
  onAuthStateChanged as firebaseOnAuthStateChanged,
  createUserWithEmailAndPassword,
  updateProfile,
} from 'firebase/auth';
import { auth, isFirebaseConfigured } from './config';

/**
 * Sign in with email and password.
 * Returns the Firebase User object on success.
 */
export async function signIn(email, password) {
  if (!isFirebaseConfigured) {
    throw new Error('Firebase is not configured. Fill in frontend/.env.local.');
  }
  const credential = await signInWithEmailAndPassword(auth, email, password);
  return credential.user;
}

/**
 * Create a new user account (admin use or first-time setup).
 */
export async function registerUser(email, password, displayName) {
  if (!isFirebaseConfigured) {
    throw new Error('Firebase is not configured. Fill in frontend/.env.local.');
  }
  const credential = await createUserWithEmailAndPassword(auth, email, password);
  if (displayName) {
    await updateProfile(credential.user, { displayName });
  }
  return credential.user;
}

/**
 * Sign out the current user.
 */
export async function signOutUser() {
  if (!isFirebaseConfigured) return;
  await firebaseSignOut(auth);
}

/**
 * Get the current Firebase ID token for API calls.
 * Returns null if no user is signed in or Firebase is not configured.
 */
export async function getIdToken() {
  if (!isFirebaseConfigured || !auth.currentUser) {
    return null;
  }
  try {
    return await auth.currentUser.getIdToken(/* forceRefresh */ false);
  } catch (err) {
    console.error('[Firebase Auth] Failed to get ID token:', err);
    return null;
  }
}

/**
 * Force-refresh the ID token (picks up new custom claims after role change).
 */
export async function refreshIdToken() {
  if (!isFirebaseConfigured || !auth.currentUser) {
    return null;
  }
  try {
    return await auth.currentUser.getIdToken(/* forceRefresh */ true);
  } catch (err) {
    console.error('[Firebase Auth] Token refresh failed:', err);
    return null;
  }
}

/**
 * Get the current user's role from Firebase custom claims.
 * Returns 'VIEWER' as default if no role claim is set.
 */
export async function getCurrentUserRole() {
  if (!isFirebaseConfigured || !auth.currentUser) {
    return null;
  }
  try {
    const tokenResult = await auth.currentUser.getIdTokenResult();
    return tokenResult.claims.role || 'OPERATOR';
  } catch (err) {
    console.error('[Firebase Auth] Failed to get role from claims:', err);
    return null;
  }
}

/**
 * Get the current user's organization ID from Firebase custom claims.
 */
export async function getCurrentUserOrg() {
  if (!isFirebaseConfigured || !auth.currentUser) {
    return null;
  }
  try {
    const tokenResult = await auth.currentUser.getIdTokenResult();
    return tokenResult.claims.organizationId || '';
  } catch (err) {
    console.error('[Firebase Auth] Failed to get org from claims:', err);
    return null;
  }
}

/**
 * Subscribe to auth state changes.
 * callback receives (user) — user is null when signed out.
 * Returns unsubscribe function.
 */
export function onAuthStateChanged(callback) {
  if (!isFirebaseConfigured) {
    // Not configured — immediately call with null and return noop
    callback(null);
    return () => {};
  }
  return firebaseOnAuthStateChanged(auth, callback);
}

/**
 * Get the currently signed-in user synchronously (may be null during loading).
 */
export function getCurrentUser() {
  if (!isFirebaseConfigured) return null;
  return auth.currentUser;
}
