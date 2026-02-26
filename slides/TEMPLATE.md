# Slides Template

Complete HTML template for Reveal.js slide decks, all slide type patterns, and content chunking rules.

## Contents
- Full HTML template
- Slide type patterns
- Content chunking rules

## Full HTML Template

Copy this template verbatim. Replace the `<!-- SLIDES GO HERE -->` comment with `<section>` elements.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Presentation</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/5.0.5/reveal.css" />
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/5.0.5/theme/black.css" />
  <style>
    .reveal h1, .reveal h2 { text-transform: none; }
    .reveal ul { text-align: left; }
    .reveal li { margin: 0.4em 0; }
    .two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 2em; }
    .reveal blockquote { font-style: italic; border-left: 4px solid #aaa; padding-left: 1em; }
    .reveal blockquote cite { display: block; margin-top: 0.5em; font-size: 0.75em; color: #bbb; }
  </style>
</head>
<body>
  <div class="reveal">
    <div class="slides">
      <!-- SLIDES GO HERE -->
    </div>
  </div>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/reveal.js/5.0.5/reveal.js"></script>
  <script>
    Reveal.initialize({ hash: true, transition: 'slide', backgroundTransition: 'fade' });
  </script>
</body>
</html>
```

**Critical CDN order:** reveal.css must appear before theme/black.css. The JS script tag must appear after the `.reveal` div, just before `</body>`.

## Slide Type Patterns

### Title Slide

Use as the first slide. One `<h1>` for the main title, one `<p>` for the subtitle.

```html
<section>
  <h1>Presentation Title</h1>
  <p>Subtitle or author · Date</p>
</section>
```

### Bullet Slide

Use for sections with key points. `<h2>` heading, then `<ul>` with `<li>` items. Max 6 items.

```html
<section>
  <h2>Section Title</h2>
  <ul>
    <li>First point</li>
    <li>Second point</li>
    <li>Third point</li>
  </ul>
</section>
```

### Two-Column Slide

Use when comparing two things or showing left/right content. Requires the `.two-col` CSS class defined in the template.

```html
<section>
  <h2>Comparison</h2>
  <div class="two-col">
    <div>
      <h3>Left Column</h3>
      <ul>
        <li>Point A</li>
        <li>Point B</li>
      </ul>
    </div>
    <div>
      <h3>Right Column</h3>
      <ul>
        <li>Point C</li>
        <li>Point D</li>
      </ul>
    </div>
  </div>
</section>
```

### Quote Slide

Use for key quotes, testimonials, or standout statements.

```html
<section>
  <blockquote>
    "The quote text goes here, kept to two or three sentences maximum."
    <cite>— Attribution, Title</cite>
  </blockquote>
</section>
```

### Code Slide

Use for showing code snippets, commands, or config. Keep code short — visible without scrolling.

```html
<section>
  <h2>Code Example</h2>
  <pre><code>def hello():
    return "world"</code></pre>
</section>
```

### Vertical Slide (Sub-points)

Nest `<section>` elements inside a parent `<section>` to create vertical drill-down slides. The parent section must have no direct content — only child sections.

```html
<section>
  <section>
    <h2>Top-level Slide</h2>
    <p>Press down arrow to see sub-slides</p>
  </section>
  <section>
    <h2>Sub-slide 1</h2>
    <ul>
      <li>Detail point</li>
    </ul>
  </section>
  <section>
    <h2>Sub-slide 2</h2>
    <ul>
      <li>More detail</li>
    </ul>
  </section>
</section>
```

## Content Chunking Rules

These rules govern how to map source content into slides.

### Slide count targets

| Source content | Target slide count |
|---|---|
| Short chat message or brief request | 4–6 slides |
| 1–2 paragraphs | 5–8 slides |
| Long document or research summary | 8–15 slides |
| Never exceed | 20 slides |

### Chunking algorithm

1. Always start with a title slide.
2. Map each top-level section of the source to one or more slides.
3. If a section has 7 or more bullet points, split it: use "Title (1/2)" and "Title (2/2)".
4. If a section has a natural left/right comparison, use a two-column slide.
5. If the source contains a memorable quote or key statement, isolate it on a quote slide.
6. If the source contains code or commands, use a code slide — do not put code inside a bullet list.
7. End with a summary or "Next Steps" slide when the source has action items or conclusions.

### Bullet point writing rules

- Each bullet is one idea, one line. No sentences longer than 12 words.
- Start bullets with a noun or verb. No leading articles ("A", "The").
- Do not nest bullet points — Reveal.js vertical slides handle hierarchy better than sub-bullets.
- Numbers and statistics should appear in bullets verbatim from the source — do not round or paraphrase data.
