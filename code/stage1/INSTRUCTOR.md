# Instructor Notes

## Publishing a pinned SITL image

Students should `docker pull`, never build ArduPilot from source in class
(a source build takes 10-20 minutes). To build and publish the pinned image:

```bash
GHCR_OWNER=your-org ./scripts/build_and_push_sitl.sh Copter-4.6.3
```

Then set `SITL_IMAGE=ghcr.io/your-org/uav-course-sitl:copter-4.6.3` in the
`.env` file you distribute to students. Bumping the ArduPilot version for a
later course run means re-running this script with a new tag and updating
that one `.env` value -- nothing else in the repo needs to change.
