-- Force app Storage buckets private and block anon/authenticated object access.
-- Backend uses the service role key, which bypasses Storage RLS.
--
-- Do NOT ALTER TABLE storage.objects — SQL Editor is not the table owner;
-- RLS is already enabled by default on storage.objects.

-- Ensure buckets exist and cannot be served as public URLs
INSERT INTO storage.buckets (id, name, public)
VALUES
  ('documents', 'documents', false),
  ('user-templates', 'user-templates', false)
ON CONFLICT (id) DO UPDATE
SET
  public = false,
  name = EXCLUDED.name;

-- Best-effort: drop common overly-permissive policy names from tutorials / dashboard defaults
DROP POLICY IF EXISTS "Public Access" ON storage.objects;
DROP POLICY IF EXISTS "Public access" ON storage.objects;
DROP POLICY IF EXISTS "Allow public read" ON storage.objects;
DROP POLICY IF EXISTS "Allow public uploads" ON storage.objects;
DROP POLICY IF EXISTS "Give users access to own folder" ON storage.objects;
DROP POLICY IF EXISTS "Allow authenticated uploads" ON storage.objects;
DROP POLICY IF EXISTS "Allow authenticated read" ON storage.objects;
DROP POLICY IF EXISTS "Anyone can upload" ON storage.objects;
DROP POLICY IF EXISTS "Anyone can read" ON storage.objects;

-- RESTRICTIVE: even if a permissive allow-all policy exists, clients cannot
-- touch documents / user-templates. Other buckets are unaffected.
DROP POLICY IF EXISTS "deny_client_access_to_app_buckets" ON storage.objects;

CREATE POLICY "deny_client_access_to_app_buckets"
  ON storage.objects
  AS RESTRICTIVE
  FOR ALL
  TO anon, authenticated
  USING (bucket_id NOT IN ('documents', 'user-templates'))
  WITH CHECK (bucket_id NOT IN ('documents', 'user-templates'));
