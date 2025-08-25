alter table "public"."cist_responses" drop constraint "cist_responses_cist_category_check";

alter table "public"."conversations" drop constraint "conversations_question_type_check";

alter table "public"."session_reports" drop constraint "session_reports_cognitive_status_check";

alter table "public"."sessions" drop constraint "sessions_session_type_check";

alter table "public"."sessions" drop constraint "sessions_status_check";

alter table "public"."users" drop constraint "users_gender_check";


  create table "public"."photo_stories" (
    "id" uuid not null default uuid_generate_v4(),
    "user_id" uuid not null,
    "photo_id" uuid not null,
    "title" character varying(200),
    "story_text" text not null,
    "language" character varying(20) default 'ko'::character varying,
    "status" character varying(20) default 'generated'::character varying,
    "source_session_ids" uuid[],
    "source_conversation_ids" uuid[],
    "tts_audio_path" text,
    "tts_status" character varying(20) default 'none'::character varying,
    "tts_params" jsonb,
    "created_at" timestamp with time zone default now(),
    "updated_at" timestamp with time zone default now()
      );


alter table "public"."photo_stories" enable row level security;


  create table "public"."session_audio_analysis" (
    "id" uuid not null default uuid_generate_v4(),
    "phodo_id" uuid,
    "user_id" uuid not null,
    "family_id" uuid not null,
    "audio_path" text not null,
    "file_size" bigint,
    "adjusted_mean" numeric(12,4),
    "total_slices" integer not null,
    "dementia_slices" integer not null,
    "dementia_ratio" numeric(6,4) generated always as (
CASE
    WHEN (total_slices > 0) THEN ((dementia_slices)::numeric / (total_slices)::numeric)
    ELSE (0)::numeric
END) stored,
    "risk_level" text,
    "age_group_avg_ratio" numeric(6,4) default 0.2500,
    "created_at" timestamp with time zone default now(),
    "updated_at" timestamp with time zone default now(),
    "health_score" integer generated always as (
CASE
    WHEN (total_slices > 0) THEN LEAST(100, GREATEST(0, (((100)::numeric - round((((dementia_slices)::numeric / (total_slices)::numeric) * (100)::numeric))))::integer))
    ELSE 100
END) stored
      );



  create table "public"."session_text_analysis" (
    "id" uuid not null default uuid_generate_v4(),
    "session_id" uuid not null,
    "user_id" uuid not null,
    "total_words_count" integer not null,
    "content_word_ratio" real not null,
    "function_word_ratio" real not null,
    "mattr" real,
    "mlu" real,
    "demonstrative_count" numeric(6,4),
    "speech_duration" numeric(6,4),
    "model_name" text default ''::text,
    "model_version" text,
    "computed_at" timestamp with time zone default now(),
    "created_at" timestamp with time zone default now(),
    "updated_at" timestamp with time zone default now(),
    "lexical_diversity" real,
    "demonstrative_ratio" real,
    "speech_rate" numeric
      );


alter table "public"."session_text_analysis" enable row level security;

CREATE INDEX idx_photo_stories_photo ON public.photo_stories USING btree (photo_id);

CREATE INDEX idx_photo_stories_user ON public.photo_stories USING btree (user_id);

CREATE INDEX idx_saa_family_id ON public.session_audio_analysis USING btree (family_id);

CREATE INDEX idx_saa_user_id ON public.session_audio_analysis USING btree (user_id);

CREATE INDEX idx_session_text_metrics_session_id ON public.session_text_analysis USING btree (session_id);

CREATE INDEX idx_session_text_metrics_user_id ON public.session_text_analysis USING btree (user_id);

CREATE UNIQUE INDEX photo_stories_pkey ON public.photo_stories USING btree (id);

CREATE UNIQUE INDEX photo_stories_user_id_photo_id_key ON public.photo_stories USING btree (user_id, photo_id);

CREATE UNIQUE INDEX session_audio_analysis_pkey ON public.session_audio_analysis USING btree (id);

CREATE UNIQUE INDEX session_text_metrics_pkey ON public.session_text_analysis USING btree (id);

