-- Add photo analysis result columns to photos table
-- photo_analyze_result: JSONB column to store OpenAI GPT-4o analysis results
-- analyzed_at: timestamp when the photo was analyzed

alter table "public"."photos" add column if not exists "photo_analyze_result" jsonb;
alter table "public"."photos" add column if not exists "analyzed_at" timestamp with time zone;

-- Add index on analyzed_at for performance
create index if not exists "idx_photos_analyzed_at" on "public"."photos" ("analyzed_at");

-- Add index on photo_analyze_result for JSON queries
create index if not exists "idx_photos_analyze_result_gin" on "public"."photos" using gin ("photo_analyze_result");