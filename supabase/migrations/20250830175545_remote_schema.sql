drop extension if exists "pg_net";

alter table "public"."cist_responses" drop constraint "cist_responses_cist_category_check";

alter table "public"."conversations" drop constraint "conversations_question_type_check";

alter table "public"."photo_stories" drop constraint "photo_stories_status_check";

alter table "public"."photo_stories" drop constraint "photo_stories_tts_status_check";

alter table "public"."session_reports" drop constraint "session_reports_cognitive_status_check";

alter table "public"."sessions" drop constraint "sessions_session_type_check";

alter table "public"."sessions" drop constraint "sessions_status_check";

alter table "public"."users" drop constraint "users_gender_check";

alter table "public"."cist_responses" add constraint "cist_responses_cist_category_check" CHECK (((cist_category)::text = ANY ((ARRAY['orientation_time'::character varying, 'orientation_place'::character varying, 'memory_registration'::character varying, 'memory_recall'::character varying, 'memory_recognition'::character varying, 'attention'::character varying, 'executive_function'::character varying, 'language_naming'::character varying])::text[]))) not valid;

alter table "public"."cist_responses" validate constraint "cist_responses_cist_category_check";

alter table "public"."conversations" add constraint "conversations_question_type_check" CHECK (((question_type)::text = ANY ((ARRAY['open_ended'::character varying, 'cist_orientation'::character varying, 'cist_memory'::character varying, 'cist_attention'::character varying, 'cist_executive'::character varying, 'cist_language'::character varying])::text[]))) not valid;

alter table "public"."conversations" validate constraint "conversations_question_type_check";

alter table "public"."photo_stories" add constraint "photo_stories_status_check" CHECK (((status)::text = ANY ((ARRAY['draft'::character varying, 'generated'::character varying, 'published'::character varying])::text[]))) not valid;

alter table "public"."photo_stories" validate constraint "photo_stories_status_check";

alter table "public"."photo_stories" add constraint "photo_stories_tts_status_check" CHECK (((tts_status)::text = ANY ((ARRAY['none'::character varying, 'queued'::character varying, 'running'::character varying, 'succeeded'::character varying, 'failed'::character varying])::text[]))) not valid;

alter table "public"."photo_stories" validate constraint "photo_stories_tts_status_check";

alter table "public"."session_reports" add constraint "session_reports_cognitive_status_check" CHECK (((cognitive_status)::text = ANY ((ARRAY['normal'::character varying, 'mild_concern'::character varying, 'moderate_concern'::character varying, 'high_concern'::character varying])::text[]))) not valid;

alter table "public"."session_reports" validate constraint "session_reports_cognitive_status_check";

alter table "public"."sessions" add constraint "sessions_session_type_check" CHECK (((session_type)::text = ANY ((ARRAY['reminiscence'::character varying, 'assessment'::character varying, 'mixed'::character varying])::text[]))) not valid;

alter table "public"."sessions" validate constraint "sessions_session_type_check";

alter table "public"."sessions" add constraint "sessions_status_check" CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'completed'::character varying, 'paused'::character varying, 'cancelled'::character varying])::text[]))) not valid;

alter table "public"."sessions" validate constraint "sessions_status_check";

alter table "public"."users" add constraint "users_gender_check" CHECK (((gender)::text = ANY ((ARRAY['male'::character varying, 'female'::character varying, 'other'::character varying])::text[]))) not valid;

alter table "public"."users" validate constraint "users_gender_check";


