# Complete Flamma backup

This branch contains the complete working project as of October 9, 2026.
It preserves the original chatbot repository history.

- `Flamma/`: chatbot source, trained text classifiers, tests, and built web interface.
- `Image/thesis-backend/`: local image backend based on upstream commit `267ae33`, including integration fixes and all four existing image checkpoints.
- Root scripts and README: local startup, stopping, and online sharing tutorial.

To restore on Windows, clone this branch or download it, install the dependencies using the first-time setup in README.md, then run start.ps1.
If you use the included frontend build, you can skip the Node.js build steps.
Treat the online URL in README.md as temporary: run share.ps1 to create a new link on your own computer.

Browser history, uploaded photos, session secrets, API keys, virtual environments, logs, and downloaded tunnel tools are excluded.
