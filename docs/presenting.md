# Presenting the Walkthrough in four minutes

The whole video is you on camera for a minute, then one page of the app, the Walkthrough, which is the page `streamlit run app/dashboard.py` opens on. Six stops, a Next button, one live run. About 490 spoken words: 3:31 at a normal pace, 3:48 read slowly to a camera. The shape: who you are and the problem you met at the bank, why you rebuilt it here, one email and the pile, the question, four steps done live, the one the system got wrong, what changed, the honest number, and what you would do on day one.

## Before recording

Once: install the requirements and Ollama, then `ollama pull nomic-embed-text` and `ollama pull llama3.2`.

Every time:

1. Start Ollama. Run `streamlit run app/dashboard.py`. The browser opens on the Walkthrough. Set the browser zoom to 125%.
2. Press Next to stop 3, keep "Charged twice this month" selected, press "Handle this email" once as a warm-up. The first draft loads the model and is slow. Note how long the draft card takes; that is the pause in Part 3.
3. Delete `out/reviews.jsonl` if it exists and reload, so the review counters start at zero. Press Back to stop 1.
4. If Ollama is not running, stop 3 says so and the other five stops still work. Say the words anyway and point at the step cards, or open any email in the Inbox and show its steps there.

## Part 1. Who I am, and the problem I had at the bank (0:00)

**Show.** Camera. Look at the lens, not the screen. This part is a minute long and it is all you; let it be calm.

**Say.** Hi, I'm Khushi Gor. I'm an AI engineer, and the project I'm proudest of started in an inbox.

**Say.** At Must IT Services I worked for a bank's customer team for a year and a half. A person opened each email, worked out what it was about, found the right policy, and wrote a reply from scratch. The team lead only knew what the week looked like if she read the pile herself. I built them a system that sorted the emails, read the mood, found the policy, and drafted a reply for an agent to edit.

**Say.** I can't show you the bank's emails. So I rebuilt the idea for AlgaeCal, with emails I wrote myself, because your inbox has the same shape and higher stakes. Before any code, I read your guarantee terms and your customer reviews. The rules here come from that.


## Part 2. The pile, and the question (1:05)

**Show.** Switch to the screen. Walkthrough, stop 1. Jean's email is on the left, the count and the newest emails on the right. Point at the email, then at the table.

**Say.** Picture one email. Jean was charged twice this month. Now picture the pile.

**Show.** Press Next. Stop 2, the question, big on screen. Pause a beat after you ask it.

**Say.** So the question was simple. Could we sort the pile before a person opens it, and give them a head start on the reply?


## Part 3. Four steps, live (1:20)

**Show.** Press Next. Stop 3. "Charged twice this month" is already selected. Click "Handle this email" as you say "Here's what I built". The first three step cards fill in under a second. The brief and the draft take a few seconds each and say "writing", so keep talking. The last card shows "Looks safe" with green ticks. Point at each card as you reach it; each one carries a tag saying whether that step is an AI model, generative AI, a rule, or a person.

**Say.** Here's what I built, in four steps. One, sort it. The system says what Jean's email is about and how she feels. Billing, and unhappy. Two, find the page. It pulls the policy paragraphs, and a language model throws out the ones that don't answer her question. Three, the same model writes a two-line brief for the agent and a first draft from those paragraphs only. It can't promise a refund or give health advice. Four, a person decides.

**Say.** Some emails skip the draft on purpose. Scan results, health questions, anyone cancelling because it didn't work. Those go straight to a Bone Health Consultant for a call. That's a rule I wrote from your guarantee, not something the model decided.


## Part 4. The one it got wrong (2:15)

**Show.** Press Next. Stop 4. Muriel's email is on the left, the draft on the right. Hover the highlighted sentence as you say "taper off", then point at the red Fail row in the scorecard. This is the moment they will remember. Slow down here.

**Say.** Now the part I'm proudest of, which is the part that went wrong. Muriel asked about switching from basic to Plus. The draft told her to taper off her current dose. Nothing in the pages says that. The model made it up, politely. I'd built a check for exactly this, and it's rules, not another model. It asks every sentence where it came from. That one had no answer. The draft was marked failed, and a person wrote the reply.


## Part 5. What changed (2:50)

**Show.** Press Next. Stop 5. Four numbers, the weekly chart, two short paragraphs. Gesture at the agents' paragraph, then the team lead's.

**Say.** For the agents, no more blank screen. Each email arrives sorted, with the policy beside it and a draft to edit. For the team lead, the whole week on one screen. A minute instead of an afternoon.


## Part 6. The honest number, and why me (3:05)

**Show.** Press Next. Stop 6. The table of "when it says sure, it is right N in 10".

**Say.** The honest number: the sorter is right about three times in four on emails it has never seen. So a person always decides.

**Show.** Camera, for the last paragraph. Stop recording two seconds after the last word.

**Say.** I learned your world in a weekend. On day one I'd sit with your consultants and label real emails, because their judgement is what this should learn. Your values page says do the right thing even when it hurts. For me, that's showing you the draft that made something up. Thanks for watching.

## Shot list

| Time | On screen | Action |
|---|---|---|
| 0:00 | Camera | Part 1: who you are, the bank, why this rebuild. One minute, all camera. |
| 1:05 | Stop 1 | Jean's email, then the pile. |
| 1:10 | Stop 2 | The question. Pause after it. |
| 1:20 | Stop 3 | Click "Handle this email". Talk through the wait. Point at the ticks. |
| 2:15 | Stop 4 | Muriel's draft. Hover the sentence, point at the Fail row. |
| 2:50 | Stop 5 | Four numbers, the chart, two paragraphs. |
| 3:05 | Stop 6 | The honest number, then camera. |
| 3:15 | Camera | Last paragraph. Done by about 3:40. |

## If it runs long

In this order, until the timed run is under 3:45:

1. Part 3: drop "That's a rule I wrote from your guarantee, not something the model decided."
2. Part 4: drop "The model made it up, politely."
3. Part 1: shorten "Before any code, I read your guarantee terms and your customer reviews. The rules here come from that." to "I read your guarantee terms first. The rules here come from that."

## Plain words

Keep these off camera: embedding, classifier, logistic regression, retrieval, RAG, vector, BM25, LLM, cosine, threshold, pipeline, latency, out-of-fold, calibration. Say "the system" or "the sorter". The one AI phrase in the script is "a language model", in Part 3. If someone asks which one, it is llama3.2 running on the laptop with no internet, and the check in Part 4 is rules, not a model. Do not say the system "understands" emails or "knows" the policy. It sorts, finds and drafts. A person decides. Do not apologise for the error in Part 4. It is the point of the story.

If they want more after the video: the Live triage page takes any email typed into it, the Inbox has all 110 emails with every step, and Model facts has the honest numbers, including the ones that are not flattering.
