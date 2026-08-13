# DotaSense Adaptive Product Design System

## Product job

DotaSense helps a ranked Dota 2 player understand recent form, inspect match evidence, choose a small training objective, and compare it with the current five-position meta. The interface is a working data product, not a marketing page.

## Direction

One information architecture, two system-controlled appearances:

- Light: Cloud Canvas, based on neutral `#f5f5f7` and white data surfaces.
- Dark: Graphite Pro, based on neutral `#0b0b0d` and `#1c1c1e` data surfaces.
- Theme follows `prefers-color-scheme`; there is no application toggle or duplicated preference.
- Blue is the only interaction accent. Green and red only encode positive and negative outcomes. Amber is reserved for warnings.
- The signature element is the player command band: identity, recent decision metrics, and verified rank in one continuous surface.

## Color tokens

| Token | Light | Dark | Use |
| --- | --- | --- | --- |
| `--background` | `#f5f5f7` | `#0b0b0d` | Page canvas |
| `--surface` | `#ffffff` | `#1c1c1e` | Primary data surface |
| `--surface-muted` | `#f0f0f2` | `#242426` | Controls and quiet rows |
| `--surface-raised` | `#ffffff` | `#2c2c2e` | Selected or floating control |
| `--text-primary` | `#1d1d1f` | `#f5f5f7` | Titles and data |
| `--text-secondary` | `#6e6e73` | `#a1a1a6` | Supporting text |
| `--text-tertiary` | `#9a9aa0` | `#6e6e73` | Metadata |
| `--accent` | `#0071e3` | `#0a84ff` | Commands, focus, selection |
| `--positive` | `#17883e` | `#30d158` | Wins and improvement |
| `--negative` | `#d70015` | `#ff453a` | Losses and regression |
| `--warning` | `#946b00` | `#ffd60a` | Stale or limited evidence |

Do not use decorative gradients, colored page backgrounds, grid textures, neon glows, or broad tinted panels.

## Typography

- Family: `-apple-system`, `BlinkMacSystemFont`, `SF Pro Display`, `SF Pro Text`, `PingFang SC`, system sans-serif.
- Data uses tabular numerals from the same family.
- Product title: 15px/700. Page title: 26-30px/700. Section title: 14-18px/650. Body: 13-14px/400-600. Utility: 10-12px/500-650.
- Avoid 800-900 weights. Letter spacing is always `0`.
- Large type is limited to page-level decisions; compact panels use compact headings.

## Layout

- Maximum workspace width: 1376px, with 24px desktop and 12px mobile gutters.
- Desktop header is a 66px translucent system bar: brand, five-view segmented navigation, share and Pro actions.
- Mobile navigation is a stable five-item bottom bar; page content reserves its safe area.
- Personal dashboard order: search, player command band, training objective, match filters and history, evidence-based side rail.
- Desktop dashboard uses a flexible main column plus a 320px rail. At narrower widths the rail becomes a full-width grid, then a vertical stack.
- Cards are only used for genuine bounded tools. Related table rows share one surface and use hairline separators.
- Match equipment always reserves six inventory slots plus one separated neutral item. Backpack slots are excluded.
- Five-position data uses only STRATZ or user-confirmed positions. Missing positions remain unavailable and are not inferred.

## Shape and depth

- Main surfaces: 8px radius.
- Inputs and segmented controls: 8px radius; inner selected segments: 6px.
- Chips and small item slots: 4-6px radius.
- Light mode may use one low-contrast surface shadow. Dark mode relies on tone and hairlines, not glow.
- Frosted material is limited to the sticky header, mobile navigation, and temporary floating controls.

## Motion

- Hover and press: 140-180ms.
- Tab content entry: 220ms opacity plus 6px vertical movement.
- No bouncing, parallax, ornamental motion, or layout-shifting animation.
- `prefers-reduced-motion: reduce` disables nonessential transitions and animation.

## Components

- Primary command: blue fill, white label, 36px in toolbars and 44px in forms.
- Secondary command: neutral surface with a hairline border. Familiar icon-only commands require a tooltip and accessible label.
- Inputs: 36px dense or 44px full form, neutral inset surface, blue focus ring.
- Segmented controls: one neutral track, one raised selected segment, no colored border around every option.
- Status chips: compact and semantic; color is never decorative.
- Icons: Lucide, normally 15-18px, with stable button dimensions.

## Evidence states

- Verified: scoreboard, STRATZ Ranked Roles position, or hero benchmark exists.
- Parsed: replay timeline or event log exists.
- Limited: only match summary exists.
- Unavailable: the product explicitly declines to infer.

Every coaching claim preserves its evidence state. Missing values remain missing and are never filled from appearance or economy proxies.

## Responsive behavior

- At 1100px the dashboard rail moves below the match workspace and uses three columns.
- At 760px the player metrics and filter controls become horizontally scrollable with stable tracks.
- At 640px the header simplifies, main padding becomes 12px, navigation moves to the bottom, and match rows use a compact two-column layout without hiding equipment.
- Fixed-format controls, item slots, tabs, and charts have stable dimensions so labels cannot shift the page.

## Avoid

- Apple logos, copied Apple marketing composition, oversized hero sections, or landing-page copy.
- Yellow-dominant, green-tinted, purple, or monochromatic blue interfaces.
- Cards inside cards, excessive borders, large decorative shadows, and explanatory text about how to use the interface.
- Unsupported claims about exact position, fight quality, ward coverage, item timing, or AI certainty.
