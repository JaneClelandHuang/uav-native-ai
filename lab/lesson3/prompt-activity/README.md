PROMPT ACTIVITY -- "Can You Prompt AI to Build This Game?"
========================================================

A one-shot prompting exercise. Separate from HW3, not graded.

    Observe.  Understand.  Specify.  Generate.  ONE SHOT.


THE EXERCISE
-----------

1. PLAY & OBSERVE
   Play the "LinkedIn Patches" puzzle game (see the class slide). Work
   out the rules for yourself -- how a shape grows, what makes a move
   legal, when the puzzle is solved.

2. REIMAGINE
   Think of each starting shape as a UAV's location, and the region it
   grows into as that UAV's assigned search area. Same mechanic,
   different framing.

3. PROMPT
   Write ONE prompt -- or one pre-planned prompt chain -- that gets a
   coding assistant to build the game in Python + Matplotlib, loading a
   puzzle from a file like problem1.json.

4. ONE SHOT
   Run your prompt(s). No follow-up prompts. No fixes. No editing the
   generated code.

The challenge: whose prompt produces the closest working game?
Prompt quality, not prompt quantity. Can you observe, understand,
specify, and communicate the problem well enough for the AI to build it?


problem1.json
------------

One puzzle instance to target. Schema:

  grid_size            the board is grid_size x grid_size cells

  drones[]             the starting shapes, one per region:
    id                 label
    x, y               the seed cell (integer grid coordinates)
    shape              required shape of the finished region --
                       "vertical-rectangle", "horizontal-rectangle",
                       "square", or "any"
    size               number of cells the finished region must cover,
                       or "any"
    color              fill colour for that region

What counts as a correct solution is part of what you work out in step 1.
