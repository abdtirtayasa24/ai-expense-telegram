---
name: "AI Telegram Expense Tracker"
description: "A premium, trustworthy, practical Telegram Mini App for Indonesian personal finance tracking."
colors:
  telegram-blue: "#3390ec"
  telegram-blue-strong: "#62b0ff"
  telegram-blue-soft: "#40698f"
  ledger-ink: "#f5f8fc"
  body-ink: "#dbe5f1"
  muted-ink: "#a8b6c7"
  soft-ink: "#7f91a6"
  telegram-night: "#17212b"
  surface: "#1e2a36"
  surface-soft: "#23313f"
  surface-muted: "#182532"
  blue-tint: "#203a56"
  border-strong: "#334457"
  border-soft: "#2b3a4a"
  border-input: "#3a4d60"
  success: "#8ee6b3"
  success-fill: "#3ed47f"
  danger: "#ff9a91"
  danger-fill: "#ff6b61"
  chart-blue: "oklch(58% 0.2 255)"
  chart-green: "oklch(64% 0.17 155)"
  chart-amber: "oklch(72% 0.17 75)"
  chart-red-orange: "oklch(62% 0.2 30)"
  chart-cyan: "oklch(60% 0.16 205)"
  chart-violet-muted: "oklch(56% 0.12 285)"
  danger-tint: "#3b2429"
  danger-surface: "#2c2026"
  danger-border: "#70414a"
typography:
  display:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "2.25rem"
    fontWeight: 800
    lineHeight: 1.05
  headline:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "1.4rem"
    fontWeight: 800
    lineHeight: 1.2
  title:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "1.05rem"
    fontWeight: 800
    lineHeight: 1.2
  body:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "0.9rem"
    fontWeight: 600
    lineHeight: 1.35
rounded:
  field: "12px"
  message: "16px"
  item: "18px"
  card: "20px"
  shell: "24px"
  hero: "28px"
  pill: "999px"
spacing:
  xs: "6px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "20px"
  page: "24px"
  panel: "clamp(20px, 5vw, 32px)"
  hero: "clamp(24px, 6vw, 48px)"
components:
  button-primary:
    backgroundColor: "{colors.telegram-blue}"
    textColor: "#f8fbff"
    rounded: "{rounded.pill}"
    padding: "10px 16px"
  button-secondary:
    backgroundColor: "{colors.blue-tint}"
    textColor: "{colors.telegram-blue-strong}"
    rounded: "{rounded.pill}"
    padding: "10px 16px"
  button-danger:
    backgroundColor: "{colors.danger-tint}"
    textColor: "{colors.danger}"
    rounded: "{rounded.pill}"
    padding: "10px 16px"
  card-main:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.body-ink}"
    rounded: "{rounded.shell}"
    padding: "{spacing.panel}"
  card-inner:
    backgroundColor: "{colors.surface-soft}"
    textColor: "{colors.body-ink}"
    rounded: "{rounded.card}"
    padding: "16px"
  input-field:
    backgroundColor: "#172331"
    textColor: "{colors.body-ink}"
    rounded: "{rounded.field}"
    padding: "10px 12px"
---

# Design System: AI Telegram Expense Tracker

## 1. Overview

**Creative North Star: "The Private Ledger"**

The interface should feel like a private financial ledger made for a modern Telegram workflow: personal, quiet, premium enough to trust, and practical enough to use every day. It is a product UI, not a campaign page, so design serves the user's next action: check cashflow, add a transaction, adjust a budget, or ask the advisor a grounded question.

The visual system now uses a Telegram dark-mode base: deep blue-gray app chrome, quiet layered surfaces, readable light ink, and Telegram Blue used sparingly for primary actions, focus, and progress. Advisor text borrows from Claude's calm reading experience: generous line-height, prose-width assistant messages, and formatted practical notes instead of dense chat blobs.

This system explicitly rejects flashy fintech marketing, crypto dashboards, generic corporate dashboards, purple AI-product slop, colorful decorative pages, heavy gradients, overdesigned metrics, and attention-seeking effects.

**Key Characteristics:**
- Telegram dark-mode surfaces with one functional accent.
- Soft, premium panel depth reserved for major containers.
- Tactile, confident controls with large rounded touch targets.
- Indonesian-first copy with direct, practical hierarchy.
- Data UI that feels personal and private, not performative.

## 2. Colors

The palette is a restrained Telegram dark product palette: Telegram Night for the app background, layered blue-gray surfaces for panels and cards, readable light ink for content, and Telegram Blue for action only.

### Primary
- **Telegram Blue**: The only primary accent. Use it for primary buttons, progress fills, focus rings, and active interactive emphasis. It should remain rare enough to feel decisive.
- **Telegram Blue Strong**: Bright blue text for secondary buttons and accessible blue-on-dark states.
- **Telegram Blue Soft**: Subtle hover border for tactile menu cards; never use it as a decorative fill.

