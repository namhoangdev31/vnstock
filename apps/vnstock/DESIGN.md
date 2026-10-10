# Vnstock Mobile Terminal — Mobile Design System Reference
> Digital Trust, Blueprinted for Mobile. A minimal, high-contrast quantitative financial interface optimized for single-hand mobile ergonomics, anchored in high contrast and a solitary electric blue accent.

**Platform:** Mobile (React Native / Expo / iOS & Android)  
**Theme:** Light & Dark (Color-blocking architecture)  
**Base Viewport:** 390px (375px – 430px responsive range)  
**Ergonomics:** One-hand thumb zone optimization, minimum touch target 44px x 44px

The design system establishes a digital-native financial trust architecture, drawing inspiration from the clarity of Coinbase and Stripe, engineered specifically for mobile screens:
1. **Color-blocking over Shadows:** Blurry drop shadows are eliminated entirely. Visual depth and hierarchy are constructed through crisp, high-contrast flat planes alternating between Pure White (`#ffffff`), Frost (`#f7f8f9`), Midnight (`#0a0b0d`), and Charcoal (`#141519`).
2. **Single Electric Accent:** `Coinbase Blue` (`#0052ff`) is the sole chromatic identifier, reserved exclusively for primary actions (Primary CTA), active navigation states, and brand glyphs.
3. **Mobile-Calibrated Typography:** The typographic scale is tightened for mobile viewports (display caps at 32px instead of desktop 80px), paired with `JetBrains Mono` for all market numbers, execution prices, percentage changes, and ticker codes.

---

## Strict Mobile Rules

1. **Mandatory CSS Tokens (No Arbitrary Colors):**
   - All background colors, text colors, and borders must reference design tokens directly (e.g. `bg-coinbase-blue`, `text-midnight`, `border-pewter`, `bg-frost`).
   - Arbitrary hex codes in component code are strictly prohibited.
2. **Zero Gradients in Code:**
   - Linear or radial gradients are strictly banned. All surfaces, cards, and buttons must be disciplined flat color planes.
3. **Zero Emojis in Text:**
   - Emojis are strictly banned in headers, labels, and tooltips. Use system line icons or typography.
4. **No Explanatory Parentheses in UI Labels:**
   - Never use parentheses in visible text to explain terms or formatting. Use dedicated helper text or tooltips instead.
5. **Touch Ergonomics:**
   - All interactive elements must maintain a minimum touch target of 44px x 44px.
   - Primary action buttons must reside in the lower half of the viewport (Bottom Thumb Zone).

---

## Tokens — Colors

| Name | Hex Value | CSS Token | Mobile Functional Role |
|------|-----------|-----------|------------------------|
| Coinbase Blue | `#0052ff` | `--color-coinbase-blue` | Full-width primary CTA buttons, active tab indicators, brand marks |
| Interactive Blue | `#578bfa` | `--color-interactive-blue` | Text links, secondary interactive elements |
| Pure White | `#ffffff` | `--color-pure-white` | Light mode canvas background, card surface, text on dark backgrounds |
| Midnight | `#0a0b0d` | `--color-midnight` | Dark mode canvas background, primary text on light backgrounds |
| Charcoal | `#141519` | `--color-charcoal` | Dark mode card containers, section contrast separators |
| Frost | `#f7f8f9` | `--color-frost` | Subtle light backgrounds, input field fills, filter chips |
| Cloud | `#eef0f3` | `--color-cloud` | Pressed feedback states, subtle light dividers |
| Pewter | `#dedfe2` | `--color-pewter` | Structural 1px border lines between content blocks |
| Slate | `#5b616e` | `--color-slate` | Secondary body text, exchange labels, helper text |
| Ash | `#8a919e` | `--color-ash` | Placeholder text, disabled component states |
| Positive Green | `#27ad75` | `--color-positive-green` | Price surges, aggressive buy delta, positive PnL badges |
| Negative Red | `#f0616d` | `--color-negative-red` | Price drops, aggressive sell delta, negative PnL badges |

---

## Tokens — Typography (Mobile Calibrated)

### Font Families
- **Display & Headlines:** `Manrope` or `CoinbaseDisplay` (weights 600, 700, track-tight -0.5px) — Delivers confident, declarative titles.
- **Body & UI Controls:** `Inter` or `CoinbaseSans` (weights 400, 600, line-height 1.4 – 1.5) — Maximum legibility at small sizes.
- **Financial Data & Tickers:** `JetBrains Mono` (weight 600, tabular figures) — Mandatory for all tickers (VN30F1M, FPT), live quotes, volumes, basis spreads, PnL, and timestamps.

