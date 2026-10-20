# Presenting the Walkthrough in four minutes

About a minute on camera, then one page of the app, the Walkthrough, which is the page `streamlit run app/dashboard.py` opens on. Five stops, a Next button, one live run. About 490 spoken words: 3:38 at 135 words a minute, 3:46 read slowly to a camera, which leaves room. The shape: who you are and what you build, the bank's inbox, one email and the question, four steps done live, the one the system got wrong, the same sorter on reviews with the SQL behind it, what changed, the honest number, day one.

## Before recording

Once: install the requirements and Ollama, then `ollama pull nomic-embed-text` and `ollama pull llama3.2`.

Every time:

1. Start Ollama. Run `streamlit run app/dashboard.py`. The browser opens on the Walkthrough. Set the browser zoom to 125% and switch on Focus, top right, so the side menu is hidden for the recording.
2. On stop 1 press "Let them arrive" once as a warm-up, so the models are loaded. Press Next to stop 2, keep "Charged twice this month" selected, press "Handle this email" once as a warm-up. The first draft loads the model and is slow. Note how long the draft card takes; that is the pause in Part 3.
3. Delete `out/reviews.jsonl` if it exists and reload, so the review counters start at zero. On stop 1 press Reset under the feed so it is ready to arrive again. Press Back to stop 1.
4. If Ollama is not running, stop 2 says so and the other four stops still work. Say the words anyway and point at the step cards, or open any email in the Inbox and show its steps there.

## Part 1. Who I am, and what I build (0:00)

**Show.** Camera, about a minute. Look at the lens, not the screen. Calm; this is the part they judge you on as a person.

**Say.** Hi, I'm Khushi Gor. I'm an AI engineer, and I've just finished my master's in computer science at Lakehead. I spent a year and a half at Must IT Services building AI that clients actually ran, mostly in finance: classification and sentiment pipelines, retrieval systems, guarded generation. I started on the OpenAI platform and ended up deploying AI inside the client's own environment.

**Say.** The project I'm proudest of started with one of them, a bank with an inbox problem. Every email was opened, sorted and answered by hand, and nobody could see the week. I built the system that sorted them, read the mood, found the policy, and drafted the reply for an agent to edit. I can't show you theirs, so I rebuilt it for AlgaeCal in a weekend, from your guarantee, your products and your reviews.


## Part 2. The pile (1:01)

**Show.** Switch to the screen. Walkthrough, stop 1. Jean's email on the left, the count on the right, the question, then the button "Let them arrive". Click it as you say "Now the pile": fourteen emails land one after another, each sorted, matched to the policy and routed by the real pipeline as it arrives. Ask the question over the top of them landing.

**Say.** Picture one email. Jean was charged twice. Now the pile. The question: could we sort it before a person opens it, and give them a head start on the reply?


## Part 3. Four steps, live (1:15)

**Show.** Press Next. Stop 2. "Charged twice this month" is already selected. Click "Handle this email" as you say "Four steps, live". The first three cards fill in under a second; the brief and the draft say "writing" for a few seconds, so keep talking; the last card shows "Looks safe" with green ticks. Point at each card as you reach it. Each one carries a tag: AI model, generative AI, rule, or person.

**Say.** Four steps, live. One, sort: a small model I trained on labelled emails says what it's about and how she feels. Billing, and unhappy. Two, find the page: search pulls your policy, and a language model throws out the paragraphs that don't answer her. Three, the same model writes a two-line brief and a first draft from those paragraphs only. It can't promise refunds or give health advice. Four, a person decides. Scan results, health questions, anyone cancelling over results skip the draft and go to a Bone Health Consultant.


## Part 4. The one it got wrong (1:55)

**Show.** Press Next. Stop 3. Muriel's email on the left, the draft on the right. Hover the highlighted sentence on "taper off", point at the red Fail row, then at the scorecard for the last sentence. Slow down here.

**Say.** The part I'm proudest of went wrong. Muriel asked about switching from basic to Plus. The draft told her to taper off her dose. Nothing in your pages says that. My check, rules, not another model, asks every sentence where it came from. That one had no answer. The draft failed, a person wrote the reply. It never sends, every step is logged, a person has the last word.


## Part 5. Your reviews (2:25)

**Show.** Press Next. Stop 4. The amber "Price and value is rising" notice and the weekly chart on the left, a two-star review with the model's one-line read and the drafted public reply on the right. Point at the red bars for "climbing", the reply card for the last sentence.

**Say.** Then the same sorter on reviews, a hundred written to match your public ones. One table, shaped for your BigQuery warehouse, and every number on the page is a SQL query I wrote. In my sample it found price complaints climbing in the last three weeks. And a bad review about a scan or a side effect never gets a public reply; a consultant calls.


## Part 6. What changed, and the honest number (2:54)

**Show.** Press Next. Stop 5. Four numbers, two short paragraphs, the table of "when it says sure, it is right N in 10".

**Say.** What changed: agents get each email sorted with a draft to edit, the team lead gets the week on one screen, and the customer gets a reply a person has checked. The honest number: right about three times in four on emails it has never seen. So a person always decides.

**Show.** Camera, for the last half minute. Stop recording two seconds after the last word.

**Say.** If I joined, day one would be with your consultants, labelling real emails, because their judgement is what this should learn. Your values page says do the right thing even when it hurts. For me, that's showing you the draft that made something up. Thanks for watching.

## Shot list

| Time | On screen | Action |
|---|---|---|
| 0:00 | Camera | Part 1: who you are, what you build, the bank, why this rebuild. About a minute. |
| 1:01 | Stop 1 | Jean's email, click "Let them arrive", the question over the landing emails. |
| 1:15 | Stop 2 | Click "Handle this email". Talk through the wait. Point at the ticks. |
| 1:55 | Stop 3 | Muriel's draft. Hover the sentence, point at the Fail row, then the scorecard. |
| 2:25 | Stop 4 | The rising-theme notice, the red bars, the drafted public reply. |
| 2:54 | Stop 5 | Four numbers, the honest-number table, then camera. |
| 3:17 | Camera | Last paragraph. Done by about 3:38. |

## If it runs long

In this order, until the timed run is under 3:45:

1. Part 6: drop "If I joined, day one would be with your consultants, labelling real emails, because their judgement is what this should learn."
2. Part 1: drop "I started on the OpenAI platform and ended up deploying AI inside the client's own environment."
3. Part 5: drop "One table, shaped for your BigQuery warehouse, and every number on the page is a SQL query I wrote."

## Plain words

Keep these off camera: embedding, classifier, logistic regression, retrieval, RAG, vector, BM25, LLM, cosine, threshold, pipeline, latency, out-of-fold, calibration. Say "the system" or "the sorter". The AI phrases in the script are "a small model I trained" and "a language model", both in Part 3. If someone asks which one, it is llama3.2 running on the laptop with no internet, and the check in Part 4 is rules, not a model. Do not say the system "understands" emails or "knows" the policy. It sorts, finds and drafts. A person decides. Do not apologise for the error in Part 4. It is the point of the story.

If they want more after the video: the Live triage page takes any email typed into it, the Inbox has all 110 emails with every step, and Model facts has the honest numbers, including the ones that are not flattering.
