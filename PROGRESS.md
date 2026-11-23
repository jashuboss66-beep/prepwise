# Development progress

## Phase 1 - Project foundation and authentication

- [x] React + Vite client with Tailwind CSS
- [x] Flask API and SQLite database through SQLAlchemy
- [x] Registration, hashed passwords, login, session persistence, and logout
- [x] Protected dashboard and client-side navigation
- [x] Phase 1 manually verified

## Phase 2 - Initial skill assessment

- [x] Seeded question bank: 5 MCQs each for aptitude, logical reasoning, verbal ability, and technical
- [x] Timed assessment interface with question navigation and saved answers
- [x] Store attempts, ordered questions, answers, overall scores, and subject results in SQLite
- [x] Evaluate answers on Flask and produce subject insights from measured performance
- [x] Detailed result review with correct answers and explanations
- [x] Per-user assessment history and ownership checks
- [x] Automated integration tests for scoring, timeout, SQLite restart persistence, and history isolation
- [x] Frontend production build
- [x] Local dev launcher starts Flask and Vite together; frontend API requests use the Vite proxy

## Phase 3 - NVIDIA Nemotron integration

- [x] Centralized Flask service for OpenRouter Chat Completions with the free Nemotron 3 Ultra model
- [x] Backend-only `OPENROUTER_API_KEY` configuration; local `.env` ignored by Git
- [x] Personalized analysis uses real stored subject results and derives score classifications in Flask
- [x] Four-week preparation roadmap with validated model output and score-based fallback
- [x] Placement-preparation tutor with profile goal and de-identified assessment history context
- [x] AI practice MCQs validate four distinct options, answer index, explanation, and subject before saving
- [x] Local chat, analysis, and question-bank fallback paths for missing keys, timeouts, API errors, and invalid responses
- [x] Per-user SQLite storage for analyses, tutor sessions/messages, and practice questions
- [x] React AI Coach, tutor chat, and practice screens with source labels and data-use notices
- [x] Automated tests for request format, API key isolation, response validation, endpoint ownership, and fallbacks
- [x] Generic live request verified against the free Nemotron endpoint
- [x] Frontend production build

## Phase 4 - Adaptive learning

- [x] Topic and subject performance summaries from saved practice answers, with assessment subject scores as first-time baselines
- [x] Deterministic difficulty selection based on up to five recent results and topic mastery context
- [x] Unseen-question-first selection with per-user repetition history
- [x] Personalized practice sessions with navigation, backend scoring, feedback, and explanations
- [x] Weak-topic recommendations, recent accuracy trend, and difficulty progression view
- [x] Dashboard recommendations and recent practice from persisted records
- [x] Practice session and answer persistence with per-user ownership checks
- [x] Expanded question bank with additional tagged practice questions; original Phase 2 assessment remains 20 questions
- [x] Automated tests for progression, recommendations, repetition prevention, persistence, validation, and user isolation

## Phase 5 - Gamification

- [x] Backend-only XP and coin rules awarded on completed assessment/practice activities
- [x] Unique per-user activity reward transactions prevent repeat payouts
- [x] Level progression at 100 XP per level with progress and level-up notifications
- [x] Automatic achievement unlocks and coin bonuses persisted per student
- [x] Consecutive-day and longest learning streaks; multiple activities on one date count as one streak day
- [x] XP leaderboard shows names, levels, and XP without emails
- [x] Rewards dashboard with XP, coins, levels, badges, streaks, leaderboard, and reward history
- [x] Automated tests for reward calculation, duplicates, level progression, achievements, streak gaps, leaderboard, persistence, and endpoint protections

## Phase 6 - Readiness and analytics

- [x] Deterministic readiness score with available-weight normalization and explicit pending categories
- [x] Aptitude/Technical scores combine actual answered assessment and practice questions; Coding remains pending until coding tasks exist
- [x] Completed timed assessments provide a clearly labeled mock-assessment proxy
- [x] Consistency score uses meaningful activity days in the last 30 days, normalized to 0-100
- [x] Topic and subject skill gaps, strongest/weakest skills, improvements, and recent performance changes
- [x] Chart.js subject, mastery radar, accuracy trend, practice activity, and difficulty distribution charts
- [x] Personalized, persisted placement report with Nemotron explanations and validated local fallbacks
- [x] Optional per-user target company preferences and general, non-guarantee preparation guidance
- [x] Dashboard readiness overview and per-user analytics/report endpoints
- [x] Tests for weighted calculations, pending components, normalization, analytics, report validation/fallback, persistence, and isolation

