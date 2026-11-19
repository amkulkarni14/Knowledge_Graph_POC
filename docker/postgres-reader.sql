\getenv reader_password LOCAL_POSTGRES_READER_PASSWORD
ALTER ROLE kg_reader PASSWORD :'reader_password';
