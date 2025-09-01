

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;


COMMENT ON SCHEMA "public" IS 'standard public schema';



CREATE EXTENSION IF NOT EXISTS "pg_graphql" WITH SCHEMA "graphql";






CREATE EXTENSION IF NOT EXISTS "pg_stat_statements" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA "extensions";






CREATE EXTENSION IF NOT EXISTS "supabase_vault" WITH SCHEMA "vault";






CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA "extensions";






CREATE OR REPLACE FUNCTION "public"."get_photos_with_conversation_status"("target_user_id" "uuid", "photo_limit" integer DEFAULT 1000) RETURNS TABLE("id" "uuid", "user_id" "uuid", "filename" character varying, "original_filename" character varying, "file_path" "text", "description" "text", "tags" "text"[], "taken_at" timestamp with time zone, "created_at" timestamp with time zone, "has_conversation" boolean)
    LANGUAGE "plpgsql"
    AS $$
BEGIN
  RETURN QUERY
  SELECT 
    p.id,
    p.user_id,
    p.filename,
    p.original_filename,
    p.file_path,
    p.description,
    p.tags,
    p.taken_at,
    p.created_at,
    CASE 
      WHEN c.photo_id IS NOT NULL THEN true 
      ELSE false 
    END as has_conversation
  FROM photos p
  LEFT JOIN (
    SELECT DISTINCT photo_id
    FROM conversations 
    WHERE user_input IS NOT NULL 
    AND user_input != ''
  ) c ON p.id = c.photo_id
  WHERE p.user_id = target_user_id 
  AND p.is_deleted = false
  ORDER BY p.created_at DESC
  LIMIT photo_limit;
END;
$$;


ALTER FUNCTION "public"."get_photos_with_conversation_status"("target_user_id" "uuid", "photo_limit" integer) OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."get_user_rows_all_tables"("p_user_id" "uuid") RETURNS "jsonb"
    LANGUAGE "plpgsql"
    AS $_$
declare
  rec record;
  sql text;
  rows jsonb;
  result jsonb := '{}'::jsonb;
begin
  for rec in
    select table_schema, table_name
    from information_schema.columns
    where table_schema = 'public'
      and column_name = 'user_id'
  loop
    sql := format(
      'select coalesce(jsonb_agg(to_jsonb(t)), ''[]''::jsonb) from %I.%I t where t.user_id = $1',
      rec.table_schema, rec.table_name
    );
    execute sql using p_user_id into rows;
    result := result || jsonb_build_object(rec.table_name, rows);
  end loop;

  return result;
end;
$_$;


ALTER FUNCTION "public"."get_user_rows_all_tables"("p_user_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."handle_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


ALTER FUNCTION "public"."handle_updated_at"() OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."is_same_family"("family_id" "uuid") RETURNS boolean
    LANGUAGE "sql" SECURITY DEFINER
    AS $$
  SELECT EXISTS (
    SELECT 1
    FROM public.family_members fm
    WHERE fm.family_id = is_same_family.family_id
      AND fm.user_id = auth.uid()::uuid
  );
$$;


ALTER FUNCTION "public"."is_same_family"("family_id" "uuid") OWNER TO "postgres";


CREATE OR REPLACE FUNCTION "public"."set_updated_at"() RETURNS "trigger"
    LANGUAGE "plpgsql"
    AS $$
begin
  new.updated_at := now();
  return new;
end $$;


ALTER FUNCTION "public"."set_updated_at"() OWNER TO "postgres";

SET default_tablespace = '';

SET default_table_access_method = "heap";


CREATE TABLE IF NOT EXISTS "public"."albums" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "name" character varying(100) NOT NULL,
    "description" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "family_id" "uuid"
);


ALTER TABLE "public"."albums" OWNER TO "postgres";


COMMENT ON TABLE "public"."albums" IS 'Photo albums for organizing user photos - NEW in T-003';



CREATE TABLE IF NOT EXISTS "public"."app_config" (
    "key" character varying(255) NOT NULL,
    "value" "jsonb" NOT NULL,
    "description" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."app_config" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."cist_responses" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "session_id" "uuid" NOT NULL,
    "user_id" "uuid" NOT NULL,
    "conversation_id" "uuid",
    "cist_category" character varying(50) NOT NULL,
    "ai_output" "text" NOT NULL,
    "expected_response" "text",
    "user_response" "text",
    "is_correct" boolean,
    "partial_score" numeric(3,2),
    "response_time_seconds" integer,
    "difficulty_level" integer DEFAULT 1,
    "notes" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    CONSTRAINT "cist_responses_cist_category_check" CHECK ((("cist_category")::"text" = ANY ((ARRAY['orientation_time'::character varying, 'orientation_place'::character varying, 'memory_registration'::character varying, 'memory_recall'::character varying, 'memory_recognition'::character varying, 'attention'::character varying, 'executive_function'::character varying, 'language_naming'::character varying])::"text"[]))),
    CONSTRAINT "cist_responses_difficulty_level_check" CHECK ((("difficulty_level" >= 1) AND ("difficulty_level" <= 5)))
);


ALTER TABLE "public"."cist_responses" OWNER TO "postgres";


CREATE OR REPLACE VIEW "public"."cist_performance_by_category" AS
 SELECT "user_id",
    "cist_category",
    "count"(*) AS "total_attempts",
    "avg"("partial_score") AS "avg_score",
    "count"(
        CASE
            WHEN ("is_correct" = true) THEN 1
            ELSE NULL::integer
        END) AS "correct_answers"
   FROM "public"."cist_responses" "cr"
  GROUP BY "user_id", "cist_category";


ALTER VIEW "public"."cist_performance_by_category" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."cist_question_templates" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "category" character varying(50) NOT NULL,
    "template_text" "text" NOT NULL,
    "context_type" character varying(50) DEFAULT 'general'::character varying,
    "difficulty_level" integer DEFAULT 1,
    "created_at" timestamp with time zone DEFAULT "now"(),
    CONSTRAINT "cist_question_templates_difficulty_level_check" CHECK ((("difficulty_level" >= 1) AND ("difficulty_level" <= 5)))
);