## Phase 7 - Integration and documentation

- [x] Audited backend routes, frontend API calls, navigation integrations, SQLAlchemy ownership checks, persistence paths, and centralized AI key handling
- [x] Added a complete student-journey integration test covering registration, login, profile preferences, assessment, AI fallbacks, adaptive practice, rewards, readiness, report, and restart persistence
- [x] Backend test suite: 19 tests passed
- [x] Frontend production build passed with Vite
- [x] Clean frontend dependency installation (`npm ci`) passed in a fresh temporary copy; repaired missing optional dependency lock entries
- [x] Windows `start.bat` launched both Flask and Vite successfully
- [x] Added Windows packaging instructions, environment template, dependency manifests, ignore rules, and source-only transfer archive
- [x] Excluded local database, real environment file, caches, virtual environment, `node_modules`, and build output from the transfer archive
- [x] Local development launcher starts Flask with Vite and proxies API requests through the frontend origin
- [ ] Browser-driven visual journey was not run in this environment; the full workflow is covered by Flask integration tests and startup was verified from the launcher

## Additional feature batch 1 - Personalized learning management

- [x] Added a separate one-to-one student profile for academic background, skill lists, preferred language, target roles, and daily/weekly study goals; reused existing account fields and target-company preferences
- [x] Added deterministic daily learning plans based on saved subject/topic performance, assessment baselines, study goals, and prior incomplete tasks
- [x] Added persisted daily and weekly missions with progress aggregated from actual practice answers, topic accuracy, completed sessions, and study goals
- [x] Integrated mission XP/coin payouts with the existing unique reward ledger and level-up behavior
- [x] Added target-versus-actual goal tracking, recent completed/missed daily goal history, and explicit study-time estimation rules
- [x] Added per-user in-app notifications for plans, missed goals, missions, achievements, level upgrades, and streak milestones
- [x] Added the My plan React page, protected API routes, navigation, and dashboard entry point
- [x] Added tests for profile updates, validation, first-time users, weak-topic plan recommendations, task carry-over, mission rewards/duplicate prevention, weekly session aggregation, goal progress, notifications, and user isolation
- [x] Backend test suite passed at the time: 24 tests
- [x] Frontend production build passed
- [x] Batch 2 remains unstarted

## Placement Learning Hub batch

- [x] Inspected and reused the existing `Question`, assessment answer, practice session/attempt, mission, AI analysis, and reward transaction models; SQLite startup migrations add only the required Hub columns and no parallel reward ledger
- [x] Seeded an original 600-question Hub bank (200 Aptitude, 150 Communication, 250 Technical) with topic, difficulty, source, and licence metadata; no third-party question text was copied
- [x] Added untimed category/topic/difficulty-based practice, immediate backend answer checks, bookmarks, incorrect/recent practice filters, history, and reward/missions integration
- [x] Added configurable timed AI assessments with randomized question/option order, persistence, existing timer/autosubmit UI, and reuse of the Nemotron analysis service
- [x] Added deterministic subject/topic/difficulty/timing/history metrics to AI assessment analysis; objective scores remain calculated from saved backend answers and the model supplies explanation only
- [x] Added persistent 10-question daily quizzes and integrated completion with existing practice mastery, streak, mission, and reward services; UTC deadline uses `DAILY_QUIZ_CUTOFF_UTC_HOUR`
- [x] Added Learning Hub route, dashboard stats/entry point, Chart.js AI analysis visualizations, and the question-bank report
- [x] Added Hub tests for seeded totals/metadata, answer feedback, bookmarks, attempt randomization and uniqueness, timing records, fallback metrics, daily quiz persistence/rewards, and student isolation
- [x] Full backend suite passed: 28 tests, including Hub workflows and existing phases
- [x] Frontend production build passed (Vite reports the existing single bundle is above its 500 kB advisory threshold)
- [ ] No browser-driven visual journey has been run in this batch


## Final UI/UX redesign

- [x] Replaced the horizontal-only navigation with a collapsible desktop sidebar, mobile drawer, page title header, unread notification indicator, and profile/sign-out menu
- [x] Applied a shared ivory, charcoal, forest, sage, and amber theme and one Manrope typography system across the existing screens; removed blue utility styling from the interface
- [x] Restyled dashboard around live assessment, practice, readiness, study goal, mission, and reward records with first-time empty states
- [x] Added consistent inline line icons, focus treatment, reduced-motion support, chart defaults, and assessment question review marking
- [x] Kept existing page routes, API calls, scoring and business logic; existing profile, company preparation, and notification features are linked from the redesigned navigation
- [x] Frontend production build passed after the final UI edits (Vite still reports the existing main bundle exceeds its 500 kB advisory threshold)
- [x] Full backend suite passed: 28 tests
- [ ] Browser visual inspection was limited to the login view because visiting protected student pages requires creating a synthetic account; no synthetic student data was added
- [x] Refreshed the source-only Windows transfer archive to include the redesigned frontend and current documentation; verified 88 entries and no build output, local database, virtual environment, or cache files


