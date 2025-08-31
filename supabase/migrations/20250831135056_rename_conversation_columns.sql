-- Rename and reorder conversation table columns
-- question_text -> ai_output
-- user_response_text -> user_input
-- Reorder columns: conversation_order, user_input, ai_output

alter table "public"."conversations" rename column "question_text" to "ai_output";
alter table "public"."conversations" rename column "user_response_text" to "user_input";

-- Reorder columns by creating new columns in desired order and copying data
alter table "public"."conversations" add column "user_input_new" text;
alter table "public"."conversations" add column "ai_output_new" text;

-- Copy data to new columns
update "public"."conversations" set "user_input_new" = "user_input";
update "public"."conversations" set "ai_output_new" = "ai_output";

-- Drop old columns
alter table "public"."conversations" drop column "user_input";
alter table "public"."conversations" drop column "ai_output";

-- Rename new columns to final names
alter table "public"."conversations" rename column "user_input_new" to "user_input";
alter table "public"."conversations" rename column "ai_output_new" to "ai_output";