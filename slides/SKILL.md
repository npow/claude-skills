---
name: slides
description: Turns bullet points, research, or structured content into a browser-based Reveal.js slide deck. Use when the user asks to create slides, a presentation, a deck, a slideshow, or says "present this", "turn this into slides", "make a deck", or mentions keynote, powerpoint, or reveal.
allowed-tools: Write, Edit, mcp__chrome-devtools__new_page, mcp__chrome-devtools__wait_for, mcp__chrome-devtools__take_screenshot
---

# Slides

Converts content from the conversation into a Reveal.js HTML slide deck, writes it to /tmp/slides.html, and opens it live in the browser.

## Workflow

1. **Extract content structure** — identify the title, sections, and key points from the conversation or user-supplied content. See [TEMPLATE.md](TEMPLATE.md) for content chunking rules.
2. **Plan slide types and count** — assign each section a slide type: title, bullet, two-column, quote, or code. Max 6 bullets per slide; split if more. See [TEMPLATE.md](TEMPLATE.md) for slide type patterns.
3. **Write /tmp/slides.html** — use the complete Reveal.js template with all CDN links in correct order. See [TEMPLATE.md](TEMPLATE.md) for the full template.
4. **Open in browser** — call `mcp__chrome-devtools__new_page` with `url: file:///tmp/slides.html`.
5. **Wait for render** — call `mcp__chrome-devtools__wait_for` on the title slide's main heading text. Timeout 10000ms.
6. **Take screenshot** — call `mcp__chrome-devtools__take_screenshot` and verify the first slide is styled and readable.
7. **Tell user how to navigate** — reply: "arrow keys to navigate, F for fullscreen". See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) if slide rendering looks wrong.

## Self-review checklist

Before delivering, verify ALL:

- [ ] Screenshot shows a styled dark slide — not plain unstyled HTML text on a white background
- [ ] Heading text is mixed-case, not ALL CAPS (custom CSS override applied)
- [ ] No slide has more than 6 bullet points
- [ ] CDN links appear in correct order: reveal.css, then black.css theme, then reveal.js
- [ ] Reveal.initialize() is called with hash: true, transition: 'slide', backgroundTransition: 'fade'
- [ ] wait_for was called before take_screenshot
- [ ] User was told: arrow keys to navigate, F for fullscreen

## Golden rules

Hard rules. Never violate these.

1. **Never allow headings to render uppercase.** Always include `.reveal h1, .reveal h2 { text-transform: none; }` in custom CSS. Reveal.js default forces uppercase and it looks bad.
2. **Never put more than 6 bullet points on one slide.** Split into two consecutive slides with a shared heading if needed (e.g. "Key Points (1/2)" and "Key Points (2/2)").
3. **Always load theme CSS after reveal.css.** The order is: reveal.css, then theme/black.css. Reversed order silently breaks all theming.
4. **Always use hash: true in Reveal.initialize.** This enables deep-linking to slides by index.
5. **Always call wait_for before take_screenshot.** Wait on the title text. Screenshotting before Reveal renders produces a blank white image.
6. **Always use new_page for first open.** Use mcp__chrome-devtools__new_page with url: file:///tmp/slides.html. Never navigate an existing page to a file:// URL.

## Reference files

| File | Contents |
|------|----------|
| [TEMPLATE.md](TEMPLATE.md) | Complete Reveal.js HTML template, all slide type patterns, content chunking rules |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Failure diagnosis table: symptoms, causes, fixes |
