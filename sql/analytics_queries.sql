-- ============================================================
-- Analytics query bank — used by src/*.py and the dashboard
-- ============================================================

-- 1. RIDE DEMAND: hourly demand pattern per city (last 30 days)
-- -----------------------------------------------------------
SELECT
    city,
    EXTRACT(HOUR FROM request_ts)   AS hour_of_day,
    EXTRACT(DOW  FROM request_ts)   AS day_of_week,
    COUNT(*)                        AS total_requests
FROM rides
WHERE request_ts >= NOW() - INTERVAL '30 days'
GROUP BY city, hour_of_day, day_of_week
ORDER BY city, day_of_week, hour_of_day;


-- 2. SURGE PRICING: avg surge by hour + cancellation impact
-- -----------------------------------------------------------
SELECT
    city,
    date_trunc('hour', request_ts)                              AS hour_bucket,
    ROUND(AVG(surge_multiplier), 2)                             AS avg_surge,
    COUNT(*) FILTER (WHERE ride_status = 'cancelled')::NUMERIC
        / NULLIF(COUNT(*), 0) * 100                             AS cancel_rate_pct
FROM rides
GROUP BY city, hour_bucket
HAVING AVG(surge_multiplier) > 1.2
ORDER BY avg_surge DESC;


-- 3. DRIVER PERFORMANCE: earnings, acceptance & rating per driver
-- -----------------------------------------------------------
SELECT
    d.driver_id,
    d.driver_name,
    d.city,
    COUNT(r.ride_id)                                    AS total_rides,
    ROUND(AVG(r.driver_rating), 2)                       AS avg_rating,
    SUM(r.final_fare) FILTER (WHERE r.ride_status='completed') AS total_earnings,
    ROUND(
        COUNT(*) FILTER (WHERE r.ride_status = 'completed')::NUMERIC
        / NULLIF(COUNT(*), 0) * 100, 2
    )                                                    AS completion_rate_pct
FROM drivers d
LEFT JOIN rides r ON r.driver_id = d.driver_id
GROUP BY d.driver_id, d.driver_name, d.city
ORDER BY total_earnings DESC NULLS LAST;


-- 4. REVENUE ANALYTICS: daily revenue, take-rate, growth %
-- -----------------------------------------------------------
WITH daily AS (
    SELECT
        date_trunc('day', request_ts) AS day,
        city,
        SUM(final_fare) FILTER (WHERE ride_status='completed') AS revenue
    FROM rides
    GROUP BY day, city
)
SELECT
    day, city, revenue,
    ROUND(
        (revenue - LAG(revenue) OVER (PARTITION BY city ORDER BY day))
        / NULLIF(LAG(revenue) OVER (PARTITION BY city ORDER BY day), 0) * 100, 2
    ) AS pct_growth_dod
FROM daily
ORDER BY city, day;


-- 5. TOP DEMAND HOTSPOTS (for geo-spatial map): pickup clusters
-- -----------------------------------------------------------
SELECT
    city,
    ROUND(pickup_lat::numeric, 3) AS lat_bucket,
    ROUND(pickup_lng::numeric, 3) AS lng_bucket,
    COUNT(*) AS demand_count
FROM rides
WHERE request_ts >= NOW() - INTERVAL '7 days'
GROUP BY city, lat_bucket, lng_bucket
ORDER BY demand_count DESC
LIMIT 200;