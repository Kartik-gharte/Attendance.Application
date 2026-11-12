# Evaluation dataset policy

This document defines the dataset that issue
[#11](https://github.com/Kartik-gharte/Attendance.Application/issues/11)
needs, and the rules that a dataset must follow before it can be used.

The purpose of this document is to make the work reproducible without
weakening the privacy rules. A dataset that violates these rules is
rejected by the harness before any measurement is taken.

## Current status

**The evaluation has not been run. No accuracy figure exists for this
project.**

The measurement machinery is implemented and tested:

| Component | Purpose |
| --- | --- |
| `app/evaluation/harness.py` | Dataset description, validation, metrics, uncertainty, report format |
| `app/evaluation/evaluate.py` | Runs the evaluation against the real models and writes the report |
| `tests/runtime/test_evaluation_harness.py` | Covers the machinery with synthetic inputs |

The biometric model assets are **not** the blocker. They are provisioned
and load correctly on the development machine:

| Asset | Location | Status |
| --- | --- | --- |
| MediaPipe Face Landmarker | `models/mediapipe/face_landmarker.task` | Present, 3.6 MB |
| InsightFace `buffalo_l` | `~/.insightface/models/buffalo_l/` | Present, five ONNX models |

The blocker is the **dataset**. There is no face imagery anywhere on the
development machine, and none may be created without a consenting
participant.

## What the dataset must contain

### Identities

At least **five** distinct identities. Two is the minimum for a meaningful
impostor comparison, but the false accept rate is the number that matters
most for a biometric system, and it is the one that needs the most
impostor pairs to estimate at all.

### Genuine attempts

At least **20** attempts per identity, where the person in the image is
the person the system is asked to identify.

A realistic genuine attempt set varies the conditions that will differ in
practice:

- lighting: indoor, dim, backlit, daylight;
- distance and framing: close, normal, slightly far;
- pose: frontal, slight turn, larger turn;
- time: different sessions, not a single burst.

All of them should still be attempts that a person could reasonably pass.

### Impostor attempts

At least **20 impostor attempts per identity pair** would be ideal. The
practical minimum is 100 impostor attempts in total, spread across the
identities so that no single pair dominates.

Every identity must attempt to match every other identity at least once.
An impostor attempt uses an image of one person with the claimed identity
of another.

### Liveness attempts

Liveness is measured separately from recognition:

- at least 20 attempts with a blink, which should succeed;
- at least 20 attempts without a blink, which should be rejected.

### Presentation attack attempts

For the anti-spoofing screening to be evaluated at all, the dataset needs
attacks that the screening is meant to catch:

- a printed photograph held in front of the camera;
- a photograph displayed on a screen, including a phone;
- a video replay on a screen.

Each attack type needs at least 20 attempts. The harness records the
outcome but does not publish the payloads or the recipes, because a
published attack recipe is a published bypass.

## Consent rules

These are not optional. The harness cannot enforce them, so the dataset
description must record that they were met.

1. **Explicit written consent** from every participant, covering the
   collection of facial images, the generation and storage of biometric
   templates, and their use for evaluating this system.
2. **A documented retention period** for the images and the templates,
   and a deletion date.
3. **Withdrawal** is possible, and the images and templates are deleted
   on request.
4. **No real student data.** The dataset must not be drawn from the
   institution's student population without a separate approval.
5. **No images in the repository.** The dataset lives outside the
   repository. Only the dataset description JSON, which contains file
   paths and identity labels but no images, is version controlled, and
   even that must use pseudonymous identity labels.

### Identity labels

Use pseudonymous labels such as `SUBJ-A`, not names or student numbers.
The label is a join key between the image file and the attempt record, and
nothing more.

## Dataset description format

The dataset is described by a JSON file. It contains paths and labels, no
images.

```json
{
  "version": 1,
  "metadata": {
    "consent_recorded": true,
    "consent_reference": "internal-review-2026-01",
    "retention_until": "2027-01-01",
    "note": "Pseudonymous labels only."
  },
  "attempts": [
    {
      "id": "genuine-SUBJ-A-0001",
      "image": "images/SUBJ-A/genuine/0001.jpg",
      "genuine_identity": "SUBJ-A",
      "claimed_identity": "SUBJ-A",
      "kind": "genuine",
      "liveness_expected": true
    },
    {
      "id": "impostor-SUBJ-A-as-SUBJ-B-0001",
      "image": "images/SUBJ-A/impostor/0001.jpg",
      "genuine_identity": "SUBJ-A",
      "claimed_identity": "SUBJ-B",
      "kind": "impostor",
      "liveness_expected": false
    }
  ]
}
```

The `kind` field is either `genuine` or `impostor`. The harness validates
that a genuine attempt has matching identities, that an impostor attempt
has different ones, that the identifiers are unique, that both kinds are
present, that at least two identities are covered, and that every image
path exists. A dataset that fails any check is rejected before the models
are loaded.

## Running the evaluation

```bash
python -m app.evaluation.evaluate \\
  --dataset /secure/path/dataset.json \\
  --output /secure/path/report.json
```

The report contains the per-attempt decisions, the metrics, and the
configuration. It contains no images, embeddings, or biometric templates.
The report is still personal data, because the attempt identifiers and
the identity labels are.

## Interpreting the result

The report contains the false accept rate and the false reject rate with
their Wilson intervals, the ROC curve, the equal error rate, and the
liveness success rate.

Read the intervals before the rates. A false accept rate of 0 percent
over 20 impostor attempts is not a claim that the system never accepts an
impostor; the interval in the report shows the range the sample supports.

A threshold recommendation may only be made from the measured data. The
current default of `0.40` is a heuristic and is not calibrated.

## What may not be claimed

Until the evaluation has been run and reviewed:

- the system must not be described as accurate or inaccurate;
- the anti-spoofing screening must not be described as effective or
  ineffective;
- the system must not be described as having certified presentation
  attack detection;
- the `0.40` threshold must not be described as optimal.

The system is an experimental academic backend. The heuristic screening
is not a trained presentation attack detection model, and no evaluation
changes that.
