/**
 * Assembles the document that goes into the page view's iframe.
 *
 * Kept pure and separate from the component because this is where the security
 * boundary is actually drawn, and a pure function is something tests can pin
 * down: given any author HTML — a full document, a bare fragment, something
 * malformed — the policy has to end up first in <head>.
 *
 * The iframe itself is rendered with sandbox="allow-scripts" and deliberately
 * without allow-same-origin, so the document has an opaque origin: no cookies,
 * no localStorage, no reach into the parent. The CSP below is the second layer,
 * and its job is to stop the page sending the rows it was handed anywhere.
 */

const HEAD_OPEN = /<head\b[^>]*>/i
const HTML_OPEN = /<html\b[^>]*>/i
const DOCTYPE = /^\s*<!doctype\b[^>]*>/i

/**
 * The runtime the author writes against. Documented for them in
 * `backend/src/arabase/mcp/page/contract.py`, which is what the AI reads before
 * it writes a page — the two must stay in step.
 */
export const BOOTSTRAP_SCRIPT = `
(function () {
  var callbacks = []
  var data = null

  function deliver(cb) {
    try {
      cb(data)
    } catch (e) {
      // A throwing page callback must not take the rest of the runtime with it.
      if (window.console && console.error) console.error(e)
    }
  }

  var api = {
    fields: [],
    rows: [],
    view: null,
    onData: function (cb) {
      if (typeof cb !== 'function') return
      callbacks.push(cb)
      if (data) deliver(cb)
    },
    setHeight: function (px) {
      post({ type: 'jadawel:height', height: Math.ceil(px) })
    },
  }

  function post(message) {
    // The parent is the only thing this document can talk to at all: the
    // sandbox has no same-origin access and the CSP blocks every network API.
    if (window.parent && window.parent !== window) {
      window.parent.postMessage(message, '*')
    }
  }

  window.addEventListener('message', function (event) {
    // Only the embedding page may drive this document.
    if (event.source !== window.parent) return
    var message = event.data
    if (!message || message.type !== 'jadawel:data') return

    data = message.payload
    api.fields = data.fields
    api.rows = data.rows
    api.view = data.view

    if (data.view && data.view.dir) {
      document.documentElement.setAttribute('dir', data.view.dir)
      if (data.view.locale) {
        document.documentElement.setAttribute('lang', data.view.locale)
      }
    }

    for (var i = 0; i < callbacks.length; i++) deliver(callbacks[i])

    // Re-measure after the page has drawn its data. The observer below only
    // speaks up when the height *changes*, so if the parent missed the first
    // measurement it would otherwise never hear another one.
    setTimeout(reportHeight, 0)
  })

  var lastHeight = 0
  function reportHeight() {
    // Measured on <body>, never on <html>. The root element is stretched to the
    // frame's own height, so measuring it hands the parent back the size it
    // just set — the frame then keeps whatever height it first had, with the
    // page's real content sitting in the top of it and blank space below.
    // <body> is content-sized, so it says what the document actually needs.
    if (!document.body) return
    var height = document.body.scrollHeight
    // A pixel or two of drift is rounding, not a change worth a round trip.
    if (height && Math.abs(height - lastHeight) > 2) {
      lastHeight = height
      post({ type: 'jadawel:height', height: height })
    }
  }

  // This script runs inside <head>, so there is no body to watch yet.
  function startObserving() {
    if (window.ResizeObserver && document.body) {
      new ResizeObserver(reportHeight).observe(document.body)
    }
    reportHeight()
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', startObserving)
  } else {
    startObserving()
  }
  window.addEventListener('load', reportHeight)

  window.jadawel = api
  post({ type: 'jadawel:ready' })
})()
`

const BASE_STYLE = `
  html, body { margin: 0; padding: 0; }
  body { font-family: system-ui, "Segoe UI", Tahoma, sans-serif; }
`

/**
 * Build the <head> content Jadawel always injects, policy first.
 *
 * A page can add its own CSP meta and cannot loosen ours by doing so: multiple
 * policies combine restrictively, every one of them has to allow a request.
 */
function injectedHead(contentSecurityPolicy, includeCharset = false) {
  const meta = contentSecurityPolicy
    ? `<meta http-equiv="Content-Security-Policy" content="${escapeAttribute(
        contentSecurityPolicy
      )}">`
    : ''
  // Charset sits directly behind the policy so it stays inside the first 1024
  // bytes the parser looks at, rather than behind the bootstrap script.
  const charset = includeCharset ? '<meta charset="utf-8">' : ''
  return `${meta}${charset}<style>${BASE_STYLE}</style><script>${BOOTSTRAP_SCRIPT}</script>`
}

function escapeAttribute(value) {
  return String(value).replace(/&/g, '&amp;').replace(/"/g, '&quot;')
}

/**
 * @param {string} html The document or fragment the author wrote.
 * @param {string} contentSecurityPolicy The policy, computed by the backend.
 * @returns {string} A complete document suitable for an iframe's srcdoc.
 */
export function buildPageDocument(html, contentSecurityPolicy) {
  const head = injectedHead(contentSecurityPolicy)
  const source = typeof html === 'string' ? html : ''

  const headMatch = source.match(HEAD_OPEN)
  if (headMatch) {
    const at = headMatch.index + headMatch[0].length
    return source.slice(0, at) + head + source.slice(at)
  }

  const htmlMatch = source.match(HTML_OPEN)
  if (htmlMatch) {
    const at = htmlMatch.index + htmlMatch[0].length
    return `${source.slice(0, at)}<head>${head}</head>${source.slice(at)}`
  }

  // A fragment, or a document written without <html>/<head>. Keep the author's
  // doctype if they wrote one so we do not end up with two.
  const doctypeMatch = source.match(DOCTYPE)
  const body = doctypeMatch ? source.slice(doctypeMatch[0].length) : source

  return `<!doctype html><html><head>${injectedHead(
    contentSecurityPolicy,
    true
  )}</head><body>${body}</body></html>`
}

export default buildPageDocument
