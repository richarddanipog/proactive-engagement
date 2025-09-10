(() => {
  const API_BASE = window.PROACTIVE_API_BASE || 'http://localhost:8000';
  const SESSION_KEY = 'pe_session_id';
  const SEEN_KEY = 'pe_seen_this_session'; // frequency cap: once per session
  const SESSION_DATA_KEY = 'pe_session_data'; // persist session data
  const SESSION_PER_PAGE = false; // true = new session every page load

  // -------- session data management --------
  let sessionData = getSessionData();

  function getSessionData() {
    try {
      const stored = sessionStorage.getItem(SESSION_DATA_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        return {
          startTime: parsed.startTime || Date.now(),
          events: Array.isArray(parsed.events) ? parsed.events : [],
        };
      }
    } catch (e) {
      // ignore parse errors
    }

    return {
      startTime: Date.now(),
      events: [],
    };
  }

  function saveSessionData() {
    try {
      sessionStorage.setItem(SESSION_DATA_KEY, JSON.stringify(sessionData));
    } catch (e) {
      // ignore storage errors
    }
  }

  function track(type, meta = {}) {
    const event = {
      type, // 'page_view' | 'click' | 'dwell_tick'
      page: getPageType(), // 'product' | 'cart' | 'collection' | 'home'
      meta, // e.g., { action: 'add_to_cart' } or { quantity: 3 }
      timestamp: Date.now(), // Unix ms
    };

    sessionData.events.push(event);

    // Keep buffer manageable
    if (sessionData.events.length > 30) {
      sessionData.events.splice(0, sessionData.events.length - 30);
    }

    saveSessionData();
  }

  // -------- session id --------
  function getSessionId() {
    if (SESSION_PER_PAGE) {
      return crypto.randomUUID ? crypto.randomUUID() : String(Math.random());
    }
    let id = sessionStorage.getItem(SESSION_KEY);
    if (!id) {
      id = crypto.randomUUID ? crypto.randomUUID() : String(Math.random());
      sessionStorage.setItem(SESSION_KEY, id);
    }
    return id;
  }

  // -------- page type detection (Shopify) --------
  function getPageType() {
    const p = window.location.pathname;
    if (/\/cart(?:\/|$)/.test(p)) return 'cart';
    if (/\/products\//.test(p)) return 'product';
    if (/\/collections\//.test(p)) return 'collection';
    if (p === '/' || /\/pages\//.test(p)) return 'home';
    return 'other'; // changed from 'product' to avoid confusion
  }

  // -------- cart items (best-effort) --------
  async function getCartCount() {
    try {
      const res = await fetch('/cart.js', { credentials: 'same-origin' });
      if (!res.ok) return 0;
      const data = await res.json();
      return data && data.item_count ? data.item_count : 0;
    } catch {
      return 0;
    }
  }

  // -------- modal (simple & accessible) --------
  function renderModal(message, ttlSeconds = 90) {
    if (!message) return;
    if (sessionStorage.getItem(SEEN_KEY) === '1') return; // frequency cap

    const overlay = document.createElement('div');
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.style.cssText =
      'position:fixed;inset:0;background:rgba(0,0,0,0.35);display:flex;align-items:center;justify-content:center;z-index:99999;';
    const box = document.createElement('div');
    box.style.cssText =
      'max-width:420px;width:calc(100% - 32px);background:#fff;border-radius:14px;padding:16px 16px 12px;box-shadow:0 6px 20px rgba(0,0,0,0.2);font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;';
    const text = document.createElement('div');
    text.textContent = message;
    text.style.cssText =
      'font-size:16px;line-height:1.4;margin-bottom:12px;color:#111;';
    const row = document.createElement('div');
    row.style.cssText = 'display:flex;gap:8px;justify-content:flex-end;';
    const closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.textContent = 'Close';
    closeBtn.style.cssText =
      'padding:8px 12px;border-radius:10px;border:1px solid #ddd;background:#fff;cursor:pointer;';
    closeBtn.addEventListener('click', () =>
      document.body.removeChild(overlay)
    );
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) document.body.removeChild(overlay);
    });
    overlay.tabIndex = -1;
    box.appendChild(text);
    row.appendChild(closeBtn);
    box.appendChild(row);
    overlay.appendChild(box);
    document.body.appendChild(overlay);
    overlay.focus();

    sessionStorage.setItem(SEEN_KEY, '1');
    if (ttlSeconds > 0) {
      setTimeout(() => {
        if (overlay.parentNode) document.body.removeChild(overlay);
      }, ttlSeconds * 1000);
    }
  }

  // -------- send snapshot to backend (/decide) --------
  async function sendSnapshotAndMaybeShow() {
    // avoid spamming backend: once per session unless user triggers significant action
    if (sessionStorage.getItem(SEEN_KEY) === '1') return;

    // add a dwell "heartbeat" event each time we send
    const elapsedSec = Math.floor((Date.now() - sessionData.startTime) / 1000);
    track('dwell_tick', {
      elapsed_sec: elapsedSec,
    });

    const session = {
      events: [...sessionData.events], // persistent events across page loads
      current_page: getPageType(),
      cart_items: await getCartCount(),
      time_on_site: elapsedSec, // now calculated from persistent start time
    };

    try {
      const res = await fetch(`${API_BASE}/decide`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session }),
      });
      if (!res.ok) return;
      const data = await res.json();
      if (data && data.should_show && data.message) {
        renderModal(data.message, data.ttl_seconds || 90);
      }
    } catch {
      /* silent */
    }
  }

  // -------- click tracking (add-to-cart, quantity +/- and manual input) --------
  function wireInteractions() {
    document.addEventListener('click', (e) => {
      const el = e.target instanceof Element ? e.target : null;
      if (!el) return;

      // Add to Cart
      const addBtn = el.closest(
        'button[name="add"], button[name="add-to-cart"], button.add-to-cart, form[action*="/cart/add"] button, [data-add-to-cart]'
      );
      if (addBtn) {
        track('click', { action: 'add_to_cart' });
        setTimeout(sendSnapshotAndMaybeShow, 400); // allow cart to update
        return;
      }

      // Quantity +/- (common selectors across Shopify themes)
      const qtyBtn = el.closest(
        'button[name="plus"], button[name="minus"], .quantity__button'
      );
      if (qtyBtn) {
        const action =
          qtyBtn.getAttribute('name') === 'plus' ||
          qtyBtn.textContent.trim() === '+'
            ? 'qty_inc'
            : qtyBtn.getAttribute('name') === 'minus' ||
              qtyBtn.textContent.trim() === '-'
            ? 'qty_dec'
            : 'qty_change';

        const wrapper =
          qtyBtn.closest(
            'form, .product-form, .quantity, .product__info-container'
          ) || document;
        const input = wrapper?.querySelector(
          'input[name="quantity"], input[type="number"][name*="quantity"]'
        );
        const value = input
          ? Number(input.value || input.getAttribute('value') || 1)
          : undefined;

        track('click', { action, quantity: value });
        setTimeout(sendSnapshotAndMaybeShow, 250);
        return;
      }
    });

    // Manual quantity input
    document.addEventListener('change', (e) => {
      const el = e.target;
      if (
        el instanceof HTMLInputElement &&
        el.name &&
        el.name.includes('quantity')
      ) {
        track('click', {
          action: 'qty_input',
          quantity: Number(el.value) || undefined,
        });
        setTimeout(sendSnapshotAndMaybeShow, 250);
      }
    });
  }

  // -------- dwell timer (periodic) --------
  function startDwellPings() {
    let lastSent = 0;
    const tick = () => {
      const elapsed = Math.floor((Date.now() - sessionData.startTime) / 1000);
      // call /decide once around ~30s and again ~90s to catch backend rules
      if (
        (elapsed >= 30 && lastSent < 30) ||
        (elapsed >= 90 && lastSent < 90)
      ) {
        lastSent = elapsed;
        sendSnapshotAndMaybeShow();
      }
      // stop after ~3 minutes to reduce noise
      if (elapsed < 180) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }

  // -------- boot --------
  function boot() {
    getSessionId();

    // track initial page view
    track('page_view', { path: location.pathname });

    wireInteractions();
    // initial check after a brief delay (let theme settle)
    setTimeout(sendSnapshotAndMaybeShow, 800);
    startDwellPings();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