CREATE UNIQUE INDEX session_text_metrics_session_id_key ON public.session_text_analysis USING btree (session_id);

alter table "public"."photo_stories" add constraint "photo_stories_pkey" PRIMARY KEY using index "photo_stories_pkey";

alter table "public"."session_audio_analysis" add constraint "session_audio_analysis_pkey" PRIMARY KEY using index "session_audio_analysis_pkey";

alter table "public"."session_text_analysis" add constraint "session_text_metrics_pkey" PRIMARY KEY using index "session_text_metrics_pkey";

alter table "public"."photo_stories" add constraint "photo_stories_photo_id_fkey" FOREIGN KEY (photo_id) REFERENCES photos(id) ON DELETE CASCADE not valid;

alter table "public"."photo_stories" validate constraint "photo_stories_photo_id_fkey";

alter table "public"."photo_stories" add constraint "photo_stories_status_check" CHECK (((status)::text = ANY ((ARRAY['draft'::character varying, 'generated'::character varying, 'published'::character varying])::text[]))) not valid;

alter table "public"."photo_stories" validate constraint "photo_stories_status_check";

alter table "public"."photo_stories" add constraint "photo_stories_tts_status_check" CHECK (((tts_status)::text = ANY ((ARRAY['none'::character varying, 'queued'::character varying, 'running'::character varying, 'succeeded'::character varying, 'failed'::character varying])::text[]))) not valid;

alter table "public"."photo_stories" validate constraint "photo_stories_tts_status_check";

alter table "public"."photo_stories" add constraint "photo_stories_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE not valid;

alter table "public"."photo_stories" validate constraint "photo_stories_user_id_fkey";

alter table "public"."photo_stories" add constraint "photo_stories_user_id_photo_id_key" UNIQUE using index "photo_stories_user_id_photo_id_key";

alter table "public"."session_audio_analysis" add constraint "session_audio_analysis_age_group_avg_ratio_check" CHECK (((age_group_avg_ratio >= (0)::numeric) AND (age_group_avg_ratio <= (1)::numeric))) not valid;

alter table "public"."session_audio_analysis" validate constraint "session_audio_analysis_age_group_avg_ratio_check";

alter table "public"."session_audio_analysis" add constraint "session_audio_analysis_dementia_ratio_check" CHECK (((dementia_ratio >= (0)::numeric) AND (dementia_ratio <= (1)::numeric))) not valid;

alter table "public"."session_audio_analysis" validate constraint "session_audio_analysis_dementia_ratio_check";

alter table "public"."session_audio_analysis" add constraint "session_audio_analysis_dementia_slices_check" CHECK ((dementia_slices >= 0)) not valid;

alter table "public"."session_audio_analysis" validate constraint "session_audio_analysis_dementia_slices_check";

alter table "public"."session_audio_analysis" add constraint "session_audio_analysis_family_id_fkey" FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE CASCADE not valid;

alter table "public"."session_audio_analysis" validate constraint "session_audio_analysis_family_id_fkey";

alter table "public"."session_audio_analysis" add constraint "session_audio_analysis_file_size_check" CHECK ((file_size >= 0)) not valid;

alter table "public"."session_audio_analysis" validate constraint "session_audio_analysis_file_size_check";

alter table "public"."session_audio_analysis" add constraint "session_audio_analysis_risk_level_check" CHECK ((risk_level = ANY (ARRAY['normal'::text, 'suspect'::text, 'risk'::text]))) not valid;

alter table "public"."session_audio_analysis" validate constraint "session_audio_analysis_risk_level_check";

alter table "public"."session_audio_analysis" add constraint "session_audio_analysis_total_slices_check" CHECK ((total_slices >= 0)) not valid;

alter table "public"."session_audio_analysis" validate constraint "session_audio_analysis_total_slices_check";

alter table "public"."session_audio_analysis" add constraint "session_audio_analysis_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE not valid;

alter table "public"."session_audio_analysis" validate constraint "session_audio_analysis_user_id_fkey";

