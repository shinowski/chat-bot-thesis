# Flamma chatbot

This folder contains the chatbot and its web interface. The image classifier
is in the sibling `Image` folder.

## Start the chatbot and image classifier together

Open **PowerShell** and run:

```powershell
cd "C:\flamma chatbot"
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

Wait a moment, then open **http://127.0.0.1:5000**. Describe your skin concern,
answer the questions, and use the image button to upload a photo.

You can upload at any time by clicking **Choose photo** or the image button.
Try **Explain simply**, **Summarize our conversation**, or **What next?**.
Use **Skip the questions** to pause screening and **Continue screening** to resume.
After a photo result or discussing a condition, ask **What is this disease?**
for an explanation. You can also ask a name directly, such as **What is contact
dermatitis?**. Without a known condition, Flamma offers disease choices.

English input supports reviewed spelling corrections, body-area and symptom
words, written timeframes, and follow-ups such as **and rosacea**, **same question
for psoriasis**, and **put that in plain English**. Original messages remain the
recorded evidence. Unrecognized medicine names are not guessed or spell-corrected.
The vocabulary changes use the existing intent model; they do not add new photo
classes or establish a diagnosis. Development checks are in
`eval/vocabulary_cases.json` and `test_vocabulary.py`.

Corrections retain complete timeframes such as **twenty-one days**, **half an
hour**, and **2-3 weeks**, plus body-area directions such as **upper back** and
**inner thigh**. Different possible areas or durations prompt a choice. Progress
reports such as **the rash has cleared up** or **the rash has come back today**
are recorded separately from the original onset and medication history.

Photo references such as **my pictures**, **these pics**, and **my images** use
the latest photo result even after another condition has been discussed. The
chat remembers whether information came from photo screening or a named
condition. Naming the same condition as a photo match starts an educational
discussion; an explicit photo question can return to the photo context. If a
different condition is named for an uploaded photo, the reply explains the
photo's actual screening match separately from that general information.

Questions such as **how long this usually last?**, **when will it clear up?**,
and **how much time does it take to heal?** retrieve source-linked information
about the condition's usual course. They preserve the reported rash duration
and do not set a personal recovery deadline. Asking how long to use a medicine
remains separate from asking about the condition's course.

## Train the English intent classifier

From this folder, use the installed Python environment:

```powershell
.\venv\Scripts\python.exe -u -B train_semantic.py --supplement data/english_location_supplement.json --supplement data/english_intent_supplement.json
```

Training selects the next unused artifact version and retains earlier models.
It uses fictional text examples, never saved chats or photos. Template families
stay together in validation, including changes to body area, symptoms, timeframe,
severity, and treatment product. A candidate must improve both accuracy and macro
F1 on the existing 130-message benchmark before activation is allowed. It also
needs conversation checks; the benchmark measures text intents, not clinical
accuracy or image recognition. Training does not add medical knowledge or drug
recommendations.
The 130-message benchmark has been reused across model versions and must not
be presented as an untouched final evaluation. Grouped validation reports one
fold out of five, not a five-fold mean.

The v5 candidate was trained on 6,405 unique examples, including 524 new English
examples. Its benchmark accuracy was 123/130 (94.6%), compared with v4's 120/130
(92.3%). Reproducible training details and the comparison are recorded in
`artifacts/intent_v5.metadata.json`; additional authored intent checks are in
`eval/results/intent-v5-generalization.json`. `artifacts/active_intent_model.json`
selects the model used when the chatbot starts.
Startup checks the selected artifact against its manifest checksum before
deserialization; `/health` reports the actual loaded artifact checksum.

For presentation evidence, known limitations, and a panel demonstration script,
see [Defense notes](DEFENSE_NOTES.md).

If the command says **already running**, open the same browser address.

Chats and photos save automatically. Use **Search conversations** to find an
old chat, or click **···** beside it to rename, export its text, or delete it.
Use the same browser and address to keep accessing your history after a restart.
Storage is on the Flamma server, including when a different device opens the
interface. This prototype has browser-session isolation, no account sign-in,
and no application-level encryption of stored records. Same-profile users and
people with server-file access may read the records. Deletion removes application
records for that browser; exports and backups are separate copies.

To stop both services, run this from `C:\flamma chatbot`:

```powershell
powershell -ExecutionPolicy Bypass -File .\stop.ps1
```

For setup, stopping the app, and troubleshooting, follow the
[step-by-step instructions in the main README](../README.md).