### Neutral
- **Ledger Ink**: Primary heading and high-emphasis text on dark surfaces. Use for titles, transaction names, and important values.
- **Body Ink**: Default readable text for app content.
- **Muted Ink**: Secondary descriptions, helper text, and low-emphasis labels.
- **Soft Ink**: Metadata and compact supporting text; do not use below accessible contrast.
- **Telegram Night**: App background. It mirrors Telegram dark mode without becoming black-terminal UI.
- **Surface**: Main panel and modal background.
- **Soft Surface**: Inner card and form surface.
- **Muted Surface**: Summary tiles, loading states, transaction rows, and quiet containers.
- **Blue Tint**: Secondary buttons, chat user bubbles, and progress tracks.
- **Strong Border / Soft Border / Input Border**: Use low-contrast dark borders to define structure before reaching for more shadow.

### Tertiary
- **Success Green**: Income and positive status. Pair with text or labels; do not rely on green alone.
- **Danger Red**: Expenses, delete actions, over-budget states, and errors. Use tinted danger backgrounds for error containers.

### Data Visualization
- **Chart Blue / Green / Amber / Red-Orange / Cyan / Muted Violet**: Reserved for categorical chart slices only, especially the interactive category donut. These are not brand accents and must not become decorative page color.

### Named Rules
**The One Accent Rule.** Telegram Blue is the only brand accent family. Strong and soft blue variants are state helpers only, not new brand colors. Categorical chart colors are allowed only inside data visualization. Do not introduce purple AI cues, neon, rainbow, or decorative palette expansions.

**The Calm Finance Rule.** State colors are functional only. Success and danger communicate meaning; they never become decorative page color.

## 3. Typography

**Display Font:** Inter, falling back to system sans-serif.
**Body Font:** Inter, falling back to system sans-serif.
**Label/Mono Font:** No distinct mono or label family exists.

**Character:** The system uses one clear sans-serif family across headings, labels, controls, and data. Weight, line-height, and prose width carry hierarchy more than font changes, keeping the product practical inside Telegram's mobile webview and readable like a calm assistant surface.

### Hierarchy
- **Display** (800, 2.25rem, ~1.05): Dashboard greeting and authentication states only. Keep it short and readable on mobile.
- **Headline** (800, 1.4rem, ~1.2): Page section titles and form panel headings.
- **Title** (800, 1.05rem, 1.2): Card titles, menu card titles, and branded labels.
- **Body** (400, 1rem, 1.6): Descriptions, advisor text, empty states, and content paragraphs. Cap longer prose around 65ch.
- **Label** (600, 0.9rem, 1.35): Form labels and compact UI descriptions.
- **Small Metadata** (500-700, 0.8rem-0.88rem): Category labels, pagination, and supplementary finance details.

### Named Rules
**The One-Family Rule.** Do not introduce display fonts, serif flourishes, or mono-forward dashboard styling. This is a private finance tool, not a brand poster.

**The No-Eyebrow-Spam Rule.** Tiny uppercase tracked labels are allowed only when they clarify state or page context. Do not place decorative uppercase kickers above every section.

## 4. Elevation

The system uses dark premium panel depth: major surfaces may use soft black ambient shadows, while inner cards rely on tonal blue-gray backgrounds and borders. Shadow is structural, not decorative. The main screen should feel layered and touchable, but never like glassmorphism or a marketing hero.

### Shadow Vocabulary
- **Hero Lift** (`box-shadow: 0 24px 80px rgb(0 0 0 / 32%)`): Use for the primary authentication or dashboard hero surface.
- **Panel Lift** (`box-shadow: 0 18px 56px rgb(0 0 0 / 26%)`): Use for page headers, page menus, and main CRUD/advisor panels.
- **Compact Lift** (`box-shadow: 0 12px 36px rgb(0 0 0 / 22%)`): Use for the compact brand bar or low-height persistent containers.
- **Modal Lift** (`box-shadow: 0 26px 90px rgb(0 0 0 / 56%)`): Use only for modal dialogs over a dim backdrop.

### Named Rules
**The Main-Panel-Only Rule.** Shadows belong on major containers and modals. Inner cards, list items, forms, and tiles use borders and tonal fills instead.

**The No-Glass Rule.** Do not add blur-backed glass cards or translucent panels unless a specific overlay problem requires it.

## 5. Components

