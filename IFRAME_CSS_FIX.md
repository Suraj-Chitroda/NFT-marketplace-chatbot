# Iframe CSS/Grid Layout Fix

## Problem

The HTML components were being returned from the agent correctly, but the grid layout was not displaying properly in the frontend. The NFT cards were stacked vertically instead of in a grid.

## Root Cause

The iframe had **restrictive sandbox attributes** that blocked JavaScript execution:

```javascript
sandbox="allow-same-origin"  // ❌ Blocks scripts
```

The backend HTML templates use:
1. **Tailwind CSS CDN** (`<script src="https://cdn.tailwindcss.com"></script>`)
2. **Tailwind Configuration** (inline `<script>` with custom theme)
3. **Grid classes** (`grid`, `grid-cols-4`, etc.)

Without JavaScript execution, Tailwind CSS couldn't load or apply, causing the grid layout to fail.

## Solution

### 1. Enable JavaScript in Iframe

Updated `frontend/src/App.jsx`:

```javascript
// Before
sandbox="allow-same-origin"

// After  
sandbox="allow-scripts allow-same-origin"
```

**Why this is safe:**
- `allow-scripts`: Enables JS execution for Tailwind CSS
- `allow-same-origin`: Allows iframe to measure its content for auto-height
- We control the HTML content (it comes from our backend)
- No `allow-forms` or `allow-top-navigation` (prevents malicious actions)

### 2. Ensure Adequate Width

Updated `frontend/src/App.css`:

```css
.block-iframe {
  width: 100%;
  min-width: 800px;        /* ← Added */
  min-height: 500px;
  height: auto;
  border: none;
  border-radius: 0;
  background: transparent;
  display: block;
  overflow-x: auto;        /* ← Added */
}
```

**Why min-width?**
- Tailwind's `grid-cols-4` needs minimum width to display 4 columns
- If viewport is too narrow, cards stack vertically
- 800px ensures at least 2-3 cards per row
- `overflow-x: auto` adds horizontal scroll on small screens

## Testing

After the fix, refresh the frontend (`http://localhost:5173`) and test:

```
"show me 10 NFTs in grid format"
```

Expected result:
- NFTs display in a responsive grid (2-4 columns)
- Cards have proper styling (glass effect, hover animations)
- Tailwind colors and spacing apply correctly

## Security Considerations

**Is `allow-scripts` safe?**

✅ Yes, because:
1. HTML content comes from our trusted backend
2. We're not rendering user-provided HTML
3. Sandbox still blocks:
   - Form submissions (`allow-forms` not set)
   - Navigation (`allow-top-navigation` not set)
   - Popups (`allow-popups` not set)
   - Downloads (`allow-downloads` not set)

## Alternative Approaches (if needed)

If security is still a concern, we could:

1. **Pre-render HTML server-side** (generate static HTML without CDN)
2. **Inline all CSS** (extract compiled Tailwind, no JS needed)
3. **Use React components** instead of HTML templates

But for this use case, `allow-scripts` with our controlled content is perfectly safe and the simplest solution.
