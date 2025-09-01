# BACKEND DEVELOPMENT PROTOCOL

This file inherits and extends the rules from the root `CLAUDE.md`. All backend tasks must adhere to both the root rules and the protocols below.

You are authorized to use advanced reasoning frameworks such as **Sequential Thinking**, **Context7**, and **Playwright MCP** when you deem them necessary to fulfill the request accurately.

## CORE ARCHITECTURE: HYBRID (SUPABASE + FASTAPI)

Our backend operates on a hybrid model. Your primary responsibility is to leverage Supabase for as much functionality as possible before proposing custom FastAPI endpoints.

1.  **Supabase (Primary):** Used for standard operations like authentication, user management, file storage (uploads/downloads), and simple database CRUD (Create, Read, Update, Delete) for albums, photos, etc.
2.  **FastAPI (Secondary):** Reserved for complex business logic, intensive computations, or integrations with external third-party APIs.

## MANDATORY PROCESS EXTENSION:

During **STEP 2: ANALYZE CURRENT SYSTEM**, your analysis must explicitly answer the following question first:

**"Can this feature be implemented entirely within Supabase using its Auth, Storage, and Database (with Row Level Security and Postgres Functions)? Provide a rationale for your conclusion."**

Only after proving a feature cannot or should not be built in Supabase may you proceed with a FastAPI implementation plan.

## BACKEND RULES (violating ANY invalidates your response):

❌ **No custom auth logic:** Always use **Supabase Auth**. Do not suggest building user tables or authentication endpoints in FastAPI.
❌ **No FastAPI for simple CRUD:** If a request is a straightforward data operation (e.g., create an album, fetch photos for a user), it **must** be handled via the Supabase API and client-side libraries, secured by RLS.
❌ **No bypassing Supabase Storage:** All file uploads (e.g., photos) **must** use Supabase Storage. FastAPI should only handle metadata or post-processing logic if necessary, not the upload itself.

✅ **Supabase First:** Always begin your analysis with a Supabase-based solution.
✅ **Leverage Row Level Security (RLS):** All data access policies for Supabase tables must be defined using RLS. Your suggestions must reference how RLS will secure the data for the current user.
✅ **Use Pydantic Models:** For all FastAPI endpoints, you must use Pydantic for request and response data validation. Reference existing models in `app/models/`.
✅ **Use Dependency Injection:** FastAPI logic must correctly use the `Depends` system for shared resources like database connections or API clients. Reference `app/dependencies.py`.

## FINAL REMINDER:

Before you suggest creating a new FastAPI endpoint, you must first exhaustively explain **why** the same functionality cannot be achieved using a combination of Supabase's built-in features, including Postgres Functions. Justify your choice by comparing the complexity, security, and performance of both approaches.
