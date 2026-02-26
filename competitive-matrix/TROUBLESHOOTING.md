
## Page selection

When multiple pages are open, the Chrome DevTools MCP may drift to a different page after `new_page`. Before calling `take_screenshot`, call `mcp__chrome-devtools__list_pages` and then `mcp__chrome-devtools__select_page` with `bringToFront: true` on the correct page ID to ensure the screenshot captures the right page.

