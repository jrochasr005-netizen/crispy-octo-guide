# How to install this tool (beginner guide)

No coding experience needed. Follow these steps in order — each one tells you
exactly what to click or type. Total time: about 20–30 minutes.

This tool runs on your own computer (Windows or Mac). It is not an app you
download from an app store — it's a small program you run from a text window
called a **terminal**. Don't worry: you'll only ever copy and paste a few
commands.

---

## Step 1 — Install Python (the program that runs the tool)

Python is free software from python.org. This tool is written in Python.

**Windows:**
1. Go to https://www.python.org/downloads/ and click the big yellow
   **Download Python** button.
2. Open the downloaded file.
3. **IMPORTANT:** on the first screen, tick the checkbox that says
   **"Add Python to PATH"** before clicking Install. If you miss this,
   the commands below won't work.
4. Click **Install Now** and wait for it to finish.

**Mac:**
1. Go to https://www.python.org/downloads/ and click **Download Python**.
2. Open the downloaded `.pkg` file and click through the installer.

---

## Step 2 — Open a terminal

This is the text window where you'll paste commands.

- **Windows:** press the Windows key, type `powershell`, press Enter.
- **Mac:** press Cmd+Space, type `terminal`, press Enter.

Check Python works — paste this and press Enter:

```
python --version
```

You should see something like `Python 3.12.x`. (On Mac, if that says
"command not found", try `python3 --version` — and use `python3` instead of
`python` in every command below.)

---

## Step 3 — Download this project

In the same terminal window, paste these two lines (press Enter after each):

```
git clone https://github.com/jrochasr005-netizen/crispy-octo-guide.git
cd crispy-octo-guide
```

If the first line says "git is not recognized" / "command not found":
- **Windows:** install Git from https://git-scm.com/download/win (just click
  Next through everything), then close and reopen PowerShell and try again.
- **Mac:** the terminal will offer to install "command line developer tools" —
  click Install, wait, then try again.

(Alternative without Git: on the GitHub page for this project, click the green
**Code** button → **Download ZIP**, unzip it, then in the terminal type
`cd ` followed by a space and drag the unzipped folder into the terminal
window, and press Enter.)

---

## Step 4 — Install the tool's two helper packages

Paste:

```
pip install -r requirements.txt
```

(If that fails on Mac, use `pip3` instead of `pip`.)

---

## Step 5 — Test it (free, no keys needed)

Paste:

```
python -m affiliate_engine.generate config.example.json --dry-run
```

If you see draft posts appear on screen, **the install worked.** 🎉
This test mode is free and doesn't contact anyone.

---

## Step 6 — Get your Claude API key (needed for real posts)

The tool uses Claude (an AI) to write your posts. That needs an API key —
think of it as a password that also tracks a small usage bill (typically a few
cents per batch of posts).

1. Go to https://console.anthropic.com and sign up.
2. Add a small amount of credit (e.g. $5) under **Billing**.
3. Go to **API Keys** → **Create Key**. Copy it somewhere private
   (a password manager is ideal).

**Golden rule: never paste any API key into a chat, an email, a text file in
this project, or anywhere public.** You'll only type it into your own terminal,
like this:

- **Windows (PowerShell):** `$env:ANTHROPIC_API_KEY = "paste-your-key-here"`
- **Mac:** `export ANTHROPIC_API_KEY="paste-your-key-here"`

This only lasts while that terminal window is open — that's a good thing.
You'll do the same with your Postiz key when you get to posting:

- **Windows:** `$env:POSTIZ_API_KEY = "paste-postiz-key-here"`
- **Mac:** `export POSTIZ_API_KEY="paste-postiz-key-here"`

(The Postiz key comes from Postiz → **Settings → Public API**. This is NOT the
AI key you may have entered inside Postiz — different thing.)

---

## Step 7 — Set up your products

1. Make your own copy of the example config:
   - **Windows:** `copy config.example.json config.json`
   - **Mac:** `cp config.example.json config.json`
2. Open `config.json` in Notepad (Windows) or TextEdit (Mac) and replace the
   sample product with the products you're an affiliate for, including **your
   real affiliate links** (you get those from each affiliate program after
   they approve you).

---

## Step 8 — The everyday routine

Once installed, this is all you do (each command is explained in README.md):

```
python -m affiliate_engine.generate config.json      # 1. AI writes drafts
python -m affiliate_engine.review                    # 2. You approve/reject each one
python -m affiliate_engine.schedule                  # 3. Spread them safely over days
python -m affiliate_engine.postiz --channels config.json          # 4. Preview
python -m affiliate_engine.postiz --channels config.json --send   # 5. Send to Postiz
```

Then check your Postiz calendar — your approved posts are queued to publish to
your connected accounts at safe times.

---

## If you get stuck

The two most common problems:

| You see... | Fix |
|---|---|
| `python is not recognized` | Reinstall Python and tick **Add Python to PATH** (Step 1). |
| `No module named pydantic` | Run Step 4 again (`pip install -r requirements.txt`). |

Everything else: copy the exact error message and ask for help with it.
