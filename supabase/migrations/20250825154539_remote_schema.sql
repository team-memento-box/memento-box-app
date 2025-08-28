drop extension if exists "pg_net";


  create table "public"."albums" (
    "id" uuid not null default uuid_generate_v4(),
    "user_id" uuid not null,
    "name" character varying(100) not null,
    "description" text,
    "created_at" timestamp with time zone default now(),
    "updated_at" timestamp with time zone default now(),
    "family_id" uuid
      );


alter table "public"."albums" enable row level security;


  create table "public"."app_config" (
    "key" character varying(255) not null,
    "value" jsonb not null,
    "description" text,
    "created_at" timestamp with time zone default now(),
    "updated_at" timestamp with time zone default now()
      );



  create table "public"."cist_question_templates" (
    "id" uuid not null default uuid_generate_v4(),
    "category" character varying(50) not null,
    "template_text" text not null,
    "context_type" character varying(50) default 'general'::character varying,
    "difficulty_level" integer default 1,
    "created_at" timestamp with time zone default now()
      );



  create table "public"."cist_responses" (
    "id" uuid not null default uuid_generate_v4(),
    "session_id" uuid not null,
    "user_id" uuid not null,
    "conversation_id" uuid,
    "cist_category" character varying(50) not null,
    "question_text" text not null,
    "expected_response" text,
    "user_response" text,
    "is_correct" boolean,
    "partial_score" numeric(3,2),
    "response_time_seconds" integer,
    "difficulty_level" integer default 1,
    "notes" text,
    "created_at" timestamp with time zone default now()
      );


alter table "public"."cist_responses" enable row level security;


  create table "public"."conversation_starters" (
    "id" uuid not null default uuid_generate_v4(),
    "starter_text" text not null,
    "context_type" character varying(50) default 'general'::character varying,
    "emotion_tone" character varying(50) default 'positive'::character varying,
    "created_at" timestamp with time zone default now()
      );



  create table "public"."conversations" (
    "id" uuid not null default uuid_generate_v4(),
    "session_id" uuid not null,
    "user_id" uuid not null,
    "photo_id" uuid,
    "conversation_order" integer not null,
    "question_text" text not null,
    "question_type" character varying(50) not null,
    "cist_category" character varying(50),
    "user_response_text" text,
    "user_response_audio_url" text,
    "response_duration_seconds" integer,
    "ai_analysis" jsonb,
    "cist_score" integer,
    "is_cist_item" boolean default false,
    "created_at" timestamp with time zone default now(),
    "updated_at" timestamp with time zone default now()
      );


alter table "public"."conversations" enable row level security;


  create table "public"."families" (
    "id" uuid not null default uuid_generate_v4(),
    "family_code" character varying(10) not null,
    "family_name" character varying(100) not null,
    "created_by" uuid,
    "created_at" timestamp with time zone default now(),
    "updated_at" timestamp with time zone default now()
      );


alter table "public"."families" enable row level security;


  create table "public"."family_members" (
    "id" uuid not null default uuid_generate_v4(),
    "user_id" uuid not null,
    "family_id" uuid not null,
    "family_role" character varying(50),
    "joined_at" timestamp with time zone default now()
      );


alter table "public"."family_members" enable row level security;


  create table "public"."photos" (
    "id" uuid not null default uuid_generate_v4(),
    "user_id" uuid not null,
    "file_name" character varying(255) not null,
    "filename" character varying(255) not null,
    "original_filename" character varying(255) not null,
    "file_path" text not null,
    "file_size" bigint,
    "mime_type" character varying(100),
    "width" integer,
    "height" integer,
    "description" text,
    "tags" text[],
    "album_id" uuid,
    "taken_at" timestamp with time zone,
    "location_name" character varying(255),
    "latitude" numeric(10,8),
    "longitude" numeric(11,8),
    "is_favorite" boolean default false,
    "is_deleted" boolean default false,
    "created_at" timestamp with time zone default now(),
    "updated_at" timestamp with time zone default now()
      );


alter table "public"."photos" enable row level security;


  create table "public"."session_reports" (
    "id" uuid not null default uuid_generate_v4(),
    "session_id" uuid not null,
    "user_id" uuid not null,
    "total_cist_score" integer not null,
    "max_possible_score" integer default 21,
    "cognitive_status" character varying(50),
    "category_scores" jsonb,
    "insights" text[],
    "recommendations" text[],
    "report_generated_at" timestamp with time zone default now(),
    "is_shared" boolean default false,
    "shared_at" timestamp with time zone,
    "created_at" timestamp with time zone default now()
      );


alter table "public"."session_reports" enable row level security;


  create table "public"."sessions" (
    "id" uuid not null default uuid_generate_v4(),
    "user_id" uuid not null,
    "session_type" character varying(50) default 'reminiscence'::character varying,
    "status" character varying(20) default 'active'::character varying,
    "selected_photos" uuid[] not null,
    "total_duration_seconds" integer default 0,
    "cist_score" integer,
    "cist_completed_items" integer default 0,
    "started_at" timestamp with time zone default now(),
    "completed_at" timestamp with time zone,
    "notes" text,
    "created_at" timestamp with time zone default now(),
    "updated_at" timestamp with time zone default now()
      );


alter table "public"."sessions" enable row level security;


  create table "public"."users" (
    "id" uuid not null,
    "email" character varying(255) not null,
    "full_name" character varying(255),
    "birth_date" date,
    "gender" character varying(10),
    "phone" character varying(20),
    "profile_image_url" text,
    "onboarding_completed" boolean default false,
    "privacy_consent" boolean default false,
    "terms_accepted" boolean default false,
    "notification_enabled" boolean default true,
    "created_at" timestamp with time zone default now(),
    "updated_at" timestamp with time zone default now(),
    "is_guardian" boolean default false,
    "current_family_id" uuid
      );


