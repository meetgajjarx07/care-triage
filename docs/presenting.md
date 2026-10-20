# Presenting the Walkthrough in four minutes

A word-for-word script for showing Care Triage to people who do not code, with what to have on screen while each part is spoken. It follows the six stops of the Walkthrough page, which is the page the app opens on. About 500 spoken words: 3:36 at a normal pace, 3:52 read slowly.

The shape is simple. One email, the pile it came from, the question, four steps done live, the one the system got wrong, what changed, and an honest number at the end.

## Before you start

Once:

1. Clone or download the repo, then `py -3.12 -m venv .venv`, activate it, `pip install -r requirements.txt`.
2. Install Ollama, then `ollama pull nomic-embed-text` and `ollama pull llama3.2`.

Every time:

1. Start Ollama. Run `streamlit run app/dashboard.py`. The browser opens on the Walkthrough. Set the browser zoom to 125%.
2. Press Next to stop 3, keep "Charged twice this month" selected, and press "Handle this email" once as a warm-up. The first draft loads the model and is slow. Note how long step 4 takes; that is your pause in Part 3.
3. Delete `out/reviews.jsonl` if it exists and reload, so the review counters start at zero. Press Back to stop 1.
4. If Ollama is not running, stop 3 says so. The other five stops work without it. Say the words anyway and point at the step cards, or open any email in the Inbox and show its steps there.

## The script

Each part has two lines: what is on screen, and what you say. Say it the way you would explain it to a friend. Pauses are fine.

### Part 1. Who I am (0:00)

**Show.** Camera. Look at the lens, not the screen.

**Say.** Hi, I'm Khushi Gor. The project I'm proudest of started in an inbox. I spent a year and a half as an AI engineer at Must IT Services, and this was for a bank. I can't show you their emails, so I rebuilt the same idea for AlgaeCal, with emails I wrote myself.

### Part 2. The pile (0:25)

**Show.** Walkthrough, stop 1. Jean's email is on the left, the count and the newest emails on the right. Say the first three sentences at the email, the next two at the table.

**Say.** Picture one email. Jean was charged twice this month. Someone opens it, works out what it's about, finds the right policy, and writes a reply from scratch. Now picture the pile. Every email, every day, the same way. The team lead only knew what the week looked like if she read it herself.

**Show.** Press Next. Stop 2, the question, big on screen. Pause a beat after you ask it.

**Say.** So the question was simple. Could we sort the pile before a person opens it, and give them a head start on the reply?

### Part 3. Four steps (1:05)

**Show.** Press Next. Stop 3. "Charged twice this month" is already selected. Click "Handle this email" as you say "Here's what I built". The first three step cards fill in under a second. The brief and the draft take a few seconds each and say "writing", so keep talking. The last card shows "Looks safe" with green ticks. Point at each card as you reach it. Each card carries a tag saying whether that step is an AI model, generative AI, a rule, or a person.

**Say.** Here's what I built, in four steps, using Jean's email. One, sort it. The system reads the email and says what it's about and how she feels. Billing, and unhappy. Two, find the page. It pulls the paragraphs of policy that might apply, and a language model throws out any that don't actually answer her question. Three, the same model writes a two-line brief for the agent, and a first draft from those paragraphs only. It can't promise a refund and it can't give health advice. Four, a person decides. Nothing is ever sent by the system.

**Say.** Some emails skip the draft on purpose. Scan results, health questions, anyone cancelling because it didn't work. Those go straight to a person for a phone call. That's a rule I wrote, not something the model decided.

### Part 4. The one it got wrong (1:50)

**Show.** Press Next. Stop 4. Muriel's email is on the left, the draft on the right. Hover the highlighted sentence as you say "taper off", then point at the red Fail row in the scorecard. This is the moment they will remember. Slow down here.

**Say.** Now the part I'm proudest of, which is the part that went wrong. Muriel asked about switching from basic to Plus. The draft told her to taper off her current dose. Nothing in the pages says that. The model made it up, politely. I'd built a check for exactly this, and it's rules, not another model. It reads every sentence and asks, where did this come from? That one had no answer. The draft was marked failed, and a person wrote the reply. That check is why I trust the system, and why it never sends anything on its own.

### Part 5. What changed (2:30)

**Show.** Press Next. Stop 5. Four numbers, the weekly chart, two short paragraphs. Gesture at the agents' paragraph, then the team lead's.

**Say.** For the agents, no more blank screen. Each email arrived sorted, with the policy beside it and a draft to edit. For the team lead, the whole week on one screen. What people write about, how they feel, who needs a call. A minute instead of an afternoon.

### Part 6. The honest number (2:50)

**Show.** Press Next. Stop 6. The table of "when it says sure, it is right N in 10".

**Say.** The honest number: the sorter is right about three times in four on emails it has never seen. Good enough to help, not good enough to trust blindly. So a person always decides.

**Show.** Camera, for the last paragraph. Stop recording two seconds after the last word.

**Say.** If I did this at AlgaeCal, my first month would be with your Bone Health Consultants, labelling real emails, because their judgement is what the system should learn. Your values page says do the right thing even when it hurts. For me, that's showing you the draft that made something up. Thanks for watching.

## Shot list

| Time | On screen | Action |
|---|---|---|
| 0:00 | Camera | Part 1. |
| 0:25 | Stop 1 | Jean's email, then the pile. |
| 0:55 | Stop 2 | The question. Pause after it. |
| 1:05 | Stop 3 | Click "Handle this email". Talk through the wait. Point at the ticks. |
| 1:50 | Stop 4 | Muriel's draft. Hover the sentence, point at the Fail row. |
| 2:30 | Stop 5 | Four numbers, the chart, two paragraphs. |
| 2:50 | Stop 6 | The honest number, then camera. |
| 3:05 | Camera | End of Part 6. |

## If it runs long

In this order, until the timed run is under 3:45:

1. Part 3: drop "That's a rule I wrote, not something the model decided."
2. Part 4: drop "and why it never sends anything on its own".
3. Part 3: shorten "and a first draft from those paragraphs only" to "and a first draft".

## Plain words

Keep these off camera: embedding, classifier, logistic regression, retrieval, RAG, vector, BM25, LLM, cosine, threshold, pipeline, latency, out-of-fold, calibration. Say "the system" or "the sorter". The one AI phrase in the script is "a language model", in Part 3. If someone asks which one, it is llama3.2 running on the laptop with no internet, and the check in Part 4 is rules, not a model. Each step card on stop 3 carries a tag saying which is which, so you can point instead of explaining.

Do not say the system "understands" emails or "knows" the policy. It sorts, finds and drafts. A person decides. And do not apologise for the error in Part 4. It is the point of the story.

## If they want more

The Live triage page takes any email typed into it. The Inbox has all 110 emails with every step. Model facts has the honest numbers, including the ones that are not flattering. The README has screenshots of each.
