-- Optional free-text feedback when joining the Pro waitlist
alter table waitlist
  add column if not exists feedback text not null default '';
