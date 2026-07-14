# DotaSense Training Cockpit Design System

## Product job

DotaSense helps a ranked Dota 2 player decide what to practice in the next three matches, then verifies whether the habit improved. The first screen must answer: should I queue, what should I play, and what is the one behavior to change?

## Visual direction

AI-native training workspace with the density of an esports analysis desk. The signature element is the three-match mission strip: one objective, three fixed match slots, one measurable success condition.

## Typography

- Display: `Avenir Next`, 700-900. Use only for page titles and the mission objective.
- Body: `Microsoft YaHei`, `Segoe UI`, sans-serif, 400-700.
- Data: `DIN Alternate`, tabular numerals, 700-900.
- Page title: 28-32px; section title: 18-20px; body: 14px; utility: 11-12px.
- Letter spacing is always `0`; uppercase utility labels may use normal browser spacing only.

## Color tokens

- Pitch: `#0d100e` - page background.
- Panel: `#171b18` - primary surface.
- Raised: `#202620` - selected or interactive surface.
- Chalk: `#f2efe6` - primary text.
- Muted: `#9da49d` - secondary text.
- Aegis gold: `#f2c94c` - primary action and current mission.
- Rune cyan: `#58c4c7` - evidence and benchmark data.
- Victory green: `#55d68b` - success and improvement.
- Defeat red: `#ef6a61` - risk and regression.

Do not use broad gradients. A faint tactical grid may appear only on the page background. Color must encode state, evidence, or action.

## Layout

- Maximum workspace width: 1480px.
- Desktop navigation uses five equal tracks: Overview, Matches, Heroes, Meta, Progress.
- Overview starts with a 96px recent-form decision strip, a compact three-match command, and a filterable personal data explorer. Lifetime totals stay secondary.
- Personal match filters default to hero, STRATZ position 1-5, result, and date range. Side, mode, lobby, and party size stay behind one compact more-filters control.
- Six decision metrics share one horizontal strip; deep metrics always disclose their valid sample count.
- Global Meta is segmented into positions 1-5 using STRATZ Ranked Roles data. Lane aggregates and economy-based estimates are never used as position labels.
- Meta tables show raw win rate, Bayesian-adjusted win rate, position sample count, and within-position pick share.
- Personal position matrices use only STRATZ `POSITION_1`-`POSITION_5` evidence. Missing positions stay unavailable and never become a chart category.
- Dense tables stay inside horizontal scroll containers on mobile.
- Match equipment always reserves six inventory slots plus one visually separated neutral item. Backpack slots are intentionally excluded. Empty slots and unavailable data use different states.
- Mobile tabs scroll horizontally with 108px minimum targets; no page-level horizontal overflow.

## Components

- Cards: 1px border, 6-8px radius, no decorative floating sections, minimal shadow.
- Primary button: gold fill, dark text, 34px in dense command bars and 44px in full workflows.
- Secondary button: transparent surface, visible border, icon plus concise command.
- Inputs: 34-36px in dense toolbars, 44px in full forms, dark inset surface, cyan focus border.
- Status chips: compact, semantic color, never decorative.
- Icons: Lucide, 16-18px, 1.75-2px stroke. Buttons use familiar icons where possible.

## Evidence states

- Verified: final scoreboard, STRATZ Ranked Roles position, or hero benchmark exists.
- Parsed: replay timelines and event logs exist.
- Limited: only match summary exists.
- Unavailable: the product explicitly declines to infer.

Every coaching claim must show its evidence state. Missing position data is shown as unavailable, never inferred.

## Product states

- Loading: quick profile and match skeleton first; deep analysis has a separate non-blocking status.
- Empty: explain how to make Steam match data public or enter another account ID.
- Error: preserve any already loaded data and identify which layer failed.
- Success: show mission progress or Pro access state in place, without a modal.
- Disabled: keep controls visible and explain the prerequisite nearby.

## Responsive behavior

- At 900px, navigation and mission evidence become horizontal scroll or single-column layouts.
- At 640px, page padding is 16px, cards are full available width, and metric text is capped at 30px.
- Fixed-format mission slots and icon buttons have stable dimensions and cannot resize from content changes.

## Avoid

- Internal labels such as "commercialization", "revenue checklist", or "start selling".
- Unsupported claims about exact positioning, fights, ward coverage, or item timing.
- Nested cards, oversized hero copy, decorative glow blobs, glassmorphism, and excessive gradients.
- A standalone Pro navigation tab. Paid value is revealed inside Match Lab and Progress.
