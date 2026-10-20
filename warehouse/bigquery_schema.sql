-- Voice of customer: one table for every piece of customer text, whatever the source.
-- BigQuery Standard SQL. At AlgaeCal the sources would be the Yotpo reviews API,
-- Amazon Seller Central review exports, Talkdesk call and chat transcripts and the
-- support mailbox, landed in Cloud Storage and loaded by a scheduled job.
-- In this demo the table is filled from data/emails.csv and data/reviews.csv
-- (all of it fictional) and queried locally with SQLite; see queries.sql.

CREATE SCHEMA IF NOT EXISTS care;

CREATE TABLE IF NOT EXISTS care.voice_of_customer (
  item_id        STRING    NOT NULL,            -- E061, R042
  source         STRING    NOT NULL,            -- email | Yotpo | Amazon | Independent site | Talkdesk
  channel        STRING    NOT NULL,            -- email | review | call | chat
  happened_at    TIMESTAMP NOT NULL,
  week_start     DATE      NOT NULL,            -- DATE_TRUNC(happened_at, WEEK(MONDAY))
  customer_ref   STRING,                        -- hashed; never the raw name in the warehouse
  product        STRING,
  stars          INT64,                         -- reviews only
  verified       BOOL,
  title          STRING,
  body           STRING,
  -- what the sorter said
  theme          STRING,                        -- results | side_effects | price | pills | shipping | support | subscription  (reviews)
  category       STRING,                        -- the seven email categories                                            (emails)
  theme_conf     FLOAT64,
  sentiment      STRING,                        -- negative | neutral | positive
  cancel_intent  BOOL,
  gist           STRING,                        -- one line written by the language model
  quote          STRING,                        -- a phrase copied from the text, checked to be in it
  -- what happened next
  action         STRING,                        -- draft_reply | consultant_call | consultant_outreach | no_action
  action_reason  STRING,
  draft          STRING,
  qa_score       INT64,
  qa_failed      STRING,
  run_id         STRING    NOT NULL
)
PARTITION BY DATE(happened_at)
CLUSTER BY source, theme;
