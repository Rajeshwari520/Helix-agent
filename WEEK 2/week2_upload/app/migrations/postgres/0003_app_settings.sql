-- 0003_app_settings: key/value settings. Stores which domain (e.g. kgit) this database
-- belongs to, so a future client's data can never be mixed into the same database.
CREATE TABLE app_settings (
    key    TEXT PRIMARY KEY,
    value  TEXT NOT NULL
);
