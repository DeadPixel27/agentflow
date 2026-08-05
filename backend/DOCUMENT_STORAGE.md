# Document storage architecture

Backends are selected by **config only**. The rest of the app never imports Supabase, S3, or filesystem code directly.

## One registry file

`app/persistence/registry.py` is the **only** place that maps env vars → implementations:

```python
_DATA_BACKENDS = {
    "memory": MemoryRepository,
    "supabase": SupabaseRepository,
}

_DOCUMENT_BACKENDS = {
    "local": LocalDocumentRepository,
    "supabase": SupabaseDocumentRepository,
    # "s3": S3DocumentRepository,   # future: add one file + one line
}
```

To add S3 later:
1. Create `persistence/documents/s3_repository.py` implementing `DocumentStorageRepository`
2. Add `"s3": S3DocumentRepository` to `_DOCUMENT_BACKENDS`
3. Set `DOCUMENT_STORAGE=s3` in `.env`

**No other files change.**

## Layout

```
app/persistence/
  protocols.py              # Interfaces (DataRepository, DocumentStorageRepository)
  registry.py               # Config → implementation (THE wiring file)
  memory_repository.py      # In-memory users/workflows/runs
  supabase_repository.py    # Only file that imports supabase for Postgres tables
  documents/
    local_repository.py     # Local disk uploads
    supabase_repository.py    # Only file that uses Supabase Storage
    validation.py             # Shared file rules
  __init__.py                 # Public API: get_repository(), get_document_store()
```

## Config

```env
PERSISTENCE_BACKEND=auto      # auto | memory | supabase
DOCUMENT_STORAGE=auto         # auto | local | supabase
SUPABASE_DOCUMENTS_BUCKET=documents
```

| `auto` | Picks Supabase when `SUPABASE_*` is set, else memory/local |

## What callers import

```python
from app.persistence import get_repository, get_document_store

get_repository().save_user(user)
await get_document_store().save_document(upload_id, file)
```

Never import `supabase`, `memory_repository`, or `local_repository` outside `registry.py`.

## Strategy pattern vs “facade”

A **facade** is a single object that hides many subsystems. What we use is closer to the **strategy pattern**:

- **Protocol** = the contract (`DataRepository`)
- **Implementations** = one file each (`memory_repository.py`, `supabase_repository.py`)
- **Registry** = picks which strategy from config

You were right: adding a backend should not mean editing a growing `if/else` facade — only the registry dict and one new file.
