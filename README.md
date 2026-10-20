# Flamma: Chatbot + Image Classifier

Chat about your skin concern, upload a photo, and see the image model's result.

## Open Flamma online

<!-- flamma-sharing:start -->
**[Open Flamma](https://simpson-susan-punch-extension.trycloudflare.com)**

Current online address: [https://simpson-susan-punch-extension.trycloudflare.com](https://simpson-susan-punch-extension.trycloudflare.com)

**Sharing is running.** This temporary link works while the host computer and sharing service are running.
<!-- flamma-sharing:end -->

The link above updates automatically when you start or stop sharing.
It works while this computer is on, connected to the internet, and running Flamma.

## 1. Start the app

This computer is already set up. Open **PowerShell**, copy these two lines,
and press **Enter**:

```powershell
cd "C:\flamma chatbot"
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

This starts both the chatbot and the image classifier. Give them a moment to
load, then open **http://127.0.0.1:5000** in your browser.

If they are already running, the command says **already running**. You can
open the same browser address and continue using the app.

## 2. Chat and upload a photo

1. Describe your skin concern, or type **I want to send an image**.
2. Click **Choose photo** in the reply or the image button beside the message
   box. Asking to upload a photo does not open the picker automatically.
3. You can upload at any time. There is no severity question to answer first.
4. Choose a **JPG, PNG, or WebP** photo smaller than **10 MB**.
5. Click **Send**.

The reply shows the model's result, confidence, and an image heatmap. If the
photo is rejected, read the reply and try another photo. The result is a
screening result, not a confirmed diagnosis.

Accepted photos also show general care and treatment options for the model's
matched class: atopic dermatitis, contact dermatitis, lichen planus, psoriasis,
or rosacea. Click **Treatment options for this photo** to discuss the saved
result without another upload. Replies include links to the care sources.
Medication options are information to discuss with a clinician; the chatbot
does not select a personal medicine, dose, or treatment plan from a photo.
A normal-skin label offers general skin care, not disease-specific medication.
Rejected photos cannot reuse an earlier photo's treatment information.

The source-backed summaries are in `Flamma/data/treatment_guidance.json`, with
the date the sources were checked. The automatic mapping and history tests
use simulated photo results; they do not measure image-model or treatment
accuracy. To run the mapping tests:

```powershell
cd "C:\flamma chatbot\Flamma"
.\venv\Scripts\python.exe -B -m unittest test_photo_treatments
```

You can write naturally: common typos and shorthand such as **rashesh**,
**2wks**, **idk**, and **can i sent pictuer** are recognized. If the wording
is unclear, the chatbot may ask a follow-up question.

Doctor questions such as **When should I see a doctor?** or
**wen shud i see a docter?** receive general care guidance, even without a
photo or condition name. Common symptom and duration typos such as
**myskin is ithcy on my elbwo** and **3dasy** are also recognized. Corrections
use a reviewed alias list; unfamiliar words may still need clarification.
The original message, medicine names, strengths, and negation are retained.
Reported physical warning signs take priority; a classifier emergency guess
alone asks about warning signs rather than claiming an emergency.

Say **I have a new rash on my leg** or **new skin concern** to start screening
a different problem within the same chat. This clears the active screening
and photo context, keeps your saved messages and photos, and preserves a
text-only preference. Statements such as **I have no rash or itching** are
recorded as symptoms you deny, separately from reported symptoms.

Replies appear in full as soon as the server responds. The loading indicator
appears only while a request is being processed; there is no word-by-word reveal.
Exported chats include the treatment sources and the date they were checked.
Questions such as **Can I use that?** ask which product you mean. Naming a
product in reply does not record it as medication you have used. If you name
two possible conditions, the chatbot asks which one to explain; a choice such
as **second one** resumes the requested topic. Explicit comparisons receive
general descriptions. Conflicting answers such as **two days or two months**
are clarified before changing the screening details.

Unchanged drafts retried after a timeout reuse the same request ID. Saved
requests return their original exchange without repeating inference or adding
another exchange to history. Changed drafts receive a new ID. Reloading a
saved conversation clears an already-confirmed retry and its restored draft.
Only retry IDs and content hashes are kept in browser session storage; chat
text and photo bytes are not stored there.

API clients can provide `request_id` (1–64 letters, digits, underscores, or
hyphens) in JSON or multipart requests. Reuse it only for the same message and
photo in the same conversation. Changed content with an existing ID returns
HTTP 409. Receipts are stored atomically with the saved exchange, scoped to the
browser owner and conversation, and removed when the conversation is deleted.
Requests without IDs remain supported but do not receive retry protection.
Run one chatbot process: its browser mutation locks coordinate inference
within that process, rather than across multiple application workers.
Starting `Flamma/app.py` also begins loading the cached text model in the
background. History and deterministic warning replies remain available while
it initializes; `/health` reports `loading` until the model is ready.

Press **Enter** to send, or **Shift + Enter** for a new line. The text box stays
ready while Flamma replies so you can type your next message without clicking
it again. Send becomes available when the current reply arrives.

After uploading a photo, you can ask **What do you think about that image?**
or **What are your thoughts about it?** The chatbot explains the saved result;
you do not need to send the same photo again. You can also answer **I don't know**
when you cannot describe a symptom or answer a screening question.

Try these messages to keep the conversation going:

- **What causes it, and how can I treat it?** — asks about both topics.
- **What is this disease?** — explains the last condition discussed or the photo's screening suggestion.
- **What is contact dermatitis?** — explains a specific condition even without a photo.
- **And treatment?** or **What next?** — follows the condition just discussed.
- **Explain simply** — asks for a shorter explanation of the last answer.
- **Summarize our conversation** — shows the details you provided and any photo result.
- **Skip the questions** — pauses screening so you can ask your own questions.
- **Continue screening** — resumes with the next unanswered question.
- **Text only please** — keeps the conversation available without requiring a photo.
- **Do you learn from my messages?** — explains how model training differs from saved history.

You can say **Thanks** or **Yes** between screening answers without losing
the current question. Medication reports such as **I've been applying a cream
for five days** are recorded as treatment use; that time does not replace how
long you have had the skin problem. You can correct treatment details or ask
about a named condition without establishing a diagnosis.

If you say **I don't know** after an explanation, Flamma offers help understanding
it. If you say it after a screening question, that answer is marked unknown.
You can correct details, for example **Actually, my left leg, not my arm, for
three weeks**. A number such as **2** needs a time unit; use **2 days** or **2 weeks**.

Flamma uses your trained text classifier, conversation rules, and a local skin
information library. It explains dermatitis, atopic dermatitis, contact
dermatitis, lichen planus, psoriasis, rosacea, and hives (urticaria). It also
explains the normal-skin screening label. If you ask **What is this disease?**
before providing a disease name or a photo result, Flamma offers condition
buttons for general information. It does not identify a disease from that
question alone. Photo screening still supports the image model's six classes.

The new explanations use American Academy of Dermatology information about
[atopic dermatitis](https://www.aad.org/public/diseases/eczema/types/atopic-dermatitis),
[contact dermatitis](https://www.aad.org/public/diseases/eczema/types/contact-dermatitis),
and [hives](https://www.aad.org/public/diseases/a-z/hives-overview).

Reports of warning signs can interrupt screening with advice to seek medical
attention. The checks distinguish some negated reports and general questions
from current symptoms. They run before text-model loading and follow
[AAD rash warning-sign guidance](https://www.aad.org/public/everyday-care/itchy-skin/rash/rash-101).
These checks are rules for an academic prototype; they still need clinician
review and do not provide a diagnosis or a validated triage assessment.

If a new photo is rejected or the image service is unavailable, Flamma clears
the active photo prediction. Follow-up replies explain that the latest photo
was not classified. Earlier photos and results remain in the saved chat.
A normal-skin match does not confirm healthy skin or rule out other conditions.
The active image classifier has an OOD gate and a shared confidence threshold;
it does not implement a separately calibrated normal-skin safety check.

## 3. Find and manage your chats

Your conversations and photos save automatically. Refresh the page or restart
the app, then open it in the **same browser at http://127.0.0.1:5000** to continue.

- Click **New conversation** to start a separate chat.
- Use **Search conversations** in the sidebar to search names and messages.
- Click an old conversation to read it and continue where you left off.
- Click **···** beside a conversation to **Rename**, **Export text**, or **Delete** it.
- Click **Clear history** to remove all your saved chats and photos. The app asks
  before deleting anything.
- On a phone or narrow window, use the menu button at the top to open history.

History is stored locally on this computer. Each browser has its own history;
there is no account or cloud sync. Clearing browser cookies removes that
browser's access to its saved chats. Text exports contain messages, with photo
attachments marked in the text.

History stays on this computer until you delete it; there is no automatic
expiry. Current chat replies do not print your messages or screening state to
service logs. Logs produced by older versions may still contain those details.
Clear history removes saved chats and photos, but does not remove old service
logs or text files you exported.

## 4. Stop the app

Open PowerShell and run:

```powershell
cd "C:\flamma chatbot"
powershell -ExecutionPolicy Bypass -File .\stop.ps1
```

This stops both services. Closing the browser or PowerShell window leaves
the services running.

## Share a link with your groupmates

Your groupmates can use Flamma in their browsers without installing anything.

### Step 1: Connect your computer to the internet

Keep your computer switched on and awake while you or your groupmates use
the online link. Your groupmates can use a different Wi-Fi network or mobile data.

### Step 2: Open PowerShell in the project folder

Open **PowerShell**, paste this command, and press **Enter**:

```powershell
cd "C:\flamma chatbot"
```

### Step 3: Start online sharing

Paste this command and press **Enter**:

```powershell
powershell -ExecutionPolicy Bypass -File .\share.ps1
```

This starts both services if needed, downloads the official Cloudflare tool
once, and checks that the online link responds. Wait until you see
**Send this link to your groupmates:** followed by an
**https://...trycloudflare.com** address. The link is also saved automatically
under **Open Flamma online** at the top of this README. Reopen this README
if your editor is showing an older copy.

### Step 4: Open the link

Click **Open Flamma** at the top of this README, or copy the full address
printed in PowerShell and paste it into your browser's address bar.

Use the **https://...trycloudflare.com** address for online access.
**http://127.0.0.1:5000** opens Flamma only on the computer running it.

### Step 5: Share it and try the chatbot

Copy the online address and send it to your groupmates. They just open it
in a browser on their phone or computer; no installation is needed.

1. Type **Hello, I have an itchy rash on my arm**, then press **Enter**.
2. To upload a photo, type **Can I upload an image?**
3. Click **Choose photo**, select a JPG, PNG, or WebP smaller than 10 MB,
   and click **Send**.
4. After the image result, ask **What does this result mean?**

Each browser has its own history. Chats and photos are stored on your
computer, and the link sends web traffic through Cloudflare. Anyone with
the link can use the app, so share it with your group only.

### Step 6: Stop online sharing

When you are finished, run this command in PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File .\stop-sharing.ps1
```

This disables the online link and marks it as stopped in this README.
Flamma stays available locally at **http://127.0.0.1:5000**.
To stop both sharing and the app services, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\stop.ps1
```

### Step 7: Access it again later

Repeat Steps 2 and 3. A new sharing session creates a **new link**, and this
README updates with that address. Copy the new link for your groupmates;
the previous session's link will no longer work. If sharing is already
running, `share.ps1` shows the same active link.

This is a temporary demo link. For more about its behavior, see
[Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/).

### If the online page does not open

1. Check that your computer is on, awake, and connected to the internet.
2. Run `share.ps1` and copy the address it prints.
3. If it still does not load, run `stop-sharing.ps1`, then `share.ps1` again.
4. Use the new link and resend it to your groupmates.
5. If sharing fails to start, open `.logs\share.error.log` to see the error.

## First-time setup on another computer

Collaborators can get the complete project from
[shinowski/chat-bot-thesis](https://github.com/shinowski/chat-bot-thesis).
Install Git, then open PowerShell and run:

```powershell
git clone https://github.com/shinowski/chat-bot-thesis.git "C:\flamma chatbot"
cd "C:\flamma chatbot"
```

Choose a different destination if that folder already exists. If you already
have a clone, save or commit your local edits, then run `git pull --ff-only`
inside it to get the latest `main` version. Continue with setup below.

You need **Python** and **Node.js** installed. Copy both project folders and
the files beside them, keeping this layout:

```text
flamma chatbot/
  Flamma/
  Image/
  requirements.txt
  start.ps1
  stop.ps1
```

Open PowerShell and run the following commands. Change the first path if you
saved the project somewhere else:

```powershell
cd "C:\flamma chatbot"
if (!(Test-Path ".\Flamma\venv\Scripts\python.exe")) { python -m venv Flamma\venv }
.\Flamma\venv\Scripts\python.exe -m pip install -r requirements.txt
cd .\Flamma\frontend
npm.cmd install
npm.cmd run build
cd ..\..
```

Wait for each command to finish. Then follow **Step 1: Start the app** above.
Install the text model once while connected to the internet:

```powershell
cd "C:\flamma chatbot"
.\Flamma\venv\Scripts\python.exe -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

Normal chat loads this cached model locally and does not check Hugging Face
on every restart. Startup begins loading it in the background; a message may
need to wait if startup is still in progress. A missing model produces a setup
error instead of repeated download attempts. Text requests have a 60-second
browser timeout, and photo requests have a 120-second timeout. If a request
times out, your draft is restored. You can resend an unchanged draft using its
original request ID, or reload the conversation to check for a saved reply.

## If something goes wrong

The image backend has been updated to commit
[`267ae33`](https://github.com/jrjrspnl/thesis-backend/commit/267ae33).
Flamma continues to use its local chatbot. Normal startup and photo screening
do not need a Gemini API key.

The backend also includes an optional `/api/chat` endpoint for Gemini. It is
not used by the current chat interface. To configure that endpoint later,
install its optional dependencies:

```powershell
cd "C:\flamma chatbot"
.\Flamma\venv\Scripts\python.exe -m pip install -r .\Image\thesis-backend\requirements-chat.txt
```

Configure `GEMINI_API_KEY` locally in the environment before restarting the
image service. `GEMINI_MODEL` can override its default model. Follow
[Google's Gemini API setup instructions](https://ai.google.dev/gemini-api/docs/api-key)
for the key; keep it out of source code and Git.

### Evaluate the text model used by the app

The app and semantic evaluations use the same model setting. The active-model
manifest at `Flamma/artifacts/active_intent_model.json` selects the trained
English candidate. Without a manifest, the app uses the original
`Flamma/semantic_classifier.pkl`. To override selection or roll back, set
`FLAMMA_INTENT_MODEL` before starting the app and evaluating it; relative paths
resolve from the `Flamma` folder. The original model is preserved.

```powershell
cd "C:\flamma chatbot"
.\Flamma\venv\Scripts\python.exe -B .\Flamma\eval\final_evaluation.py
```

The evaluation saves `Flamma/eval/results/intent-evaluation.json`, including
the selected model's path and checksum, dependency versions, per-intent
metrics, and predictions. These are text-intent results, not evidence of
medical safety or image diagnostic accuracy. Image accuracy, false-normal
results, skin-tone performance, and rejection of unsupported diseases need
a separate labeled dataset and clinical review. The skin prefilter's
thresholds also remain unvalidated. Existing pickle models can emit a
scikit-learn version warning; matching the model's training environment or
retraining in a recorded environment remains necessary for reproducibility.

### Train another English chatbot candidate

Training uses the fictional patterns in `data/intents.json` and
`data/training_supplement.json`. The active v5 also uses 480 fictional body-area
examples from `data/english_location_supplement.json` and 524 broader English
examples from `data/english_intent_supplement.json`, supplied with
`--supplement`. Training does not use saved conversations or images.
Patterns are normalized the same way as chat messages; duplicates are removed
and conflicting labels are excluded. Classes are balanced during fitting.
Similar templates stay in the same validation group so a body-part or number
variation cannot appear on both sides of the split. The existing 130-case
benchmark is excluded from fitting and used after model settings are chosen.
It has been reused for successive model comparisons, so it is an engineering
benchmark, not an untouched final academic or clinical validation set.

Give each candidate a new filename to keep the active model safe:

```powershell
cd "C:\flamma chatbot"
.\Flamma\venv\Scripts\python.exe -B .\Flamma\train_semantic.py --supplement .\Flamma\data\english_location_supplement.json --supplement .\Flamma\data\english_intent_supplement.json
```

The adjacent `.metadata.json` report contains source checksums, package
versions, validation results, and the comparison with the active model.
Training caches embeddings locally for repeated runs. Inspect the report and
run the chatbot regression tests before selecting a candidate. Selection
requires a passing comparison report and matching model checksum; restart
Flamma to load the selected model. `--activate` can select a newly trained
candidate after its comparison passes. For rollback, set
`FLAMMA_INTENT_MODEL=semantic_classifier.pkl` and restart.

The v3 run improved intent accuracy from 80/130 (61.5%) to 119/130 (91.5%).
The active v5 uses 6,405 unique fictional examples and grouped validation,
scoring 123/130 (94.6%) with macro F1 0.948, compared with v4's
120/130 (92.3%) and macro F1 0.926. Its location precision remains 0.643
and recall 0.900 on ten authored location examples; mistakes remain.
The original checkpoint, v3, and v4 remain available.
These are text-intent results on a small, authored benchmark;
they do not establish medical or image accuracy. Training improves message
recognition; explanations still use the existing skin-information library
and conversation rules.

The English conversation rules understand additional shorthand, a fortnight,
questions about triggers and spread, and choices such as **the third one**.
They keep a product mentioned in a question separate from medication actually
used, preserve the affected area and rash duration when discussing a cream,
and handle **I don't remember which cream I used** without skipping another
unanswered screening question. Courtesy replies retain a pending product question.
An educational medicine-warning question receives conditional information;
reports of current warning symptoms still take priority.

The active v4 passed all 68 existing conversation turns and all 41 turns in
14 newly authored development scenarios. The latter improved from 18/41
before the routing fixes to 41/41; these scenarios informed development and
are not independent validation. Reports are saved in
`Flamma/eval/results/english-v4-conversations.json` and
`Flamma/eval/results/english-v4-challenges.json`.

Follow-up handling also separates explicitly stated rash details and treatment
use in one message. For example, **My rash is on my arm for two weeks and I
used a cream for three days** records two weeks as the rash timeframe and
three days as the treatment timeframe. **Both** answers an immediately
preceding choice of affected areas, and **the second one** answers a duration
choice while preserving its unit. These choices expire when the topic changes.
Known product references do not repeatedly ask for the same name. When an
unknown product was used, Flamma asks for its name before recording the usage
and keeps that usage separate from the rash timeframe. Explicit non-use is
recorded as none. The original messages stay in history.

Personal questions such as **Is this my skin conditon?** or **Do I have
rosacea?** explain that a chat and screening photo cannot confirm a diagnosis.
**Is it treatable?**, **Is it curable?**, and **Can it be managed?** retrieve
management information for the condition being discussed. After a rejected
photo, a condition named by the user can still be discussed as general
information; it does not become the photo's result. Explicit questions about
that rejected photo remain unable to receive condition-specific care.
Condition overviews show a management summary; detailed care appears when
asked for, with one **General care** section.

The six authored diagnosis-follow-up scenarios improved from 6/16 to 16/16
turns. Reports are in `Flamma/eval/results/diagnosis-followups-before.json`
and `diagnosis-followups-after.json`; these are development checks, not
clinical validation. A simulated-photo browser test also covers the rejected
photo, named rosacea, diagnosis question, and treatability question after reload.

Treatability and curability questions now use brief, condition-specific answers
with source links, reviewed on 2026-10-15. **What can I do next?** gives general
self-care steps and asks the next missing screening detail, rather than
repeating the full treatment section. A **Treatment options for ...** follow-up
opens detailed care when requested. The six additional authored care scenarios
improved from 8/17 to 17/17 turns; reports are saved as
`Flamma/eval/results/concise-care-before.json` and `concise-care-after.json`.

Known rosacea spellings such as **roscea** are understood without altering
unlisted medicine names. **How about roscea** and **What about rosacea?** switch
the information topic while preserving the preceding question, including a
brief treatability or curability answer. A subject change does not confirm a
diagnosis or overwrite an accepted photo label. When rosacea is discussed for
a concern on the buttocks, Flamma notes that rosacea mainly affects the face
and the described concern needs assessment; it does not assume the same cause
or give facial-care steps for that site. The five authored subject-switch
scenarios improved from 5/13 to 13/13 turns, with reports in
`Flamma/eval/results/topic-switch-before.json` and `topic-switch-after.json`.

Specific unknown answers such as **I can't remember when it started** mark
only that screening detail as unknown. **I don't know how long it's been
there** does not skip an unanswered location. Forgetting a product name in
a suitability question does not record medication use.
Progress reports such as **It is getting better today** or **The itching has
stopped** are stored separately from the original rash duration and included
in summaries as the user's words. They do not establish recovery or a diagnosis.
Not using or getting a treatment no longer negates a nearby warning symptom;
an actual symptom denial still receives conditional information.

The 12 new authored progress/uncertainty scenarios improved from 10/23 to
23/23 turns (`Flamma/eval/results/progress-uncertainty-before.json` and
`progress-uncertainty-after.json`). These changes fix dialogue state and
negation handling; they preceded the subsequent v5 classifier training. These
development checks do not replace clinical validation.

After a treatment report, the reply shows the recorded rash details separately
from the treatment details. The photo step offers **Choose photo** and **Text
only**, so continuing the chat does not require an upload.

The 12 newly authored follow-up scenarios improved from 15/26 to 26/26 turns;
they are development checks, not independent validation. Reports are in
`Flamma/eval/results/followups-before.json` and `followups-after.json`.

| Problem | What to do |
| --- | --- |
| PowerShell says **already running** | Open http://127.0.0.1:5000. To restart the app, follow Step 4, then Step 1. |
| PowerShell says **unrecognized service** | Another program is using port 5000 or 8000. Close that program, then start Flamma again. |
| The browser cannot open the page | Wait a moment and refresh. If it still fails, check the error logs below. |
| The chatbot cannot reach the image classifier | Check `.logs\image.error.log`, then stop and restart both services. |
| Python environment not found | Complete the first-time setup above. |

Error logs are in `C:\flamma chatbot\.logs`. Open `flamma.error.log` or
`image.error.log` in a text editor to see what happened.
