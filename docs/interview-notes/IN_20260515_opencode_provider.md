# Interview Notes: IN_20260515_opencode_provider

**Interviewer(s):** SA
**Participant(s):** eol
**Session Type:** Technical discovery
**Date:** 2026-05-15

---

## General

| Question | Answer |
|----------|--------|
| What is the goal? | Add OpencodeProvider as a pluggable AIProvider backend that calls opencode serve's HTTP REST API |
| Why is this needed? | Ollama not running, no Gemini/OpenAI API keys available. opencode serve provides free AI access locally on port 4096 |
| What API does opencode serve expose? | `POST /session` (create session), `POST /session/{id}/message` (send prompt, collect text parts) |

---

## Domain Questions

| Q# | Question | Answer |
|----|----------|--------|
| Q1 | How does OpencodeProvider authenticate? | `opencode:<password>` basic auth via `OPENCODE_SERVER_PASSWORD` env var |
| Q2 | What is the session lifecycle? | One persistent session created in `__init__`, reused across all `chat()` calls. Auto-recreated on 404 from message endpoint |
| Q3 | Does OpencodeProvider use the model parameter? | No — accepts but ignores with logged warning. opencode's model is configured server-side |
| Q4 | How is the response parsed? | Collect all text parts (`type == "text"`) from the parts array, join with "\\n". Skip reasoning/step-start/step-finish parts |
| Q5 | What env vars control OpencodeProvider? | `OPENCODE_BASE_URL` (default http://127.0.0.1:4096), `OPENCODE_SERVER_PASSWORD` (required), `OPENCODE_SESSION_TIMEOUT` (default 120) |
| Q6 | Does it use DSR_AI_API_KEY? | No — OpencodeProvider has its own auth scheme. DSR_AI_API_KEY is for Gemini/OpenAI only |
| Q7 | Error handling? | 401 on init → AuthenticationError immediately. 401/404 on message → session recreate + retry once. 429 → exponential backoff 15s/2x/3. 5xx → ProviderError. Connection error → ConnectionError |
| Q8 | How do tests work? | Use httpx.MockTransport with sync handler. Mock POST /session returns {"id": "mock-sid"}. Mock POST /session/mock-sid/message returns text parts |