ALTER TABLE "public"."cist_question_templates" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."conversation_starters" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "starter_text" "text" NOT NULL,
    "context_type" character varying(50) DEFAULT 'general'::character varying,
    "emotion_tone" character varying(50) DEFAULT 'positive'::character varying,
    "created_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."conversation_starters" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."conversations" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "session_id" "uuid" NOT NULL,
    "user_id" "uuid" NOT NULL,
    "photo_id" "uuid",
    "conversation_order" integer NOT NULL,
    "ai_output" "text" NOT NULL,
    "question_type" character varying(50) NOT NULL,
    "cist_category" character varying(50),
    "user_input" "text",
    "user_response_audio_url" "text",
    "response_duration_seconds" integer,
    "ai_analysis" "jsonb",
    "cist_score" integer,
    "is_cist_item" boolean DEFAULT false,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    CONSTRAINT "conversations_question_type_check" CHECK ((("question_type")::"text" = ANY ((ARRAY['open_ended'::character varying, 'cist_orientation'::character varying, 'cist_memory'::character varying, 'cist_attention'::character varying, 'cist_executive'::character varying, 'cist_language'::character varying])::"text"[])))
);


ALTER TABLE "public"."conversations" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."families" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "family_code" character varying(10) NOT NULL,
    "family_name" character varying(100) NOT NULL,
    "created_by" "uuid",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."families" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."family_members" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "family_id" "uuid" NOT NULL,
    "family_role" character varying(50),
    "joined_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."family_members" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."photo_stories" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "photo_id" "uuid" NOT NULL,
    "title" character varying(200),
    "story_text" "text" NOT NULL,
    "language" character varying(20) DEFAULT 'ko'::character varying,
    "status" character varying(20) DEFAULT 'generated'::character varying,
    "source_session_ids" "uuid"[],
    "source_conversation_ids" "uuid"[],
    "tts_audio_path" "text",
    "tts_status" character varying(20) DEFAULT 'none'::character varying,
    "tts_params" "jsonb",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "family_id" "uuid" NOT NULL,
    CONSTRAINT "photo_stories_status_check" CHECK ((("status")::"text" = ANY ((ARRAY['draft'::character varying, 'generated'::character varying, 'published'::character varying])::"text"[]))),
    CONSTRAINT "photo_stories_tts_status_check" CHECK ((("tts_status")::"text" = ANY ((ARRAY['none'::character varying, 'queued'::character varying, 'running'::character varying, 'succeeded'::character varying, 'failed'::character varying])::"text"[])))
);


ALTER TABLE "public"."photo_stories" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."photos" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "file_name" character varying(255) NOT NULL,
    "filename" character varying(255) NOT NULL,
    "original_filename" character varying(255) NOT NULL,
    "file_path" "text" NOT NULL,
    "file_size" bigint,
    "mime_type" character varying(100),
    "width" integer,
    "height" integer,
    "description" "text",
    "tags" "text"[],
    "album_id" "uuid",
    "taken_at" timestamp with time zone,
    "location_name" character varying(255),
    "latitude" numeric(10,8),
    "longitude" numeric(11,8),
    "is_favorite" boolean DEFAULT false,
    "is_deleted" boolean DEFAULT false,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"()
);


ALTER TABLE "public"."photos" OWNER TO "postgres";


COMMENT ON COLUMN "public"."photos"."filename" IS 'Generated unique filename for storage - NEW in T-003';



COMMENT ON COLUMN "public"."photos"."original_filename" IS 'Original user-uploaded filename - NEW in T-003';



COMMENT ON COLUMN "public"."photos"."file_size" IS 'File size in bytes (BIGINT for large files) - UPDATED in T-003';



COMMENT ON COLUMN "public"."photos"."album_id" IS 'Reference to albums table - NEW in T-003';



CREATE TABLE IF NOT EXISTS "public"."session_audio_analysis" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "phodo_id" "uuid",
    "user_id" "uuid" NOT NULL,
    "family_id" "uuid" NOT NULL,
    "audio_path" "text" NOT NULL,
    "file_size" bigint,
    "adjusted_mean" numeric(12,4),
    "total_slices" integer NOT NULL,
    "dementia_slices" integer NOT NULL,
    "dementia_ratio" numeric(6,4) GENERATED ALWAYS AS (
CASE
    WHEN ("total_slices" > 0) THEN (("dementia_slices")::numeric / ("total_slices")::numeric)
    ELSE (0)::numeric
END) STORED,
    "risk_level" "text",
    "age_group_avg_ratio" numeric(6,4) DEFAULT 0.2500,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "health_score" integer GENERATED ALWAYS AS (
CASE
    WHEN ("total_slices" > 0) THEN LEAST(100, GREATEST(0, (((100)::numeric - "round"(((("dementia_slices")::numeric / ("total_slices")::numeric) * (100)::numeric))))::integer))
    ELSE 100
END) STORED,
    CONSTRAINT "session_audio_analysis_age_group_avg_ratio_check" CHECK ((("age_group_avg_ratio" >= (0)::numeric) AND ("age_group_avg_ratio" <= (1)::numeric))),
    CONSTRAINT "session_audio_analysis_dementia_ratio_check" CHECK ((("dementia_ratio" >= (0)::numeric) AND ("dementia_ratio" <= (1)::numeric))),
    CONSTRAINT "session_audio_analysis_dementia_slices_check" CHECK (("dementia_slices" >= 0)),
    CONSTRAINT "session_audio_analysis_file_size_check" CHECK (("file_size" >= 0)),
    CONSTRAINT "session_audio_analysis_risk_level_check" CHECK (("risk_level" = ANY (ARRAY['normal'::"text", 'suspect'::"text", 'risk'::"text"]))),
    CONSTRAINT "session_audio_analysis_total_slices_check" CHECK (("total_slices" >= 0))
);


ALTER TABLE "public"."session_audio_analysis" OWNER TO "postgres";


COMMENT ON COLUMN "public"."session_audio_analysis"."dementia_ratio" IS 'dementia_slices / total_slices (0~1)';



COMMENT ON COLUMN "public"."session_audio_analysis"."risk_level" IS 'UI 표시용 위험 단계: normal | suspect | risk';



COMMENT ON COLUMN "public"."session_audio_analysis"."age_group_avg_ratio" IS '동일 연령대 평균 비율 (MVP 상수, 추후 통계로 교체)';



COMMENT ON COLUMN "public"."session_audio_analysis"."health_score" IS '총 점수 (0~100): 100 - dementia_ratio*100, 높을수록 양호';