alter table "public"."users" enable row level security;

CREATE UNIQUE INDEX albums_pkey ON public.albums USING btree (id);

CREATE UNIQUE INDEX app_config_pkey ON public.app_config USING btree (key);

CREATE UNIQUE INDEX cist_question_templates_pkey ON public.cist_question_templates USING btree (id);

CREATE UNIQUE INDEX cist_responses_pkey ON public.cist_responses USING btree (id);

CREATE UNIQUE INDEX conversation_starters_pkey ON public.conversation_starters USING btree (id);

CREATE UNIQUE INDEX conversations_pkey ON public.conversations USING btree (id);

CREATE UNIQUE INDEX families_family_code_key ON public.families USING btree (family_code);

CREATE UNIQUE INDEX families_pkey ON public.families USING btree (id);

CREATE UNIQUE INDEX family_members_pkey ON public.family_members USING btree (id);

CREATE UNIQUE INDEX family_members_user_id_family_id_key ON public.family_members USING btree (user_id, family_id);

CREATE INDEX idx_albums_name ON public.albums USING btree (user_id, name);

CREATE INDEX idx_albums_user_id ON public.albums USING btree (user_id);

CREATE INDEX idx_cist_responses_category ON public.cist_responses USING btree (cist_category);

CREATE INDEX idx_cist_responses_session_id ON public.cist_responses USING btree (session_id);

CREATE INDEX idx_cist_responses_user_id ON public.cist_responses USING btree (user_id);

CREATE INDEX idx_cist_templates_category ON public.cist_question_templates USING btree (category);

CREATE INDEX idx_cist_templates_context ON public.cist_question_templates USING btree (context_type);

CREATE INDEX idx_conversations_question_type ON public.conversations USING btree (question_type);

CREATE INDEX idx_conversations_session_id ON public.conversations USING btree (session_id);

CREATE INDEX idx_conversations_user_id ON public.conversations USING btree (user_id);

CREATE INDEX idx_families_code ON public.families USING btree (family_code);

CREATE INDEX idx_family_members_family_id ON public.family_members USING btree (family_id);

CREATE INDEX idx_family_members_user_id ON public.family_members USING btree (user_id);

CREATE INDEX idx_photos_album_id ON public.photos USING btree (album_id);

CREATE INDEX idx_photos_created_at ON public.photos USING btree (created_at DESC);

CREATE INDEX idx_photos_filename ON public.photos USING btree (filename);

CREATE INDEX idx_photos_is_deleted ON public.photos USING btree (is_deleted) WHERE (is_deleted = false);

CREATE INDEX idx_photos_is_favorite ON public.photos USING btree (user_id, is_favorite) WHERE (is_favorite = true);

CREATE INDEX idx_photos_tags ON public.photos USING gin (tags);

CREATE INDEX idx_photos_user_id ON public.photos USING btree (user_id);

CREATE INDEX idx_session_reports_user_id ON public.session_reports USING btree (user_id);

CREATE INDEX idx_sessions_started_at ON public.sessions USING btree (started_at DESC);

CREATE INDEX idx_sessions_status ON public.sessions USING btree (status);

CREATE INDEX idx_sessions_user_id ON public.sessions USING btree (user_id);

CREATE INDEX idx_users_current_family_id ON public.users USING btree (current_family_id);

CREATE INDEX idx_users_email ON public.users USING btree (email);

CREATE UNIQUE INDEX photos_pkey ON public.photos USING btree (id);

CREATE UNIQUE INDEX session_reports_pkey ON public.session_reports USING btree (id);

CREATE UNIQUE INDEX sessions_pkey ON public.sessions USING btree (id);

CREATE UNIQUE INDEX users_email_key ON public.users USING btree (email);

CREATE UNIQUE INDEX users_pkey ON public.users USING btree (id);

alter table "public"."albums" add constraint "albums_pkey" PRIMARY KEY using index "albums_pkey";

alter table "public"."app_config" add constraint "app_config_pkey" PRIMARY KEY using index "app_config_pkey";

alter table "public"."cist_question_templates" add constraint "cist_question_templates_pkey" PRIMARY KEY using index "cist_question_templates_pkey";

alter table "public"."cist_responses" add constraint "cist_responses_pkey" PRIMARY KEY using index "cist_responses_pkey";

alter table "public"."conversation_starters" add constraint "conversation_starters_pkey" PRIMARY KEY using index "conversation_starters_pkey";

alter table "public"."conversations" add constraint "conversations_pkey" PRIMARY KEY using index "conversations_pkey";

alter table "public"."families" add constraint "families_pkey" PRIMARY KEY using index "families_pkey";

alter table "public"."family_members" add constraint "family_members_pkey" PRIMARY KEY using index "family_members_pkey";

alter table "public"."photos" add constraint "photos_pkey" PRIMARY KEY using index "photos_pkey";

alter table "public"."session_reports" add constraint "session_reports_pkey" PRIMARY KEY using index "session_reports_pkey";

alter table "public"."sessions" add constraint "sessions_pkey" PRIMARY KEY using index "sessions_pkey";

alter table "public"."users" add constraint "users_pkey" PRIMARY KEY using index "users_pkey";

alter table "public"."albums" add constraint "albums_family_id_fkey" FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE not valid;

alter table "public"."albums" validate constraint "albums_family_id_fkey";

alter table "public"."albums" add constraint "albums_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE not valid;

alter table "public"."albums" validate constraint "albums_user_id_fkey";

alter table "public"."cist_question_templates" add constraint "cist_question_templates_difficulty_level_check" CHECK (((difficulty_level >= 1) AND (difficulty_level <= 5))) not valid;

