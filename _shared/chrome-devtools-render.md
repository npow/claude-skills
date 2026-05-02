# Chrome DevTools Render Workflow

Standard pattern for opening an HTML file in the browser, waiting for it to render, taking a screenshot, and fixing problems.

## Steps

1. **Open in browser** -- call `mcp__chrome-devtools__new_page` with `url: file:///tmp/<filename>.html`.
   - Always use `new_page` for the first open. Never navigate an existing page to a `file://` URL.

2. **Wait for render** -- call `mcp__chrome-devtools__wait_for` on a text string that appears only after the page has fully rendered (e.g. a heading, a legend label, or a column header). Timeout 8000-10000ms.
   - Never call `take_screenshot` immediately after `new_page` -- the page may still be loading.

3. **Take screenshot** -- call `mcp__chrome-devtools__take_screenshot` and visually verify the output is correct (readable text, expected layout, no blank areas).

4. **Fix-and-reload cycle** -- if the screenshot shows problems:
   1. Edit the HTML file to fix the issue.
   2. Call `mcp__chrome-devtools__navigate_page` with `type: reload`.
   3. Call `wait_for` again, then `take_screenshot` to verify the fix.
   - Only use `navigate_page` with `type: reload` for subsequent fixes -- never for the initial open.