CREATE TABLE IF NOT EXISTS "public"."session_reports" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "session_id" "uuid" NOT NULL,
    "user_id" "uuid" NOT NULL,
    "total_cist_score" integer NOT NULL,
    "max_possible_score" integer DEFAULT 21,
    "cognitive_status" character varying(50),
    "category_scores" "jsonb",
    "insights" "text"[],
    "recommendations" "text"[],
    "report_generated_at" timestamp with time zone DEFAULT "now"(),
    "is_shared" boolean DEFAULT false,
    "shared_at" timestamp with time zone,
    "created_at" timestamp with time zone DEFAULT "now"(),
    CONSTRAINT "session_reports_cognitive_status_check" CHECK ((("cognitive_status")::"text" = ANY ((ARRAY['normal'::character varying, 'mild_concern'::character varying, 'moderate_concern'::character varying, 'high_concern'::character varying])::"text"[])))
);


ALTER TABLE "public"."session_reports" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."session_text_analysis" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "session_id" "uuid" NOT NULL,
    "user_id" "uuid" NOT NULL,
    "lexical_diversity" real NOT NULL,
    "mlu" real NOT NULL,
    "demonstrative_ratio" real NOT NULL,
    "speech_rate" real,
    "created_at" timestamp with time zone DEFAULT "now"(),
    CONSTRAINT "session_text_metrics_function_word_count_check" CHECK (("speech_rate" >= (0)::double precision)),
    CONSTRAINT "session_text_metrics_total_duration_seconds_check" CHECK (("demonstrative_ratio" >= (0)::double precision)),
    CONSTRAINT "session_text_metrics_total_utterances_check" CHECK (("mlu" >= (0)::double precision)),
    CONSTRAINT "session_text_metrics_total_words_check" CHECK (("lexical_diversity" >= (0)::double precision))
);


ALTER TABLE "public"."session_text_analysis" OWNER TO "postgres";


COMMENT ON TABLE "public"."session_text_analysis" IS '전체 대화 텍스트 기반 언어 분석';



CREATE TABLE IF NOT EXISTS "public"."sessions" (
    "id" "uuid" DEFAULT "extensions"."uuid_generate_v4"() NOT NULL,
    "user_id" "uuid" NOT NULL,
    "session_type" character varying(50) DEFAULT 'reminiscence'::character varying,
    "status" character varying(20) DEFAULT 'active'::character varying,
    "selected_photos" "uuid"[] NOT NULL,
    "total_duration_seconds" integer DEFAULT 0,
    "cist_score" integer,
    "cist_completed_items" integer DEFAULT 0,
    "started_at" timestamp with time zone DEFAULT "now"(),
    "completed_at" timestamp with time zone,
    "notes" "text",
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    CONSTRAINT "sessions_session_type_check" CHECK ((("session_type")::"text" = ANY ((ARRAY['reminiscence'::character varying, 'assessment'::character varying, 'mixed'::character varying])::"text"[]))),
    CONSTRAINT "sessions_status_check" CHECK ((("status")::"text" = ANY ((ARRAY['active'::character varying, 'completed'::character varying, 'paused'::character varying, 'cancelled'::character varying])::"text"[])))
);


ALTER TABLE "public"."sessions" OWNER TO "postgres";


CREATE OR REPLACE VIEW "public"."user_album_summary" AS
 SELECT "a"."id" AS "album_id",
    "a"."name" AS "album_name",
    "a"."description",
    "a"."user_id",
    "count"("p"."id") AS "photo_count",
    "max"("p"."created_at") AS "last_photo_added"
   FROM ("public"."albums" "a"
     LEFT JOIN "public"."photos" "p" ON ((("a"."id" = "p"."album_id") AND ("p"."is_deleted" = false))))
  GROUP BY "a"."id", "a"."name", "a"."description", "a"."user_id";


ALTER VIEW "public"."user_album_summary" OWNER TO "postgres";


CREATE TABLE IF NOT EXISTS "public"."users" (
    "id" "uuid" NOT NULL,
    "email" character varying(255) NOT NULL,
    "full_name" character varying(255),
    "birth_date" "date",
    "gender" character varying(10),
    "phone" character varying(20),
    "profile_image_url" "text",
    "onboarding_completed" boolean DEFAULT false,
    "privacy_consent" boolean DEFAULT false,
    "terms_accepted" boolean DEFAULT false,
    "notification_enabled" boolean DEFAULT true,
    "created_at" timestamp with time zone DEFAULT "now"(),
    "updated_at" timestamp with time zone DEFAULT "now"(),
    "is_guardian" boolean DEFAULT false,
    "current_family_id" "uuid",
    CONSTRAINT "users_gender_check" CHECK ((("gender")::"text" = ANY ((ARRAY['male'::character varying, 'female'::character varying, 'other'::character varying])::"text"[])))
);


ALTER TABLE "public"."users" OWNER TO "postgres";


CREATE OR REPLACE VIEW "public"."user_session_summary" AS
 SELECT "u"."id" AS "user_id",
    "u"."full_name",
    "u"."email",
    "count"("s"."id") AS "total_sessions",
    "avg"("s"."cist_score") AS "avg_cist_score",
    "max"("s"."started_at") AS "last_session_date",
    "sum"("s"."total_duration_seconds") AS "total_conversation_time"
   FROM ("public"."users" "u"
     LEFT JOIN "public"."sessions" "s" ON (("u"."id" = "s"."user_id")))
  WHERE (("s"."status")::"text" = 'completed'::"text")
  GROUP BY "u"."id", "u"."full_name", "u"."email";


ALTER VIEW "public"."user_session_summary" OWNER TO "postgres";


ALTER TABLE ONLY "public"."albums"
    ADD CONSTRAINT "albums_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."app_config"
    ADD CONSTRAINT "app_config_pkey" PRIMARY KEY ("key");



ALTER TABLE ONLY "public"."cist_question_templates"
    ADD CONSTRAINT "cist_question_templates_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."cist_responses"
    ADD CONSTRAINT "cist_responses_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."conversation_starters"
    ADD CONSTRAINT "conversation_starters_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."conversations"
    ADD CONSTRAINT "conversations_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."families"
    ADD CONSTRAINT "families_family_code_key" UNIQUE ("family_code");



ALTER TABLE ONLY "public"."families"
    ADD CONSTRAINT "families_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."family_members"
    ADD CONSTRAINT "family_members_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."family_members"
    ADD CONSTRAINT "family_members_user_id_family_id_key" UNIQUE ("user_id", "family_id");



ALTER TABLE ONLY "public"."photo_stories"
    ADD CONSTRAINT "photo_stories_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."photo_stories"
    ADD CONSTRAINT "photo_stories_user_id_photo_id_key" UNIQUE ("user_id", "photo_id");



