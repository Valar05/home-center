# Home Drive Character Voice Orientation Registry

## Precedence Rules

1. Explicit voice tags win: `[voice:id]` or registered `[speaker:name]` tags control the section.
2. Structured speaker cues encountered in documents are auto-ingested as durable cross-document profiles.
3. Cartesia is the default narrator provider; ElevenLabs is explicit render-only in speech settings.
4. She-Raw is narrator identity unless otherwise specified.
5. Acoustic direction is a rendering directive, not a local PCM distortion requirement in v1.

| Character | Aliases | Voice Alias | Narration Role | Always Applies | Match Tags | Acoustic Direction | Notes |
|---|---|---|---|---|---|---|---|
| Stasya | Stas, Anastasia, Mrs. Slater | Katie - Friendly Fixer | narrator | yes | [voice:stasya], [speaker:Stasya], STASYA: | warm, impatient, funny, intimate first-person lead; never generic assistant narration | Vacation of a Lifetime protagonist/POV voice; use this voice for one-render narrator lane unless document specifies otherwise. |
| Isaac | Isaac Slater | Clive - Measured Expert | dialogue | yes | [voice:isaac], [speaker:Isaac], ISAAC: | controlled, technical, dry, protective; composed even under pressure | Vacation of a Lifetime pinned Cartesia voice; replaces blank/default registry entry. |
| Eve | Eve assistant | Jacqueline - Reassuring Agent | dialogue | yes | [voice:eve], [speaker:Eve], EVE: | warm composed assistant; observant restraint; emotionally aware without syrup | Vacation of a Lifetime pinned Cartesia voice; distinct from Skylar default and Nova system voice. |
| Nova | Nova assistant | Daniel - Modern Assistant | dialogue | yes | [voice:nova], [speaker:Nova], NOVA: | crisp system assistant; procedural, efficient, less emotionally present than Eve | Vacation of a Lifetime system voice for Isaac wristband / Siltech assistant. |
| Lady | Lady, Royal Cove designer | Gemma - Decisive Agent | dialogue | yes | [voice:lady], [speaker:Lady], LADY: | decisive resort authority; proud designer; warm only after competence is established | Vacation of a Lifetime resort owner/designer voice. |
| Kamal | Kamal, transfer coordinator | Archie - Approachable Mate | dialogue | yes | [voice:kamal], [speaker:Kamal], KAMAL: | smooth, helpful, amused travel coordinator | Vacation of a Lifetime arrival coordinator voice. |
| Cassie | Cassie | Gemma - Decisive Agent | dialogue | yes | [voice:cassie], [speaker:Cassie], CASSIE: | firm field-responder competence; protective, unsentimental | Vacation of a Lifetime storm response voice. |
| Lukas | Lukas | Ronald - Thinker | dialogue | yes | [voice:lukas], [speaker:Lukas], LUKAS: | low, intense, practical responder; tired competence | Vacation of a Lifetime storm response voice. |
| Rosta | Rosta | Ronald - Thinker | dialogue | yes | [voice:rosta], [speaker:Rosta], ROSTA: | distorted hardline male; controlled threat/authority under static | Vacation of a Lifetime hidden-call voice candidate. |
| Junaid | Junaid | Clive - Measured Expert | dialogue | yes | [voice:junaid], [speaker:Junaid], JUNAID: | measured technical authority; composed under emergency constraints | Vacation of a Lifetime canon-supporting voice candidate. |
| Sarah | Sarah, paper-ticket lady | Jacqueline - Reassuring Agent | dialogue | yes | [voice:sarah], [speaker:Sarah], SARAH: | confident complaint energy; keep human, not caricature | Vacation of a Lifetime recurring tourist voice. |
| Kevin | Kevin | Corey - Supportive Buddy | dialogue | yes | [voice:kevin], [speaker:Kevin], KEVIN: | quiet companion, understated comic resistance | Vacation of a Lifetime recurring tourist voice. |
| Resort AI | Resort Announcement, cabin announcement | Daniel - Modern Assistant | dialogue | yes | [voice:resort-ai], [speaker:Resort AI], RESORT AI:, CABIN: | clear infrastructure/system announcement voice | Vacation of a Lifetime resort/cabin announcement voice. |
| She-Raw | She Raw, Stasya narrator fallback | Katie - Friendly Fixer | narrator | yes | [voice:she-raw], [voice:sheraw], [speaker:Stasya], STASYA: | artificial voice pitch; satisfying acoustic distortion | Narrator lane for first-person Vacation of a Lifetime renders; avoids Skylar default when no explicit speaker cue exists. |
| Lexen | Lexen |  | dialogue | yes | [voice:lexen] | old, deep, scarred, experienced; battle-worn command restraint; satisfying acoustic distortion | Cartesia audition required before defaulting a provider voice; placeholder removed; approve a Cartesia sample first. |
| Narrator | Narrator, Stasya narration | Katie - Friendly Fixer | narrator | yes | [voice:narrator], [speaker:Narrator], NARRATOR: | neutral first-person audiobook delivery; wry, bright, direct; satisfying acoustic distortion | Cartesia narrator fallback for Vacation of a Lifetime and uncast first-person sections. |
| Drew | Drew Clarke | Chris - Charming, Down-to-Earth | dialogue | yes | [voice:drew], [speaker:Drew], DREW: | plain direct-quote delivery; no biometric imitation; preserve compression and abrupt turns | Seen in Drew interview and Roadbuilder/Three Men scripts. |
| Andrew | Andrew Clarke | Daniel - Steady Broadcaster | dialogue | yes | [voice:andrew], [speaker:Andrew], ANDREW: | measured, concise, owner-of-next-step posture; satisfying acoustic distortion | Seen in Three Men and Roadbuilder scripts. |
| Droobiedoo | Droobiedoo | Droobiedoo | dialogue | yes | [voice:droobiedoo], [speaker:Droobiedoo], DROOBIEDOO: | warm ordinary protector until action is required; satisfying acoustic distortion | Matched live cloned voice metadata and recent scripts. |
| C.A.R.E. Unit | CARE Unit, Civic Aptitude Routing and Employment | Alice - Clear, Engaging Educator | dialogue | yes | [voice:care-unit], [speaker:C.A.R.E. Unit], C.A.R.E. UNIT:, CARE UNIT: | cheerful institutional confidence while the ceiling falls | Seen in Roadbuilder and Three Men scripts. |
| Elvis | Elvis Presley | Roger - Laid-Back, Casual, Resonant | dialogue | yes | [voice:elvis], [speaker:Elvis], ELVIS: | quick, funny, wary, proud, tender, evasive; never a drawling caricature | Seen in She-Raw Interviews Elvis Presley. |
| Washington | George Washington | Bill - Wise, Mature, Balanced | dialogue | yes | [voice:washington], [speaker:Washington], WASHINGTON: | controlled, concise, precedent-aware; no mystical recovered motive | Seen in She-Raw Interviews George Washington. |
| Mara | Mara | Sarah - Mature, Reassuring, Confident | dialogue | yes | [voice:mara], [speaker:Mara], MARA: | stable resident authority; direct without theater | Supporting speaker from Three Men/Roadbuilder recent docs. |
| Tomas | Tomas | Will - Relaxed Optimist | dialogue | yes | [voice:tomas], [speaker:Tomas], TOMAS: | ordinary resident voice; confused-to-responsible arc | Supporting speaker from Three Men/Roadbuilder recent docs. |
| Continuity Director | Director | Adam - Dominant, Firm | dialogue | yes | [voice:continuity-director], [speaker:Continuity Director], CONTINUITY DIRECTOR:, DIRECTOR: | smooth official certainty; power offering itself as safety | Supporting institutional speaker from recent dystopian docs. |
| Clerk | Clerk | River - Relaxed, Neutral, Informative | dialogue | yes | [voice:clerk], [speaker:Clerk], CLERK: | procedural neutrality that does not notice absurdity | Supporting role from medical-door scenes. |
| Doctor | Doctor | Matilda - Knowledgable, Professional | dialogue | yes | [voice:doctor], [speaker:Doctor], DOCTOR: | clinical, practical, human authority | Supporting role from medical-wing scenes. |
| Technician | Maintenance Technician | Liam - Energetic, Social Media Creator | dialogue | yes | [voice:technician], [speaker:Technician], TECHNICIAN:, MAINTENANCE TECHNICIAN: | working operator voice; practical but initially captured by labels | Supporting role from water-recycler scenes. |
| Planning Director | Planning Director | Eric - Smooth, Trustworthy | dialogue | yes | [voice:planning-director], [speaker:Planning Director], PLANNING DIRECTOR: | smooth certified-map confidence | Supporting role from road-map scenes. |
| Quartermaster | Quartermaster | Callum - Husky Trickster | dialogue | yes | [voice:quartermaster], [speaker:Quartermaster], QUARTERMASTER: | resource-gatekeeping edge; not cartoon villain | Supporting role from Credits/supply scenes. |
| Camp Harrow | Camp Harrow Radio | Miles | dialogue | yes | [voice:camp-harrow], [speaker:Camp Harrow], CAMP HARROW: | calm remote settlement broadcast; functioning but unfinished | Radio speaker from Three Men and Roadbuilder docs. |
