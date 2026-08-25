# Peer Review — DynamiX: A Multi-Level Autoscaling Architecture for Distributed Stream Processing

**Review date**: 2026-08-08
**Review mode**: `academic-paper-reviewer` full panel, developmental tone (manuscript is a partial draft — see Field Analysis)
**Manuscript reviewed**: `~/Downloads/DynamiX A Multi-Level Autoscaling Architecture for Distributed Stream Processing.docx.pdf` (21 pages; content ends mid-§IV — no Results, no Conclusion)
**Panel**: Editor-in-Chief + 3 Peer Reviewers + Devil's Advocate (5 independent reviews) + Editorial Synthesis

---

## Field Analysis Summary

| Dimension | Result |
|---|---|
| Primary Discipline | Distributed systems / cloud computing — resource elasticity for distributed stream processing |
| Secondary Disciplines | IoT, container orchestration (Kubernetes), fog/edge computing (claimed, not implemented) |
| Research Paradigm | Systems research: design + implementation + empirical performance evaluation |
| Methodology Type | Experimental / quasi-experimental (A/B/C/D condition comparison) + implementation artifact |
| Target Journal Tier | Q3, leaning Q2 at best (citation pool ceiling; base work ARiSto [15] published at a workshop) |
| Paper Maturity | **First draft — incomplete.** §IV.B empty; Section V (Results) and Section VI (Conclusion) do not exist |

**Recommended target journals** (once complete): *Journal of Parallel and Distributed Computing* (Elsevier), *Cluster Computing* (Springer), *IEEE Internet of Things Journal* (if reframed toward IoT). ALGOCLOUD or a similar workshop is a realistic first target, consistent with where ARiSto [15] itself was published.

### Reviewer Configuration

