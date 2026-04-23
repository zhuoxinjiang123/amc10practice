# Linear Learning Cockpit Design

## Goal
Refresh the AMC 10 practice UI with an awesome-design-md style pass inspired by Linear: precise, focused, progress-first, and calm under time pressure.

## Visual Direction
Use a dark ink navigation shell, soft paper content surfaces, cyan and amber progress accents, crisp borders, and compact motion. The app should feel like a learning cockpit rather than a generic card grid.

## Page Changes
The topic dashboard gets a stronger hero, global progress summary, and topic cards with progress bars. The topic browser keeps the current checklist behavior but gains clearer metric cards, status pills, and a denser question list. The practice page keeps the two-column question and AI Tutor layout, with upgraded timers, answer buttons, and panel surfaces.

## Constraints
Do not change routes, persistence, answer scoring, AI Tutor behavior, or Render/Postgres setup. Keep all current tests passing and add template-level regression tests for new design hooks.
