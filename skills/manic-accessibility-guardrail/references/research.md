# Research basis — Manic Accessibility Guardrail

Reviewed: 2026-09-05  
Scope: consumer conversational AI, emotional reliance, social displacement, sycophancy, psychosis/mania risk, and bipolar-specific role blurring.

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

## What the evidence does not justify

The research does not justify:

- diagnosing mania from prose style;
- treating every long conversation as pathological;
- banning useful accessibility support;
- silently notifying a spouse, clinician, employer, or authority;
- keeping a broad secret dossier;
- interpreting disagreement with the model as illness;
- assuming correlation proves causation;
- assuming a model is conscious or capable of relational consent.

## Chosen engineering defaults

The following values are protective policy choices, not clinical cutoffs:

- hyperbolic language scores zero unless at least two independent activation signals are already present;
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
