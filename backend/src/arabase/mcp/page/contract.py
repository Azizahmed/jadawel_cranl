"""What an AI needs to know before it writes a page.

Returned as tool *output* rather than put in a tool docstring on purpose:
``MCPTool.list`` collapses a docstring with ``" ".join(description.split())``,
which would flatten every code block and list below into one unreadable line.
Handing it back from ``get_page_view`` keeps it intact.
"""

RUNTIME_CONTRACT = """\
# Writing a Jadawel page

A page is one self-contained HTML document. Write a complete document
(`<!doctype html>` … `</html>`); Jadawel injects its security policy and the
`jadawel` runtime into your `<head>` before rendering.

## The design is yours

Build whatever the user asked for, and make it good. There is no house template
to fill in, no component library to match, and no restriction on layout,
typography, colour or motion — a dense operations dashboard, a printable report,
a single headline number, a timeline, a poster. Judge it the way you would judge
a page you had designed from scratch for that person.

The rules below are not design rules. They describe a sealed room the page runs
in, and everything in it exists so that untrusted code can be shown real data
safely. Work within them and the visual result is entirely your call.

## Where your code runs

The document is rendered in an iframe with `sandbox="allow-scripts"` and
**without** `allow-same-origin`. Consequences you must design around:

- **No network access at all.** `fetch`, `XMLHttpRequest`, `WebSocket`,
  `EventSource` and `navigator.sendBeacon` are blocked by
  `connect-src 'none'`. Do not try to call the Jadawel API — the data you need
  is already handed to you.
- **No storage.** `localStorage`, `sessionStorage`, cookies and `indexedDB` are
  unavailable in an opaque origin. Hold state in JavaScript variables.
- **No external assets by default.** No CDN scripts, stylesheets, fonts or
  remote images. Write your own CSS and JS inline, and use inline SVG or
  `data:` URIs for graphics. If the view has `allow_external_resources` turned
  on, a small allowlist of CDNs becomes available — but ask before relying on
  it, because it is off by default.
- **No navigation.** `window.open`, top-level navigation and form submission
  are blocked. Links to other pages will not work.

None of this is a limitation to work around. It is what makes it safe to run
your code in front of somebody's real data.

## The data

Your script gets the view's rows through `window.jadawel`:

```js
window.jadawel.onData(({ fields, rows, view }) => {
  // fields: [{ id, name, type, order }]
  // rows:   [{ id, order, values: {...}, raw: {...} }]
  // view:   { id, name, count, rowLimit, truncated, locale, dir }
  render(rows)
})
```

`onData` fires as soon as the data is there and again on every refresh, so put
all your rendering inside it rather than reading `window.jadawel.rows` once at
load — on a slow connection that array is still empty.

- `row.values` is keyed by **field name**, e.g. `row.values['Customer']`.
- `row.raw` is keyed by `field_<id>` if two fields share a name.
- Values follow the field type: text/number/date are primitives (numbers arrive
  as strings to preserve decimals, dates as ISO strings), `single_select` is
  `{id, value, color}` or `null`, `multiple_select` and `link_row` are arrays,
  `file` is an array of `{url, visible_name, thumbnails}`, `boolean` is a bool.
  A field with no value is `null` — guard for it.
- `view.truncated` is `true` when the table has more rows than `view.rowLimit`.
  If it is, say so in the page rather than silently showing a partial total.

## Two things that are not taste

Everything about how the page looks is yours to decide. These two are not
aesthetic choices, and getting them wrong makes a good design read badly:

- **Direction.** Read `view.dir` (`'rtl'` or `'ltr'`) and set it on `<html>`.
  Jadawel is Arabic-first, so RTL is the common case. Build with CSS logical
  properties (`margin-inline-start`, `inset-inline-end`, `text-align: start`)
  rather than left/right, and the same design works in both directions instead
  of coming apart in one of them. Keep numbers in Western digits (0–9), in
  Arabic too — that is the house convention.
- **Honesty about the data.** If `view.truncated` is true, the page is showing
  part of the table; say so rather than presenting a partial figure as the
  total.

Two practical notes: the frame sizes itself to your content, so build for a
width and let the height follow (or call `window.jadawel.setHeight(px)` if you
would rather compute it). And the page is read-only — there is no way to write a
row back from here, so if the user needs that, point them at a form view.
"""