ALTER TABLE ONLY "public"."photos"
    ADD CONSTRAINT "photos_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."session_audio_analysis"
    ADD CONSTRAINT "session_audio_analysis_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."session_reports"
    ADD CONSTRAINT "session_reports_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."session_text_analysis"
    ADD CONSTRAINT "session_text_metrics_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."session_text_analysis"
    ADD CONSTRAINT "session_text_metrics_session_id_key" UNIQUE ("session_id");



ALTER TABLE ONLY "public"."sessions"
    ADD CONSTRAINT "sessions_pkey" PRIMARY KEY ("id");



ALTER TABLE ONLY "public"."users"
    ADD CONSTRAINT "users_email_key" UNIQUE ("email");



ALTER TABLE ONLY "public"."users"
    ADD CONSTRAINT "users_pkey" PRIMARY KEY ("id");



CREATE INDEX "idx_albums_name" ON "public"."albums" USING "btree" ("user_id", "name");



CREATE INDEX "idx_albums_user_id" ON "public"."albums" USING "btree" ("user_id");



CREATE INDEX "idx_cist_responses_category" ON "public"."cist_responses" USING "btree" ("cist_category");



CREATE INDEX "idx_cist_responses_session_id" ON "public"."cist_responses" USING "btree" ("session_id");



CREATE INDEX "idx_cist_responses_user_id" ON "public"."cist_responses" USING "btree" ("user_id");



CREATE INDEX "idx_cist_templates_category" ON "public"."cist_question_templates" USING "btree" ("category");



CREATE INDEX "idx_cist_templates_context" ON "public"."cist_question_templates" USING "btree" ("context_type");



CREATE INDEX "idx_conversations_question_type" ON "public"."conversations" USING "btree" ("question_type");



CREATE INDEX "idx_conversations_session_id" ON "public"."conversations" USING "btree" ("session_id");



CREATE INDEX "idx_conversations_user_id" ON "public"."conversations" USING "btree" ("user_id");



CREATE INDEX "idx_families_code" ON "public"."families" USING "btree" ("family_code");



CREATE INDEX "idx_family_members_family_id" ON "public"."family_members" USING "btree" ("family_id");



CREATE INDEX "idx_family_members_user_id" ON "public"."family_members" USING "btree" ("user_id");



CREATE INDEX "idx_photo_stories_family" ON "public"."photo_stories" USING "btree" ("family_id");



CREATE INDEX "idx_photo_stories_family_user" ON "public"."photo_stories" USING "btree" ("family_id", "user_id");



CREATE INDEX "idx_photo_stories_photo" ON "public"."photo_stories" USING "btree" ("photo_id");



CREATE INDEX "idx_photo_stories_user" ON "public"."photo_stories" USING "btree" ("user_id");



CREATE INDEX "idx_photos_album_id" ON "public"."photos" USING "btree" ("album_id");



CREATE INDEX "idx_photos_created_at" ON "public"."photos" USING "btree" ("created_at" DESC);



CREATE INDEX "idx_photos_filename" ON "public"."photos" USING "btree" ("filename");



CREATE INDEX "idx_photos_is_deleted" ON "public"."photos" USING "btree" ("is_deleted") WHERE ("is_deleted" = false);



CREATE INDEX "idx_photos_is_favorite" ON "public"."photos" USING "btree" ("user_id", "is_favorite") WHERE ("is_favorite" = true);



CREATE INDEX "idx_photos_tags" ON "public"."photos" USING "gin" ("tags");



CREATE INDEX "idx_photos_user_id" ON "public"."photos" USING "btree" ("user_id");



CREATE INDEX "idx_saa_family_id" ON "public"."session_audio_analysis" USING "btree" ("family_id");



CREATE INDEX "idx_saa_user_id" ON "public"."session_audio_analysis" USING "btree" ("user_id");



CREATE INDEX "idx_session_reports_user_id" ON "public"."session_reports" USING "btree" ("user_id");



CREATE INDEX "idx_session_text_metrics_session_id" ON "public"."session_text_analysis" USING "btree" ("session_id");



CREATE INDEX "idx_session_text_metrics_user_id" ON "public"."session_text_analysis" USING "btree" ("user_id");



CREATE INDEX "idx_sessions_started_at" ON "public"."sessions" USING "btree" ("started_at" DESC);



CREATE INDEX "idx_sessions_status" ON "public"."sessions" USING "btree" ("status");



CREATE INDEX "idx_sessions_user_id" ON "public"."sessions" USING "btree" ("user_id");



CREATE INDEX "idx_users_current_family_id" ON "public"."users" USING "btree" ("current_family_id");



CREATE INDEX "idx_users_email" ON "public"."users" USING "btree" ("email");



CREATE OR REPLACE TRIGGER "albums_updated_at" BEFORE UPDATE ON "public"."albums" FOR EACH ROW EXECUTE FUNCTION "public"."handle_updated_at"();



CREATE OR REPLACE TRIGGER "app_config_updated_at" BEFORE UPDATE ON "public"."app_config" FOR EACH ROW EXECUTE FUNCTION "public"."handle_updated_at"();



CREATE OR REPLACE TRIGGER "conversations_updated_at" BEFORE UPDATE ON "public"."conversations" FOR EACH ROW EXECUTE FUNCTION "public"."handle_updated_at"();



CREATE OR REPLACE TRIGGER "photos_updated_at" BEFORE UPDATE ON "public"."photos" FOR EACH ROW EXECUTE FUNCTION "public"."handle_updated_at"();



CREATE OR REPLACE TRIGGER "sessions_updated_at" BEFORE UPDATE ON "public"."sessions" FOR EACH ROW EXECUTE FUNCTION "public"."handle_updated_at"();



CREATE OR REPLACE TRIGGER "trg_photo_stories_updated" BEFORE UPDATE ON "public"."photo_stories" FOR EACH ROW EXECUTE FUNCTION "public"."set_updated_at"();



CREATE OR REPLACE TRIGGER "users_updated_at" BEFORE UPDATE ON "public"."users" FOR EACH ROW EXECUTE FUNCTION "public"."handle_updated_at"();