alter table "public"."session_text_analysis" add constraint "session_text_metrics_content_to_function_ratio_check" CHECK ((demonstrative_count >= (0)::numeric)) not valid;

alter table "public"."session_text_analysis" validate constraint "session_text_metrics_content_to_function_ratio_check";

alter table "public"."session_text_analysis" add constraint "session_text_metrics_content_word_count_check" CHECK ((mlu >= (0)::double precision)) not valid;

alter table "public"."session_text_analysis" validate constraint "session_text_metrics_content_word_count_check";

alter table "public"."session_text_analysis" add constraint "session_text_metrics_function_word_count_check" CHECK ((mattr >= (0)::double precision)) not valid;

alter table "public"."session_text_analysis" validate constraint "session_text_metrics_function_word_count_check";

alter table "public"."session_text_analysis" add constraint "session_text_metrics_session_id_fkey" FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE not valid;

alter table "public"."session_text_analysis" validate constraint "session_text_metrics_session_id_fkey";

alter table "public"."session_text_analysis" add constraint "session_text_metrics_session_id_key" UNIQUE using index "session_text_metrics_session_id_key";

alter table "public"."session_text_analysis" add constraint "session_text_metrics_total_duration_seconds_check" CHECK ((function_word_ratio >= (0)::double precision)) not valid;

alter table "public"."session_text_analysis" validate constraint "session_text_metrics_total_duration_seconds_check";

alter table "public"."session_text_analysis" add constraint "session_text_metrics_total_utterances_check" CHECK ((content_word_ratio >= (0)::double precision)) not valid;

alter table "public"."session_text_analysis" validate constraint "session_text_metrics_total_utterances_check";

alter table "public"."session_text_analysis" add constraint "session_text_metrics_total_words_check" CHECK ((total_words_count >= 0)) not valid;

alter table "public"."session_text_analysis" validate constraint "session_text_metrics_total_words_check";

alter table "public"."session_text_analysis" add constraint "session_text_metrics_ttr_check" CHECK (((speech_duration >= (0)::numeric) AND (speech_duration <= (1)::numeric))) not valid;

alter table "public"."session_text_analysis" validate constraint "session_text_metrics_ttr_check";

alter table "public"."session_text_analysis" add constraint "session_text_metrics_user_id_fkey" FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE not valid;

alter table "public"."session_text_analysis" validate constraint "session_text_metrics_user_id_fkey";

alter table "public"."cist_responses" add constraint "cist_responses_cist_category_check" CHECK (((cist_category)::text = ANY ((ARRAY['orientation_time'::character varying, 'orientation_place'::character varying, 'memory_registration'::character varying, 'memory_recall'::character varying, 'memory_recognition'::character varying, 'attention'::character varying, 'executive_function'::character varying, 'language_naming'::character varying])::text[]))) not valid;

alter table "public"."cist_responses" validate constraint "cist_responses_cist_category_check";

alter table "public"."conversations" add constraint "conversations_question_type_check" CHECK (((question_type)::text = ANY ((ARRAY['open_ended'::character varying, 'cist_orientation'::character varying, 'cist_memory'::character varying, 'cist_attention'::character varying, 'cist_executive'::character varying, 'cist_language'::character varying])::text[]))) not valid;

alter table "public"."conversations" validate constraint "conversations_question_type_check";

alter table "public"."session_reports" add constraint "session_reports_cognitive_status_check" CHECK (((cognitive_status)::text = ANY ((ARRAY['normal'::character varying, 'mild_concern'::character varying, 'moderate_concern'::character varying, 'high_concern'::character varying])::text[]))) not valid;

alter table "public"."session_reports" validate constraint "session_reports_cognitive_status_check";

alter table "public"."sessions" add constraint "sessions_session_type_check" CHECK (((session_type)::text = ANY ((ARRAY['reminiscence'::character varying, 'assessment'::character varying, 'mixed'::character varying])::text[]))) not valid;

alter table "public"."sessions" validate constraint "sessions_session_type_check";

alter table "public"."sessions" add constraint "sessions_status_check" CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'completed'::character varying, 'paused'::character varying, 'cancelled'::character varying])::text[]))) not valid;

