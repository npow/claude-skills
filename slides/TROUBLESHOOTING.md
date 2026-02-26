# Slides Troubleshooting

Failure diagnosis for Reveal.js slide decks. Use this table when the screenshot or visual output looks wrong.

## Failure Diagnosis Table

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Screenshot shows plain text on white background, no dark theme | Theme CSS failed to load, or CSS link order is wrong | Verify reveal.css appears before theme/black.css in `<head>`. Both CDN URLs must use the exact version `5.0.5`. |
| All headings render in ALL CAPS | Custom CSS override is missing | Add `.reveal h1, .reveal h2 { text-transform: none; }` inside a `<style>` block in `<head>`. |
| Screenshot is entirely blank or white | Reveal.js CDN JS failed to load, or `Reveal.initialize()` not called | Confirm the `<script src="...reveal.js">` tag is present after the `.reveal` div. Confirm `Reveal.initialize(...)` is called in the inline script. |
| wait_for times out — title text never appears | Reveal.js did not initialize; HTML file was not written before new_page was called | Verify the file was written successfully with Write tool before calling new_page. Check that the title text string passed to wait_for exactly matches the h1 text in the HTML. |
| Vertical slides not navigating with down arrow | Parent section has direct content in addition to child sections | The parent `<section>` of a vertical group must contain only child `<section>` elements — no direct `<h2>`, `<p>`, or `<ul>` content at the parent level. |
| Bullet list is right-aligned or centered | Missing `.reveal ul { text-align: left; }` in custom CSS | Add `text-align: left` to the ul rule in the `<style>` block. |
| Two-column layout collapses into single column | `.two-col` CSS class missing from `<style>` block | Ensure the template's full `<style>` block is included, including `.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 2em; }`. |
| Code block shows as plain text without monospace font | Code is inside a `<li>` or `<p>` instead of `<pre><code>` | Move code content into a `<pre><code>...</code></pre>` block. Never put code samples inside bullet lists. |
| Navigation keys (arrow keys) not working | Reveal.js failed to initialize — likely JS CDN failure | Open browser console via evaluate_script and check for errors. If CDN is unreachable, there is no offline fallback — verify network access. |
| Slides render but `hash: true` deep-linking broken | Reveal.initialize called without `hash: true` | Confirm the initialize call is `Reveal.initialize({ hash: true, transition: 'slide', backgroundTransition: 'fade' })`. |
| Screenshot taken before slide renders — shows loading state | take_screenshot called before wait_for resolved | Always call wait_for with the title text and wait for it to succeed before calling take_screenshot. |
| Theme applied but slide background is not dark | reveal.css is missing and only theme CSS was included | Both CDN links are required: reveal.css (layout) AND theme/black.css (colors). Neither alone is sufficient. |

## Catch-all

If none of the above match the observed symptom: use `mcp__chrome-devtools__evaluate_script` to run `() => document.documentElement.outerHTML` and inspect the rendered HTML for missing tags. Also run `() => Reveal.getState()` — if this throws a ReferenceError, Reveal did not initialize.

## Page selection

When multiple pages are open, the Chrome DevTools MCP may drift to a different page after `new_page`. Before calling `take_screenshot`, call `mcp__chrome-devtools__list_pages` and then `mcp__chrome-devtools__select_page` with `bringToFront: true` on the correct page ID to ensure the screenshot captures the right page.

