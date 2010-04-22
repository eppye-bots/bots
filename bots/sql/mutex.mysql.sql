ALTER TABLE mutex MODIFY ts timestamp  DEFAULT current_timestamp;
ALTER TABLE mutex ALTER COLUMN mutexer     SET DEFAULT 0;

