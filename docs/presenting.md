# Presenting the Walkthrough in four minutes

About a minute on camera, then one page of the app, the Walkthrough, which is the page `streamlit run app/dashboard.py` opens on. Five stops, a Next button, one live run. About 494 spoken words: 3:40 at 135 words a minute, 3:48 read slowly to a camera, which leaves room. The shape: who you are and what you build, the bank's inbox, one email and the question, four steps done live, the one the system got wrong, the same sorter on reviews with the SQL behind it, what changed, the honest number, day one.

## Before recording

Once: install the requirements and Ollama, then `ollama pull nomic-embed-text` and `ollama pull llama3.2`.

Every time:

1. Start Ollama. Run `streamlit run app/dashboard.py`. The browser opens on the Walkthrough. Set the browser zoom to 125% and switch on Focus, top right, so the side menu is hidden for the recording.
2. On stop 1 press "Let them arrive" once as a warm-up, so the models are loaded. Press Next to stop 2, keep "Charged twice this month" selected, press "Handle this email" once as a warm-up. The first draft loads the model and is slow. Note how long the draft card takes; that is the pause in Part 3.
3. Delete `out/reviews.jsonl` if it exists and reload, so the review counters start at zero. On stop 1 press Reset under the feed so it is ready to arrive again. Press Back to stop 1.
4. If Ollama is not running, stop 2 says so and the other four stops still work. Say the words anyway and point at the step cards, or open any email in the Inbox and show its steps there.

## Part 1. Who I am, and the bank (0:00)

**Show.** Camera. Look at the lens. Calm, your own pace.

**Say.** Hi, I'm Khushi Gor. I'm an AI engineer, and I've just finished my master's in computer science at Lakehead. I worked at Must IT Services for a year and a half, mostly for clients in finance, building AI they could actually run.

**Say.** The project I'm most proud of was for a banking client. They had an inbox problem: every email opened, sorted and answered by hand. I built a system that sorted those emails before anyone opened them, found the policies that applied, and wrote a first draft of the reply. I can't show you that system, so I rebuilt the same idea for AlgaeCal's customer care.


## Part 2. The pile (0:48)

**Show.** Screen. Stop 1. Jean's email on the left. Click "Let them arrive" on "110 other emails" and let them land while you ask the question.

**Say.** Imagine an email from Jean saying she was charged twice this month, and 110 other emails waiting behind it. The question was: could we sort them before someone opens them, and give that person a head start on the reply?


## Part 3. Four steps, live (1:05)

**Show.** Next. Stop 2. Click "Handle this email" as you say it. Point at each card as it fills: sorted, policy, who handles it, draft, check.

**Say.** When I click Handle this email, the system works out what the email is about and how the customer feels. Jean is billing, and unhappy. Then it pulls only the AlgaeCal policies that apply to her email. Then it decides who should handle it. If it's about scan results or someone's health condition, it skips the draft and goes straight to a Bone Health Consultant. Otherwise it writes a short draft from those policies only.

**Say.** I gave the draft rules. It must stay inside AlgaeCal's policies, it must not promise a refund, it must not give medical advice, and it must answer the actual question. And a human makes the final decision.


## Part 4. The one it got wrong (1:55)

**Show.** Next. Stop 3. Hover the highlighted sentence on "tapering", point at the red Fail row. Slow down.

**Say.** The part I'm most proud of is the time it made something up. Muriel wanted to switch from Basic to Plus, and the draft told her to taper her dose. That is not in any AlgaeCal policy. I'd built a check that asks every sentence of the draft where it came from. That sentence had no answer, so the draft failed, and a person wrote the reply.


## Part 5. Your reviews (2:25)

**Show.** Next. Stop 4. Point at the red bars, then the reply card.

**Say.** I pointed the same sorter at a hundred reviews, written to match what AlgaeCal's public ones say. Every number on that page is a SQL query, and in my sample it found price complaints climbing. A bad review about a scan or a side effect never gets a public reply; a consultant calls instead.


## Part 6. What changed, and the honest number (2:49)

**Show.** Next. Stop 5. Four numbers, the accuracy table.

**Say.** What changed: agents get each email sorted with a draft to edit, the team lead sees the whole week on one screen, and the customer gets a reply a person has checked. The honest number: it was right about three times out of four on emails it had never seen. Useful, but not something to trust blindly, so a person always decides.

**Show.** Camera. Stop recording two seconds after the last word.

**Say.** If I joined, on day one I'd work with your consultants to label real emails, because their judgement is what this system needs to learn. Your values say do the right thing even if it hurts. For me, showing you the draft that invented something is exactly that. Thank you for watching.

## Shot list

| Time | On screen | Action |
|---|---|---|
| 0:00 | Camera | Part 1: who you are, what you build, the bank, why this rebuild. About a minute. |
| 0:48 | Stop 1 | Jean's email, click "Let them arrive", the question over the landing emails. |
| 1:05 | Stop 2 | Click "Handle this email". Talk through the wait. Point at the ticks. |
| 1:55 | Stop 3 | Muriel's draft. Hover the sentence, point at the Fail row, then the scorecard. |
| 2:25 | Stop 4 | The rising-theme notice, the red bars, the drafted public reply. |
| 2:49 | Stop 5 | Four numbers, the honest-number table, then camera. |
| 3:16 | Camera | Last paragraph. Done by about 3:40. |

## If it runs long

In this order, until the timed run is under 3:45:

1. Part 5: drop the whole reviews part and press Next through stop 4 without comment.
2. Part 3: drop "Jean is billing, and unhappy."
3. Part 1: drop "and I've just finished my master's in computer science at Lakehead".

## Plain words

Keep these off camera: embedding, classifier, logistic regression, retrieval, RAG, vector, BM25, LLM, cosine, threshold, pipeline, latency, out-of-fold, calibration. Say "the system" or "the sorter". The AI phrases in the script are "a small model I trained" and "a language model", both in Part 3. If someone asks which one, it is llama3.2 running on the laptop with no internet, and the check in Part 4 is rules, not a model. Do not say the system "understands" emails or "knows" the policy. It sorts, finds and drafts. A person decides. Do not apologise for the error in Part 4. It is the point of the story.

If they want more after the video: the Live triage page takes any email typed into it, the Inbox has all 110 emails with every step, and Model facts has the honest numbers, including the ones that are not flattering.