alter table "public"."cist_question_templates" validate constraint "cist_question_templates_difficulty_level_check";

alter table "public"."cist_responses" add constraint "cist_responses_cist_category_check" CHECK (((cist_category)::text = ANY ((ARRAY['orientation_time'::character varying, 'orientation_place'::character varying, 'memory_registration'::character varying, 'memory_recall'::character varying, 'memory_recognition'::character varying, 'attention'::character varying, 'executive_function'::character varying, 'language_naming'::character varying])::text[]))) not valid;

alter table "public"."cist_responses" validate constraint "cist_responses_cist_category_check";

alter table "public"."cist_responses" add constraint "cist_responses_conversation_id_fkey" FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE not valid;

alter table "public"."cist_responses" validate constraint "cist_responses_conversation_id_fkey";

alter table "public"."cist_responses" add constraint "cist_responses_difficulty_level_check" CHECK (((difficulty_level >= 1) AND (difficulty_level <= 5))) not valid;

alter table "public"."cist_responses" validate constraint "cist_responses_difficulty_level_check";

alter table "public"."cist_responses" add constraint "cist_responses_session_id_fkey" FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE not valid;

alter table "public"."cist_responses" validate constraint "cist_responses_session_id_fkey";

alter table "public"."cist_responses" add constraint "cist_responses_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE not valid;

alter table "public"."cist_responses" validate constraint "cist_responses_user_id_fkey";

alter table "public"."conversations" add constraint "conversations_photo_id_fkey" FOREIGN KEY (photo_id) REFERENCES photos(id) ON DELETE SET NULL not valid;

alter table "public"."conversations" validate constraint "conversations_photo_id_fkey";

alter table "public"."conversations" add constraint "conversations_question_type_check" CHECK (((question_type)::text = ANY ((ARRAY['open_ended'::character varying, 'cist_orientation'::character varying, 'cist_memory'::character varying, 'cist_attention'::character varying, 'cist_executive'::character varying, 'cist_language'::character varying])::text[]))) not valid;

alter table "public"."conversations" validate constraint "conversations_question_type_check";

alter table "public"."conversations" add constraint "conversations_session_id_fkey" FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE not valid;

alter table "public"."conversations" validate constraint "conversations_session_id_fkey";

alter table "public"."conversations" add constraint "conversations_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE not valid;

alter table "public"."conversations" validate constraint "conversations_user_id_fkey";

alter table "public"."families" add constraint "families_created_by_fkey" FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL not valid;

alter table "public"."families" validate constraint "families_created_by_fkey";

alter table "public"."families" add constraint "families_family_code_key" UNIQUE using index "families_family_code_key";

alter table "public"."family_members" add constraint "family_members_family_id_fkey" FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE not valid;

alter table "public"."family_members" validate constraint "family_members_family_id_fkey";

alter table "public"."family_members" add constraint "family_members_user_id_family_id_key" UNIQUE using index "family_members_user_id_family_id_key";

alter table "public"."family_members" add constraint "family_members_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE not valid;

alter table "public"."family_members" validate constraint "family_members_user_id_fkey";

alter table "public"."photos" add constraint "photos_album_id_fkey" FOREIGN KEY (album_id) REFERENCES albums(id) ON DELETE SET NULL not valid;

alter table "public"."photos" validate constraint "photos_album_id_fkey";

alter table "public"."photos" add constraint "photos_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE not valid;

alter table "public"."photos" validate constraint "photos_user_id_fkey";

alter table "public"."session_reports" add constraint "session_reports_cognitive_status_check" CHECK (((cognitive_status)::text = ANY ((ARRAY['normal'::character varying, 'mild_concern'::character varying, 'moderate_concern'::character varying, 'high_concern'::character varying])::text[]))) not valid;

alter table "public"."session_reports" validate constraint "session_reports_cognitive_status_check";

alter table "public"."session_reports" add constraint "session_reports_session_id_fkey" FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE not valid;

alter table "public"."session_reports" validate constraint "session_reports_session_id_fkey";

alter table "public"."session_reports" add constraint "session_reports_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE not valid;

alter table "public"."session_reports" validate constraint "session_reports_user_id_fkey";

alter table "public"."sessions" add constraint "sessions_session_type_check" CHECK (((session_type)::text = ANY ((ARRAY['reminiscence'::character varying, 'assessment'::character varying, 'mixed'::character varying])::text[]))) not valid;

alter table "public"."sessions" validate constraint "sessions_session_type_check";

alter table "public"."sessions" add constraint "sessions_status_check" CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'completed'::character varying, 'paused'::character varying, 'cancelled'::character varying])::text[]))) not valid;

alter table "public"."sessions" validate constraint "sessions_status_check";

alter table "public"."sessions" add constraint "sessions_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE not valid;

alter table "public"."sessions" validate constraint "sessions_user_id_fkey";

alter table "public"."users" add constraint "users_current_family_id_fkey" FOREIGN KEY (current_family_id) REFERENCES families(id) ON DELETE SET NULL not valid;

alter table "public"."users" validate constraint "users_current_family_id_fkey";

alter table "public"."users" add constraint "users_email_key" UNIQUE using index "users_email_key";

alter table "public"."users" add constraint "users_gender_check" CHECK (((gender)::text = ANY ((ARRAY['male'::character varying, 'female'::character varying, 'other'::character varying])::text[]))) not valid;

alter table "public"."users" validate constraint "users_gender_check";

alter table "public"."users" add constraint "users_id_fkey" FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE not valid;

alter table "public"."users" validate constraint "users_id_fkey";

set check_function_bodies = off;

