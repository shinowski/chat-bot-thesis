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

If the command says **already running**, open the same browser address.

Chats and photos save automatically. Use **Search conversations** to find an
old chat, or click **···** beside it to rename, export its text, or delete it.
Use the same browser and address to keep accessing your history after a restart.

To stop both services, run this from `C:\flamma chatbot`:

```powershell
powershell -ExecutionPolicy Bypass -File .\stop.ps1
```

For setup, stopping the app, and troubleshooting, follow the
[step-by-step instructions in the main README](../README.md).
