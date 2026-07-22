# Home Drive Character Voice Orientation Registry

## Precedence Rules

1. Explicit voice tags win: `[voice:id]` or registered `[speaker:name]` tags control the section.
2. Structured speaker cues encountered in documents are auto-ingested as durable cross-document profiles.
3. Cartesia is the default narrator provider; ElevenLabs is explicit render-only in speech settings.
4. She-Raw is narrator identity unless otherwise specified.
5. Acoustic direction is a rendering directive, not a local PCM distortion requirement in v1.

| Character | Aliases | Voice Alias | Narration Role | Always Applies | Match Tags | Acoustic Direction | Notes |
|---|---|---|---|---|---|---|---|
| She-Raw | She Raw |  | narrator | yes | [voice:she-raw], [voice:sheraw] | artificial voice pitch; satisfying acoustic distortion | Narrator identity; provider voice defaults to Cartesia unless overridden. |
| Lexen | Lexen |  | dialogue | yes | [voice:lexen] | old, deep, scarred, experienced; battle-worn command restraint; satisfying acoustic distortion | Cartesia audition required before defaulting a provider voice; placeholder removed; approve a Cartesia sample first. |
| Narrator | Narrator | Skylar - Friendly Guide | narrator | yes | [voice:narrator], [speaker:Narrator], NARRATOR: | neutral audiobook delivery; artificial voice pitch; satisfying acoustic distortion | Starter profile from recent Docs scan; default narration voice remains Cartesia. |
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