## Follow-up experience improvements

- [x] Unified today's recommended task, study goal progress, and completed mission count in the dashboard's Today card; first-time students receive a direct first-assessment action
- [x] Added actual per-topic session feedback and a one-click retry for the weakest topic after adaptive practice
- [x] Grouped AI Tutor, AI Coach, and AI Practice in a dedicated navigation section
- [x] Added text summaries and accessible labels for readiness charts; marked practice answer choices with their selected state
- [x] Kept performance comparisons grounded in saved records; the readiness screen continues to show recorded recent-versus-previous change
- [x] Frontend production build passed after these changes

## Coding practice demo

- [x] Added three original DSA exercises based on arrays/hashing, maximum-subarray sums, and binary search topic areas in Striver's A2Z sheet; no sheet problem text was copied
- [x] Added a responsive coding screen with Python, C++, Java, and JavaScript choice, language-specific starter code, sample runner, hidden test submission, hints, submission history, and accessible editor/result states
- [x] Flask proxies code execution to configurable Judge0 CE; source is not executed inside the application server; fixed batch polling to read Judge0's documented status_id response field and added actionable connection/configuration errors
- [x] Persisted student-scoped coding submissions and awarded XP/coins once for the first accepted solution per problem
- [x] Connected each student's best per-problem test pass rate to the placement readiness coding component
- [x] Added tests for catalog/language allowlisting, runner batching and status polling, saved results, outage messages, validation, user isolation, readiness scoring, and one-time rewards
- [x] Full backend suite passed: 37 tests; coding tests cover language choice, response polling, auth retry, and actionable errors
- [x] For the official public Judge0 CE host, retry once without an optional token rejected with 401/403; private/custom hosts keep requiring their configured token
- [ ] Live Judge0 execution depends on external runner/network availability; the direct smoke test could not resolve the Judge0 host in this environment

## Coding practice launcher fix

- [x] Fixed stale backend reuse: the combined launcher now always starts a fresh Flask process, so updated Judge0 settings from `backend/.env` are read after restart
- [x] Flask selects a free local port (5000–5099), and Vite's `/api` proxy targets that exact port; this also avoids confusing API errors when port 5000 was occupied
- [x] Verified launcher starts Flask on 5001 when 5000 is occupied and Vite on 5174 when 5173 is occupied
- [x] Full backend suite passed: 37 tests; frontend production build passed; launcher JavaScript syntax checks passed
- [ ] Live Judge0 execution remains dependent on external service/network availability; localhost HTTP smoke checks are blocked in this execution environment

## Coding practice runner replacement

- [x] Replaced the Judge0 integration with Wandbox's public compile API to remove the rejected Judge0 token dependency
- [x] Compiler IDs and supported language versions are resolved from the live catalog and cached for one hour; Python, C++, Java, and JavaScript stay available in the language picker
- [x] Keeps code execution outside Flask, validates compiler responses, checks sample and hidden outputs, and preserves student-scoped submissions and one-time rewards
- [x] Added runner adapter tests for dynamic compiler selection, compilation payloads, result evaluation, outages, persistence, and user isolation
- [ ] Live runner verification depends on public Wandbox availability; direct external API access is blocked in this environment
- [x] Updated coding-page text to match the new online sandbox runner
- [x] Final verification after runner switch: all 35 backend tests passed and Vite production build passed; live public compiler call was unavailable from this environment
- [x] Final error-diagnosis pass: identified screenshot failure as HTTP 403 from the external runner, added explicit client identification and surfaced a sanitized denial detail; full suite passed (36 tests)

## Coding practice terminal and compiler compatibility

- [x] C++ compiler selection now prefers GNU GCC builds for the starter's `<bits/stdc++.h>` include; ANSI color codes are stripped from compiler errors
- [x] Added an editable stdin terminal with a Run with input action and stdout/error output panel
- [x] Custom input runs are validated and do not create saved submissions or rewards
- [x] Added coverage for compiler preference, custom stdin/output, and no-reward terminal runs