| Reviewer | Identity | Focus |
|---|---|---|
| EIC | Associate Editor, *J. Parallel Distrib. Comput.*, cloud-native elasticity background | Journal fit, originality, overall readiness |
| R1 (Methodology) | Systems-performance-evaluation methodologist, autoscaling benchmarking | Experimental design rigor, reproducibility, controlled-comparison validity |
| R2 (Domain) | Distributed stream-processing researcher, ARiSto-literate | Literature completeness, ARiSto version accuracy, novelty positioning |
| R3 (Perspective) | Cloud infrastructure / SRE background | Controller-interaction stability lens, cloud-fog framing, practical deployment cost |
| DA (Devil's Advocate) | — | Core-claim stress test: does multi-level actually beat single-level, or is this an unstable two-controller interaction? |

---

## EIC Review Report

**Reviewer Identity**: Associate Editor, *Journal of Parallel and Distributed Computing* (Elsevier) — background in cloud-native resource elasticity and container-orchestrated distributed systems.

**Overall Recommendation**: Major Revision *(functionally: not ready for formal review — see Editorial Decision)*
**Confidence Score**: 4/5

### Summary Assessment
The manuscript proposes DynamiX, integrating ARiSto's topology-level autoscaling with KEDA-driven Kubernetes pod scaling for Storm-based IoT stream processing, bridged by a composite `weight_scale` metric. The writing through §III.D and §IV.A is competent and the engineering description is concrete. However, the manuscript as submitted ends mid-§IV: **§IV.B is an empty header, and Section V (Results) and Section VI (Conclusion) do not exist.** A journal cannot evaluate originality-in-practice, significance, or fit without seeing whether the central claim — multi-level beats single-level — is actually demonstrated. This recommendation reflects that gap, not a judgment that the existing content is poor.

### Strengths
1. **Honest self-critique of the base algorithm (§III.C)**: identifies and explains a genuine correctness defect (the cumulative-acknowledgement formula returning near-zero when Nimbus stats haven't refreshed) with a clear before/after formula. The strongest, most concrete technical contribution currently visible.
2. **§III.D names its own limitation instead of hiding it**: the paragraph on ARiSto/KEDA timing asymmetry (30-60s vs. 5-10min) reads like the authors already know where the hard problem is.
3. **Clear, falsifiable core claim**: "multi-level beats any single level" is testable, and the implied G1-style condition matrix is the right shape of experiment to test it.

### Weaknesses
1. **Manuscript is structurally incomplete** — no §IV.B content, no Section V, no Section VI. *Severity: Critical.*
2. **Unresolved internal notes left in submitted text** — §III.C contains an untranslated Vietnamese to-do note ("Phần này phải bổ sung thêm sơ đồ hoạt động ARIsTo...") directly in the manuscript body, signaling the draft wasn't proofread as submission-ready. *Severity: Minor.*
3. **"Novel architecture" framing outruns current evidence** — Table I self-scores DynamiX as "Coordinated multi-level autoscaling... Hybrid adaptive" in the same table as the comparators, before any result justifies that positioning. *Severity: Major.* Suggestion: hold the framing until Section V supports it, or soften to "integration architecture" pending evaluation.

### Detailed Comments
- **Journal Fit**: on-target for JPDC (cf. citation [24], same venue); realistic tier Q3.
- **Originality**: real but incremental — two published systems (ARiSto 2018, KEDA 2020) plus one formula fix; Table I itself places DynamiX alongside six prior "hybrid/predictive/adaptive" approaches.
- **Significance**: unassessable without Section V. If the multi-level claim holds, significance is real (a genuine open coordination gap between app-level and infra-level elasticity); if not, the paper still has value as a cautionary result about naively combining two reactive controllers.
- **Structural Coherence**: breaks exactly at the missing sections.
- **Title & Abstract**: claims "cloud–fog environments" three times; architecture (Fig. 2) has no fog tier — see R3 Weakness 1.
- **Conclusion**: N/A — does not exist.

### Questions for Authors
1. What is the actual target venue/tier?
2. Is there a reason §IV.B was left as a bare header rather than removed — is cluster-spec data collected but not yet transcribed?

### Minor Issues
- Vietnamese draft note in §III.C.
- Fig. 3.11 notation inconsistency: "avg(bolt_capacity)" (singular) vs. "avg(spouts_complete_latency)" (plural).

---

## Methodology Review Report (Peer Reviewer 1)

**Reviewer Identity**: Systems-performance-evaluation methodologist — autoscaling benchmarking, control-loop empirical validation.

**Overall Recommendation**: Major Revision
**Confidence Score**: 4/5

### Summary Assessment
The paper describes a 4-condition comparison design (implied: static / KEDA-only / ARiSto-only / DynamiX under an identical load ramp) that is, in principle, the right design to isolate the multi-level effect. But the manuscript currently provides no cluster specification, no replicate count, no statement of run duration/control conditions, and no results. Without those, methodological rigor cannot be scored as anything but incomplete — the design's *concept* is sound, its *execution* is entirely unverifiable from the text as written.

### Strengths
1. **The formula defect diagnosis is methodologically sound reasoning** (§III.C): identifying a spurious near-zero numerator caused by a polling-interval artifact, fixed with a fixed-window estimator, is exactly the right kind of "why does the reactive signal misbehave" analysis.
2. **Threshold values are stated explicitly and their provenance acknowledged** (0.5 bolt-capacity, 100ms latency, 0.75 weight_scale, 300s cooldown), even if only justified as "empirically selected" (see Weakness 3).
3. **The coordination-gap paragraph in §III.D quantifies the asymmetry** (30-60s vs. 5-10min) rather than leaving it qualitative.

### Weaknesses
1. **§IV.B "Experimental Environment" is empty**: no CPU/RAM/node count, no Storm/K8s version pins, no replicate count `n`, no statement of whether conditions are run hands-off. *Severity: Critical.* Suggestion: at minimum, a table of cluster spec + software versions + `n` per condition + confirmation that no manual intervention occurred during data collection.
2. **The controlled-comparison premise is not defended**: for the 4-condition matrix to isolate the effect of combining layers, all four need identical load, identical hardware, and identical operator hands-off-ness. Nothing in the text commits to this. *Severity: Critical.* Suggestion: state the control protocol explicitly; if any run required operator intervention to reach its reported state, that run must be excluded or the intervention disclosed — a mixed human+autoscaler result cannot be attributed to the autoscaler.
3. **`weight_scale` weights (0.6/0.2/0.2) and threshold (0.75) are asserted as "empirically selected" with no sensitivity analysis reported** (§III.D.2). *Severity: Major.* Suggestion: include a parameter sweep (window/threshold/bolt-capacity-threshold) if one exists or is planned.

### Detailed Comments
- **Research Design**: comparative, controlled-in-principle A/B/C/D design over a common load ramp — appropriate shape; execution unverifiable (Weakness 1/2).
- **Sampling/Data Collection**: DEBS 2014 replay via MQTT at varied injection rates (§IV.A) — appropriate, standard benchmark, well-described.
- **Analysis Methods / Results Presentation**: N/A, no Results section.
- **Reproducibility**: near-zero currently — no version pins, no config disclosure, no cluster spec, no data/code availability statement.
- **Methodological Fallacies Detected**: flagging in advance — if any run required manual correction to reach its "good" result and only that corrected run gets reported, that's a textbook survivorship-bias pattern.

### Questions for Authors
1. How many replicates per condition are planned/collected, and will confidence intervals or per-run variance be reported?
2. Does the data-collection pipeline distinguish an autoscaler-triggered rebalance from a manually-triggered one in the logs? If not, how will the paper certify reported "DynamiX" behavior is autonomous?
3. Is a parameter-sensitivity experiment (window/threshold values) planned for this paper or a follow-up?

### Minor Issues
- Fig. 3.7/3.9/3.11 numbering doesn't match this manuscript's own Section numbering (III.C/III.D) — likely leftover from the source thesis document.

---

## Domain Review Report (Peer Reviewer 2)

**Reviewer Identity**: Distributed stream-processing researcher — Apache Storm elasticity, familiar with ARiSto [15] and adjacent autoscaling literature (Enel [27], PA-SPS [24], Daedalus [7]).

**Overall Recommendation**: Major Revision
**Confidence Score**: 4/5

### Summary Assessment
Related Work (§II) is reasonably current (2021-2025 dominant) and correctly separates application-level, infrastructure-level, and cloud-fog resource-management literature into three coherent subsections with a genuinely useful comparison table (Table I) — the paper's strongest section. The main gaps are precision issues: which ARiSto version is actually the base, whether scale-down exists at the topology layer at all, and whether Table I's coarse columns actually distinguish DynamiX from prior "hybrid adaptive" approaches like [31] and [33] as sharply as the table implies.

### Strengths
1. **Table I is a genuine comparative contribution**, not a citation dump — lets a reader see the field's shape at a glance and correctly locate the gap (nothing else in the table is "Multi-level").
2. **§II.A-C literature organization by scaling layer** mirrors the paper's own architecture — good structural discipline; the lit review is set up to motivate the contribution, not just background.
3. **Accurate attribution of ARiSto's original contribution** (§II.A) — the base work is represented fairly.

### Weaknesses
1. **ARiSto base version never stated.** [15] describes the 2018 original, but ARiSto has four documented versions (v1-v4) with materially different capabilities — v3+ reportedly adds scale-down logic — and the paper never says which version DynamiX extends. *Severity: Major.* Suggestion: one sentence, e.g. "DynamiX extends ARiSto v1, the original topology-level elasticity mechanism based on spout throughput severity tracking" (or whichever is true).
2. **Scale-down (scale-in) behavior for the topology/ARiSto layer is not described anywhere in §III.C.** Only scale-out steps are given; §III.D describes KEDA's scale-in explicitly, so the silence on the ARiSto side reads as omission, not deliberate design. *Severity: Major.* Suggestion: state explicitly whether topology-layer scale-in is implemented; if not, list as a limitation/future work.
3. **Table I's "Scaling Layer"/"Adaptation Strategy" columns may understate similarity to prior hybrid work** — [31] (HyPA) and [33] (Zhu et al.) both carry adaptation strategies close to "Hybrid adaptive," the same label DynamiX gives itself. *Severity: Minor.* Suggestion: one paragraph in §II.D contrasting DynamiX's uncoordinated dual reactive controllers against [31]/[33]'s predictive/ML-based coordination — a defensible point in DynamiX's favor if made explicitly.

### Detailed Comments
- **Literature Review**: good recency, correct subfield span, genuine Table I synthesis, reasonably convincing gap argument.
- **Theoretical Framework**: applied with real depth (§III.C-D formulas/thresholds), not superficially cited.
- **Academic Argument Quality**: factually accurate; one imprecision — §III.C's "600-second window... independent of Nimbus refresh timing" is true of the numerator behavior but should clarify whether staleness can still occur *within* that window.
- **Missing Key References**: none glaring; recommend an ARiSto version reference beyond [15] if extending v2+.

### Questions for Authors
1. Which ARiSto version (v1-v4) is the extension base?
2. Is topology-layer (ARiSto) scale-in implemented at all, or only KEDA-layer scale-in?

### Minor Issues
- Terminology inconsistency: "supervisor node" vs. "Supervisor pod" — pick one and use consistently.

---

## Perspective Review Report (Peer Reviewer 3)

**Reviewer Identity**: Cloud infrastructure / SRE-background engineer bringing a control-loop-stability lens from outside the stream-processing subfield.

**Overall Recommendation**: Major Revision
**Confidence Score**: 3/5 (adjacent, not core, discipline — deferring to R1/DA on deeper control-theory implications)

### Summary Assessment
As an outsider to the Storm/stream-processing subfield, what jumps out is a mismatch between what the paper claims to be built for (cloud–fog IoT) and what it actually is (single-cluster Kubernetes-native), plus two unexamined operational consequences of otherwise well-defended design choices: the scale-up-only policy's cost trajectory, and the end-user-facing effect of the "brief period where executor scaling stalls" the paper already admits happens.

### Strengths
1. **The 300s cooldown rationale is genuinely well-reasoned from an SRE standpoint** (§III.D) — "premature pod removal would force ARiSto into repeated worker-process-exhaustion states" is real operational reasoning, not an asserted-without-justification constant.
2. **Admitting the coordination gap in writing (§III.D) rather than hiding it** is unusually honest for this genre, and gives the "future work" pointer real specificity.
3. **The composite `weight_scale` metric is a sensible answer to a genuinely hard cross-layer problem** — translating an application-internal signal into something an infrastructure-level scaler can consume without needing Storm internals shows real understanding of the "impedance mismatch," in the paper's own words.

### Weaknesses
1. **Cloud–fog framing doesn't match the architecture.** Abstract and intro repeat "cloud–fog" language; Fig. 2 shows every component inside a single "Kubernetes cluster" box — no fog-tier component anywhere. *Severity: Major.* Suggestion (pick one): reposition as "cloud-native IoT stream processing" throughout, or add an actual edge/fog preprocessing tier and evaluate its latency contribution.
2. **The scale-up-only, never-scale-down infrastructure policy (§III.D) has an unaddressed cost trajectory** — sustained-load episodes only grow pod count, and the cost/stability trade-off is never discussed. *Severity: Minor.* Suggestion: one sentence acknowledging the trade-off, even if scale-down stays future work.
3. **The end-user consequence of the admitted coordination gap is never named.** §III.D's "stall" happens exactly during a load spike — for smart-home IoT, that's sensor events queuing/dropping at the worst moment. *Severity: Minor.* Suggestion: connect the coordination gap to its IoT-application-level consequence.

### Detailed Comments
- **Assumption Audit**: implicit assumption that K8s pod-level scaling is the correct proxy for "infrastructure elasticity" in a cloud-fog paper — reasonable for cloud, undercuts the fog framing. Paradigmatic assumption: reactive-only control (both loops threshold-triggered) — worth a sentence against the predictive alternatives Table I itself lists ([24]/[28]/[29]/[33]).
- **Practical Impact**: plausible use case; feasibility for the claimed cloud-fog setting currently unverified.
- **Broader Implications**: no ethical/privacy gap flagged; not needed for this specific contribution.

### Cross-Disciplinary Reading Recommendations
- Hellerstein et al., *Feedback Control of Computing Systems* (Wiley, 2004) — classic control-theory framing for the "two independent reactive loops" question DA raises.
- Aazam, Zeadally & Harras [12] (already cited) — worth pulling into the architecture section itself to either justify or drop the fog framing.

### Questions for Authors
1. Is there a concrete plan to add a fog/edge component, or should the framing be revised to "cloud-native"?
2. Has infrastructure cost (pod-hours) been measured or planned as a metric alongside throughput/latency?

### Minor Issues
- "Fog Computing" introduced in §I as a paradigm the paper extends but never operationalized again after §II.C.

---

## Devil's Advocate Review

### Strongest Counter-Argument
Before the challenge: the paper's willingness to name its own limitation in §III.D — rather than hide the ARiSto/KEDA timing asymmetry — is unusual and creditable.

That admission is also the seed of the strongest case against the paper. The central claim is that combining two independently-tuned reactive controllers — ARiSto (topology-level, ~30-60s reaction) and KEDA (infra-level, ~5-10min reaction) — produces better outcomes than either alone. But two uncoordinated control loops acting on a shared resource is a textbook recipe for instability, not synergy, unless something actively prevents interference. The paper's only interference-prevention mechanisms are (1) KEDA's scale-up-only policy and (2) a 300s cooldown — both one-directional guards against a specific failure mode (premature pod removal), not a general stability argument. Nothing in §III.D shows the two controllers *converge* to a jointly-good state; it only shows one *doesn't actively fight* the other in one direction. §III.D's own text describes the resulting failure mode directly: "ARiSto may exhaust the existing maxWorkers limit before new supervisors register, causing a brief period where executor scaling stalls" — that is not a minor edge case, it is exactly the signature you'd expect from an unmanaged multi-loop interaction: one controller outrunning the resource the other controller was supposed to supply. Until the paper shows empirically that this failure mode is rare/brief/recoverable rather than dominant, the more parsimonious explanation for any observed "DynamiX beats single-level" result is not "coordinated elasticity" — it's "KEDA eventually gets there and ARiSto happens to benefit," which is a much weaker and less interesting claim than the one in the title.

### Issue List

#### CRITICAL
| # | Dimension | Issue Description | Location | Field-Norm Boundary | Evidence-Crossing Rationale |
|---|-----------|-------------------|----------|---------------------|-----------------------------|
| 1 | Core Thesis Challenge | The central claim ("multi-level autoscaling outperforms single-level") has zero supporting empirical evidence in the current draft — no Results section exists. | Section V (absent) | — (universal, not subfield-relative) | — |
| 2 | Logic Chain Validation / Stronger Counter-Narrative | §III.D's own text describes the exact instability mechanism the counter-argument predicts, with no test of whether it dominates. The counter-narrative ("KEDA eventually compensates, ARiSto isn't doing anything special") is at least as consistent with the described mechanism as the paper's own claim. | §III.D, final paragraph | — (internal logic-chain gap) | — |

#### MAJOR
| # | Dimension | Issue Description | Location | Field-Norm Boundary | Evidence-Crossing Rationale |
|---|-----------|-------------------|----------|---------------------|-----------------------------|
| 1 | Overgeneralization / "So What?" Test | "Novel... architecture" (Abstract, title) is strong for what Table I shows is an integration of two previously-published systems plus one formula correction. | Abstract; Table I | [FIELD-NORM UNVERIFIED] — no external source pinning this subfield's novelty bar; flagging the internal inconsistency only. | — |
| 2 | Alternative Paths Analysis | No discussion of whether a single well-tuned controller (KEDA alone, corrected `weight_scale`) could achieve comparable results — directly answerable by the paper's own condition matrix, which isn't run/reported yet. | §III.B/D; Section V (absent) | — | — |

#### MINOR
| # | Dimension | Issue Description | Location |
|---|-----------|-------------------|----------|
| 1 | Stakeholder Blind Spots | Operator/on-call perspective (monotonically growing pod count, mid-spike scaling stalls in production) absent. R3 covers the deployment-cost angle in more depth; flagging presence/absence only. | §III.D |

### Ignored Alternative Explanations/Paths
1. **Single-controller sufficiency**: a well-tuned KEDA-only baseline (with the corrected `weight_scale` formula) might capture most of the benefit attributed to "multi-level," since the formula fix — not the multi-level architecture — is the paper's one clearly-validated technical contribution (§III.C).
2. **Confound between "more time observed" and "better outcome."** If the DynamiX condition needs to run longer than single-layer conditions for KEDA to finish provisioning, any comparison needs a controlled, matched observation window — otherwise an apparent DynamiX advantage could just be "observed for longer."

### Missing Stakeholder Perspectives
- On-call/SRE operator dealing with unbounded pod growth and mid-spike stalls in production.

### Unexamined Premise
The paper assumes a fixed-topology, fixed-load-schedule benchmark (DEBS 2014 replay at controlled ramps) is representative of the coordination problem it's trying to solve. But the failure mode named in §III.D is most likely to bite under *unpredictable* load spikes, not the smooth, pre-scripted 1000→4000→8000 ramp (§IV.A). A scripted ramp gives KEDA's slow reaction time the best possible chance to keep up. The paper's own benchmark design may be structurally biased toward hiding the exact instability its Strongest Counter-Argument predicts.

### Observations (Non-Defects)
- The paper's honesty about the coordination gap (§III.D) is unusual enough to flag positively, separate from Strengths above.

---

# Editorial Decision Package

## Part 1: Editorial Decision Letter

Reviewed by 5 independent reviewers (EIC + 3 peer reviewers + Devil's Advocate) in developmental mode, given the manuscript's current draft state.

### Decision: **Major Revision** *(procedural, not qualitative — see rationale)*

### Consensus Analysis

**[CONSENSUS-4]** (all 4 non-DA reviewers agree):
1. The manuscript is structurally incomplete — §IV.B is empty, Section V and VI don't exist. Every reviewer's ability to assess their assigned dimension is bottlenecked by this.

**Corroborated findings (2/4, not consensus-3 — the other 2 silent, not disputing)**:
1. "Novel architecture" framing overstates the current contribution — EIC + R2, independently corroborated in substance by DA's MAJOR #1.
2. ARiSto scale-down/version ambiguity — R2 only among the 4 (single-reviewer finding, Confidence 4), but cheap to fix.

### Points of Disagreement
None rose to genuine SPLIT (a disputed existence/severity claim) in this round — reviewers differed in emphasis, not in disagreement about whether a raised issue was real.

### DA-CRITICAL Issues (tracked independently)
1. **Foundation Collapse — zero evidence for the central claim.** Corroborated in substance by all 4 other reviewers' incompleteness findings. **EIC assessment: valid — this is the actual gate on any decision.** Required response: Section V must exist before any Accept/Reject verdict is meaningful.
2. **Logic Chain Break — §III.D's own admitted failure mode is the strongest available counter-narrative to the paper's own thesis, and is untested.** R3's Weakness 3 and R1's Weakness 2 independently gesture at pieces of it. **EIC assessment: valid — the single highest-priority technical item for Section V design.** Required response: design data collection to explicitly distinguish "DynamiX coordinates well" from "KEDA eventually compensates regardless of ARiSto" — a paper that honestly reports the counter-narrative winning is still a legitimate, publishable result.

### Decision Rationale
No reviewer scored below the incompleteness bottleneck, and no reviewer found a fundamental flaw in what *is* written — §III's technical content (formula fix, composite metric, coordination-gap admission) is sound-to-strong engineering writing. The rubric-weighted score computes well below the Reject threshold (~41/100), but that's an artifact of scoring "Evidence Sufficiency" and "Argument Coherence" against a manuscript missing half its sections, not a quality verdict on what's present. **Major Revision** is used as the closest available category to "return once Sections V-VI exist and DA's counter-narrative has been empirically addressed."

### Summary of Key Issues
1. Write Section V/VI (blocks everything — CONSENSUS-4).
2. Design Section V to distinguish "coordinated benefit" from "KEDA eventually compensates" (DA-CRITICAL #2).
3. Resolve cloud-fog framing mismatch (R3) and novelty-framing overstatement (EIC+R2+DA).
4. Fix cheap items: ARiSto version/scale-down statement (R2), Vietnamese draft notes (EIC), `weight_scale` sensitivity justification (R1).

---

## Part 2: Revision Roadmap

### Required Revisions (Must Fix)

| # | Revision Item | Source | Priority | Estimated Effort |
|---|--------------|--------|----------|-----------------|
| R1 | Write §IV.B (cluster spec, versions, `n`, hands-off confirmation) and Section V with real data | EIC, R1 | P1 | Depends on data-collection status |
| R2 | Design Section V to distinguish "coordinated benefit" from "KEDA alone compensates" | DA (Critical #2), R1/R3 | P1 | 1-2 days analysis once data exists |
| R3 | State whether any reported run required manual intervention; exclude or flag such runs | R1 (Critical #2) | P1 | Depends on data audit |
| R4 | Write Section VI (Conclusion) | EIC | P1 | 0.5 day once V exists |
| R5 | Fix cloud–fog framing (reposition as cloud-native, or add a real fog tier) | R3 (Major #1) | P1 | 0.5 day to weeks |

### Suggested Revisions (Should Fix)

| # | Revision Item | Source | Priority | Expected Improvement |
|---|--------------|--------|----------|---------------------|
| S1 | Soften "novel architecture" framing / sharpen Table I differentiation vs. [31]/[33] | EIC, R2, DA | P2 | Removes easiest attack surface |
| S2 | State ARiSto base version (v1-v4); describe or flag topology-layer scale-in status | R2 (Major #1, #2) | P2 | Closes a checkable factual gap |
| S3 | Justify `weight_scale` weights beyond "empirically selected," or cite a sensitivity sweep | R1 (Major #3) | P2 | Preempts the most predictable reviewer question |
| S4 | Acknowledge scale-up-only cost trajectory; note end-user consequence of coordination-gap stall | R3 (Minor #2, #3) | P2/P3 | Strengthens practical framing cheaply |

### Revision Checklist

**Priority 1 — Structural**
- [ ] §IV.B + Section V written from real, controlled, hands-off data
- [ ] Section V designed to test coordination-benefit-vs-compensation directly
- [ ] Manual-intervention audit and disclosure for any run used
- [ ] Section VI written
- [ ] Cloud-fog framing resolved

**Priority 2 — Content Supplementation**
- [ ] Novelty framing calibrated to Table I
- [ ] ARiSto version + scale-down status stated
- [ ] `weight_scale` weight justification added

**Priority 3 — Text and Formatting**
- [ ] Remove Vietnamese draft notes (§III.C)
- [ ] Fix Fig. 3.7/3.9/3.11 numbering consistency
- [ ] Standardize "Supervisor pod" vs. "supervisor node" terminology

---

## Part 3: Reviewer Summary

| Reviewer | Recommendation | Confidence | Key Point |
|---|---|---|---|
| EIC | Major Revision | 4 | Can't evaluate fit/significance with no Results/Conclusion; existing §III content is sound |
| R1 (Methodology) | Major Revision | 4 | Design is right in shape but unverifiable — no cluster spec, no replicate count, no controlled-comparison commitment |
| R2 (Domain) | Major Revision | 4 | Strong lit review; needs ARiSto version pinned and scale-down behavior addressed |
| R3 (Perspective) | Major Revision | 3 | Cloud-fog claim doesn't match the (cloud-only) architecture; admitted coordination gap has unaddressed cost/UX consequences |
| DA | *(challenge only, no recommendation)* | — | Central claim has zero current evidence; the paper's own §III.D text already names the strongest counter-narrative to its own thesis |

---

## Reviewer's note (session context, not part of the formal panel output)

This review is unusually well-grounded because it was produced from inside the project's actual repo and data, not just the manuscript — several findings above (R1's manual-intervention flag, DA's stronger counter-narrative) are sharper because of direct knowledge that the `G1-dynamix-r1` run needed a manual rebalance to reach its good result, and that the poller (`storm_snapshot.py`) can't distinguish that from autonomous behavior. A real journal reviewer would never have that visibility. DA's CRITICAL #2 and R1's Critical #2 aren't hypothetical risks here — they describe something that already happened once. Fixing `CLAUDE.md` Open blocker #3 and re-running G1-dynamix clean before Section V gets written removes a good chunk of this review's Major-severity items on its own.