### Mobile Type Scale

| Role | Family | Weight | Size | Line Height | Letter Spacing | Mobile Usage |
|------|--------|--------|------|-------------|----------------|--------------|
| display | Display | 700 | 32px | 36px (1.12) | -0.6px | Hero banner on Onboarding screen |
| heading-lg | Display | 700 | 26px | 32px (1.23) | -0.4px | Primary screen title on Login / Home |
| heading | Display | 600 | 22px | 28px (1.27) | -0.3px | Widget cards, ATC forecast block headers |
| heading-sm | Sans | 600 | 18px | 24px (1.33) | -0.2px | Subheaders, settings group titles |
| body | Sans | 400 | 15px | 22px (1.46) | 0 | Paragraph copy, market news descriptions |
| subheading | Sans | 500 | 14px | 20px (1.42) | 0 | Input field labels, secondary actions |
| caption | Sans | 400 | 12px | 16px (1.33) | +0.1px | Timestamps, form hint labels |
| micro | Sans | 600 | 10px | 14px (1.40) | +0.3px | Status badges, category pills |
| data-mono | Mono | 600 | 14px | 18px (1.28) | 0 | Stock prices, percentage chips, order sizes |
| data-mono-lg | Mono | 700 | 20px | 24px (1.20) | -0.2px | Account equity balance, large index values |

---

## Tokens — Mobile Spacing & Layout

**Base Grid Unit:** 4px / 8px

### Mobile Spacing Scale
- `--spacing-4`: 4px (Gap between icon and small label)
- `--spacing-8`: 8px (Gap between filter chips, compact padding)
- `--spacing-12`: 12px (Vertical gap between form inputs)
- `--spacing-16`: 16px (Standard screen gutter, card inner padding)
- `--spacing-20`: 20px (Comfortable screen gutter, widget gap)
- `--spacing-24`: 24px (Section separation gap)
- `--spacing-32`: 32px (Top spacing above major headers)

### Mobile Safe Area & Dimensions
- **Screen Horizontal Gutter:** 16px
- **Top App Bar Height:** 52px (excluding status bar inset)
- **Bottom Tab Bar Height:** 60px (plus 34px safe area bottom inset on modern devices)
- **Standard Button Touch Height:** 48px – 52px
- **Input Field Touch Height:** 48px
- **List Row Touch Height:** 64px – 72px

---

## Tokens — Shapes & Border Radius

| Element | Value | Role on Mobile |
|---------|-------|----------------|
| buttons-pill | 48px | Full-width primary CTA buttons (Full pill) |
| buttons-secondary | 48px | Secondary outline and flat buttons |
| cards | 16px | Overview widget containers, forecast cards |
| cards-compact | 12px | Ticker list item cards, quick news tiles |
| bottom-sheet | 24px | Top corner radius for swipeable bottom sheets |
| inputs | 12px | Email and password input containers |
| tags-pill | 9999px | Category filter chips, session badges |
| badges-square | 6px | Step counter badges, HOSE/HNX exchange tags |

---

## Mobile Component Specifications

### 1. Primary Full-Width CTA Button
- **Purpose:** Primary confirmation and form submission action.
- **Dimensions:** Width 100%, height 48px – 52px.
- **Styling:** Solid flat fill `Coinbase Blue` (`#0052ff`), text `Pure White` (`#ffffff`), font weight 600, size 15px, radius 48px (full pill).
- **Active / Pressed State:** Subtle opacity reduction to 85% or tactile scale `scale(0.98)` for haptic response. Strictly no drop shadow.

### 2. Secondary Outline / Frost Pill Button
- **Purpose:** Secondary actions such as PWA install or view details.
- **Dimensions:** Height 48px, radius 48px.
- **Styling:** Background `Frost` (`#f7f8f9`) or 1px border `Pewter` (`#dedfe2`), text `Midnight` (`#0a0b0d`), font weight 600.

### 3. Mobile Form Input Field
- **Purpose:** Clean, accessible input field optimized for the mobile virtual keyboard.
- **Structure:** Label placed above in 13px bold. Input field height 48px, background `Frost` (`#f7f8f9`) in light mode or `Charcoal` (`#141519`) in dark mode, 1px border `Pewter` (`#dedfe2`), border radius 12px, horizontal padding 16px.
- **Focus State:** 1.5px border transition to `Coinbase Blue` (`#0052ff`).

