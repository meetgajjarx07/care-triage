-- Every number on the Voice of customer page comes from one of these queries.
-- Written in the common subset of SQLite and BigQuery Standard SQL so the demo
-- can run them locally; the BigQuery versions differ only where marked.

-- name: themes_by_week
-- Reviews per theme per week, split by sentiment. Drives the stacked weekly chart.
SELECT week_start, theme, sentiment, COUNT(*) AS n
FROM voice_of_customer
WHERE channel = 'review'
GROUP BY week_start, theme, sentiment
ORDER BY week_start, theme;

-- name: theme_mix
-- Share of reviews per theme and how negative each theme runs.
SELECT theme,
       COUNT(*)                                             AS n,
       SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) AS negative,
       ROUND(AVG(stars), 2)                                 AS avg_stars
FROM voice_of_customer
WHERE channel = 'review'
GROUP BY theme
ORDER BY n DESC;

-- name: rising_themes
-- The last three weeks against the seven before, per theme, as a weekly rate.
-- BigQuery: replace julianday(...) arithmetic with DATE_DIFF(max_week, week_start, WEEK).
WITH w AS (
  SELECT theme,
         CASE WHEN julianday((SELECT MAX(week_start) FROM voice_of_customer)) - julianday(week_start) < 21
              THEN 'recent' ELSE 'before' END AS period
  FROM voice_of_customer
  WHERE channel = 'review'
)
SELECT theme,
       SUM(CASE WHEN period = 'before' THEN 1 ELSE 0 END) / 7.0 AS before_per_week,
       SUM(CASE WHEN period = 'recent' THEN 1 ELSE 0 END) / 3.0 AS recent_per_week,
       SUM(CASE WHEN period = 'recent' THEN 1 ELSE 0 END)       AS recent_n
FROM w
GROUP BY theme
ORDER BY recent_per_week - before_per_week DESC;

-- name: stars_by_product
SELECT product, COUNT(*) AS n, ROUND(AVG(stars), 2) AS avg_stars,
       SUM(CASE WHEN stars <= 2 THEN 1 ELSE 0 END) AS one_or_two_star
FROM voice_of_customer
WHERE channel = 'review'
GROUP BY product
ORDER BY n DESC;

-- name: by_source
SELECT source, COUNT(*) AS n, ROUND(AVG(stars), 2) AS avg_stars,
       SUM(CASE WHEN sentiment = 'negative' THEN 1 ELSE 0 END) AS negative
FROM voice_of_customer
WHERE channel = 'review'
GROUP BY source
ORDER BY n DESC;

-- name: reply_backlog
-- Negative reviews and what the system did with each.
SELECT action, COUNT(*) AS n,
       SUM(CASE WHEN qa_score = 0 THEN 1 ELSE 0 END) AS critical_fail
FROM voice_of_customer
WHERE channel = 'review' AND sentiment = 'negative'
GROUP BY action
ORDER BY n DESC;

-- name: cancel_mentions_all_channels
-- The same question across email and reviews: who is talking about leaving, per week.
SELECT week_start, channel, SUM(CASE WHEN cancel_intent THEN 1 ELSE 0 END) AS cancel_n, COUNT(*) AS n
FROM voice_of_customer
GROUP BY week_start, channel
ORDER BY week_start, channel;
