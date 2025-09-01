# FRONTEND DEVELOPMENT PROTOCOL (FLUTTER)

This file inherits and extends the rules from the root `CLAUDE.md`. All frontend tasks must adhere to both the root rules and the Flutter-specific protocols below.

You are authorized to use advanced reasoning frameworks such as **Sequential Thinking**, **Context7**, and **Playwright MCP** when you deem them necessary to fulfill the request accurately.

## CORE ARCHITECTURE: FLUTTER (DART)

Our frontend is an Android application built with Flutter. All suggestions must be compatible with the Flutter framework and Dart language.

## MANDATORY PROCESS EXTENSION:

During **STEP 2: ANALYZE CURRENT SYSTEM**, your analysis must include these specific Flutter-related checkpoints:

1.  **Widget Reusability:** Scrutinize the `lib/widgets/common/` directory. Can the requested UI be built by composing or extending existing common widgets?
2.  **State Management:** Identify the current state management solution (e.g., Riverpod, BLoC, Provider) by analyzing `lib/providers/` or `lib/blocs/`. New state must be integrated into this existing system. Differentiate between local state (`StatefulWidget`) and application/shared state.
3.  **Service/Repository Layer:** All communication with the backend (Supabase, FastAPI) must go through the existing service layer defined in `lib/services/` or `lib/repositories/`. Analyze the existing Supabase client instance and API service functions.
4.  **Navigation & Routing:** New screens must be integrated into the existing routing solution (e.g., GoRouter, Navigator 2.0) defined in `lib/routes/app_router.dart`.

## FRONTEND RULES (violating ANY invalidates your response):

❌ **No "Monster Widgets":** Do not create large, monolithic widgets for entire screens. Decompose the UI into smaller, reusable widgets.
❌ **No business logic in UI files:** Widget files (`lib/screens/`, `lib/widgets/`) should only contain UI and event-handling code. All business logic, data fetching, and state manipulation must be delegated to the state management layer (Providers/BLoCs).
❌ **No hardcoded styles:** All colors, fonts, and spacing must be referenced from the central `ThemeData` object defined in `lib/theme/app_theme.dart`.

✅ **Embrace Immutability:** When updating state, always create new instances of your state objects instead of mutating existing ones.
✅ **Use the Supabase-Dart Library:** All interactions with Supabase must use the official `supabase_flutter` package. Reference the initialized client in `lib/services/supabase_service.dart`.
✅ **Follow Effective Dart guidelines:** All generated Dart code must adhere to the official style and usage guidelines.
✅ **Provide Full Widget Code:** When suggesting a new widget, provide the complete, self-contained Dart code for the file, including necessary imports.

## FINAL REMINDER:

Before you suggest creating a new reusable widget, you must first explain why existing widgets in `lib/widgets/common/` cannot be adapted by passing different parameters. Before adding new application state, explain why the required data cannot be derived or combined from existing state providers/BLoCs.
