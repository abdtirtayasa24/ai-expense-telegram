---
name: "AI Telegram Expense Tracker"
description: "A premium, trustworthy, practical Telegram Mini App for Indonesian personal finance tracking."
colors:
  telegram-blue: "#2374e1"
  telegram-blue-strong: "#1859ad"
  telegram-blue-soft: "#bfd5f5"
  ledger-ink: "#0f172a"
  body-ink: "#172033"
  muted-ink: "#526173"
  soft-ink: "#6b7b91"
  cool-porcelain: "#f4f7fb"
  surface: "#ffffff"
  surface-soft: "#fbfdff"
  surface-muted: "#f6f9fd"
  blue-tint: "#edf4ff"
  border-strong: "#dce5f2"
  border-soft: "#e5edf7"
  border-input: "#cfd9e8"
  success: "#087443"
  success-fill: "#12b76a"
  danger: "#b42318"
  danger-fill: "#f04438"
  chart-blue: "oklch(58% 0.2 255)"
  chart-green: "oklch(64% 0.17 155)"
  chart-amber: "oklch(72% 0.17 75)"
  chart-red-orange: "oklch(62% 0.2 30)"
  chart-cyan: "oklch(60% 0.16 205)"
  chart-violet-muted: "oklch(56% 0.12 285)"
  danger-tint: "#fff1f1"
  danger-surface: "#fff7f7"
  danger-border: "#fecaca"
typography:
  display:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "clamp(2rem, 7vw, 4rem)"
    fontWeight: 800
    lineHeight: 1
  headline:
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "clamp(1.4rem, 4vw, 2rem)"
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
    textColor: "{colors.surface}"
    rounded: "{rounded.pill}"
    padding: "10px 16px"
  button-secondary:
    backgroundColor: "{colors.blue-tint}"
    textColor: "#1859ad"
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
    backgroundColor: "{colors.surface}"
    textColor: "{colors.body-ink}"
    rounded: "{rounded.field}"
    padding: "10px 12px"
---

# Design System: AI Telegram Expense Tracker

## 1. Overview

**Creative North Star: "The Private Ledger"**

The interface should feel like a private financial ledger made for a modern Telegram workflow: personal, quiet, premium enough to trust, and practical enough to use every day. It is a product UI, not a campaign page, so design serves the user's next action: check cashflow, add a transaction, adjust a budget, or ask the advisor a grounded question.

The visual system is restrained and cool-toned. White panels sit on Cool Porcelain backgrounds with Telegram Blue used sparingly for primary action, focus, and progress. Rounded shapes and measured shadows create a premium panel feel without becoming flashy fintech or corporate BI.

This system explicitly rejects flashy fintech marketing, crypto dashboards, generic corporate dashboards, purple AI-product slop, colorful decorative pages, heavy gradients, overdesigned metrics, and attention-seeking effects.

**Key Characteristics:**
- Cool neutral surfaces with one functional accent.
- Soft, premium panel depth reserved for major containers.
- Tactile, confident controls with large rounded touch targets.
- Indonesian-first copy with direct, practical hierarchy.
- Data UI that feels personal and private, not performative.

## 2. Colors

The palette is a restrained cool-blue product palette: Ledger Ink for authority, Cool Porcelain for calm, and Telegram Blue for action only.

### Primary
- **Telegram Blue**: The only primary accent. Use it for primary buttons, progress fills, focus rings, and active interactive emphasis. It should remain rare enough to feel decisive.
- **Telegram Blue Strong**: Darker blue text for secondary buttons and accessible blue-on-tint states.
- **Telegram Blue Soft**: Subtle hover border for tactile menu cards; never use it as a decorative fill.

### Neutral
- **Ledger Ink**: Primary heading and high-emphasis text. Use for titles, transaction names, and important values.
- **Body Ink**: Default readable text for app content.
- **Muted Ink**: Secondary descriptions, helper text, and low-emphasis labels.
- **Soft Ink**: Metadata and small supporting text; do not use below accessible contrast on tinted surfaces.
- **Cool Porcelain**: App background. It keeps the Mini App calm without using beige, cream, or warm paper defaults.
- **Surface White**: Main panel and modal background.
- **Soft Surface**: Inner card and form surface.
- **Muted Surface**: Summary tiles, loading states, and quiet containers.
- **Blue Tint**: Secondary buttons, chat user bubbles, and progress tracks.
- **Strong Border / Soft Border / Input Border**: Use borders to define structure before reaching for more shadow.

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

**Character:** The system uses one clear sans-serif family across headings, labels, controls, and data. Weight carries hierarchy more than font changes, which keeps the product practical and trustworthy inside Telegram's mobile webview.