ALTER TABLE ONLY "public"."albums"
    ADD CONSTRAINT "albums_family_id_fkey" FOREIGN KEY ("family_id") REFERENCES "public"."families"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."albums"
    ADD CONSTRAINT "albums_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."cist_responses"
    ADD CONSTRAINT "cist_responses_conversation_id_fkey" FOREIGN KEY ("conversation_id") REFERENCES "public"."conversations"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."cist_responses"
    ADD CONSTRAINT "cist_responses_session_id_fkey" FOREIGN KEY ("session_id") REFERENCES "public"."sessions"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."cist_responses"
    ADD CONSTRAINT "cist_responses_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."conversations"
    ADD CONSTRAINT "conversations_photo_id_fkey" FOREIGN KEY ("photo_id") REFERENCES "public"."photos"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."conversations"
    ADD CONSTRAINT "conversations_session_id_fkey" FOREIGN KEY ("session_id") REFERENCES "public"."sessions"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."conversations"
    ADD CONSTRAINT "conversations_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."families"
    ADD CONSTRAINT "families_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "public"."users"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."family_members"
    ADD CONSTRAINT "family_members_family_id_fkey" FOREIGN KEY ("family_id") REFERENCES "public"."families"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."family_members"
    ADD CONSTRAINT "family_members_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."photo_stories"
    ADD CONSTRAINT "photo_stories_family_id_fkey" FOREIGN KEY ("family_id") REFERENCES "public"."families"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."photo_stories"
    ADD CONSTRAINT "photo_stories_photo_id_fkey" FOREIGN KEY ("photo_id") REFERENCES "public"."photos"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."photo_stories"
    ADD CONSTRAINT "photo_stories_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."photos"
    ADD CONSTRAINT "photos_album_id_fkey" FOREIGN KEY ("album_id") REFERENCES "public"."albums"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."photos"
    ADD CONSTRAINT "photos_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."session_audio_analysis"
    ADD CONSTRAINT "session_audio_analysis_family_id_fkey" FOREIGN KEY ("family_id") REFERENCES "public"."families"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."session_audio_analysis"
    ADD CONSTRAINT "session_audio_analysis_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."session_reports"
    ADD CONSTRAINT "session_reports_session_id_fkey" FOREIGN KEY ("session_id") REFERENCES "public"."sessions"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."session_reports"
    ADD CONSTRAINT "session_reports_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."session_text_analysis"
    ADD CONSTRAINT "session_text_metrics_session_id_fkey" FOREIGN KEY ("session_id") REFERENCES "public"."sessions"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."session_text_analysis"
    ADD CONSTRAINT "session_text_metrics_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."sessions"
    ADD CONSTRAINT "sessions_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE CASCADE;



ALTER TABLE ONLY "public"."users"
    ADD CONSTRAINT "users_current_family_id_fkey" FOREIGN KEY ("current_family_id") REFERENCES "public"."families"("id") ON DELETE SET NULL;



ALTER TABLE ONLY "public"."users"
    ADD CONSTRAINT "users_id_fkey" FOREIGN KEY ("id") REFERENCES "auth"."users"("id") ON DELETE CASCADE;



CREATE POLICY "Delete cist_responses (self or family via session)" ON "public"."cist_responses" FOR DELETE TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM (("public"."sessions" "s"
     JOIN "public"."family_members" "me" ON (("me"."user_id" = "auth"."uid"())))
     JOIN "public"."family_members" "target" ON ((("target"."user_id" = "s"."user_id") AND ("target"."family_id" = "me"."family_id"))))
  WHERE ("s"."id" = "cist_responses"."session_id"))));



CREATE POLICY "Family can insert conversations" ON "public"."conversations" FOR INSERT TO "authenticated" WITH CHECK ((EXISTS ( SELECT 1
   FROM (("public"."sessions" "s"
     JOIN "public"."family_members" "me" ON (("me"."user_id" = "auth"."uid"())))
     JOIN "public"."family_members" "target" ON ((("target"."user_id" = "s"."user_id") AND ("target"."family_id" = "me"."family_id"))))
  WHERE ("s"."id" = "conversations"."session_id"))));



CREATE POLICY "Family can insert session_reports" ON "public"."session_reports" FOR INSERT TO "authenticated" WITH CHECK ((EXISTS ( SELECT 1
   FROM (("public"."sessions" "s"
     JOIN "public"."family_members" "me" ON (("me"."user_id" = "auth"."uid"())))
     JOIN "public"."family_members" "target" ON ((("target"."user_id" = "s"."user_id") AND ("target"."family_id" = "me"."family_id"))))
  WHERE ("s"."id" = "session_reports"."session_id"))));



CREATE POLICY "Family can insert sessions" ON "public"."sessions" FOR INSERT TO "authenticated" WITH CHECK ((EXISTS ( SELECT 1
   FROM ("public"."family_members" "me"
     JOIN "public"."family_members" "target" ON (("target"."family_id" = "me"."family_id")))
  WHERE (("me"."user_id" = "auth"."uid"()) AND ("target"."user_id" = "sessions"."user_id")))));



CREATE POLICY "Family can update conversations" ON "public"."conversations" FOR UPDATE TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM (("public"."sessions" "s"
     JOIN "public"."family_members" "me" ON (("me"."user_id" = "auth"."uid"())))
     JOIN "public"."family_members" "target" ON ((("target"."user_id" = "s"."user_id") AND ("target"."family_id" = "me"."family_id"))))
  WHERE ("s"."id" = "conversations"."session_id")))) WITH CHECK ((EXISTS ( SELECT 1
   FROM (("public"."sessions" "s"
     JOIN "public"."family_members" "me" ON (("me"."user_id" = "auth"."uid"())))
     JOIN "public"."family_members" "target" ON ((("target"."user_id" = "s"."user_id") AND ("target"."family_id" = "me"."family_id"))))
  WHERE ("s"."id" = "conversations"."session_id"))));



CREATE POLICY "Family can update sessions" ON "public"."sessions" FOR UPDATE TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM ("public"."family_members" "me"
     JOIN "public"."family_members" "target" ON (("target"."family_id" = "me"."family_id")))
  WHERE (("me"."user_id" = "auth"."uid"()) AND ("target"."user_id" = "sessions"."user_id"))))) WITH CHECK ((EXISTS ( SELECT 1
   FROM ("public"."family_members" "me"
     JOIN "public"."family_members" "target" ON (("target"."family_id" = "me"."family_id")))
  WHERE (("me"."user_id" = "auth"."uid"()) AND ("target"."user_id" = "sessions"."user_id")))));



CREATE POLICY "Family can view conversations" ON "public"."conversations" FOR SELECT TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM (("public"."sessions" "s"
     JOIN "public"."family_members" "me" ON (("me"."user_id" = "auth"."uid"())))
     JOIN "public"."family_members" "target" ON ((("target"."user_id" = "s"."user_id") AND ("target"."family_id" = "me"."family_id"))))
  WHERE ("s"."id" = "conversations"."session_id"))));



