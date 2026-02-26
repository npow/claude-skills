# Chart.js Templates and Data Patterns

Complete copy-paste HTML templates for each chart type. Replace the DATA sections with actual values.

## Contents
- Color palette
- Bar chart template
- Line chart template
- Pie / doughnut chart template
- Radar chart template
- Data format patterns
- Multi-dataset pattern

---

## Color palette

Always use these colors in order. Never define ad-hoc colors inside dataset objects.

```javascript
const PALETTE = [
  '#c0392b', // red
  '#2980b9', // blue
  '#27ae60', // green
  '#8e44ad', // purple
  '#d35400', // orange
  '#16a085', // teal
];
```

For charts that need fill (line area, radar): append `'33'` to the hex for 20% opacity background fill (e.g. `'#c0392b33'`).

---

## Bar chart template

```html
<!DOCTYPE html>
<html>
<head>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #1e1e2e; font-family: 'Segoe UI', sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; }
  .chart-container { width: 90vw; height: 500px; }
</style>
</head>
<body>
<div class="chart-container">
  <canvas id="chart"></canvas>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<script>
const PALETTE = ['#c0392b','#2980b9','#27ae60','#8e44ad','#d35400','#16a085'];

Chart.defaults.color = '#cdd6f4';
Chart.defaults.borderColor = 'rgba(255,255,255,0.1)';

new Chart(document.getElementById('chart'), {
  type: 'bar',
  data: {
    labels: ['Label A', 'Label B', 'Label C', 'Label D'],  // X-axis categories
    datasets: [
      {
        label: 'Dataset Name',
        data: [42, 75, 31, 88],
        backgroundColor: PALETTE[0],
        borderColor: PALETTE[0],
        borderWidth: 1,
        borderRadius: 4,
      },
      // Add more datasets for grouped bars, using PALETTE[1], PALETTE[2], etc.
    ],
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      title: {
        display: true,
        text: 'Chart Title Here',
        font: { size: 18 },
        padding: { bottom: 20 },
      },
      legend: { position: 'top' },
    },
    scales: {
      x: { grid: { color: 'rgba(255,255,255,0.08)' } },
      y: {
        beginAtZero: true,
        grid: { color: 'rgba(255,255,255,0.08)' },
      },
    },
  },
});
</script>
</body>
</html>
```

---

## Line chart template

```html
<!DOCTYPE html>
<html>
<head>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #1e1e2e; font-family: 'Segoe UI', sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; }
  .chart-container { width: 90vw; height: 500px; }
</style>
</head>
<body>
<div class="chart-container">
  <canvas id="chart"></canvas>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<script>
const PALETTE = ['#c0392b','#2980b9','#27ae60','#8e44ad','#d35400','#16a085'];

Chart.defaults.color = '#cdd6f4';
Chart.defaults.borderColor = 'rgba(255,255,255,0.1)';

new Chart(document.getElementById('chart'), {
  type: 'line',
  data: {
    labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],  // X-axis time/category labels
    datasets: [
      {
        label: 'Series Name',
        data: [10, 25, 18, 40, 35, 60],
        borderColor: PALETTE[0],
        backgroundColor: PALETTE[0] + '33',  // 20% opacity fill
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointHoverRadius: 6,
      },
      // Add more series using PALETTE[1], PALETTE[2], etc.
    ],
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      title: {
        display: true,
        text: 'Chart Title Here',
        font: { size: 18 },
        padding: { bottom: 20 },
      },
      legend: { position: 'top' },
    },
    scales: {
      x: { grid: { color: 'rgba(255,255,255,0.08)' } },
      y: {
        beginAtZero: true,
        grid: { color: 'rgba(255,255,255,0.08)' },
      },
    },
  },
});
</script>
</body>
</html>
```

---

## Pie / doughnut chart template

Use `type: 'pie'` for a filled pie, `type: 'doughnut'` for a ring. Everything else is identical.