### Buttons
- **Shape:** Confident pill controls (999px radius).
- **Primary:** Telegram Blue fill with near-white text and 10px 16px padding. Use for the single main action in a form or chat composer.
- **Hover / Focus:** Keep hover subtle. Focus must remain visible with the existing blue focus ring. Disabled buttons reduce opacity and show wait cursor.
- **Secondary:** Blue Tint background, soft border, and bright blue text. Use for back, retry, pagination, and cancel actions.
- **Danger:** Danger Tint background, danger border, and Danger Red text. Use only for destructive actions.

### Cards / Containers
- **Corner Style:** Main panels use generous rounded shells (24px-28px). Inner cards use 18px-20px.
- **Background:** Main panels use Surface; nested surfaces use Soft Surface or Muted Surface.
- **Shadow Strategy:** Follow the Main-Panel-Only Rule. Do not add shadows to every card in a grid.
- **Border:** Use 1px dark blue-gray borders for structure (`#334457`, `#2b3a4a`, `#3a4d60`).
- **Internal Padding:** Main panels use responsive panel padding; inner cards use 14px-18px.

### Inputs / Fields
- **Style:** Dark fields with a 1px Input Border, 12px radius, inherited typography, and 10px 12px padding.
- **Focus:** Use the blue focus ring consistently on inputs, selects, and buttons.
- **Error / Disabled:** Error states use Danger Tint or Danger Surface with Danger Red text. Disabled states should remain readable and obviously inactive.

### Navigation
- **Style:** The current navigation is a menu grid of tactile cards beneath the dashboard summary. Menu cards use Soft Surface, Soft Border, bold titles, and muted descriptions.
- **Hover / Active:** Hover shifts border to a stronger blue-tinted border and the surface to Muted Surface. Avoid full-blue inactive menu cards.
- **Mobile:** Collapse menu and dashboard grids to one column under 760px.

### Data Lists, Charts, and Progress
- **Transaction rows:** Mobile-first compact rows. Transaction name/meta stay left; amount plus Edit/Hapus actions stay right even on mobile. Use accessible symbols for transaction type (`↗` pemasukan, `↘` pengeluaran) and short Indonesian dates such as `27 Jun`.
- **Category donut:** Category breakdown uses a dependency-free SVG donut. It is interactive by hover/focus/tap, defaults to an unselected total state, and shows selected category details only after interaction. Legend chips must be compact and wrap safely on mobile.
- **Trend bars:** Monthly trend uses dual horizontal bars, not a line chart, because bars remain readable in narrow mobile cards. Keep month labels and net cashflow text compact so the bars have enough width.
- **Budget progress:** Tracks use Blue Tint; fills use Telegram Blue for neutral progress, Success Green for income/healthy remaining states, and Danger Red for over-budget states.
- **Over Budget:** Use Danger Surface and Danger Border plus explicit text/percentage; do not rely on red alone.

### Advisor Chat
- **Style:** User messages use a Telegram-style blue bubble aligned to the right. Assistant messages use a quiet dark surface, readable Body Ink, and prose width around 65-70ch.
- **Behavior:** Keep chat input compact and task-first. Advisor output should feel like a Claude-style practical note: formatted paragraphs/lists, generous line-height, no spectacle.

## 6. Do's and Don'ts

### Do:
- **Do** use a Telegram dark-mode base for Mini App surfaces.
- **Do** use Telegram Blue as the only primary accent and keep it below roughly 10% of a screen.
- **Do** keep major panels premium with 24px-28px corners, 1px dark blue-gray borders, and restrained ambient shadow.
- **Do** rely on Ledger Ink for headings and values so finance data remains easy to scan.
- **Do** preserve visible focus states on every button, input, and select.
- **Do** communicate income, expense, danger, and over-budget states with both color and text or accessible labels.
- **Do** keep mobile charts compact: interactive category donut for share-of-expense, horizontal bars for monthly trends.
- **Do** keep advisor chat readable like a Claude-style practical note: prose-width assistant messages, formatted paragraphs/lists, and generous line-height.
- **Do** keep Indonesian UI copy direct, practical, and free of financial jargon.

### Don't:
- **Don't** make it flashy fintech marketing, crypto dashboards, generic corporate BI dashboards, purple AI-product slop, or colorful decorative pages.
- **Don't** add heavy gradients, gradient text, neon accents, glassmorphism, decorative blur panels, or black terminal-style styling.
- **Don't** introduce purple as an AI cue, even as a secondary accent; muted violet is permitted only as a categorical chart slice when needed for distinction.
- **Don't** use line charts for the current mobile monthly trend card unless the layout is redesigned with enough horizontal space.
- **Don't** turn dashboard metrics into overdesigned hero-stat cards.
- **Don't** use side-stripe borders as colored accents on cards, list items, callouts, or alerts.
- **Don't** place tiny uppercase tracked eyebrows above every section as decoration.
- **Don't** use color alone to explain status; pair it with readable labels, values, or helper text.
