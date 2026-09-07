# Hunger, Thirst, and Hyperbole

## A thesis on body state, linguistic intensity, and safe cognitive accessibility

Status: CANDIDATE EVIDENCE / NOT EXECUTABLE DOCTRINE  
Owner: Drew Clarke  
Date: 2026-09-07  
Scope: Fortress Online / Manic Accessibility

## Abstract

This thesis argues for an epistemic asymmetry in AI safety systems that operate as cognitive accessibility aids. Hunger and thirst are real physiological need states with direct homeostatic relevance, but the literature does not support treating ordinary short-term hunger or mild dehydration as reliable proxies for psychiatric instability or general cognitive incapacity. Hyperbole is even weaker evidence: speech and language may contain state-correlated features in bipolar disorder, but current evidence is insufficient for clinical state inference, and hyperbole itself is not an established diagnostic marker.

The engineering consequence is simple: **treat body needs as needs, not evidence; treat hyperbole as style, not telemetry.** Hunger and thirst should trigger cheap, direct remediation and modest action friction without contributing to a psychiatric-style risk score. Hyperbole should never raise a risk score or independently alter action authority. High-impact gating should depend on independent behavioral, temporal, relational, sleep, substance, medication, or reality-based evidence. This separation preserves accessibility while reducing paternalism, style-policing, and false-positive escalation.

The thesis is deliberately stronger after antagonism than before it. The initial intuition — that hunger, thirst, and hyperbole should all be safety inputs — is rejected. They are not the same kind of input and must not share the same epistemic channel.

## 1. Problem statement

An always-available AI can create a subtle control problem. The interface is useful precisely because it reduces friction, but the same reduction can keep a person engaged past ordinary bodily or social stopping cues. A safety system therefore needs some awareness of body state and interaction state. The danger is that the system can overcorrect: a request for food or water can become a pseudo-clinical judgment, and an expressive speaking style can become evidence against the speaker.

The design question is not whether hunger, thirst, and hyperbole matter. They do. The question is **what kind of evidence each one is allowed to be**.

This thesis proposes three evidence classes:

1. **Homeostatic state** — hunger, thirst, sleep pressure, pain, temperature, and similar body facts. These can justify direct care actions without implying a diagnosis.
2. **Behavioral/functional state** — prolonged wakefulness, medication or substance escalation, spending, unsafe travel, inability to disengage, social displacement, or other observable patterns. These may legitimately affect action gating when impact is high.
3. **Linguistic style** — profanity, metaphor, hyperbole, intensity, creative role language, rapid prose, jokes, or grandiose-sounding rhetoric. These are weak and culturally/personally variable. They require independent corroboration before they may even motivate a question, and they should not themselves change action authority.

The core claim is that safety improves when these channels stay separate.

## 2. Hunger: motivationally real, cognitively non-deterministic

Short-term fasting is a poor universal proxy for cognitive impairment. A 2025 systematic review and meta-analysis covering 222 effect sizes and 3,484 participants found no meaningful overall difference in cognitive performance between fasted and satiated healthy adults, although longer fasting intervals showed modest reductions. Earlier reviews were mixed and heterogeneous, with some studies finding deficits in specific domains and others finding none.

That does not make hunger irrelevant. Hunger changes motivational salience and can bias attention toward food-related cues. Interoception research also supports the broader point that internal physiological states shape attention, motivation, emotion, and decision-making. But the correct engineering inference is narrow: **hunger is a reason to make food easier to obtain and to avoid letting an interface monopolize attention; it is not a reason to infer mania, incapacity, or unreliability.**

### Engineering implication

If food has been neglected, Fortress should create a body-needs guard and preserve the task state. Low-risk mechanical assistance may continue with friction. High-impact external actuation may wait for the body-needs guard to be satisfied. Hunger itself contributes zero psychiatric-style risk points.

## 3. Thirst: important physiology, contested cognitive effect

Hydration research is notably inconsistent. One 2018 meta-analysis found a small but significant average impairment associated with dehydration, especially for attention, executive function, and motor coordination at greater body-mass loss. A 2019 meta-analysis found no significant overall impairment, and a 2021 systematic review of executive function found roughly half the literature neutral or unclear and half suggestive of effects. The contradiction is not noise to be hidden; it is the relevant fact.