```html
<!DOCTYPE html>
<html>
<head>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #1e1e2e; font-family: 'Segoe UI', sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; }
  .chart-container { width: 70vw; height: 500px; }
</style>
</head>
<body>
<div class="chart-container">
  <canvas id="chart"></canvas>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<script>
const PALETTE = ['#c0392b','#2980b9','#27ae60','#8e44ad','#d35400','#16a085'];

Chart.defaults.color = '#cdd6f4';
Chart.defaults.borderColor = 'rgba(255,255,255,0.1)';

new Chart(document.getElementById('chart'), {
  type: 'doughnut',  // or 'pie'
  data: {
    labels: ['Slice A', 'Slice B', 'Slice C', 'Slice D'],
    datasets: [
      {
        data: [40, 25, 20, 15],
        backgroundColor: [PALETTE[0], PALETTE[1], PALETTE[2], PALETTE[3]],
        borderColor: '#1e1e2e',
        borderWidth: 2,
      },
    ],
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      title: {
        display: true,
        text: 'Chart Title Here',
        font: { size: 18 },
        padding: { bottom: 20 },
      },
      legend: { position: 'right' },
    },
  },
});
</script>
</body>
</html>
```

---

## Radar chart template

```html
<!DOCTYPE html>
<html>
<head>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #1e1e2e; font-family: 'Segoe UI', sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; }
  .chart-container { width: 70vw; height: 550px; }
</style>
</head>
<body>
<div class="chart-container">
  <canvas id="chart"></canvas>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<script>
const PALETTE = ['#c0392b','#2980b9','#27ae60','#8e44ad','#d35400','#16a085'];

Chart.defaults.color = '#cdd6f4';
Chart.defaults.borderColor = 'rgba(255,255,255,0.1)';

new Chart(document.getElementById('chart'), {
  type: 'radar',
  data: {
    labels: ['Metric A', 'Metric B', 'Metric C', 'Metric D', 'Metric E'],
    datasets: [
      {
        label: 'Option 1',
        data: [80, 65, 90, 55, 70],
        borderColor: PALETTE[0],
        backgroundColor: PALETTE[0] + '33',
        pointBackgroundColor: PALETTE[0],
      },
      {
        label: 'Option 2',
        data: [60, 85, 50, 90, 45],
        borderColor: PALETTE[1],
        backgroundColor: PALETTE[1] + '33',
        pointBackgroundColor: PALETTE[1],
      },
    ],
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      title: {
        display: true,
        text: 'Chart Title Here',
        font: { size: 18 },
        padding: { bottom: 20 },
      },
      legend: { position: 'top' },
    },
    scales: {
      r: {
        beginAtZero: true,
        grid: { color: 'rgba(255,255,255,0.12)' },
        angleLines: { color: 'rgba(255,255,255,0.12)' },
        pointLabels: { color: '#cdd6f4', font: { size: 13 } },
        ticks: { backdropColor: 'transparent' },
      },
    },
  },
});
</script>
</body>
</html>
```

---

## Data format patterns

### Single dataset (most bar/line charts)

```javascript
datasets: [
  {
    label: 'Revenue',
    data: [120, 190, 150, 210, 180],
    backgroundColor: PALETTE[0],
    borderColor: PALETTE[0],
  },
],
```

### Multiple datasets (grouped bars or multi-line)

```javascript
datasets: [
  { label: 'Model A', data: [12, 18, 9, 24], backgroundColor: PALETTE[0], borderColor: PALETTE[0] },
  { label: 'Model B', data: [8, 22, 14, 19], backgroundColor: PALETTE[1], borderColor: PALETTE[1] },
  { label: 'Model C', data: [15, 11, 20, 16], backgroundColor: PALETTE[2], borderColor: PALETTE[2] },
],
```

### Pie / doughnut (single dataset, multiple colors)

```javascript
datasets: [
  {
    data: [45, 30, 15, 10],
    backgroundColor: [PALETTE[0], PALETTE[1], PALETTE[2], PALETTE[3]],
    borderColor: '#1e1e2e',
    borderWidth: 2,
  },
],
```

### Time series labels

For monthly data: `['Jan 2025', 'Feb 2025', 'Mar 2025', ...]`
For daily data: `['2025-01-01', '2025-01-02', ...]`
For versions/releases: `['v1.0', 'v1.1', 'v2.0', ...]`

---

## Choosing the right chart type

| Data shape | Chart type |
|------------|------------|
| Categories with one value each | bar |
| Categories with multiple values | bar (grouped datasets) |
| Values over time / ordered sequence | line |
| Part-of-whole proportions | pie or doughnut |
| Multi-axis comparison of options | radar |
| Cumulative or stacked area | line with `fill: true` and stacking |

For benchmark comparisons between options across multiple criteria, prefer radar. For cost/performance over time, prefer line.