### 4. Financial Ticker List Row
- **Purpose:** Single asset display row in watchlists, screener tables, and search results.
- **Dimensions:** Height 64px, horizontal padding 16px, bottom border 1px `Pewter` (`#dedfe2`).
- **Left Column:** Ticker symbol in bold 15px JetBrains Mono, exchange name below in 12px `Slate`.
- **Right Column:** Current market price in 15px bold JetBrains Mono, with a percentage change pill badge (background `#27ad75`/15 with text `#27ad75` for gains, or `#f0616d`/15 with text `#f0616d` for losses).

### 5. Persistent Bottom Tab Bar
- **Purpose:** Core thumb navigation anchored to the bottom edge.
- **Dimensions:** Height 60px plus safe area bottom inset. Background `Pure White` (`#ffffff`) with top border 1px `Pewter` (`#dedfe2`).
- **4 Primary Tabs:** Home, Derivatives, Equities, Settings.
- **Active State:** Icon and label in `Coinbase Blue` (`#0052ff`).
- **Inactive State:** Icon and label in `Slate` (`#5b616e`).

### 6. Bottom Sheet Modal
- **Purpose:** Fast filter selection, order ticket placement, or detailed breakdowns without page transitions.
- **Styling:** Top border radius 24px, centered drag handle (width 36px, height 4px, rounded pill) in `Pewter`, background `Pure White` or `Midnight`.

---

## Do's and Don'ts (Mobile Specific)

### Do
- Maintain a consistent 16px screen gutter across all views.
- Anchor primary CTA buttons to the bottom thumb reach area.
- Use `JetBrains Mono` for all financial figures to guarantee clean tabular alignment.
- Establish visual depth through high-contrast flat color blocks (`#ffffff` vs `#0a0b0d` and `#f7f8f9`).
- Ensure all touch targets meet or exceed the 44px x 44px threshold.

### Don't
- Never use blurry drop shadows to convey elevation — use flat color blocking instead.
- Never use gradients anywhere in the mobile codebase.
- Never use emojis in UI labels or headers.
- Never use parentheses in labels to provide definitions or explanations.
- Never exceed 32px for mobile display headlines to prevent viewport overflow.
- Never allow uncontained horizontal table overflow without explicit swipe mechanics.

---

## Agent Prompt Guide for Stitch (Mobile-Specific Examples)

### Example Prompt: Mobile Onboarding Screen
```text
A high-converting, clean mobile onboarding screen for Vnstock Mobile Terminal. Viewport mobile 390x844.

Visual Style: High-contrast light and dark color-blocking inspired by Coinbase. Canvas Pure White #ffffff, high-contrast section Midnight #0a0b0d, primary brand accent Coinbase Blue #0052ff, positive green #27ad75, borders Pewter #dedfe2. Numeric values in JetBrains Mono font. Strictly zero gradients, zero blurry shadows, zero emojis.

Layout & Hierarchy:
1. Top Bar: Subtle clean header with brand mark: 36px blue square in #0052ff, rounded 8px, letter V in white. Title "Vnstock Mobile" in 18px Manrope bold.
2. Hero Visual Mockup: A crisp floating market terminal card with Midnight #0a0b0d background, rounded 16px, padding 16px:
   - Header: "VN30F1M" in white JetBrains Mono 15px, live price "1,315.60", change tag "+12.40 (+0.95%)" in #27ad75.
   - Micro chart sparkline in #578bfa with horizontal VWAP guide.
   - Two metric chips: "Dự báo ATC: 1,288.0" and "Độ lệch Basis: -2.1".
3. Headline Section: Bold Manrope headline 26px in #0a0b0d: "Nắm bắt thị trường trong tầm tay". Subtitle in 14px #5b616e: "Hệ thống phân tích định lượng độc lập và tối ưu vị thế phái sinh theo thời gian thực".
4. Two Compact Feature Tiles: 2-column horizontal grid of Frost #f7f8f9 cards, rounded 12px, padding 12px:
   - Tile 1: Badge "3 ENGINES", title "Phân tích đa chiều", subtitle "Kỹ thuật, dòng tiền, xác suất".
   - Tile 2: Badge "SIMULATION", title "Sổ lệnh mô phỏng", subtitle "Khởi điểm 1 tỷ VND an toàn".
5. Thumb-Zone Action Dock: Bottom container with full-width primary pill button "Bắt đầu ngay" in #0052ff, text white bold 15px, height 48px, rounded 48px. Below is secondary pill button "Cài đặt ứng dụng PWA" in #f7f8f9, text #0a0b0d. Bottom link "Đã có tài khoản? Đăng nhập".
```

