CREATE USER grassroots WITH PASSWORD 'grassroots' CREATEDB;
CREATE DATABASE "cic_cache";
CREATE DATABASE "cic_eth";
CREATE DATABASE "cic_meta";
GRANT ALL PRIVILEGES 
ON DATABASE "cic_cache", "cic_eth", "cic_meta"
TO grassroots;