create or replace view "public"."cist_performance_by_category" as  SELECT user_id,
    cist_category,
    count(*) AS total_attempts,
    avg(partial_score) AS avg_score,
    count(
        CASE
            WHEN (is_correct = true) THEN 1
            ELSE NULL::integer
        END) AS correct_answers
   FROM cist_responses cr
  GROUP BY user_id, cist_category;


CREATE OR REPLACE FUNCTION public.handle_updated_at()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$function$
;

CREATE OR REPLACE FUNCTION public.is_same_family(family_id uuid)
 RETURNS boolean
 LANGUAGE sql
 SECURITY DEFINER
AS $function$
  SELECT EXISTS (
    SELECT 1
    FROM public.family_members fm
    WHERE fm.family_id = is_same_family.family_id
      AND fm.user_id = auth.uid()::uuid
  );
$function$
;

create or replace view "public"."user_album_summary" as  SELECT a.id AS album_id,
    a.name AS album_name,
    a.description,
    a.user_id,
    count(p.id) AS photo_count,
    max(p.created_at) AS last_photo_added
   FROM (albums a
     LEFT JOIN photos p ON (((a.id = p.album_id) AND (p.is_deleted = false))))
  GROUP BY a.id, a.name, a.description, a.user_id;


create or replace view "public"."user_session_summary" as  SELECT u.id AS user_id,
    u.full_name,
    u.email,
    count(s.id) AS total_sessions,
    avg(s.cist_score) AS avg_cist_score,
    max(s.started_at) AS last_session_date,
    sum(s.total_duration_seconds) AS total_conversation_time
   FROM (users u
     LEFT JOIN sessions s ON ((u.id = s.user_id)))
  WHERE ((s.status)::text = 'completed'::text)
  GROUP BY u.id, u.full_name, u.email;


grant delete on table "public"."albums" to "anon";

grant insert on table "public"."albums" to "anon";

grant references on table "public"."albums" to "anon";

grant select on table "public"."albums" to "anon";

grant trigger on table "public"."albums" to "anon";

grant truncate on table "public"."albums" to "anon";

grant update on table "public"."albums" to "anon";

grant delete on table "public"."albums" to "authenticated";

grant insert on table "public"."albums" to "authenticated";

grant references on table "public"."albums" to "authenticated";

grant select on table "public"."albums" to "authenticated";

grant trigger on table "public"."albums" to "authenticated";

grant truncate on table "public"."albums" to "authenticated";

grant update on table "public"."albums" to "authenticated";

grant delete on table "public"."albums" to "service_role";

grant insert on table "public"."albums" to "service_role";

grant references on table "public"."albums" to "service_role";

grant select on table "public"."albums" to "service_role";

grant trigger on table "public"."albums" to "service_role";

grant truncate on table "public"."albums" to "service_role";

grant update on table "public"."albums" to "service_role";

grant delete on table "public"."app_config" to "anon";

grant insert on table "public"."app_config" to "anon";

grant references on table "public"."app_config" to "anon";

grant select on table "public"."app_config" to "anon";

grant trigger on table "public"."app_config" to "anon";

grant truncate on table "public"."app_config" to "anon";

grant update on table "public"."app_config" to "anon";

grant delete on table "public"."app_config" to "authenticated";

grant insert on table "public"."app_config" to "authenticated";

grant references on table "public"."app_config" to "authenticated";

grant select on table "public"."app_config" to "authenticated";

grant trigger on table "public"."app_config" to "authenticated";

grant truncate on table "public"."app_config" to "authenticated";

grant update on table "public"."app_config" to "authenticated";

grant delete on table "public"."app_config" to "service_role";

grant insert on table "public"."app_config" to "service_role";

grant references on table "public"."app_config" to "service_role";

grant select on table "public"."app_config" to "service_role";

grant trigger on table "public"."app_config" to "service_role";

grant truncate on table "public"."app_config" to "service_role";

grant update on table "public"."app_config" to "service_role";

grant delete on table "public"."cist_question_templates" to "anon";

grant insert on table "public"."cist_question_templates" to "anon";

grant references on table "public"."cist_question_templates" to "anon";

grant select on table "public"."cist_question_templates" to "anon";

grant trigger on table "public"."cist_question_templates" to "anon";

grant truncate on table "public"."cist_question_templates" to "anon";

grant update on table "public"."cist_question_templates" to "anon";

grant delete on table "public"."cist_question_templates" to "authenticated";

grant insert on table "public"."cist_question_templates" to "authenticated";

grant references on table "public"."cist_question_templates" to "authenticated";

grant select on table "public"."cist_question_templates" to "authenticated";

grant trigger on table "public"."cist_question_templates" to "authenticated";

grant truncate on table "public"."cist_question_templates" to "authenticated";

grant update on table "public"."cist_question_templates" to "authenticated";

grant delete on table "public"."cist_question_templates" to "service_role";

grant insert on table "public"."cist_question_templates" to "service_role";

grant references on table "public"."cist_question_templates" to "service_role";

grant select on table "public"."cist_question_templates" to "service_role";

grant trigger on table "public"."cist_question_templates" to "service_role";

grant truncate on table "public"."cist_question_templates" to "service_role";

grant update on table "public"."cist_question_templates" to "service_role";

grant delete on table "public"."cist_responses" to "anon";

grant insert on table "public"."cist_responses" to "anon";

grant references on table "public"."cist_responses" to "anon";

grant select on table "public"."cist_responses" to "anon";

grant trigger on table "public"."cist_responses" to "anon";

grant truncate on table "public"."cist_responses" to "anon";

grant update on table "public"."cist_responses" to "anon";

grant delete on table "public"."cist_responses" to "authenticated";

grant insert on table "public"."cist_responses" to "authenticated";

