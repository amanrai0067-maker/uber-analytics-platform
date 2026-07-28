CREATE TABLE IF NOT EXISTS drivers (
    driver_id           SERIAL PRIMARY KEY,
    driver_name         VARCHAR(100) NOT NULL,
    city                VARCHAR(50)  NOT NULL,
    vehicle_type        VARCHAR(20)  NOT NULL,       -- Go / Premier / Auto / Moto
    rating              NUMERIC(2,1) DEFAULT 5.0,
    joined_date         DATE NOT NULL,
    is_active           BOOLEAN DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS riders (
    rider_id            SERIAL PRIMARY KEY,
    rider_name          VARCHAR(100) NOT NULL,
    city                VARCHAR(50)  NOT NULL,
    signup_date         DATE NOT NULL
);
CREATE TABLE IF NOT EXISTS rides (
    ride_id             BIGSERIAL PRIMARY KEY,
    rider_id            INT,                          -- <-- REFERENCES riders(rider_id) hata diya
    driver_id           INT,                          -- <-- REFERENCES drivers(driver_id) hata diya
    city                VARCHAR(50) NOT NULL,
    pickup_lat          NUMERIC(9,6) NOT NULL,
    pickup_lng          NUMERIC(9,6) NOT NULL,
    drop_lat            NUMERIC(9,6) NOT NULL,
    drop_lng            NUMERIC(9,6) NOT NULL,
    request_ts          TIMESTAMP NOT NULL,
    pickup_ts           TIMESTAMP,
    drop_ts             TIMESTAMP,
    distance_km         NUMERIC(6,2) NOT NULL,
    base_fare           NUMERIC(8,2) NOT NULL,
    surge_multiplier    NUMERIC(3,2) DEFAULT 1.00,
    final_fare          NUMERIC(8,2) NOT NULL,
    payment_type        VARCHAR(20),
    vehicle_type        VARCHAR(20) NOT NULL,        
    ride_status         VARCHAR(20) NOT NULL,        
    rider_rating        NUMERIC(2,1),
    driver_rating       NUMERIC(2,1)
);
-- Indexes for the query patterns analytics will actually hit
CREATE INDEX IF NOT EXISTS idx_rides_request_ts   ON rides (request_ts);
CREATE INDEX IF NOT EXISTS idx_rides_city_ts       ON rides (city, request_ts);
CREATE INDEX IF NOT EXISTS idx_rides_driver        ON rides (driver_id);
CREATE INDEX IF NOT EXISTS idx_rides_status         ON rides (ride_status);

-- ============================================================
-- Materialized view: hourly demand per city (feeds forecasting)
-- ============================================================
DROP MATERIALIZED VIEW IF EXISTS mv_hourly_demand;

CREATE MATERIALIZED VIEW mv_hourly_demand AS
SELECT
    city,
    date_trunc('hour', request_ts)              AS hour_bucket,
    COUNT(*)                                     AS ride_requests,
    SUM(CASE WHEN ride_status = 'completed' THEN 1 ELSE 0 END) AS completed_rides,
    AVG(surge_multiplier)                        AS avg_surge,
    SUM(final_fare) FILTER (WHERE ride_status='completed')     AS revenue
FROM rides
GROUP BY city, date_trunc('hour', request_ts);

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_hourly_demand
    ON mv_hourly_demand (city, hour_bucket);