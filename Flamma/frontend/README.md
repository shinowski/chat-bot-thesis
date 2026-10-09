# Flamma frontend

The active React interface is in this folder. Flask serves its built files
from `dist` at http://127.0.0.1:5000.

For regular startup, follow the [main README](../../README.md).

To edit the interface, start both services using the main README, then run:

```powershell
cd "C:\flamma chatbot\Flamma\frontend"
npm.cmd install
npm.cmd run dev
```

Open the address printed by Vite. Requests to the chatbot and history API
are forwarded to Flask.

After editing, update the interface served by Flask:

```powershell
npm.cmd run build
```

Keep `dist`, `node_modules`, and `Flamma\venv` for the working local setup.
The small `Flamma\package.json` declares shared JavaScript files as modules;
frontend dependencies and build commands belong to this folder's package.json.
