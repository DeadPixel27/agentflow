/** Persist a home-page run intent across /account sign-in (Files via IndexedDB). */

const META_KEY = "nexora_pending_run";
const DB_NAME = "nexora_pending_run";
const DB_VERSION = 1;
const STORE = "files";

export type PendingRunKind = "run" | "sample";

export interface PendingRunMeta {
  kind: PendingRunKind;
  templateId: string | null;
  task: string;
}

export interface PendingRun extends PendingRunMeta {
  files: File[];
}

interface StoredFile {
  name: string;
  type: string;
  buffer: ArrayBuffer;
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onerror = () => reject(req.error ?? new Error("IndexedDB open failed"));
    req.onsuccess = () => resolve(req.result);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE);
      }
    };
  });
}

async function idbPut(files: StoredFile[]): Promise<void> {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.objectStore(STORE).put(files, "pending");
    tx.oncomplete = () => {
      db.close();
      resolve();
    };
    tx.onerror = () => {
      db.close();
      reject(tx.error ?? new Error("IndexedDB put failed"));
    };
  });
}

async function idbGet(): Promise<StoredFile[] | null> {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readonly");
    const req = tx.objectStore(STORE).get("pending");
    req.onsuccess = () => {
      db.close();
      resolve((req.result as StoredFile[] | undefined) ?? null);
    };
    req.onerror = () => {
      db.close();
      reject(req.error ?? new Error("IndexedDB get failed"));
    };
  });
}

async function idbClear(): Promise<void> {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, "readwrite");
    tx.objectStore(STORE).delete("pending");
    tx.oncomplete = () => {
      db.close();
      resolve();
    };
    tx.onerror = () => {
      db.close();
      reject(tx.error ?? new Error("IndexedDB clear failed"));
    };
  });
}

function readMeta(): PendingRunMeta | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(META_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as PendingRunMeta;
    if (parsed.kind !== "run" && parsed.kind !== "sample") return null;
    return {
      kind: parsed.kind,
      templateId: parsed.templateId ?? null,
      task: typeof parsed.task === "string" ? parsed.task : "",
    };
  } catch {
    return null;
  }
}

export function hasPendingRun(): boolean {
  return readMeta() !== null;
}

/** Atomically read + clear metadata so only one resume can claim the intent. */
export function claimPendingMeta(): PendingRunMeta | null {
  const meta = readMeta();
  if (!meta) return null;
  if (typeof window !== "undefined") {
    sessionStorage.removeItem(META_KEY);
  }
  return meta;
}

export async function savePendingRun(input: {
  kind: PendingRunKind;
  files?: File[];
  templateId?: string | null;
  task?: string;
}): Promise<void> {
  if (typeof window === "undefined") return;

  const meta: PendingRunMeta = {
    kind: input.kind,
    templateId: input.templateId ?? null,
    task: input.task ?? "",
  };
  sessionStorage.setItem(META_KEY, JSON.stringify(meta));

  if (input.kind === "run" && input.files?.length) {
    const stored: StoredFile[] = await Promise.all(
      input.files.map(async (file) => ({
        name: file.name,
        type: file.type || "application/octet-stream",
        buffer: await file.arrayBuffer(),
      })),
    );
    await idbPut(stored);
  } else {
    try {
      await idbClear();
    } catch {
      /* ignore */
    }
  }
}

export async function loadPendingRun(): Promise<PendingRun | null> {
  const meta = readMeta();
  if (!meta) return null;

  if (meta.kind === "sample") {
    return { ...meta, files: [] };
  }

  try {
    const stored = await idbGet();
    const files =
      stored?.map(
        (f) => new File([f.buffer], f.name, { type: f.type }),
      ) ?? [];
    return { ...meta, files };
  } catch {
    return { ...meta, files: [] };
  }
}

/** Claim meta + load files for resume. Clears sessionStorage immediately. */
export async function claimPendingRun(): Promise<PendingRun | null> {
  const meta = claimPendingMeta();
  if (!meta) return null;

  if (meta.kind === "sample") {
    try {
      await idbClear();
    } catch {
      /* ignore */
    }
    return { ...meta, files: [] };
  }

  try {
    const stored = await idbGet();
    await idbClear();
    const files =
      stored?.map(
        (f) => new File([f.buffer], f.name, { type: f.type }),
      ) ?? [];
    return { ...meta, files };
  } catch {
    return { ...meta, files: [] };
  }
}

export async function clearPendingRun(): Promise<void> {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(META_KEY);
  try {
    await idbClear();
  } catch {
    /* ignore */
  }
}