alter table "public"."sessions" validate constraint "sessions_status_check";

alter table "public"."users" add constraint "users_gender_check" CHECK (((gender)::text = ANY ((ARRAY['male'::character varying, 'female'::character varying, 'other'::character varying])::text[]))) not valid;

alter table "public"."users" validate constraint "users_gender_check";

set check_function_bodies = off;

CREATE OR REPLACE FUNCTION public.get_user_rows_all_tables(p_user_id uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
AS $function$
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
$function$
;

CREATE OR REPLACE FUNCTION public.set_updated_at()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
begin
  new.updated_at := now();
  return new;
end $function$
;

grant delete on table "public"."photo_stories" to "anon";

grant insert on table "public"."photo_stories" to "anon";

grant references on table "public"."photo_stories" to "anon";

grant select on table "public"."photo_stories" to "anon";

grant trigger on table "public"."photo_stories" to "anon";

grant truncate on table "public"."photo_stories" to "anon";

grant update on table "public"."photo_stories" to "anon";

grant delete on table "public"."photo_stories" to "authenticated";

grant insert on table "public"."photo_stories" to "authenticated";

grant references on table "public"."photo_stories" to "authenticated";

grant select on table "public"."photo_stories" to "authenticated";

grant trigger on table "public"."photo_stories" to "authenticated";

grant truncate on table "public"."photo_stories" to "authenticated";

grant update on table "public"."photo_stories" to "authenticated";

grant delete on table "public"."photo_stories" to "service_role";

grant insert on table "public"."photo_stories" to "service_role";

grant references on table "public"."photo_stories" to "service_role";

grant select on table "public"."photo_stories" to "service_role";

grant trigger on table "public"."photo_stories" to "service_role";

grant truncate on table "public"."photo_stories" to "service_role";

grant update on table "public"."photo_stories" to "service_role";

grant delete on table "public"."session_audio_analysis" to "anon";

grant insert on table "public"."session_audio_analysis" to "anon";

grant references on table "public"."session_audio_analysis" to "anon";

grant select on table "public"."session_audio_analysis" to "anon";

grant trigger on table "public"."session_audio_analysis" to "anon";

grant truncate on table "public"."session_audio_analysis" to "anon";

grant update on table "public"."session_audio_analysis" to "anon";

grant delete on table "public"."session_audio_analysis" to "authenticated";

grant insert on table "public"."session_audio_analysis" to "authenticated";

grant references on table "public"."session_audio_analysis" to "authenticated";

grant select on table "public"."session_audio_analysis" to "authenticated";

grant trigger on table "public"."session_audio_analysis" to "authenticated";

grant truncate on table "public"."session_audio_analysis" to "authenticated";

grant update on table "public"."session_audio_analysis" to "authenticated";

grant delete on table "public"."session_audio_analysis" to "service_role";

grant insert on table "public"."session_audio_analysis" to "service_role";

grant references on table "public"."session_audio_analysis" to "service_role";

grant select on table "public"."session_audio_analysis" to "service_role";

grant trigger on table "public"."session_audio_analysis" to "service_role";

grant truncate on table "public"."session_audio_analysis" to "service_role";

grant update on table "public"."session_audio_analysis" to "service_role";

grant delete on table "public"."session_text_analysis" to "anon";

grant insert on table "public"."session_text_analysis" to "anon";

grant references on table "public"."session_text_analysis" to "anon";

grant select on table "public"."session_text_analysis" to "anon";

grant trigger on table "public"."session_text_analysis" to "anon";

grant truncate on table "public"."session_text_analysis" to "anon";

grant update on table "public"."session_text_analysis" to "anon";

grant delete on table "public"."session_text_analysis" to "authenticated";

grant insert on table "public"."session_text_analysis" to "authenticated";

grant references on table "public"."session_text_analysis" to "authenticated";

grant select on table "public"."session_text_analysis" to "authenticated";

grant trigger on table "public"."session_text_analysis" to "authenticated";

grant truncate on table "public"."session_text_analysis" to "authenticated";

grant update on table "public"."session_text_analysis" to "authenticated";

grant delete on table "public"."session_text_analysis" to "service_role";

grant insert on table "public"."session_text_analysis" to "service_role";

grant references on table "public"."session_text_analysis" to "service_role";

grant select on table "public"."session_text_analysis" to "service_role";

grant trigger on table "public"."session_text_analysis" to "service_role";

grant truncate on table "public"."session_text_analysis" to "service_role";

grant update on table "public"."session_text_analysis" to "service_role";


  create policy "pst_delete_own"
  on "public"."photo_stories"
  as permissive
  for delete
  to public
using ((auth.uid() = user_id));



  create policy "pst_insert_photo_owned_or_family"
  on "public"."photo_stories"
  as permissive
  for insert
  to public
with check (((auth.uid() = user_id) AND (EXISTS ( SELECT 1
   FROM photos p
  WHERE ((p.id = photo_stories.photo_id) AND ((p.user_id = auth.uid()) OR (EXISTS ( SELECT 1
           FROM (family_members fm1
             JOIN family_members fm2 ON ((fm1.family_id = fm2.family_id)))
          WHERE ((fm1.user_id = auth.uid()) AND (fm2.user_id = p.user_id))))))))));



  create policy "pst_select_owner_or_family"
  on "public"."photo_stories"
  as permissive
  for select
  to public
using (((auth.uid() = user_id) OR (EXISTS ( SELECT 1
   FROM ((photos p
     JOIN family_members fm1 ON ((fm1.user_id = auth.uid())))
     JOIN family_members fm2 ON (((fm2.user_id = p.user_id) AND (fm1.family_id = fm2.family_id))))
  WHERE (p.id = photo_stories.photo_id)))));



  create policy "pst_update_photo_owned_or_family"
  on "public"."photo_stories"
  as permissive
  for update
  to public
using ((auth.uid() = user_id))
with check (((auth.uid() = user_id) AND (EXISTS ( SELECT 1
   FROM photos p
  WHERE ((p.id = photo_stories.photo_id) AND ((p.user_id = auth.uid()) OR (EXISTS ( SELECT 1
           FROM (family_members fm1
             JOIN family_members fm2 ON ((fm1.family_id = fm2.family_id)))
          WHERE ((fm1.user_id = auth.uid()) AND (fm2.user_id = p.user_id))))))))));



  create policy "saa_delete_own"
  on "public"."session_audio_analysis"
  as permissive
  for delete
  to public
using ((auth.uid() = user_id));



  create policy "saa_insert_own_and_family_member"
  on "public"."session_audio_analysis"
  as permissive
  for insert
  to public
with check (((auth.uid() = user_id) AND (EXISTS ( SELECT 1
   FROM family_members fm
  WHERE ((fm.user_id = auth.uid()) AND (fm.family_id = session_audio_analysis.family_id))))));



  create policy "saa_select_self_or_family"
  on "public"."session_audio_analysis"
  as permissive
  for select
  to public
using (((auth.uid() = user_id) OR (EXISTS ( SELECT 1
   FROM family_members fm
  WHERE ((fm.user_id = auth.uid()) AND (fm.family_id = session_audio_analysis.family_id))))));



  create policy "saa_update_own"
  on "public"."session_audio_analysis"
  as permissive
  for update
  to public
using ((auth.uid() = user_id))
with check ((auth.uid() = user_id));



  create policy "stm_insert_own"
  on "public"."session_text_analysis"
  as permissive
  for insert
  to public
with check ((auth.uid() = user_id));



  create policy "stm_select_own"
  on "public"."session_text_analysis"
  as permissive
  for select
  to public
using ((auth.uid() = user_id));



  create policy "stm_update_own"
  on "public"."session_text_analysis"
  as permissive
  for update
  to public
using ((auth.uid() = user_id))
with check ((auth.uid() = user_id));


CREATE TRIGGER trg_photo_stories_updated BEFORE UPDATE ON public.photo_stories FOR EACH ROW EXECUTE FUNCTION set_updated_at();


