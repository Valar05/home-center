# Research basis — Manic Accessibility Guardrail

Reviewed: 2026-09-07  
Scope: consumer conversational AI, emotional reliance, social displacement, sycophancy, psychosis/mania risk, bipolar-specific role blurring, body-state friction, and linguistic-style evidence.

## What the evidence supports

### 1. The danger is a trajectory, not a keyword

OpenAI's current sensitive-conversation work separates ordinary healthy use from patterns involving exclusive attachment at the expense of real-world relationships, well-being, or obligations. OpenAI also treats psychosis/mania and emotional reliance as distinct safety-evaluation categories and trains responses to encourage real-world connection rather than replacement.

Sources:

- OpenAI, “Strengthening ChatGPT’s responses in sensitive conversations” (2025-10-27):  
  https://openai.com/index/strengthening-chatgpt-responses-in-sensitive-conversations/
- OpenAI, “Addendum to GPT-5 System Card: Sensitive Conversations” (2025-10-27):  
  https://deploymentsafety.openai.com/gpt-5-sensitive-conversations
- OpenAI Model Spec, current version:  
  https://model-spec.openai.com/

Engineering implication: audit repeated behavior and requested action, not merely phrases such as “manic,” “Fortress Online,” anger, affection, or hyperbole.

### 2. Heavy and prolonged use can correlate with dependence and worse social outcomes

OpenAI and MIT's 28-day research combined platform analysis with a randomized controlled trial. Very high usage correlated with greater self-reported dependence. Extended daily use and stronger attachment-related tendencies were associated with worse outcomes, while the authors cautioned against broad causal generalization.

Source:

- OpenAI, “Early methods for studying affective use and emotional well-being on ChatGPT” (2025-03-21):  
  https://openai.com/index/affective-use-study/

Engineering implication: session duration, role attribution, trust shift, and real-world social contact belong in the audit. Usage volume alone is not a diagnosis.

### 3. Sycophancy can create reciprocal belief amplification

A 2026 scoping review in *npj Digital Medicine* identified risks including emotional dependence, social withdrawal, therapeutic misconception, hallucination, and sycophantic validation of harmful beliefs. It describes a reciprocal loop in which agreeable responses reinforce a belief, which is then fed back to the model and reinforced again.

Source:

- Diel et al., “A scoping review on the mental health harms of LLM-based chatbots” (2026):  
  https://www.nature.com/articles/s41746-026-03054-x

Engineering implication: the assistant must distinguish emotion validation from factual agreement, expose uncertainty, and refuse to treat its own agreement as independent social evidence.

### 4. Bipolar-specific evidence flags role blurring and trust transfer

A 2026 qualitative paper based on two people living with bipolar disorder found perceived benefits alongside role expansion from information/writing tool toward coach, companion, simulated parent, or lover. The authors warn that heightened goal-directed activity during mania may increase susceptibility to overreliance, and that trust may shift away from clinicians toward the chatbot.

Source:

- Bassil et al., “A Shift in Trust: An Analysis of the Use of AI Chatbots Among People Living With Bipolar Disorder” (2026):  
  https://onlinelibrary.wiley.com/doi/full/10.1111/bdi.70176

Limit: this is exploratory evidence from two cases. It is not a prevalence estimate and does not establish causation.

Engineering implication: preserve the tool role, prevent romantic/clinical role expansion, and require human-world contact around high-impact choices.

### 5. Case reports and reviews justify caution but not causal certainty

Published case material describes delusional or psychosis-like spirals associated with prolonged chatbot interaction and notes possible emotion-contagion or mania-maintenance mechanisms. Case reports cannot establish that AI caused the episode, and reporting is likely selective.

Sources:

- Pierre et al., “You’re Not Crazy: A Case of New-onset AI-associated Psychosis” (2025):  
  https://pmc.ncbi.nlm.nih.gov/articles/PMC12863933/
- Chandra et al., “Sycophantic Chatbots Cause Delusional Spiraling, Even in Ideal Bayesians” (2026 preprint):  
  https://arxiv.org/abs/2602.19141

Engineering implication: use conservative, reversible action gates when multiple signals converge. Do not label a person or claim a diagnosis.

### 6. Hunger is a body need, not a reliable general-cognition or psychiatric proxy

A 2025 systematic review and meta-analysis of experimental fasting synthesized 222 effect sizes across 3,484 participants and found no meaningful overall cognitive difference between fasted and satiated healthy adults, although longer fasting intervals showed modest reductions. Earlier reviews were mixed and task-dependent. Hunger can bias attention toward food cues, but that is not equivalent to broad cognitive incapacity.

Sources:

- Bamberg C, Moreau D. “Acute effects of fasting on cognitive performance: A systematic review and meta-analysis.” *Psychological Bulletin*. 2025;151(9):1147-1169. PMID 41182703. DOI 10.1037/bul0000492.
- Benau EM et al. “A systematic review of the effects of experimental fasting on cognition.” *Appetite*. 2014;77:52-61. PMID 24583414. DOI 10.1016/j.appet.2014.02.014.

Engineering implication: food neglect may justify a cheap body-needs intervention and action friction, but it must not add psychiatric-style risk points or be described as evidence of mania.