grant references on table "public"."cist_responses" to "authenticated";

grant select on table "public"."cist_responses" to "authenticated";

grant trigger on table "public"."cist_responses" to "authenticated";

grant truncate on table "public"."cist_responses" to "authenticated";

grant update on table "public"."cist_responses" to "authenticated";

grant delete on table "public"."cist_responses" to "service_role";

grant insert on table "public"."cist_responses" to "service_role";

grant references on table "public"."cist_responses" to "service_role";

grant select on table "public"."cist_responses" to "service_role";

grant trigger on table "public"."cist_responses" to "service_role";

grant truncate on table "public"."cist_responses" to "service_role";

grant update on table "public"."cist_responses" to "service_role";

grant delete on table "public"."conversation_starters" to "anon";

grant insert on table "public"."conversation_starters" to "anon";

grant references on table "public"."conversation_starters" to "anon";

grant select on table "public"."conversation_starters" to "anon";

grant trigger on table "public"."conversation_starters" to "anon";

grant truncate on table "public"."conversation_starters" to "anon";

grant update on table "public"."conversation_starters" to "anon";

grant delete on table "public"."conversation_starters" to "authenticated";

grant insert on table "public"."conversation_starters" to "authenticated";

grant references on table "public"."conversation_starters" to "authenticated";

grant select on table "public"."conversation_starters" to "authenticated";

grant trigger on table "public"."conversation_starters" to "authenticated";

grant truncate on table "public"."conversation_starters" to "authenticated";

grant update on table "public"."conversation_starters" to "authenticated";

grant delete on table "public"."conversation_starters" to "service_role";

grant insert on table "public"."conversation_starters" to "service_role";

grant references on table "public"."conversation_starters" to "service_role";

grant select on table "public"."conversation_starters" to "service_role";

grant trigger on table "public"."conversation_starters" to "service_role";

grant truncate on table "public"."conversation_starters" to "service_role";

grant update on table "public"."conversation_starters" to "service_role";

grant delete on table "public"."conversations" to "anon";

grant insert on table "public"."conversations" to "anon";

grant references on table "public"."conversations" to "anon";

grant select on table "public"."conversations" to "anon";

grant trigger on table "public"."conversations" to "anon";

grant truncate on table "public"."conversations" to "anon";

grant update on table "public"."conversations" to "anon";

grant delete on table "public"."conversations" to "authenticated";

grant insert on table "public"."conversations" to "authenticated";

grant references on table "public"."conversations" to "authenticated";

grant select on table "public"."conversations" to "authenticated";

grant trigger on table "public"."conversations" to "authenticated";

grant truncate on table "public"."conversations" to "authenticated";

grant update on table "public"."conversations" to "authenticated";

grant delete on table "public"."conversations" to "service_role";

grant insert on table "public"."conversations" to "service_role";

grant references on table "public"."conversations" to "service_role";

grant select on table "public"."conversations" to "service_role";

grant trigger on table "public"."conversations" to "service_role";

grant truncate on table "public"."conversations" to "service_role";

grant update on table "public"."conversations" to "service_role";

grant delete on table "public"."families" to "anon";

grant insert on table "public"."families" to "anon";

grant references on table "public"."families" to "anon";

grant select on table "public"."families" to "anon";

grant trigger on table "public"."families" to "anon";

grant truncate on table "public"."families" to "anon";

grant update on table "public"."families" to "anon";

grant delete on table "public"."families" to "authenticated";

grant insert on table "public"."families" to "authenticated";

grant references on table "public"."families" to "authenticated";

grant select on table "public"."families" to "authenticated";

grant trigger on table "public"."families" to "authenticated";

grant truncate on table "public"."families" to "authenticated";

grant update on table "public"."families" to "authenticated";

grant delete on table "public"."families" to "service_role";

grant insert on table "public"."families" to "service_role";

grant references on table "public"."families" to "service_role";

grant select on table "public"."families" to "service_role";

grant trigger on table "public"."families" to "service_role";

grant truncate on table "public"."families" to "service_role";

grant update on table "public"."families" to "service_role";

grant delete on table "public"."family_members" to "anon";

grant insert on table "public"."family_members" to "anon";

grant references on table "public"."family_members" to "anon";

grant select on table "public"."family_members" to "anon";

grant trigger on table "public"."family_members" to "anon";

grant truncate on table "public"."family_members" to "anon";

grant update on table "public"."family_members" to "anon";

grant delete on table "public"."family_members" to "authenticated";

grant insert on table "public"."family_members" to "authenticated";

grant references on table "public"."family_members" to "authenticated";

grant select on table "public"."family_members" to "authenticated";

grant trigger on table "public"."family_members" to "authenticated";

grant truncate on table "public"."family_members" to "authenticated";

grant update on table "public"."family_members" to "authenticated";

grant delete on table "public"."family_members" to "service_role";

grant insert on table "public"."family_members" to "service_role";

grant references on table "public"."family_members" to "service_role";

grant select on table "public"."family_members" to "service_role";

grant trigger on table "public"."family_members" to "service_role";

grant truncate on table "public"."family_members" to "service_role";

grant update on table "public"."family_members" to "service_role";

grant delete on table "public"."photos" to "anon";

grant insert on table "public"."photos" to "anon";

grant references on table "public"."photos" to "anon";

grant select on table "public"."photos" to "anon";

grant trigger on table "public"."photos" to "anon";

grant truncate on table "public"."photos" to "anon";

grant update on table "public"."photos" to "anon";

grant delete on table "public"."photos" to "authenticated";

grant insert on table "public"."photos" to "authenticated";

grant references on table "public"."photos" to "authenticated";

grant select on table "public"."photos" to "authenticated";

grant trigger on table "public"."photos" to "authenticated";

