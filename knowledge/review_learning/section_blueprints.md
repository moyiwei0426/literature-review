# Section Blueprints for Pedestrian-Crossing / AV-Reviews

## Quality targets
- **Target word count per section**: 250–500 words (intro/methods: 350–500; factors/gap: 300–450; conclusion: 200–300)
- **Minimum claims per section**: 3 distinct evidence-anchored claims
- **Citation density**: at least 1 citation anchor per 80 words of substantive prose
- **No placeholder text**: every section must contain at least 2 specific paper-id or finding anchors
- **Technical terms**: no underscores; proper noun capitalization; units reported (seconds, meters, etc.)

---

## Introduction
**Objective**: Establish the review's motivation, scope, and why the topic matters for traffic safety and/or AV deployment.

**Move sequence**:
1. **Stakes** (2–4 concrete facts): global pedestrian fatality numbers, intersection fraction of fatalities, injury cost estimates — anchored to specific reports where possible.
2. **Context narrowing**: signalized intersection specificities — tension between regulatory waiting and behavioral willingness to wait.
3. **Behavioral challenge**: why pedestrian crossing behavior at signals is non-trivial (heterogeneity, context dependence, interaction effects, heuristic calibration).
4. **Literature fragmentation**: prior reviews exist but vary in scope, methodology, or evidence base — state what's missing.
5. **Scope and contribution**: review boundaries (time range, evidence types, geographic coverage); explicit contribution statement.

**Structure template**:
```
Opening: [2-3 sentences establishing stakes with numbers]
↓
Narrowing: [2-3 sentences narrowing to signalized context]
↓
Challenge: [2-3 sentences on modeling difficulty / behavioral complexity]
↓
Gap: [2 sentences on what existing reviews leave unaddressed]
↓
Scope: [1-2 sentences on what this review covers]
↓
Contribution: [1 sentence on what the review contributes or synthesizes]
```

**Good closing hooks** for the intro section:
- "This review synthesizes findings from [N] studies across [time range] to provide [specific synthesis claim]."
- "The review is organized as follows: Section 2 reviews methodological approaches; Section 3 examines [topic]; Section 4 identifies verified gaps; Section 5 discusses implications."

---

## Methodological Approaches / Taxonomy
**Objective**: Categorize and compare the modeling paradigms, experimental designs, or analytical frameworks used in the literature.

**Move sequence**:
1. Announce organizing principle: number of paradigm/family categories.
2. Per family: definition → typical inputs → evidence from reviewed papers → strengths → limitations → validation status.
3. Cross-family comparison on: ecological validity, internal validity, interpretability, policy utility.
4. Closing synthesis: which families dominate, where the field is moving, what remains underutilized.

**Evidence template per method family**:
```
[Family name] models represent pedestrian crossing decisions as [representation basis].
[Studies using this approach] report [specific finding] with [metric/parameter].
A key strength is [X]; a key limitation is [Y], which restricts the approach's utility for [specific context or question].
Ecological validity concerns arise when [condition], because [specific reason].
```

**Closing synthesis template**:
```
Across these [N] paradigms, a clear tension emerges between [dimension A, e.g., interpretive richness] and [dimension B, e.g., predictive performance].
[Family A] offers the most tractable policy interpretation; [Family B] captures [phenomenon] but requires [data/validation].
No single paradigm has been validated across the full range of [contexts/populations] represented in this review.
```

---

## Factors and Determinants
**Objective**: Partition evidence on what influences crossing decisions into named clusters; synthesize consensus and flag contradictions.

**Move sequence**:
1. Announce factor taxonomy (3–5 clusters).
2. Per cluster: define the factor → state consensus finding → cite specific studies with effect direction/magnitude → flag contradictory findings with explanation → identify key moderators.
3. Cross-cluster synthesis: which factors are most consistently influential; which are understudied; interaction effects between clusters.

**Factor cluster examples** (from pedestrian crossing literature):
- Individual/demographic: age, gender, disability status, smartphone distraction, familiarity with location
- Traffic flow: vehicle speed, gap size, vehicle volume, approach grade
- Signal timing: wait duration, walk interval length, all-red phase, countdown timers
- Environmental: weather, lighting, crosswalk geometry, presence of other pedestrians
- Social/group: group size effects, peer pressure, social norms signaling

**Consensus-then-contradiction template**:
```
The evidence consistently identifies [factor] as [direction] influence on [outcome], with [specific effect size or threshold] reported in [N] studies.
By contrast, [Study X] found [opposite/null finding], a divergence likely attributable to [methodological difference, sample characteristic, or context difference].
A notable moderator is [variable], which appears to [condition/amplify/attenuate] the [factor] effect.
```

---

## Gap Section
**Objective**: Present verified gaps grounded in specific evidence — what partial work exists, why it's insufficient, and what resolving it would require.

**Gap entry template** (repeat for each gap):
```
Gap [letter/number]: [Precise gap statement, 1 sentence]
Partial evidence: [Study X] examined [scope] and reported [finding], but this work did not address [gap element] because [specific limitation].
Why insufficient: [2 sentences on what remains unknown or untested and why the existing evidence cannot resolve the gap].
Severity: [1 sentence on why this gap matters for the field or for practical outcomes].
Research need: [1 sentence on what study design or data would resolve it].
```

**Number of gaps**: 3–6 verified gaps (do not fabricate gaps; only report gaps supported by the matrix evidence).

**Quality checklist**:
- [ ] Each gap has a specific partial-evidence anchor (at least one paper in the matrix that relates but doesn't resolve)
- [ ] Each gap states the structural insufficiency (not just "more research needed")
- [ ] At least one gap connects to AV / emerging technology implications (for current-state reviews)
- [ ] Gap severity is indicated (critical / significant / moderate)

---

## Conclusion
**Objective**: Provide a field-level synthesis — not a section-by-section summary.

**Move sequence**:
1. Field-level framing statement (1–2 sentences): what overall picture emerges from the reviewed evidence.
2. 2–3 stable conclusions: what the evidence reliably supports, stated with confidence.
3. 2–3 unresolved tensions: what remains contested, with attribution to methodological or contextual differences.
4. 2–3 research priorities: what needs to happen next, directly tied to the verified gaps from the gap section.

**Anti-patterns**:
- "This review examined [N] papers and found..." (summary, not synthesis)
- "Future research should study more topics" (generic, no gap anchor)

**Research priority template**:
```
Priority [N]: Address gap [letter] by [specific research design or data collection approach], which would directly advance understanding of [mechanism/context] and carry implications for [practical outcome].
```

---

## Review-type specific notes

### For AV-pedestrian interaction reviews
- Intro must explicitly address: existing pedestrian heuristics are calibrated to human-driver behavior
- Methods section should include: eHMI modality comparison, implicit vs. explicit interaction
- Gap section should always include: longitudinal behavioral adaptation, cross-cultural coverage
- Closing should address: calibration of pedestrian heuristics to AV behavior patterns over time

### For pedestrian crossing behavior reviews (general)
- Factor taxonomy is central: individual / traffic / infrastructure / temporal / social
- Method section should flag: ecological validity vs. internal validity tension
- Gap section: cross-cultural threshold transfer, smartphone distraction multidimensionality, metric standardization
