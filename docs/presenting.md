# Presenting the Walkthrough in four minutes

The whole video is you on camera for a minute, then one page of the app, the Walkthrough, which is the page `streamlit run app/dashboard.py` opens on. Seven stops, a Next button, one live run. About 505 spoken words: 3:44 at 135 words a minute, 3:53 read slowly to a camera. The shape: who you are and what you did for clients, the problem at the bank, why you rebuilt it here, one email and the pile, the question, four steps done live, the one the system got wrong and what responsible AI looks like, what changed, the same sorter on reviews, the honest number, and day one.

## Before recording

Once: install the requirements and Ollama, then `ollama pull nomic-embed-text` and `ollama pull llama3.2`.

Every time:

1. Start Ollama. Run `streamlit run app/dashboard.py`. The browser opens on the Walkthrough. Set the browser zoom to 125%.
2. Press Next to stop 3, keep "Charged twice this month" selected, press "Handle this email" once as a warm-up. The first draft loads the model and is slow. Note how long the draft card takes; that is the pause in Part 3.
3. Delete `out/reviews.jsonl` if it exists and reload, so the review counters start at zero. Press Back to stop 1.
4. If Ollama is not running, stop 3 says so and the other five stops still work. Say the words anyway and point at the step cards, or open any email in the Inbox and show its steps there.

## Part 1. Who I am, and the problem at the bank (0:00)

**Show.** Camera. Look at the lens, not the screen. This first minute is all you, so let it be calm and unhurried.

**Say.** Hi, I'm Khushi Gor. For a year and a half I was an AI engineer at Must IT Services. Our clients were mostly in finance, and my job was making AI they could actually run. I started on the OpenAI platform and ended up building AI that ran inside the client's own walls, so their data never left.

**Say.** One client, a bank, had a problem that lived in an inbox. Every email was opened, sorted and answered by hand. I built them a system that sorted the emails, read the mood, found the policy, and drafted a reply for an agent to edit.

**Say.** I can't show you theirs. So I studied your guarantee, your products and your reviews, and built a small version for your inbox.


## Part 2. The pile, and the question (0:56)

**Show.** Switch to the screen. Walkthrough, stop 1. Jean's email is on the left, the count and the newest emails on the right. Point at the email, then at the table.

**Say.** Picture one email. Jean was charged twice this month. Now picture the pile.

**Show.** Press Next. Stop 2, the question, big on screen. Pause a beat after you ask it.

**Say.** Could we sort the pile before a person opens it, and give them a head start on the reply?


## Part 3. Four steps, live (1:10)

**Show.** Press Next. Stop 3. "Charged twice this month" is already selected. Click "Handle this email" as you say "Here's what I built". The first three step cards fill in under a second. The brief and the draft take a few seconds each and say "writing", so keep talking. The last card shows "Looks safe" with green ticks. Point at each card as you reach it; each one carries a tag saying whether that step is an AI model, generative AI, a rule, or a person.

**Say.** Here's what I built, in four steps. One, sort it: what it's about, how she feels. Billing, and unhappy. Two, find the page. It pulls your policy, and a language model throws out the paragraphs that don't answer her. Three, the same model writes a two-line brief and a first draft, from your policy only. It can't promise refunds or give health advice. Four, a person decides.

**Say.** Scan results, health questions, anyone cancelling because it didn't work: those skip the draft and go straight to a Bone Health Consultant.


## Part 4. The one it got wrong (1:50)

**Show.** Press Next. Stop 4. Muriel's email is on the left, the draft on the right. Hover the highlighted sentence as you say "taper off", then point at the red Fail row in the scorecard. On the last two sentences, gesture at the scorecard: that is the log and the guardrails they are hearing about. Slow down here.

**Say.** Now the part I'm proudest of, because it went wrong. Muriel asked about switching from basic to Plus. The draft told her to taper off her dose. Nothing in your pages says that. A check I built, rules, not another model, asks every sentence where it came from. That one had no answer. The draft failed, a person wrote the reply. That's responsible AI in practice. It never sends, every step is logged, and a person has the last word.


## Part 5. What changed (2:25)

**Show.** Press Next. Stop 5. Four numbers, the weekly chart, two short paragraphs. Gesture at the agents' paragraph, then the team lead's.

**Say.** For the agents, no more blank screen. Each email arrives sorted, with a draft to edit. For the team lead, the whole week on one screen.


## Part 6. Your reviews (2:37)

**Show.** Press Next. Stop 6. The themes-by-week chart on the left with the amber "Price and value is rising" notice above it; a two-star review on the right with the model's one-line read and the drafted public reply marked QA 100. Point at the tall red bars for "climbing", at the notice for "the week it happens", and at the reply card for the last sentence.

**Say.** Then I pointed the same sorter at reviews, a hundred written to match what your public ones say. Same four steps, and every number on the page is a SQL query, shaped for your warehouse. It found price complaints climbing in the last three weeks. The business should hear that the week it happens, not at quarter end. And a bad review about a scan or a side effect never gets a public reply; a consultant calls instead.


## Part 7. The honest number, and day one (3:12)

**Show.** Press Next. Stop 7. The table of "when it says sure, it is right N in 10".

**Say.** The honest number: it's right about three times in four on emails it has never seen. So a person always decides.

**Show.** Camera, for the last paragraph. Stop recording two seconds after the last word.

**Say.** I learned your world in a weekend. On day one I'd sit with your consultants and label real emails, because their judgement is what this should learn. Your values page says do the right thing even when it hurts. For me, that's showing you the draft that made something up. Thanks for watching.

## Shot list

| Time | On screen | Action |
|---|---|---|
| 0:00 | Camera | Part 1: who you are, the clients, the bank, why this rebuild. A minute, all camera. |
| 0:56 | Stop 1 | Jean's email, then the pile. |
| 1:02 | Stop 2 | The question. Pause after it. |
| 1:10 | Stop 3 | Click "Handle this email". Talk through the wait. Point at the ticks. |
| 1:50 | Stop 4 | Muriel's draft. Hover the sentence, point at the Fail row, then the scorecard. |
| 2:25 | Stop 5 | Four numbers, the chart, two paragraphs. |
| 2:37 | Stop 6 | The rising-theme notice, the red bars, the drafted public reply. |
| 3:12 | Stop 7 | The honest number, then camera. |
| 3:21 | Camera | Last paragraph. Done by about 3:44. |

## If it runs long

In this order, until the timed run is under 3:45:

1. Part 7: drop "On day one I'd sit with your consultants and label real emails, because their judgement is what this should learn."
2. Part 6: drop "Same four steps, and every number on the page is a SQL query, shaped for your warehouse."
3. Part 1: drop "I started on the OpenAI platform and ended up building AI that ran inside the client's own walls, so their data never left."

## Plain words

Keep these off camera: embedding, classifier, logistic regression, retrieval, RAG, vector, BM25, LLM, cosine, threshold, pipeline, latency, out-of-fold, calibration. Say "the system" or "the sorter". The one AI phrase in the script is "a language model", in Part 3. If someone asks which one, it is llama3.2 running on the laptop with no internet, and the check in Part 4 is rules, not a model. Do not say the system "understands" emails or "knows" the policy. It sorts, finds and drafts. A person decides. Do not apologise for the error in Part 4. It is the point of the story.

If they want more after the video: the Live triage page takes any email typed into it, the Inbox has all 110 emails with every step, and Model facts has the honest numbers, including the ones that are not flattering.
