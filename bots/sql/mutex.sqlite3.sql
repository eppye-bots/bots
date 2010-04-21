DROP TABLE mutex ;

CREATE TABLE mutex (
mutexk integer PRIMARY KEY NOT NULL,
mutexer integer DEFAULT 0,
ts datetime NOT NULL DEFAULT CURRENT_TIMESTAMP
);