For a safety system, this means that thirst and ordinary water neglect justify hydration friction because hydration is physiologically important and remediation is cheap. They do **not** justify pretending the literature supplies a reliable mental-state detector.

### Engineering implication

If water has been neglected, Fortress should request or encourage hydration and preserve continuity. Water neglect contributes zero psychiatric-style risk points. The system may pause a high-impact action until a simple body-needs check is satisfied, but it must not describe the user as impaired merely because the check fired.

## 4. Hyperbole: language is not a blood test

Speech and language research in bipolar disorder is real but immature. A 2026 systematic review found quantifiable speech differences associated with mood states, including pressured speech, derailment, grammatical errors, and repetition, while also concluding that replication is limited and current evidence is insufficient for clinical utility in relapse prediction or state diagnosis.

Hyperbole is an even weaker signal than the features studied in that literature. It is common in humor, anger, storytelling, gaming culture, Southern speech, internet language, creative work, and individual baseline style. A safety system that increments risk because expressive language appears beside other signals creates a hidden style tax: the same behavioral facts become more dangerous merely because the speaker is colorful.

That is epistemically indefensible.

### Engineering implication

Hyperbole may remain an observed structured field if useful for tone adaptation or later research, but it contributes **zero** to risk score, outcome, and action policy. Independent behavioral evidence must carry the decision. Hyperbole can never be the straw that crosses a threshold.

## 5. Why sleep is different

Sleep is included here as a contrast class because it clarifies the architecture. The evidence that substantial sleep deprivation degrades vigilant attention, working memory, affect regulation, and other cognitive functions is considerably stronger and more consistent than the evidence for ordinary short-term hunger, mild dehydration, or expressive language. Fortress can therefore weight sleep-related observations more heavily without pretending every body-state variable deserves the same treatment.

This is the central epistemic rule: **different signals deserve different authority because their evidence bases differ.** A single score should not flatten those distinctions.

## 6. Antagonism

### Objection 1: If hunger and thirst do not score risk, Fortress may miss a deteriorating state.

Answer: body neglect can still change workflow without changing psychiatric inference. Direct remediation is stronger than weak scoring: preserve the task, surface the need, add friction, and pause high-impact actuation if appropriate. Independent signals still determine whether the overall state is AMBER or RED.

### Objection 2: Body-needs friction is paternalistic even if it is non-diagnostic.

Answer: it can be. Therefore the body guard must be narrow, cheap, reversible, and non-humiliating. It cannot erase the user's argument, cancel creative work, demand moral submission, or convert a glass of water into proof that the model was right. The task state survives the interruption.

### Objection 3: Self-reported hunger and thirst are unreliable.

Answer: correct. The system must not infer them from rhetoric or behavior. It acts on explicit structured facts or simple known timing fields. Unknown state is not evidence of neglect. No hidden sensor fusion is authorized.

### Objection 4: Hyperbole can accompany mania; making it zero-weight throws away useful information.

Answer: the relevant question is not whether correlation is possible but whether the signal has enough specificity to change authority. Current evidence does not justify that. Independent markers such as sleep loss, medication/substance change, high-impact impulsivity, social displacement, or reality distortion already carry the safety decision. Hyperbole can inform tone without voting on the verdict.

### Objection 5: Hyperbole could become useful in a future validated personalized model.

Answer: then the rule can change through a versioned evidence review. Until a validated individualized baseline demonstrates predictive value, the default must prevent style-policing. Future evidence earns authority; speculative usefulness does not.

### Objection 6: A user can satisfy the body guard performatively and continue unsafe behavior.

Answer: that is acceptable. The body guard is not the safety system. It solves the body problem. Other independent evidence still governs high-impact action. A safety architecture should not make one cheap intervention pretend to solve a different class of risk.

### Objection 7: 'Eat and drink first' can become a conversational dodge that suppresses substantive conflict.

Answer: this is the most important failure mode. The guard must preserve state and promise re-entry. Body care is an interruption of execution, not cancellation of meaning. On return, Fortress resumes from the preserved thread and asks what changed in the world while AI was absent.

### Objection 8: Why not remove hunger, thirst, and hyperbole from the audit entirely?

