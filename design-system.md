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
- Desktop navigation uses five equal tracks: Today, Match Lab, Hero Pool, Meta, Progress.
- The Today page starts with profile context and the mission strip, followed by recent matches and evidence coverage.
- Dense tables stay inside horizontal scroll containers on mobile.
- Mobile tabs scroll horizontally with 124px minimum targets; no page-level horizontal overflow.

## Components

- Cards: 1px border, 6-8px radius, no decorative floating sections, minimal shadow.
- Primary button: gold fill, dark text, 44px minimum height.
- Secondary button: transparent surface, visible border, icon plus concise command.
- Inputs: 44px minimum height, dark inset surface, cyan focus border.
- Status chips: compact, semantic color, never decorative.
- Icons: Lucide, 16-18px, 1.75-2px stroke. Buttons use familiar icons where possible.

## Evidence states

- Verified: final scoreboard or hero benchmark exists.
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
