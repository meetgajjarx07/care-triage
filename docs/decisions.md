# Decision records

Five decisions that shaped the pipeline, with what would make me change them. Numbers are from `models/eval.json`, `models/metrics.json`, `models/retrieval_eval.json` and `out/run.json` as of the 2026-10-18 run.

## 1. Embeddings plus logistic regression as the classifier, not the LLM

**Context.** Seven categories, three sentiments, 110 labelled emails. I tried three things with 5-fold cross-validation repeated four times: TF-IDF word and character n-grams into logistic regression, llama3.2 zero-shot with the label names, and nomic-embed-text vectors into logistic regression.

**Decision.** Embeddings into logistic regression. Cross-validated accuracy 77% (plus or minus 9 points across folds) against 59% for TF-IDF and 54% for the zero-shot model on the same held-out split. Out-of-fold accuracy on all 110 is 73%, macro F1 0.72. Sentiment: 81% cross-validated against 64% for TF-IDF.

**Consequences.** One embedding call per email, shared with the retriever, then a model that trains in under a second and predicts in well under a millisecond. The model is under-confident (expected calibration error 0.30), so I put confidence bands on top and checked them out-of-fold: high is right 88% of the time, medium 79%, low 52%. The weak classes are safety concern (recall 0.56) and positive feedback (0.57).

**What would change it.** Several hundred labels per class, at which point a fine-tuned small encoder is worth trying. Or a category set that changes weekly, where the zero-shot model's lack of training would matter more than its accuracy.

## 2. Rules route, the model does not

**Context.** Some emails must never get a templated reply: a guarantee claim with scan results, a safety question with medical context, a customer who is unhappy about results, a cancellation. The cost of getting these wrong is a lost customer or a health risk, not a slightly off reply.

**Decision.** Four plain rules in `config/triage.yaml`, evaluated in order, on the predicted category, the predicted sentiment and a regular expression over the body. The model supplies the inputs; it does not decide who picks up the phone. On the current run 34 of 110 emails route to a consultant: 15 guarantee claims, 10 cancel intents, 6 medical, 3 unhappy with results.

**Consequences.** Anyone can read why an email was routed, and the reason is logged on every row and every trace. Changing a rule is a YAML edit plus a parity test, not a retrain. The rules inherit the classifier's mistakes: a guarantee claim predicted as a results question with neutral sentiment would get a draft. That is what the confidence band and the human review are for.

**What would change it.** Evidence from the review log that a rule fires wrongly more often than it fires rightly. The Activity page is where that evidence would show up.

## 3. BM25 plus dense retrieval fused with reciprocal rank fusion

**Context.** Seven short policy documents, 56 chunks. Customers write "my scan got worse"; the policy says "DEXA". Customers also write exact tokens like "Prop 65" or "RMA" that an embedding model blurs.

**Decision.** Both retrievers, fused by reciprocal rank fusion with k=60, plus a category boost worth one first place vote toward the documents a category usually lives in.

**Consequences.** On the proxy label (the expected document for the true category appears in the top 4), plain BM25 scores 89%, dense alone 81%, the hybrid without the boost 83%. BM25 alone wins at top 4 on this corpus, and the Model quality check list shows that as a failed check rather than hiding it. The hybrid is slightly ahead at top 1 (65.5% against 63.6%) and in MRR (0.751 against 0.746), which is the wording gap cases. With the boost, using the classifier's predicted category as the pipeline does, 98% of emails get the right document in the top 4; the two misses are classifier misses, not retriever misses. Dense costs about 9 ms per query against 0.2 ms for BM25.

**What would change it.** A knowledge base ten times this size, where sparse retrieval starts missing paraphrases, or per email relevance judgements that show the dense ranks are not earning their keep. The production version of this pattern at my previous job used Pinecone or Qdrant with a reranker; here that would be more machinery than the data justifies.

## 4. Deterministic QA rules instead of an LLM judge

**Context.** The drafting model is a 3B parameter model. It is mostly fine and sometimes confidently wrong. One draft told a customer that AlgaeCal Plus contains strontium. It does not; Strontium Boost is a separate product.

**Decision.** Seven rules taken straight from the system prompt, three of them critical: grounded (no number or instruction word outside the retrieved notes or the customer's email), no refund promise, no medical directive. Then answers first, under 140 words, plain tone, signed as Customer Care. A critical fail sets the score to 0. Sentence level embedding support is shown as a soft signal next to it.

**Consequences.** On the current run 13 of 76 drafts score below 100 and 10 of those are critical: 7 grounding, 2 refund wording, 1 medical directive. The checks run in under a millisecond and every fail has a visible reason. Two things I tried and dropped: scoring every content word against the notes flagged 75 of 76 drafts, because a polite reply uses words the policy does not; asking llama3.2 to judge its own drafts missed the strontium error, flagged sentences copied straight from the notes, and looped. The rules catch the dangerous class of error, not every error.

**What would change it.** A larger judge model running locally with a measured false negative rate on a labelled set of bad drafts. Until that measurement exists, a rule I can read beats a score I cannot explain.

## 5. No auto send. A person reads every draft.

**Context.** The drafts are good enough to save an agent time and not good enough to speak for the company unread. The review log makes this measurable.

**Decision.** The pipeline writes drafts to a file and a dashboard. Nothing in this repository can send an email. Every draft carries its provenance (which policy sections, which model, how long), its QA score and its sentence support, and sits in the Inbox until someone approves, edits or discards it. Corrections are logged for the next training run and do not touch the live model.

**Consequences.** The outcome for the team is time saved per email and a weekly picture of what customers write about, not headcount removed. The review log doubles as the labelling tool, which is how the model improves without a separate annotation project.

**What would change it.** Months of review data showing a category where approved-as-written is near 100% and the critical QA fail rate is near zero. Even then, the first step would be pre-filling the agent's reply box, not sending.
