/**
 * frontend/src/firebase/config.js
 *
 * Firebase Web SDK initialization for FactoryMind AI.
 * Reads configuration from VITE_FIREBASE_* environment variables.
 *
 * IMPORTANT: Do NOT hardcode credentials here. Use frontend/.env.local
 */

import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';
import { getFirestore } from 'firebase/firestore';
import { getStorage } from 'firebase/storage';

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
};

// Only initialize if API key is configured
const isFirebaseConfigured = !!firebaseConfig.apiKey;

let app = null;
let auth = null;
let db = null;
let storage = null;

if (isFirebaseConfigured) {
  app = initializeApp(firebaseConfig);
  auth = getAuth(app);
  db = getFirestore(app);
  storage = getStorage(app);
  console.log('[Firebase] Web SDK initialized for project:', firebaseConfig.projectId);
} else {
  console.warn(
    '[Firebase] Web SDK NOT configured — VITE_FIREBASE_API_KEY is empty. ' +
    'Fill in frontend/.env.local with your Firebase project values.'
  );
}

export { app, auth, db, storage, isFirebaseConfigured };
export default app;