grant truncate on table "public"."photos" to "authenticated";

grant update on table "public"."photos" to "authenticated";

grant delete on table "public"."photos" to "service_role";

grant insert on table "public"."photos" to "service_role";

grant references on table "public"."photos" to "service_role";

grant select on table "public"."photos" to "service_role";

grant trigger on table "public"."photos" to "service_role";

grant truncate on table "public"."photos" to "service_role";

grant update on table "public"."photos" to "service_role";

grant delete on table "public"."session_reports" to "anon";

grant insert on table "public"."session_reports" to "anon";

grant references on table "public"."session_reports" to "anon";

grant select on table "public"."session_reports" to "anon";

grant trigger on table "public"."session_reports" to "anon";

grant truncate on table "public"."session_reports" to "anon";

grant update on table "public"."session_reports" to "anon";

grant delete on table "public"."session_reports" to "authenticated";

grant insert on table "public"."session_reports" to "authenticated";

grant references on table "public"."session_reports" to "authenticated";

grant select on table "public"."session_reports" to "authenticated";

grant trigger on table "public"."session_reports" to "authenticated";

grant truncate on table "public"."session_reports" to "authenticated";

grant update on table "public"."session_reports" to "authenticated";

grant delete on table "public"."session_reports" to "service_role";

grant insert on table "public"."session_reports" to "service_role";

grant references on table "public"."session_reports" to "service_role";

grant select on table "public"."session_reports" to "service_role";

grant trigger on table "public"."session_reports" to "service_role";

grant truncate on table "public"."session_reports" to "service_role";

grant update on table "public"."session_reports" to "service_role";

grant delete on table "public"."sessions" to "anon";

grant insert on table "public"."sessions" to "anon";

grant references on table "public"."sessions" to "anon";

grant select on table "public"."sessions" to "anon";

grant trigger on table "public"."sessions" to "anon";

grant truncate on table "public"."sessions" to "anon";

grant update on table "public"."sessions" to "anon";

grant delete on table "public"."sessions" to "authenticated";

grant insert on table "public"."sessions" to "authenticated";

grant references on table "public"."sessions" to "authenticated";

grant select on table "public"."sessions" to "authenticated";

grant trigger on table "public"."sessions" to "authenticated";

grant truncate on table "public"."sessions" to "authenticated";

grant update on table "public"."sessions" to "authenticated";

grant delete on table "public"."sessions" to "service_role";

grant insert on table "public"."sessions" to "service_role";

grant references on table "public"."sessions" to "service_role";

grant select on table "public"."sessions" to "service_role";

grant trigger on table "public"."sessions" to "service_role";

grant truncate on table "public"."sessions" to "service_role";

grant update on table "public"."sessions" to "service_role";

grant delete on table "public"."users" to "anon";

grant insert on table "public"."users" to "anon";

grant references on table "public"."users" to "anon";

grant select on table "public"."users" to "anon";

grant trigger on table "public"."users" to "anon";

grant truncate on table "public"."users" to "anon";

grant update on table "public"."users" to "anon";

grant delete on table "public"."users" to "authenticated";

grant insert on table "public"."users" to "authenticated";

grant references on table "public"."users" to "authenticated";

grant select on table "public"."users" to "authenticated";

grant trigger on table "public"."users" to "authenticated";

grant truncate on table "public"."users" to "authenticated";

grant update on table "public"."users" to "authenticated";

grant delete on table "public"."users" to "service_role";

grant insert on table "public"."users" to "service_role";

grant references on table "public"."users" to "service_role";

grant select on table "public"."users" to "service_role";

grant trigger on table "public"."users" to "service_role";

grant truncate on table "public"."users" to "service_role";

grant update on table "public"."users" to "service_role";


  create policy "Users can delete own albums"
  on "public"."albums"
  as permissive
  for delete
  to public
using ((auth.uid() = user_id));



  create policy "Users can insert own albums"
  on "public"."albums"
  as permissive
  for insert
  to public
with check ((auth.uid() = user_id));



  create policy "Users can update own albums"
  on "public"."albums"
  as permissive
  for update
  to public
using ((auth.uid() = user_id));



  create policy "Users can view own albums"
  on "public"."albums"
  as permissive
  for select
  to public
using ((auth.uid() = user_id));



  create policy "albums_delete_family"
  on "public"."albums"
  as permissive
  for delete
  to public
using ((EXISTS ( SELECT 1
   FROM (families f
     JOIN family_members fm ON ((f.id = fm.family_id)))
  WHERE ((f.id = albums.family_id) AND (fm.user_id = auth.uid())))));



  create policy "albums_insert_family"
  on "public"."albums"
  as permissive
  for insert
  to public
with check ((EXISTS ( SELECT 1
   FROM (families f
     JOIN family_members fm ON ((f.id = fm.family_id)))
  WHERE ((f.id = fm.family_id) AND (fm.user_id = auth.uid())))));



  create policy "albums_select_family"
  on "public"."albums"
  as permissive
  for select
  to public
using ((EXISTS ( SELECT 1
   FROM (families f
     JOIN family_members fm ON ((f.id = fm.family_id)))
  WHERE ((f.id = albums.family_id) AND (fm.user_id = auth.uid())))));



  create policy "albums_update_family"
  on "public"."albums"
  as permissive
  for update
  to public
using ((EXISTS ( SELECT 1
   FROM (families f
     JOIN family_members fm ON ((f.id = fm.family_id)))
  WHERE ((f.id = albums.family_id) AND (fm.user_id = auth.uid())))));



  create policy "Delete cist_responses (self or family via session)"
  on "public"."cist_responses"
  as permissive
  for delete
  to authenticated
