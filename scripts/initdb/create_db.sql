CREATE USER grassroots WITH PASSWORD 'tralala' CREATEDB;
CREATE DATABASE "cic-cache";
CREATE DATABASE "cic-eth";
CREATE DATABASE "cic-notify";
CREATE DATABASE "cic-meta";
CREATE DATABASE "cic-signer";
GRANT ALL PRIVILEGES 
ON DATABASE "cic-cache", "cic-eth", "cic-notify", "cic-meta", "cic-signer"
TO grassroots;
