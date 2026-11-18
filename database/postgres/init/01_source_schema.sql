-- Sample retail source schema (same data as src/kg/sources/sample_data.py)
-- psql -d retail -f sql/01_source_schema.sql
-- Contains deliberate data problems so every stage has something to show:
--   * customers 2 and 11 share an e-mail (entity resolution)
--   * order 1012 references customer 99 that does not exist (orphan)
--   * product 206 has a negative price (business rule)
--   * orders.customer_id has NO declared foreign key (legacy pattern)

CREATE TABLE IF NOT EXISTS public.locations (
    location_id integer PRIMARY KEY,
    city        varchar(100) NOT NULL,
    state       varchar(100),
    country     varchar(100) NOT NULL,
    updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.organizations (
    org_id          integer PRIMARY KEY,
    org_name        varchar(200) NOT NULL,
    industry        varchar(100),
    hq_location_id  integer REFERENCES public.locations(location_id),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.customers (
    customer_id integer PRIMARY KEY,
    full_name   varchar(200) NOT NULL,
    email       varchar(320) NOT NULL,
    phone       varchar(20),
    location_id integer REFERENCES public.locations(location_id),
    org_id      integer REFERENCES public.organizations(org_id),
    referred_by integer REFERENCES public.customers(customer_id),
    segment     varchar(20),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.products (
    product_id      integer PRIMARY KEY,
    product_name    varchar(200) NOT NULL,
    category        varchar(100),
    unit_price      numeric(12,2) NOT NULL,
    manufacturer_id integer REFERENCES public.organizations(org_id),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.orders (
    order_id     integer PRIMARY KEY,
    customer_id  integer NOT NULL,            -- intentionally no FK
    order_date   date NOT NULL,
    status       varchar(20) NOT NULL,
    total_amount numeric(12,2),
    updated_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.order_items (
    order_id   integer NOT NULL REFERENCES public.orders(order_id),
    product_id integer NOT NULL REFERENCES public.products(product_id),
    quantity   integer NOT NULL CHECK (quantity > 0),
    unit_price numeric(12,2) NOT NULL,
    PRIMARY KEY (order_id, product_id)
);

-- Indexes for cheap extraction (FK columns are NOT indexed automatically)
CREATE INDEX IF NOT EXISTS ix_customers_location   ON public.customers(location_id);
CREATE INDEX IF NOT EXISTS ix_customers_org        ON public.customers(org_id);
CREATE INDEX IF NOT EXISTS ix_customers_referred   ON public.customers(referred_by);
CREATE INDEX IF NOT EXISTS ix_customers_email_norm ON public.customers(lower(trim(email)));
CREATE INDEX IF NOT EXISTS ix_orders_customer      ON public.orders(customer_id);
CREATE INDEX IF NOT EXISTS ix_order_items_product  ON public.order_items(product_id);
CREATE INDEX IF NOT EXISTS ix_customers_updated    ON public.customers(updated_at);
CREATE INDEX IF NOT EXISTS ix_orders_updated       ON public.orders(updated_at);
CREATE INDEX IF NOT EXISTS ix_products_updated     ON public.products(updated_at);

-- Read-only role for the graph builder. Set the real password from your vault:
--   ALTER ROLE kg_reader PASSWORD '...';
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'kg_reader') THEN
    CREATE ROLE kg_reader LOGIN;
  END IF;
END $$;
GRANT USAGE ON SCHEMA public TO kg_reader;
GRANT SELECT ON public.locations, public.organizations, public.customers,
                public.products, public.orders, public.order_items TO kg_reader;
ALTER ROLE kg_reader SET default_transaction_read_only = on;
ALTER ROLE kg_reader SET statement_timeout = '5min';

-- Sample rows ---------------------------------------------------------------
INSERT INTO public.locations VALUES
 (1,'Pune','Maharashtra','India','2026-11-01 09:00'), (2,'Mumbai','Maharashtra','India','2026-11-01 09:00'),
 (3,'Bengaluru','Karnataka','India','2026-11-01 09:00'), (4,'Hyderabad','Telangana','India','2026-11-01 09:00'),
 (5,'Delhi','Delhi','India','2026-11-01 09:00') ON CONFLICT DO NOTHING;

INSERT INTO public.organizations VALUES
 (10,'Acme Retail Pvt Ltd','Retail',2,'2026-11-01 09:00'),
 (11,'Zenith Electronics','Manufacturing',3,'2026-11-01 09:00'),
 (12,'Nimbus Software','IT Services',1,'2026-11-01 09:00') ON CONFLICT DO NOTHING;

INSERT INTO public.customers VALUES
 (1,'Rahul Verma','rahul.verma@example.com','9876500001',1,12,NULL,'Gold','2026-11-01 09:00'),
 (2,'Priya Sharma','priya.sharma@example.com','9876500002',2,10,1,'Silver','2026-11-01 09:00'),
 (3,'Amit Patel','amit.patel@example.com',NULL,3,11,1,'Gold','2026-11-01 09:00'),
 (4,'Sneha Iyer','sneha.iyer@example.com','9876500004',3,12,3,'Bronze','2026-11-01 09:00'),
 (5,'Vikram Singh','vikram.singh@example.com','9876500005',5,NULL,NULL,'Silver','2026-11-01 09:00'),
 (6,'Anjali Rao','anjali.rao@example.com','9876500006',4,11,2,'Gold','2026-11-01 09:00'),
 (7,'Karan Mehta','karan.mehta@example.com',NULL,NULL,NULL,NULL,NULL,'2026-11-01 09:00'),
 (8,'Neha Gupta','neha.gupta@example.com','9876500008',1,10,4,'Silver','2026-11-09 18:30'),
 (11,'  priya SHARMA ','Priya.Sharma@Example.com ','9876500002',2,10,NULL,'silver','2026-11-01 09:00')
 ON CONFLICT DO NOTHING;

INSERT INTO public.products VALUES
 (201,'Laptop Pro 14','Electronics',89999,11,'2026-11-01 09:00'),
 (202,'Wireless Mouse','Accessories',1299,11,'2026-11-01 09:00'),
 (203,'Office Chair','Furniture',15499,10,'2026-11-01 09:00'),
 (204,'Noise Cancelling Headphones','Electronics',24999,11,'2026-11-01 09:00'),
 (205,'Project Tracker SaaS','Software',4999,12,'2026-11-01 09:00'),
 (206,'USB-C Hub','Accessories',-50,11,'2026-11-01 09:00') ON CONFLICT DO NOTHING;

INSERT INTO public.orders VALUES
 (1001,1,'2026-09-02','DELIVERED',91298,'2026-11-01 09:00'), (1002,2,'2026-09-05','DELIVERED',15499,'2026-11-01 09:00'),
 (1003,3,'2026-09-09','SHIPPED',114998,'2026-11-01 09:00'),  (1004,1,'2026-09-20','DELIVERED',4999,'2026-11-01 09:00'),
 (1005,4,'2026-10-01','CANCELLED',24999,'2026-11-01 09:00'), (1006,5,'2026-10-03','DELIVERED',1299,'2026-11-01 09:00'),
 (1007,6,'2026-10-07','DELIVERED',90000,'2026-11-01 09:00'), (1008,11,'2026-10-12','DELIVERED',2598,'2026-11-01 09:00'),
 (1009,8,'2026-10-15','PLACED',26298,'2026-11-09 18:30'),    (1010,3,'2026-10-18','DELIVERED',4999,'2026-11-01 09:00'),
 (1011,6,'2026-10-22','SHIPPED',15499,'2026-11-09 18:30'),   (1012,99,'2026-10-25','PLACED',1299,'2026-11-01 09:00')
 ON CONFLICT DO NOTHING;

INSERT INTO public.order_items VALUES
 (1001,201,1,89999),(1001,202,1,1299),(1002,203,1,15499),(1003,201,1,89999),(1003,204,1,24999),
 (1004,205,1,4999),(1005,204,1,24999),(1006,202,1,1299),(1007,201,1,89999),(1008,202,2,1299),
 (1009,204,1,24999),(1009,202,1,1299),(1010,205,1,4999),(1011,203,1,15499),(1012,202,1,1299)
 ON CONFLICT DO NOTHING;
