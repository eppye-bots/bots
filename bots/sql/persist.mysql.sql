DROP TABLE persist ;

CREATE TABLE persist (
domein VARCHAR(35) ,
botskey VARCHAR(35) ,
content TEXT ,
ts timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
PRIMARY KEY (domein, botskey)
);
