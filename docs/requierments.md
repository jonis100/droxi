# Clinic Inbox — Take-Home Assignment

## Background

A medical clinic network uses an external system where patients submit messages (questions, medication refills, etc.). Our platform periodically receives batches of these **inbox items** and must organize them for doctors to review efficiently.

## Business Rules

- Each **inbox item** has: patient ID, message text, optional medications, assigned department (Dermatology / Radiology / Primary), and status (Open / Closed).
- Incoming items must be grouped into **patient requests** — one request per patient per department — so a doctor sees a single consolidated entry instead of many individual items.
- Items can change between batches: message or medications updated, department reassigned, or status set to Closed.
- Closing an item clears its content from the active request but keeps the item record for audit. When all items in a request are closed, the request is closed too. Closed requests are medical history and must be preserved.
- Department reassignment moves an item from one request to another.

## Deliverables

1. **Design document** — Data model, API design, assumptions about scale and system behavior, and trade-offs between your implementation and what a production system would require.
2. **Backend (Python)** — Ingestion, grouping logic, REST API. A working prototype is sufficient — not a production-ready system.
3. **Frontend (Angular)** — Simple dashboard showing a department's open requests with live updates. Functional, not polished.
4. **Tests** — Cover core grouping and update logic.

## Assumptions

Think about the expected scale (patients, doctors, departments), data volumes, event ordering, and failure scenarios. State your assumptions explicitly in the design document — we want to see your reasoning, not a "correct" answer.

## Evaluation Focus

- System analysis — how you decomposed requirements into a working model.
- System design — data modeling, API design, separation of concerns.
- Code quality and documented trade-offs.
- Frontend: sound structure matters, styling does not.

## Logistics

- **Timeline:** 3–4 days / ~4 hours of effort.
- **Tools:** AI assistants, any libraries/frameworks — all permitted.
- **Ambiguity:** Document your assumption and proceed.
- **Submission:** Return to us a zip file which will include your assigment
