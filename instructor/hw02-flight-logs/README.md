# HW2 flight log answer keys — INSTRUCTOR ONLY

Full analysis for the two logs selected for HW2 (Flight Logs + Prompt
Engineering). Not for student distribution — see each file's own header.

- `fence-breach-fuchsia.md` — repeated geofence breaches, single clean
  cause (hovering right at the fence boundary), low complexity.
- `failsafe-cascade-lime.md` — radio/GCS comms failsafe cascade, text-
  narrated via `MSG` entries, moderate complexity, good contrast to the
  fence-breach log's evidence style.

The raw `.bin` files themselves are the **student-facing** artifact,
distributed via a GitHub Release (not committed to any git history):
https://github.com/nd-native-ai-uav/native-ai-uav-resources/releases/tag/hw02-flight-logs

That's a new shared repo, `nd-native-ai-uav/native-ai-uav-resources` --
NOT the `native-ai-uav-fall-2026` template repo. Template Releases don't
carry over to individually-generated student repos, so shared
downloadable material (flight logs, datasets, etc. -- not per-student
homework) belongs in this separate repo instead. Read access is granted
via the `fall-2026-students` GitHub team (currently empty -- add students
to this team as they enroll; it has pull-only access to
native-ai-uav-resources).

A third, harder log (`FUCHSIA/2025-09-04 10-23-55.bin`, the stale-home
waypoint-displacement incident) was considered and set aside as too
advanced for HW2 — see `~/nier-2027/incident-report.md` (outside this
repo; real unpublished research data). Vibration/chipped-propeller
before/during/after is a candidate for a later assignment, pending May
2026 flight logs not yet downloaded.