using ((EXISTS ( SELECT 1
   FROM ((sessions s
     JOIN family_members me ON ((me.user_id = auth.uid())))
     JOIN family_members target ON (((target.user_id = s.user_id) AND (target.family_id = me.family_id))))
  WHERE (s.id = cist_responses.session_id))));



  create policy "Insert cist_responses (self or family via session)"
  on "public"."cist_responses"
  as permissive
  for insert
  to authenticated
with check ((EXISTS ( SELECT 1
   FROM ((sessions s
     JOIN family_members me ON ((me.user_id = auth.uid())))
     JOIN family_members target ON (((target.user_id = s.user_id) AND (target.family_id = me.family_id))))
  WHERE (s.id = cist_responses.session_id))));



  create policy "Update cist_responses (self or family via session)"
  on "public"."cist_responses"
  as permissive
  for update
  to authenticated
using ((EXISTS ( SELECT 1
   FROM ((sessions s
     JOIN family_members me ON ((me.user_id = auth.uid())))
     JOIN family_members target ON (((target.user_id = s.user_id) AND (target.family_id = me.family_id))))
  WHERE (s.id = cist_responses.session_id))))
with check ((EXISTS ( SELECT 1
   FROM ((sessions s
     JOIN family_members me ON ((me.user_id = auth.uid())))
     JOIN family_members target ON (((target.user_id = s.user_id) AND (target.family_id = me.family_id))))
  WHERE (s.id = cist_responses.session_id))));



  create policy "View cist_responses (self or family)"
  on "public"."cist_responses"
  as permissive
  for select
  to authenticated
using ((EXISTS ( SELECT 1
   FROM ((sessions s
     JOIN family_members me ON ((me.user_id = auth.uid())))
     JOIN family_members target ON (((target.user_id = s.user_id) AND (target.family_id = me.family_id))))
  WHERE (s.id = cist_responses.session_id))));



  create policy "Family can insert conversations"
  on "public"."conversations"
  as permissive
  for insert
  to authenticated
with check ((EXISTS ( SELECT 1
   FROM ((sessions s
     JOIN family_members me ON ((me.user_id = auth.uid())))
     JOIN family_members target ON (((target.user_id = s.user_id) AND (target.family_id = me.family_id))))
  WHERE (s.id = conversations.session_id))));



  create policy "Family can update conversations"
  on "public"."conversations"
  as permissive
  for update
  to authenticated
using ((EXISTS ( SELECT 1
   FROM ((sessions s
     JOIN family_members me ON ((me.user_id = auth.uid())))
     JOIN family_members target ON (((target.user_id = s.user_id) AND (target.family_id = me.family_id))))
  WHERE (s.id = conversations.session_id))))
with check ((EXISTS ( SELECT 1
   FROM ((sessions s
     JOIN family_members me ON ((me.user_id = auth.uid())))
     JOIN family_members target ON (((target.user_id = s.user_id) AND (target.family_id = me.family_id))))
  WHERE (s.id = conversations.session_id))));



  create policy "Family can view conversations"
  on "public"."conversations"
  as permissive
  for select
  to authenticated
using ((EXISTS ( SELECT 1
   FROM ((sessions s
     JOIN family_members me ON ((me.user_id = auth.uid())))
     JOIN family_members target ON (((target.user_id = s.user_id) AND (target.family_id = me.family_id))))
  WHERE (s.id = conversations.session_id))));



  create policy "Users can insert own conversations"
  on "public"."conversations"
  as permissive
  for insert
  to public
with check ((auth.uid() = user_id));



  create policy "Users can update own conversations"
  on "public"."conversations"
  as permissive
  for update
  to public
using ((auth.uid() = user_id));



  create policy "Users can view own conversations"
  on "public"."conversations"
  as permissive
  for select
  to public
using ((auth.uid() = user_id));



  create policy "Users can view own families"
  on "public"."families"
  as permissive
  for select
  to public
using (((created_by = auth.uid()) OR (EXISTS ( SELECT 1
   FROM family_members fm
  WHERE ((fm.family_id = families.id) AND (fm.user_id = auth.uid())))) OR (family_code IS NOT NULL)));



  create policy "families_delete"
  on "public"."families"
  as permissive
  for delete
  to public
using ((created_by = auth.uid()));



  create policy "families_insert"
  on "public"."families"
  as permissive
  for insert
  to public
with check (true);



  create policy "families_update"
  on "public"."families"
  as permissive
  for update
  to public
using ((created_by = auth.uid()));



  create policy "Users can delete own family_members"
  on "public"."family_members"
  as permissive
  for delete
  to public
using ((user_id = auth.uid()));



  create policy "Users can insert own family_members"
  on "public"."family_members"
  as permissive
  for insert
  to public
with check ((user_id = auth.uid()));



  create policy "Users can update own family_members"
  on "public"."family_members"
  as permissive
  for update
  to public
using ((user_id = auth.uid()));



  create policy "Users can view family_members in same family"
  on "public"."family_members"
  as permissive
  for select
  to public
using (is_same_family(family_id));



  create policy "Users can delete own photos"
  on "public"."photos"
  as permissive
  for delete
  to public
using ((auth.uid() = user_id));



  create policy "Users can insert own photos"
  on "public"."photos"
  as permissive
  for insert
  to public
with check ((auth.uid() = user_id));



  create policy "Users can update own photos"
  on "public"."photos"
  as permissive
  for update
  to public
using ((auth.uid() = user_id));



  create policy "Users can view own photos"
  on "public"."photos"
  as permissive
  for select
  to public
using ((auth.uid() = user_id));



  create policy "photos_delete_family"
  on "public"."photos"
  as permissive
  for delete
  to public