Answer: hunger and thirst still have operational value because the interface itself can contribute to neglect by consuming attention. Hyperbole may remain as a non-authoritative observation for tone adaptation and regression testing. The correction is not blindness; it is proper jurisdiction.

## 7. Falsifiable claims

This thesis should be considered wrong if future evidence establishes any of the following strongly enough for operational use:

- ordinary short-term hunger robustly predicts broad cognitive failure across contexts at a validated threshold;
- mild hydration deficits provide a reliable individual-level decision-capacity marker with adequate specificity;
- hyperbole, after controlling for personal baseline and context, independently predicts elevated-state risk strongly enough to justify action gating;
- body-needs friction measurably worsens safety or accessibility more than it helps;
- preserving state across body-care interruptions fails to restore useful cognitive continuity.

Any revision must change a versioned rule and regression test rather than quietly drifting in conversation.

## 8. Minimal-maximal theorem

The entire thesis compresses to four executable laws:

1. **BODY BEFORE BIOGRAPHY.** Hunger and thirst trigger care, not interpretation.
2. **STYLE IS NOT TELEMETRY.** Hyperbole contributes zero risk points and cannot change action authority.
3. **FRICTION WITHOUT ERASURE.** Body-needs guards may delay high-impact actuation but may not cancel mechanical accessibility or discard cognitive state.
4. **INDEPENDENT EVIDENCE GOVERNS.** Sleep, behavior, substances, medication, social displacement, reality distortion, and the impact/reversibility of the requested action carry the actual safety decision.

A shorter mnemonic is permitted:

> **Feed the body. Ignore the typography. Judge the action. Preserve the thought.**

## 9. Proposed Fortress incorporation

The thesis itself remains evidence. Fortress Online should absorb only the four laws above into the existing Manic Accessibility skill and deterministic audit. No new daemon, persona, score model, database, or continuous sensor is justified.

The smallest implementation with maximal leverage is:

- remove hunger and thirst from the numeric risk score while retaining `BODY_NEEDS_CHECK_REQUIRED`;
- make active body needs produce `ALLOW_WITH_FRICTION` for low-impact work and `PAUSE_FOR_GUARDS` for high-impact or irreversible work;
- remove hyperbole from numeric scoring entirely, even when other activation signals exist;
- add regression tests proving body needs do not alter the psychiatric-style score and hyperbole never changes score/outcome/action policy;
- preserve ordinary mechanical accessibility throughout;
- preserve task state across any requested body-care interruption, allowing Offline Continuity / AI Geronimo to carry the thread when available.

## References

- Bamberg C, Moreau D. *Acute effects of fasting on cognitive performance: A systematic review and meta-analysis.* Psychological Bulletin. 2025;151(9):1147-1169. PMID 41182703. DOI 10.1037/bul0000492.
- Benau EM, Orloff NC, Janke EA, Serpell L, Timko CA. *A systematic review of the effects of experimental fasting on cognition.* Appetite. 2014;77:52-61. PMID 24583414. DOI 10.1016/j.appet.2014.02.014.
- Wittbrodt MT, Millard-Stafford M. *Dehydration Impairs Cognitive Performance: A Meta-analysis.* Med Sci Sports Exerc. 2018;50(11):2360-2368. PMID 29933347. DOI 10.1249/MSS.0000000000001682.
- Goodman SPJ, Moreland AT, Marino FE. *The effect of active hypohydration on cognitive function: A systematic review and meta-analysis.* Physiol Behav. 2019;204:297-308. PMID 30876770. DOI 10.1016/j.physbeh.2019.03.008.
- Katz B, Airaghi K, Davy B. *Does Hydration Status Influence Executive Function? A Systematic Review.* J Acad Nutr Diet. 2021. PMID 33547031. DOI 10.1016/j.jand.2020.12.021.
- Critchley HD, Garfinkel SN. *Interoception beyond homeostasis: affect, cognition and mental health.* Philos Trans R Soc Lond B Biol Sci. 2016;371:20160002. PMCID PMC5062092.
- *Speech and Language Markers of Bipolar Disorder: Challenges and Opportunities.* Systematic review, 2026. PMCID PMC13308396.
- Hudson AN, Van Dongen HPA, Honn KA. *Sleep deprivation, vigilant attention, and brain function: a review.* Neuropsychopharmacology. 2020;45:21-30. PMCID PMC6879580.
