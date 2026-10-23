# Integrated Flamma project

The main branch contains the integrated project saved on October 24, 2026.
The earlier October 9 snapshot remains on `backup/full-flamma-2026-10-09`.

- `Flamma/`: local chatbot, active intent v7, retained training artifacts, contextual reply choices, optional severity discussions, tests, and built frontend.
- `Image/thesis-backend/`: partner update `b064ee0` plus local integration safeguards. The active image checkpoint is `resnet50_skin_finale_oe.pth`; blur checks, skin crops, the normal-skin gate, and Grad-CAM++ are integrated.
- Root README and scripts: setup, startup, stopping, and online sharing.
- `reports/`: authored development/review documents and synthetic evaluation evidence. Older dated reports describe their historical models, not the newly merged image checkpoint.

The current integration passed 440 Python tests and live service checks. The real image checkpoint and direct Grad-CAM++ generation were exercised on synthetic pixel fixtures; these checks do not measure clinical accuracy.

Clone main and follow the first-time setup in README.md. The checked-in frontend build is ready to serve. Run share.ps1 for a new temporary online link.

Saved chats, uploads, session secrets, API keys, local environments, runtime logs, downloaded tunnel tools, bytecode, and reproducible embedding caches are excluded.
