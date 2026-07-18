# uav-native-ai

**CSE 40701 — Native AI Software and Systems Engineering for UAVs.**

This repo is both the course website (published via GitHub Pages) and the
runnable infrastructure code students work with. If you're looking for the
syllabus, schedule, or lesson materials, the published site is easier to
read than browsing markdown source here:

**Course site:** https://janeclelandhuang.github.io/uav-native-ai/

## Layout

```
uav-native-ai/
  index.md, syllabus.md, schedule.md   <- course site pages (Jekyll source)
  lessons/                             <- one page per lesson
  _layouts/, _config.yml, assets/      <- site scaffolding/theme
  code/
    stage1/                            <- Stage 1 UAV infrastructure
                                           (ArduPilot SITL, MQTT backend,
                                           matplotlib viewer) -- see
                                           code/stage1/ARCHITECTURE.md
```

## Local development (site)

```
bundle exec jekyll serve
```

## Local development (Stage 1 infra)

See `code/stage1/SETUP.md` and `code/stage1/ARCHITECTURE.md`.