### Hierarchy
- **Display** (800, clamp(2rem, 7vw, 4rem), 1): Dashboard greeting and authentication states only. Keep it short and readable on mobile.
- **Headline** (800, clamp(1.4rem, 4vw, 2rem), ~1.2): Page section titles and form panel headings.
- **Title** (800, 1.05rem, 1.2): Card titles, menu card titles, and branded labels.
- **Body** (400, 1rem, 1.6): Descriptions, advisor text, empty states, and content paragraphs. Cap longer prose around 65ch.
- **Label** (600, 0.9rem, 1.35): Form labels and compact UI descriptions.
- **Small Metadata** (500-700, 0.8rem-0.88rem): Category labels, pagination, and supplementary finance details.

### Named Rules
**The One-Family Rule.** Do not introduce display fonts, serif flourishes, or mono-forward dashboard styling. This is a private finance tool, not a brand poster.

**The No-Eyebrow-Spam Rule.** Tiny uppercase tracked labels are allowed only when they clarify state or page context. Do not place decorative uppercase kickers above every section.

## 4. Elevation

The system uses premium panel depth: major surfaces may use soft ambient shadows, while inner cards rely on tonal backgrounds and borders. Shadow is structural, not decorative. The main screen should feel layered and touchable, but never like glassmorphism or a marketing hero.

### Shadow Vocabulary
- **Hero Lift** (`box-shadow: 0 24px 80px rgb(26 41 61 / 12%)`): Use for the primary authentication or dashboard hero surface.
- **Panel Lift** (`box-shadow: 0 16px 48px rgb(26 41 61 / 10%)`): Use for page headers, page menus, and main CRUD/advisor panels.
- **Compact Lift** (`box-shadow: 0 12px 36px rgb(26 41 61 / 8%)`): Use for the compact brand bar or low-height persistent containers.
- **Modal Lift** (`box-shadow: 0 24px 80px rgb(15 23 42 / 28%)`): Use only for modal dialogs over a dim backdrop.

### Named Rules
**The Main-Panel-Only Rule.** Shadows belong on major containers and modals. Inner cards, list items, forms, and tiles use borders and tonal fills instead.

**The No-Glass Rule.** Do not add blur-backed glass cards or translucent panels unless a specific overlay problem requires it.

## 5. Components

### Buttons
- **Shape:** Confident pill controls (999px radius).
- **Primary:** Telegram Blue fill with white text and 10px 16px padding. Use for the single main action in a form or chat composer.
- **Hover / Focus:** Keep hover subtle. Focus must remain visible with the existing blue focus ring. Disabled buttons reduce opacity and show wait cursor.
- **Secondary:** Blue Tint background with darker blue text. Use for back, retry, pagination, and cancel actions.
- **Danger:** Danger Tint background with Danger Red text. Use only for destructive actions.

### Cards / Containers
- **Corner Style:** Main panels use generous rounded shells (24px-28px). Inner cards use 18px-20px.
- **Background:** Main panels are Surface White; nested surfaces use Soft Surface or Muted Surface.
- **Shadow Strategy:** Follow the Main-Panel-Only Rule. Do not add shadows to every card in a grid.
- **Border:** Use 1px cool borders for structure (`#dce5f2`, `#e5edf7`, `#cfd9e8`).
- **Internal Padding:** Main panels use responsive panel padding; inner cards use 14px-18px.

### Inputs / Fields
- **Style:** White fields with a 1px Input Border, 12px radius, inherited typography, and 10px 12px padding.
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
- **Style:** User messages use Blue Tint and Body Ink; assistant messages use Muted Surface and Muted Ink.
- **Behavior:** Keep chat input compact and task-first. Advisor output should feel like a practical note, not a chatbot spectacle.

## 6. Do's and Don'ts

### Do:
- **Do** use Telegram Blue as the only primary accent and keep it below roughly 10% of a screen.
- **Do** keep major panels premium with 24px-28px corners, 1px cool borders, and restrained ambient shadow.
- **Do** rely on Ledger Ink for headings and values so finance data remains easy to scan.
- **Do** preserve visible focus states on every button, input, and select.
- **Do** communicate income, expense, danger, and over-budget states with both color and text or accessible labels.
- **Do** keep mobile charts compact: interactive category donut for share-of-expense, horizontal bars for monthly trends.
- **Do** keep Indonesian UI copy direct, practical, and free of financial jargon.

### Don't:
- **Don't** make it flashy fintech marketing, crypto dashboards, generic corporate BI dashboards, purple AI-product slop, or colorful decorative pages.
- **Don't** add heavy gradients, gradient text, neon accents, glassmorphism, or decorative blur panels.
- **Don't** introduce purple as an AI cue, even as a secondary accent; muted violet is permitted only as a categorical chart slice when needed for distinction.
- **Don't** use line charts for the current mobile monthly trend card unless the layout is redesigned with enough horizontal space.
- **Don't** turn dashboard metrics into overdesigned hero-stat cards.
- **Don't** use side-stripe borders as colored accents on cards, list items, callouts, or alerts.
- **Don't** place tiny uppercase tracked eyebrows above every section as decoration.
- **Don't** use color alone to explain status; pair it with readable labels, values, or helper text.
