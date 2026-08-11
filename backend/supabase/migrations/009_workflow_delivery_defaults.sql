-- V2: default delivery targets on workflows (email / Google Sheets)
ALTER TABLE workflows ADD COLUMN IF NOT EXISTS default_email TEXT;
ALTER TABLE workflows ADD COLUMN IF NOT EXISTS default_sheets_url TEXT;