### Example Prompt: Mobile Login Screen
```text
A focused, distraction-free mobile login screen for Vnstock Mobile Terminal. Viewport mobile 390x844.

Visual Style: Light theme with architectural clarity. Canvas Pure White #ffffff, fields Frost #f7f8f9 with border Pewter #dedfe2, primary action Coinbase Blue #0052ff, text Midnight #0a0b0d, helper text Slate #5b616e. Strict zero gradients, zero emojis.

Layout & Hierarchy:
1. Top Bar: Minimalist back arrow button on top left (height 44px).
2. Header: Large bold headline 26px Manrope "Đăng nhập", subtitle 14px #5b616e "Truy cập tài khoản định lượng của bạn".
3. Form Container:
   - Field 1: Top label "Địa chỉ email" 13px bold #0a0b0d. Input container height 48px, background #f7f8f9, 1px border #dedfe2, rounded 12px, placeholder "investor@vnstock.com" in JetBrains Mono.
   - Field 2: Top label "Mật khẩu" with right-aligned link "Quên mật khẩu" in #0052ff. Input container height 48px, secure masked text with eye toggle icon on the right.
   - Checkbox: Square flat checkbox in #dedfe2 with label "Ghi nhớ phiên đăng nhập trên máy này" in 13px #5b616e.
4. Primary Action: Full-width button "Đăng nhập tài khoản" in solid #0052ff, text white bold 15px, height 48px, rounded 48px.
5. Biometric Row: Secondary button height 48px in #f7f8f9 with fingerprint line icon and text "Đăng nhập nhanh bằng vân tay".
6. Bottom Switcher: Bottom center text "Chưa có tài khoản? Đăng ký thành viên mới" with link in #0052ff.
```

---

## Quick Start — CSS & Tailwind Configuration

### CSS Custom Properties
```css
:root {
  /* Colors */
  --color-coinbase-blue: #0052ff;
  --color-interactive-blue: #578bfa;
  --color-pure-white: #ffffff;
  --color-midnight: #0a0b0d;
  --color-slate: #5b616e;
  --color-ash: #8a919e;
  --color-frost: #f7f8f9;
  --color-cloud: #eef0f3;
  --color-pewter: #dedfe2;
  --color-charcoal: #141519;
  --color-positive-green: #27ad75;
  --color-negative-red: #f0616d;

  /* Typography Families */
  --font-display: 'Manrope', ui-sans-serif, system-ui, -apple-system, sans-serif;
  --font-sans: 'Inter', ui-sans-serif, system-ui, -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, monospace;

  /* Mobile Type Scale */
  --text-display: 32px;
  --text-heading-lg: 26px;
  --text-heading: 22px;
  --text-heading-sm: 18px;
  --text-body: 15px;
  --text-subheading: 14px;
  --text-caption: 12px;
  --text-micro: 10px;

  /* Mobile Spacing & Layout */
  --spacing-unit: 8px;
  --spacing-4: 4px;
  --spacing-8: 8px;
  --spacing-12: 12px;
  --spacing-16: 16px;
  --spacing-20: 20px;
  --spacing-24: 24px;
  --spacing-32: 32px;
  --mobile-gutter: 16px;
  --touch-target-min: 44px;
  --button-height: 48px;
  --tab-bar-height: 60px;

  /* Border Radius */
  --radius-pill: 48px;
  --radius-card: 16px;
  --radius-card-sm: 12px;
  --radius-input: 12px;
  --radius-badge: 6px;
  --radius-full: 9999px;
}
```

### Tailwind v4 `@theme`
```css
@theme {
  /* Colors */
  --color-coinbase-blue: #0052ff;
  --color-interactive-blue: #578bfa;
  --color-pure-white: #ffffff;
  --color-midnight: #0a0b0d;
  --color-slate: #5b616e;
  --color-ash: #8a919e;
  --color-frost: #f7f8f9;
  --color-cloud: #eef0f3;
  --color-pewter: #dedfe2;
  --color-charcoal: #141519;
  --color-positive-green: #27ad75;
  --color-negative-red: #f0616d;

  /* Typography Families */
  --font-display: 'Manrope', ui-sans-serif, system-ui, sans-serif;
  --font-sans: 'Inter', ui-sans-serif, system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, monospace;

  /* Mobile Scale */
  --text-display: 32px;
  --text-heading-lg: 26px;
  --text-heading: 22px;
  --text-heading-sm: 18px;
  --text-body: 15px;
  --text-subheading: 14px;
  --text-caption: 12px;
  --text-micro: 10px;

  /* Radii */
  --radius-pill: 48px;
  --radius-card: 16px;
  --radius-card-sm: 12px;
  --radius-input: 12px;
  --radius-badge: 6px;
  --radius-full: 9999px;
}
```