CREATE POLICY "Family can view session_reports" ON "public"."session_reports" FOR SELECT TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM (("public"."sessions" "s"
     JOIN "public"."family_members" "me" ON (("me"."user_id" = "auth"."uid"())))
     JOIN "public"."family_members" "target" ON ((("target"."user_id" = "s"."user_id") AND ("target"."family_id" = "me"."family_id"))))
  WHERE ("s"."id" = "session_reports"."session_id"))));



CREATE POLICY "Family can view sessions" ON "public"."sessions" FOR SELECT TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM ("public"."family_members" "me"
     JOIN "public"."family_members" "target" ON (("target"."family_id" = "me"."family_id")))
  WHERE (("me"."user_id" = "auth"."uid"()) AND ("target"."user_id" = "sessions"."user_id")))));



CREATE POLICY "Family members can view basic info" ON "public"."users" FOR SELECT USING ((EXISTS ( SELECT 1
   FROM "public"."family_members" "fm1",
    "public"."family_members" "fm2"
  WHERE (("fm1"."user_id" = "auth"."uid"()) AND ("fm2"."user_id" = "users"."id") AND ("fm1"."family_id" = "fm2"."family_id")))));



CREATE POLICY "Insert cist_responses (self or family via session)" ON "public"."cist_responses" FOR INSERT TO "authenticated" WITH CHECK ((EXISTS ( SELECT 1
   FROM (("public"."sessions" "s"
     JOIN "public"."family_members" "me" ON (("me"."user_id" = "auth"."uid"())))
     JOIN "public"."family_members" "target" ON ((("target"."user_id" = "s"."user_id") AND ("target"."family_id" = "me"."family_id"))))
  WHERE ("s"."id" = "cist_responses"."session_id"))));



CREATE POLICY "Update cist_responses (self or family via session)" ON "public"."cist_responses" FOR UPDATE TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM (("public"."sessions" "s"
     JOIN "public"."family_members" "me" ON (("me"."user_id" = "auth"."uid"())))
     JOIN "public"."family_members" "target" ON ((("target"."user_id" = "s"."user_id") AND ("target"."family_id" = "me"."family_id"))))
  WHERE ("s"."id" = "cist_responses"."session_id")))) WITH CHECK ((EXISTS ( SELECT 1
   FROM (("public"."sessions" "s"
     JOIN "public"."family_members" "me" ON (("me"."user_id" = "auth"."uid"())))
     JOIN "public"."family_members" "target" ON ((("target"."user_id" = "s"."user_id") AND ("target"."family_id" = "me"."family_id"))))
  WHERE ("s"."id" = "cist_responses"."session_id"))));



CREATE POLICY "Users can delete own albums" ON "public"."albums" FOR DELETE USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can delete own family_members" ON "public"."family_members" FOR DELETE USING (("user_id" = "auth"."uid"()));



CREATE POLICY "Users can delete own photos" ON "public"."photos" FOR DELETE USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can delete own profile" ON "public"."users" FOR DELETE USING (("auth"."uid"() = "id"));



CREATE POLICY "Users can insert own albums" ON "public"."albums" FOR INSERT WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can insert own conversations" ON "public"."conversations" FOR INSERT WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can insert own family_members" ON "public"."family_members" FOR INSERT WITH CHECK (("user_id" = "auth"."uid"()));



CREATE POLICY "Users can insert own photos" ON "public"."photos" FOR INSERT WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can insert own reports" ON "public"."session_reports" FOR INSERT WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can insert own sessions" ON "public"."sessions" FOR INSERT WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can update own albums" ON "public"."albums" FOR UPDATE USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can update own conversations" ON "public"."conversations" FOR UPDATE USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can update own family_members" ON "public"."family_members" FOR UPDATE USING (("user_id" = "auth"."uid"()));



CREATE POLICY "Users can update own photos" ON "public"."photos" FOR UPDATE USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can update own profile" ON "public"."users" FOR UPDATE USING (("auth"."uid"() = "id")) WITH CHECK (("auth"."uid"() = "id"));



CREATE POLICY "Users can update own sessions" ON "public"."sessions" FOR UPDATE USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can upsert own profile" ON "public"."users" FOR INSERT WITH CHECK (("auth"."uid"() = "id"));



CREATE POLICY "Users can view family_members in same family" ON "public"."family_members" FOR SELECT USING ("public"."is_same_family"("family_id"));



CREATE POLICY "Users can view own albums" ON "public"."albums" FOR SELECT USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can view own conversations" ON "public"."conversations" FOR SELECT USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can view own families" ON "public"."families" FOR SELECT USING ((("created_by" = "auth"."uid"()) OR (EXISTS ( SELECT 1
   FROM "public"."family_members" "fm"
  WHERE (("fm"."family_id" = "families"."id") AND ("fm"."user_id" = "auth"."uid"())))) OR ("family_code" IS NOT NULL)));



CREATE POLICY "Users can view own photos" ON "public"."photos" FOR SELECT USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can view own profile" ON "public"."users" FOR SELECT TO "authenticated" USING (("auth"."uid"() = "id"));



CREATE POLICY "Users can view own reports" ON "public"."session_reports" FOR SELECT USING (("auth"."uid"() = "user_id"));



CREATE POLICY "Users can view own sessions" ON "public"."sessions" FOR SELECT USING (("auth"."uid"() = "user_id"));



CREATE POLICY "View cist_responses (self or family)" ON "public"."cist_responses" FOR SELECT TO "authenticated" USING ((EXISTS ( SELECT 1
   FROM (("public"."sessions" "s"
     JOIN "public"."family_members" "me" ON (("me"."user_id" = "auth"."uid"())))
     JOIN "public"."family_members" "target" ON ((("target"."user_id" = "s"."user_id") AND ("target"."family_id" = "me"."family_id"))))
  WHERE ("s"."id" = "cist_responses"."session_id"))));



ALTER TABLE "public"."albums" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "albums_delete_family" ON "public"."albums" FOR DELETE USING ((EXISTS ( SELECT 1
   FROM ("public"."families" "f"
     JOIN "public"."family_members" "fm" ON (("f"."id" = "fm"."family_id")))
  WHERE (("f"."id" = "albums"."family_id") AND ("fm"."user_id" = "auth"."uid"())))));



CREATE POLICY "albums_insert_family" ON "public"."albums" FOR INSERT WITH CHECK ((EXISTS ( SELECT 1
   FROM ("public"."families" "f"
     JOIN "public"."family_members" "fm" ON (("f"."id" = "fm"."family_id")))
  WHERE (("f"."id" = "fm"."family_id") AND ("fm"."user_id" = "auth"."uid"())))));