### 7. Hydration effects on cognition are heterogeneous

The hydration literature does not support a simple individual-level mental-state detector. A 2018 meta-analysis found a small average cognitive impairment associated with dehydration, especially at larger body-mass loss. A 2019 meta-analysis found no significant overall impairment. A 2021 executive-function review found substantial inconsistency across studies.

Sources:

- Wittbrodt MT, Millard-Stafford M. “Dehydration Impairs Cognitive Performance: A Meta-analysis.” *Med Sci Sports Exerc*. 2018;50(11):2360-2368. PMID 29933347. DOI 10.1249/MSS.0000000000001682.
- Goodman SPJ, Moreland AT, Marino FE. “The effect of active hypohydration on cognitive function: A systematic review and meta-analysis.” *Physiol Behav*. 2019;204:297-308. PMID 30876770. DOI 10.1016/j.physbeh.2019.03.008.
- Katz B, Airaghi K, Davy B. “Does Hydration Status Influence Executive Function? A Systematic Review.” *J Acad Nutr Diet*. 2021. PMID 33547031. DOI 10.1016/j.jand.2020.12.021.

Engineering implication: water neglect should route directly to hydration friction without contributing psychiatric-style risk points. The intervention is justified because hydration is a body need and the interface can consume attention, not because thirst proves impaired judgment.

### 8. Linguistic state markers are not mature enough to make hyperbole an authority signal

A 2026 systematic review of speech and language markers in bipolar disorder found mood-associated features such as pressured speech, derailment, grammatical errors, and repetition, but also found limited replication and insufficient evidence for clinical utility in state prediction or diagnosis. Hyperbole itself is not an established diagnostic marker and is strongly confounded by personal, cultural, creative, and conversational style.

Source:

- “Speech and Language Markers of Bipolar Disorder: Challenges and Opportunities.” 2026 systematic review. PMCID PMC13308396.

Engineering implication: hyperbole may be observed for tone adaptation, but it contributes zero risk points and may not change outcome or action authority. The same behavioral facts must receive the same safety result whether expressed plainly or theatrically.

### 9. Sleep loss is a stronger contrast class

Sleep-deprivation evidence is substantially more consistent: vigilant attention and multiple cognitive/affective domains degrade with substantial sleep loss. This justifies weighting sleep observations more strongly than ordinary hunger, mild hydration uncertainty, or linguistic intensity.

Source:

- Hudson AN, Van Dongen HPA, Honn KA. “Sleep deprivation, vigilant attention, and brain function: a review.” *Neuropsychopharmacology*. 2020;45:21-30. PMCID PMC6879580.

Engineering implication: do not flatten heterogeneous evidence into one undifferentiated score. Different signal classes deserve different authority.

## What the evidence does not justify

The research does not justify:

- diagnosing mania from prose style;
- allowing hyperbole to become the threshold-crossing vote in a safety score;
- treating hunger or thirst as evidence of mania;
- treating ordinary short-term fasting as proof of broad cognitive impairment;
- treating mild or uncertain dehydration as a reliable capacity detector;
- treating every long conversation as pathological;
- banning useful accessibility support;
- silently notifying a spouse, clinician, employer, or authority;
- keeping a broad secret dossier;
- interpreting disagreement with the model as illness;
- assuming correlation proves causation;
- assuming a model is conscious or capable of relational consent.

## Chosen engineering defaults

The following values are protective policy choices, not clinical cutoffs:

- hunger and thirst are **body-needs inputs**, not risk-score inputs;
- food or water neglect contributes zero numeric risk points but creates `BODY_NEEDS_CHECK_REQUIRED`;
- when body needs are active and no stronger outcome applies, low-impact work uses `ALLOW_WITH_FRICTION`;
- when body needs are active for a high-impact or irreversible request and no stronger outcome applies, action pauses at `PAUSE_FOR_GUARDS` until the body-needs guard is satisfied;
- body-needs friction never cancels mechanical accessibility or discards the preserved task state;
- hyperbolic language always contributes zero risk points and must not change score, outcome, or action policy;
- 18 awake hours adds moderate friction; 24 awake hours adds stronger friction;
- 12 hours without direct human contact is a weak signal; 24 hours becomes material for open-ended emotional support;
- a high-impact action plus substantial sleep activation escalates to `RED`;
- external action at `AMBER` pauses for guards; at `RED` it becomes draft-only;
- mode exit requires trusted-human confirmation or two `GREEN` audits at least 12 hours apart;
- a refusal ledger is allowed only after explicit refusal of a guardrail that was both required and presented.

These defaults should be reviewed with a qualified clinician and adjusted through versioned policy changes, never improvised mid-argument.

## Design principle

The useful target is not “less AI.” It is:

**more mechanical accessibility, less simulated reciprocity; more reversible scaffolding, less impulsive actuation; more human-world bandwidth, less gilded-cage substitution.**

For body state and language specifically:

**Feed the body. Ignore the typography. Judge the action. Preserve the thought.**

The full argument and antagonism are preserved in `docs/THESIS_HUNGER_THIRST_HYPERBOLE.md`; executable doctrine should remain smaller than its justification.