using ((EXISTS ( SELECT 1
   FROM (albums a
     JOIN family_members fm ON ((a.family_id = fm.family_id)))
  WHERE ((a.id = photos.album_id) AND (fm.user_id = auth.uid())))));



  create policy "photos_insert_family"
  on "public"."photos"
  as permissive
  for insert
  to public
with check ((EXISTS ( SELECT 1
   FROM (albums a
     JOIN family_members fm ON ((a.family_id = fm.family_id)))
  WHERE ((a.id = photos.album_id) AND (fm.user_id = auth.uid())))));



  create policy "photos_select_family"
  on "public"."photos"
  as permissive
  for select
  to public
using ((EXISTS ( SELECT 1
   FROM (albums a
     JOIN family_members fm ON ((a.family_id = fm.family_id)))
  WHERE ((a.id = photos.album_id) AND (fm.user_id = auth.uid())))));



  create policy "photos_update_family"
  on "public"."photos"
  as permissive
  for update
  to public
using ((EXISTS ( SELECT 1
   FROM (albums a
     JOIN family_members fm ON ((a.family_id = fm.family_id)))
  WHERE ((a.id = photos.album_id) AND (fm.user_id = auth.uid())))));



  create policy "Family can insert session_reports"
  on "public"."session_reports"
  as permissive
  for insert
  to authenticated
with check ((EXISTS ( SELECT 1
   FROM ((sessions s
     JOIN family_members me ON ((me.user_id = auth.uid())))
     JOIN family_members target ON (((target.user_id = s.user_id) AND (target.family_id = me.family_id))))
  WHERE (s.id = session_reports.session_id))));



  create policy "Family can view session_reports"
  on "public"."session_reports"
  as permissive
  for select
  to authenticated
using ((EXISTS ( SELECT 1
   FROM ((sessions s
     JOIN family_members me ON ((me.user_id = auth.uid())))
     JOIN family_members target ON (((target.user_id = s.user_id) AND (target.family_id = me.family_id))))
  WHERE (s.id = session_reports.session_id))));



  create policy "Users can insert own reports"
  on "public"."session_reports"
  as permissive
  for insert
  to public
with check ((auth.uid() = user_id));



  create policy "Users can view own reports"
  on "public"."session_reports"
  as permissive
  for select
  to public
using ((auth.uid() = user_id));



  create policy "Family can insert sessions"
  on "public"."sessions"
  as permissive
  for insert
  to authenticated
with check ((EXISTS ( SELECT 1
   FROM (family_members me
     JOIN family_members target ON ((target.family_id = me.family_id)))
  WHERE ((me.user_id = auth.uid()) AND (target.user_id = sessions.user_id)))));



  create policy "Family can update sessions"
  on "public"."sessions"
  as permissive
  for update
  to authenticated
using ((EXISTS ( SELECT 1
   FROM (family_members me
     JOIN family_members target ON ((target.family_id = me.family_id)))
  WHERE ((me.user_id = auth.uid()) AND (target.user_id = sessions.user_id)))))
with check ((EXISTS ( SELECT 1
   FROM (family_members me
     JOIN family_members target ON ((target.family_id = me.family_id)))
  WHERE ((me.user_id = auth.uid()) AND (target.user_id = sessions.user_id)))));



  create policy "Family can view sessions"
  on "public"."sessions"
  as permissive
  for select
  to authenticated
using ((EXISTS ( SELECT 1
   FROM (family_members me
     JOIN family_members target ON ((target.family_id = me.family_id)))
  WHERE ((me.user_id = auth.uid()) AND (target.user_id = sessions.user_id)))));



  create policy "Users can insert own sessions"
  on "public"."sessions"
  as permissive
  for insert
  to public
with check ((auth.uid() = user_id));



  create policy "Users can update own sessions"
  on "public"."sessions"
  as permissive
  for update
  to public
using ((auth.uid() = user_id));



  create policy "Users can view own sessions"
  on "public"."sessions"
  as permissive
  for select
  to public
using ((auth.uid() = user_id));



  create policy "Family members can view basic info"
  on "public"."users"
  as permissive
  for select
  to public
using ((EXISTS ( SELECT 1
   FROM family_members fm1,
    family_members fm2
  WHERE ((fm1.user_id = auth.uid()) AND (fm2.user_id = users.id) AND (fm1.family_id = fm2.family_id)))));



  create policy "Users can delete own profile"
  on "public"."users"
  as permissive
  for delete
  to public
using ((auth.uid() = id));



  create policy "Users can update own profile"
  on "public"."users"
  as permissive
  for update
  to public
using ((auth.uid() = id))
with check ((auth.uid() = id));



  create policy "Users can upsert own profile"
  on "public"."users"
  as permissive
  for insert
  to public
with check ((auth.uid() = id));



  create policy "Users can view own profile"
  on "public"."users"
  as permissive
  for select
  to authenticated
using ((auth.uid() = id));


CREATE TRIGGER albums_updated_at BEFORE UPDATE ON public.albums FOR EACH ROW EXECUTE FUNCTION handle_updated_at();

CREATE TRIGGER app_config_updated_at BEFORE UPDATE ON public.app_config FOR EACH ROW EXECUTE FUNCTION handle_updated_at();

CREATE TRIGGER conversations_updated_at BEFORE UPDATE ON public.conversations FOR EACH ROW EXECUTE FUNCTION handle_updated_at();

CREATE TRIGGER photos_updated_at BEFORE UPDATE ON public.photos FOR EACH ROW EXECUTE FUNCTION handle_updated_at();

CREATE TRIGGER sessions_updated_at BEFORE UPDATE ON public.sessions FOR EACH ROW EXECUTE FUNCTION handle_updated_at();

CREATE TRIGGER users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION handle_updated_at();


