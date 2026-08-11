-- Per-workflow Google Sheets tab name for auto-delivery
ALTER TABLE workflows ADD COLUMN IF NOT EXISTS default_sheet_name TEXT;
