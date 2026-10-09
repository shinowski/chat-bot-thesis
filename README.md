# Flamma: Chatbot + Image Classifier

Chat about your skin concern, upload a photo, and see the image model's result.

## Open Flamma online

<!-- flamma-sharing:start -->
**[Open Flamma](https://situation-plant-guestbook-blvd.trycloudflare.com)**

Current online address: [https://situation-plant-guestbook-blvd.trycloudflare.com](https://situation-plant-guestbook-blvd.trycloudflare.com)

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

You can write naturally: common typos and shorthand such as **rashesh**,
**2wks**, **idk**, and **can i sent pictuer** are recognized. If the wording
is unclear, the chatbot may ask a follow-up question.

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
The first chat message may take longer while the text model loads or downloads.

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

| Problem | What to do |
| --- | --- |
| PowerShell says **already running** | Open http://127.0.0.1:5000. To restart the app, follow Step 4, then Step 1. |
| PowerShell says **unrecognized service** | Another program is using port 5000 or 8000. Close that program, then start Flamma again. |
| The browser cannot open the page | Wait a moment and refresh. If it still fails, check the error logs below. |
| The chatbot cannot reach the image classifier | Check `.logs\image.error.log`, then stop and restart both services. |
| Python environment not found | Complete the first-time setup above. |

Error logs are in `C:\flamma chatbot\.logs`. Open `flamma.error.log` or
`image.error.log` in a text editor to see what happened.