CREATE POLICY "albums_select_family" ON "public"."albums" FOR SELECT USING ((EXISTS ( SELECT 1
   FROM ("public"."families" "f"
     JOIN "public"."family_members" "fm" ON (("f"."id" = "fm"."family_id")))
  WHERE (("f"."id" = "albums"."family_id") AND ("fm"."user_id" = "auth"."uid"())))));



CREATE POLICY "albums_update_family" ON "public"."albums" FOR UPDATE USING ((EXISTS ( SELECT 1
   FROM ("public"."families" "f"
     JOIN "public"."family_members" "fm" ON (("f"."id" = "fm"."family_id")))
  WHERE (("f"."id" = "albums"."family_id") AND ("fm"."user_id" = "auth"."uid"())))));



ALTER TABLE "public"."cist_responses" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."conversations" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."families" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "families_delete" ON "public"."families" FOR DELETE USING (("created_by" = "auth"."uid"()));



CREATE POLICY "families_insert" ON "public"."families" FOR INSERT WITH CHECK (true);



CREATE POLICY "families_update" ON "public"."families" FOR UPDATE USING (("created_by" = "auth"."uid"()));



ALTER TABLE "public"."family_members" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."photo_stories" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."photos" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "photos_delete_family" ON "public"."photos" FOR DELETE USING ((EXISTS ( SELECT 1
   FROM ("public"."albums" "a"
     JOIN "public"."family_members" "fm" ON (("a"."family_id" = "fm"."family_id")))
  WHERE (("a"."id" = "photos"."album_id") AND ("fm"."user_id" = "auth"."uid"())))));



CREATE POLICY "photos_insert_family" ON "public"."photos" FOR INSERT WITH CHECK ((EXISTS ( SELECT 1
   FROM ("public"."albums" "a"
     JOIN "public"."family_members" "fm" ON (("a"."family_id" = "fm"."family_id")))
  WHERE (("a"."id" = "photos"."album_id") AND ("fm"."user_id" = "auth"."uid"())))));



CREATE POLICY "photos_select_family" ON "public"."photos" FOR SELECT USING ((EXISTS ( SELECT 1
   FROM ("public"."albums" "a"
     JOIN "public"."family_members" "fm" ON (("a"."family_id" = "fm"."family_id")))
  WHERE (("a"."id" = "photos"."album_id") AND ("fm"."user_id" = "auth"."uid"())))));



CREATE POLICY "photos_update_family" ON "public"."photos" FOR UPDATE USING ((EXISTS ( SELECT 1
   FROM ("public"."albums" "a"
     JOIN "public"."family_members" "fm" ON (("a"."family_id" = "fm"."family_id")))
  WHERE (("a"."id" = "photos"."album_id") AND ("fm"."user_id" = "auth"."uid"())))));



CREATE POLICY "pst_delete_own" ON "public"."photo_stories" FOR DELETE USING (("auth"."uid"() = "user_id"));



CREATE POLICY "pst_insert_photo_owned_or_family" ON "public"."photo_stories" FOR INSERT WITH CHECK ((("auth"."uid"() = "user_id") AND (EXISTS ( SELECT 1
   FROM "public"."photos" "p"
  WHERE (("p"."id" = "photo_stories"."photo_id") AND (("p"."user_id" = "auth"."uid"()) OR (EXISTS ( SELECT 1
           FROM ("public"."family_members" "fm1"
             JOIN "public"."family_members" "fm2" ON (("fm1"."family_id" = "fm2"."family_id")))
          WHERE (("fm1"."user_id" = "auth"."uid"()) AND ("fm2"."user_id" = "p"."user_id"))))))))));



CREATE POLICY "pst_select_owner_or_family" ON "public"."photo_stories" FOR SELECT USING ((("auth"."uid"() = "user_id") OR (EXISTS ( SELECT 1
   FROM (("public"."photos" "p"
     JOIN "public"."family_members" "fm1" ON (("fm1"."user_id" = "auth"."uid"())))
     JOIN "public"."family_members" "fm2" ON ((("fm2"."user_id" = "p"."user_id") AND ("fm1"."family_id" = "fm2"."family_id"))))
  WHERE ("p"."id" = "photo_stories"."photo_id")))));



CREATE POLICY "pst_update_photo_owned_or_family" ON "public"."photo_stories" FOR UPDATE USING (("auth"."uid"() = "user_id")) WITH CHECK ((("auth"."uid"() = "user_id") AND (EXISTS ( SELECT 1
   FROM "public"."photos" "p"
  WHERE (("p"."id" = "photo_stories"."photo_id") AND (("p"."user_id" = "auth"."uid"()) OR (EXISTS ( SELECT 1
           FROM ("public"."family_members" "fm1"
             JOIN "public"."family_members" "fm2" ON (("fm1"."family_id" = "fm2"."family_id")))
          WHERE (("fm1"."user_id" = "auth"."uid"()) AND ("fm2"."user_id" = "p"."user_id"))))))))));



CREATE POLICY "saa_delete_own" ON "public"."session_audio_analysis" FOR DELETE USING (("auth"."uid"() = "user_id"));



CREATE POLICY "saa_insert_own_and_family_member" ON "public"."session_audio_analysis" FOR INSERT WITH CHECK ((("auth"."uid"() = "user_id") AND (EXISTS ( SELECT 1
   FROM "public"."family_members" "fm"
  WHERE (("fm"."user_id" = "auth"."uid"()) AND ("fm"."family_id" = "session_audio_analysis"."family_id"))))));



CREATE POLICY "saa_select_self_or_family" ON "public"."session_audio_analysis" FOR SELECT USING ((("auth"."uid"() = "user_id") OR (EXISTS ( SELECT 1
   FROM "public"."family_members" "fm"
  WHERE (("fm"."user_id" = "auth"."uid"()) AND ("fm"."family_id" = "session_audio_analysis"."family_id"))))));



CREATE POLICY "saa_update_own" ON "public"."session_audio_analysis" FOR UPDATE USING (("auth"."uid"() = "user_id")) WITH CHECK (("auth"."uid"() = "user_id"));



ALTER TABLE "public"."session_reports" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."session_text_analysis" ENABLE ROW LEVEL SECURITY;


ALTER TABLE "public"."sessions" ENABLE ROW LEVEL SECURITY;


CREATE POLICY "stm_insert_own" ON "public"."session_text_analysis" FOR INSERT WITH CHECK (("auth"."uid"() = "user_id"));



