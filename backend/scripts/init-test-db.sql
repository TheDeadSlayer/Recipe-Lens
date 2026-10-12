-- Creates the test database alongside the main database.
-- This script is run once by the postgres container on first initialisation.
CREATE DATABASE recipelens_test;
GRANT ALL PRIVILEGES ON DATABASE recipelens_test TO recipelens;
