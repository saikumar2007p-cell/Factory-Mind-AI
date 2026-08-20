/**
 * frontend/src/firebase/storage.js
 *
 * Firebase Cloud Storage service for FactoryMind AI.
 * Handles file upload/download for CSV, XLSX, PDFs, maintenance docs, reports.
 *
 * File organization:
 *   organizations/{organizationId}/datasets/
 *   organizations/{organizationId}/documents/
 *   organizations/{organizationId}/maintenance/
 *   organizations/{organizationId}/reports/
 */

import {
  ref,
  uploadBytes,
  getDownloadURL as fbGetDownloadURL,
  deleteObject,
  listAll,
} from 'firebase/storage';
import { storage, isFirebaseConfigured } from './config';

/**
 * Upload a file to Firebase Storage.
 *
 * @param {File} file - The file to upload
 * @param {string} organizationId - Org ID for path scoping
 * @param {string} category - One of: datasets, documents, maintenance, reports
 * @param {Object} metadata - Optional custom metadata
 * @returns {{ storagePath, downloadUrl }} or null
 */
export async function uploadFile(file, organizationId, category = 'documents', metadata = {}) {
  if (!isFirebaseConfigured || !storage) {
    console.warn('[Firebase Storage] Not configured — upload skipped');
    return null;
  }

  const safeName = file.name.replace(/[/\\]/g, '_');
  const storagePath = `organizations/${organizationId}/${category}/${safeName}`;
  const storageRef = ref(storage, storagePath);

  try {
    const snapshot = await uploadBytes(storageRef, file, {
      customMetadata: {
        organizationId,
        category,
        uploadedBy: metadata.uploadedBy || 'unknown',
        ...metadata,
      },
    });

    const downloadUrl = await fbGetDownloadURL(snapshot.ref);

    return {
      storagePath,
      downloadUrl,
      size: file.size,
      contentType: file.type,
      name: file.name,
    };
  } catch (err) {
    console.error('[Firebase Storage] Upload failed:', err);
    return null;
  }
}

/**
 * Get download URL for an existing file.
 */
export async function getDownloadURL(storagePath) {
  if (!isFirebaseConfigured || !storage) return null;
  try {
    const storageRef = ref(storage, storagePath);
    return await fbGetDownloadURL(storageRef);
  } catch (err) {
    console.error('[Firebase Storage] getDownloadURL failed:', err);
    return null;
  }
}

/**
 * Delete a file from Firebase Storage.
 */
export async function deleteFile(storagePath) {
  if (!isFirebaseConfigured || !storage) return false;
  try {
    const storageRef = ref(storage, storagePath);
    await deleteObject(storageRef);
    return true;
  } catch (err) {
    console.error('[Firebase Storage] Delete failed:', err);
    return false;
  }
}

/**
 * List all files in an organization's category folder.
 */
export async function listFiles(organizationId, category = 'documents') {
  if (!isFirebaseConfigured || !storage) return [];
  try {
    const prefix = `organizations/${organizationId}/${category}/`;
    const listRef = ref(storage, prefix);
    const result = await listAll(listRef);
    const files = await Promise.all(
      result.items.map(async (itemRef) => {
        const url = await fbGetDownloadURL(itemRef);
        return {
          name: itemRef.name,
          storagePath: itemRef.fullPath,
          downloadUrl: url,
        };
      })
    );
    return files;
  } catch (err) {
    console.error('[Firebase Storage] listFiles failed:', err);
    return [];
  }
}