CREATE POLICY "stm_select_own" ON "public"."session_text_analysis" FOR SELECT USING (("auth"."uid"() = "user_id"));



CREATE POLICY "stm_update_own" ON "public"."session_text_analysis" FOR UPDATE USING (("auth"."uid"() = "user_id")) WITH CHECK (("auth"."uid"() = "user_id"));



ALTER TABLE "public"."users" ENABLE ROW LEVEL SECURITY;




ALTER PUBLICATION "supabase_realtime" OWNER TO "postgres";


GRANT USAGE ON SCHEMA "public" TO "postgres";
GRANT USAGE ON SCHEMA "public" TO "anon";
GRANT USAGE ON SCHEMA "public" TO "authenticated";
GRANT USAGE ON SCHEMA "public" TO "service_role";

























































































































































GRANT ALL ON FUNCTION "public"."get_photos_with_conversation_status"("target_user_id" "uuid", "photo_limit" integer) TO "anon";
GRANT ALL ON FUNCTION "public"."get_photos_with_conversation_status"("target_user_id" "uuid", "photo_limit" integer) TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_photos_with_conversation_status"("target_user_id" "uuid", "photo_limit" integer) TO "service_role";



GRANT ALL ON FUNCTION "public"."get_user_rows_all_tables"("p_user_id" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."get_user_rows_all_tables"("p_user_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."get_user_rows_all_tables"("p_user_id" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."handle_updated_at"() TO "anon";
GRANT ALL ON FUNCTION "public"."handle_updated_at"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."handle_updated_at"() TO "service_role";



GRANT ALL ON FUNCTION "public"."is_same_family"("family_id" "uuid") TO "anon";
GRANT ALL ON FUNCTION "public"."is_same_family"("family_id" "uuid") TO "authenticated";
GRANT ALL ON FUNCTION "public"."is_same_family"("family_id" "uuid") TO "service_role";



GRANT ALL ON FUNCTION "public"."set_updated_at"() TO "anon";
GRANT ALL ON FUNCTION "public"."set_updated_at"() TO "authenticated";
GRANT ALL ON FUNCTION "public"."set_updated_at"() TO "service_role";


















GRANT ALL ON TABLE "public"."albums" TO "anon";
GRANT ALL ON TABLE "public"."albums" TO "authenticated";
GRANT ALL ON TABLE "public"."albums" TO "service_role";



GRANT ALL ON TABLE "public"."app_config" TO "anon";
GRANT ALL ON TABLE "public"."app_config" TO "authenticated";
GRANT ALL ON TABLE "public"."app_config" TO "service_role";



GRANT ALL ON TABLE "public"."cist_responses" TO "anon";
GRANT ALL ON TABLE "public"."cist_responses" TO "authenticated";
GRANT ALL ON TABLE "public"."cist_responses" TO "service_role";



GRANT ALL ON TABLE "public"."cist_performance_by_category" TO "anon";
GRANT ALL ON TABLE "public"."cist_performance_by_category" TO "authenticated";
GRANT ALL ON TABLE "public"."cist_performance_by_category" TO "service_role";



GRANT ALL ON TABLE "public"."cist_question_templates" TO "anon";
GRANT ALL ON TABLE "public"."cist_question_templates" TO "authenticated";
GRANT ALL ON TABLE "public"."cist_question_templates" TO "service_role";



GRANT ALL ON TABLE "public"."conversation_starters" TO "anon";
GRANT ALL ON TABLE "public"."conversation_starters" TO "authenticated";
GRANT ALL ON TABLE "public"."conversation_starters" TO "service_role";



GRANT ALL ON TABLE "public"."conversations" TO "anon";
GRANT ALL ON TABLE "public"."conversations" TO "authenticated";
GRANT ALL ON TABLE "public"."conversations" TO "service_role";



GRANT ALL ON TABLE "public"."families" TO "anon";
GRANT ALL ON TABLE "public"."families" TO "authenticated";
GRANT ALL ON TABLE "public"."families" TO "service_role";



GRANT ALL ON TABLE "public"."family_members" TO "anon";
GRANT ALL ON TABLE "public"."family_members" TO "authenticated";
GRANT ALL ON TABLE "public"."family_members" TO "service_role";



GRANT ALL ON TABLE "public"."photo_stories" TO "anon";
GRANT ALL ON TABLE "public"."photo_stories" TO "authenticated";
GRANT ALL ON TABLE "public"."photo_stories" TO "service_role";



GRANT ALL ON TABLE "public"."photos" TO "anon";
GRANT ALL ON TABLE "public"."photos" TO "authenticated";
GRANT ALL ON TABLE "public"."photos" TO "service_role";



GRANT ALL ON TABLE "public"."session_audio_analysis" TO "anon";
GRANT ALL ON TABLE "public"."session_audio_analysis" TO "authenticated";
GRANT ALL ON TABLE "public"."session_audio_analysis" TO "service_role";



GRANT ALL ON TABLE "public"."session_reports" TO "anon";
GRANT ALL ON TABLE "public"."session_reports" TO "authenticated";
GRANT ALL ON TABLE "public"."session_reports" TO "service_role";



GRANT ALL ON TABLE "public"."session_text_analysis" TO "anon";
GRANT ALL ON TABLE "public"."session_text_analysis" TO "authenticated";
GRANT ALL ON TABLE "public"."session_text_analysis" TO "service_role";



GRANT ALL ON TABLE "public"."sessions" TO "anon";
GRANT ALL ON TABLE "public"."sessions" TO "authenticated";
GRANT ALL ON TABLE "public"."sessions" TO "service_role";



GRANT ALL ON TABLE "public"."user_album_summary" TO "anon";
GRANT ALL ON TABLE "public"."user_album_summary" TO "authenticated";
GRANT ALL ON TABLE "public"."user_album_summary" TO "service_role";



GRANT ALL ON TABLE "public"."users" TO "anon";
GRANT ALL ON TABLE "public"."users" TO "authenticated";
GRANT ALL ON TABLE "public"."users" TO "service_role";



GRANT ALL ON TABLE "public"."user_session_summary" TO "anon";
GRANT ALL ON TABLE "public"."user_session_summary" TO "authenticated";
GRANT ALL ON TABLE "public"."user_session_summary" TO "service_role";









ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON SEQUENCES TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON FUNCTIONS TO "service_role";






ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "postgres";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "anon";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "authenticated";
ALTER DEFAULT PRIVILEGES FOR ROLE "postgres" IN SCHEMA "public" GRANT ALL ON TABLES TO "service_role";






























RESET ALL;
