/**
 * Stroke validation UI from SSE JSON { type: "strokes", S1, S2 }.
 * Patches EventSource so any /api/stream connection applies stroke updates without
 * duplicating connections. Loads before app.js.
 */
(function () {
  'use strict';

  function resetStrokeValidationDisplay() {
    ['stroke-count-1', 'stroke-count-2', 'stroke-counter'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.textContent = '0';
    });
  }

  var lastStrokes = null;

  function applyStrokeDisplay(o) {
    var e1 = document.getElementById('stroke-count-1');
    var e2 = document.getElementById('stroke-count-2');
    var ec = document.getElementById('stroke-counter');
    var beakerEl = document.getElementById('stroke-beaker');
    if (e1 && o.S1 != null) e1.textContent = String(o.S1);
    if (e2 && o.S2 != null) e2.textContent = String(o.S2);
    if (ec && beakerEl) {
      var b = parseInt(String(beakerEl.textContent).trim(), 10);
      if (isNaN(b)) b = 1;
      var v = b === 2 ? o.S2 : o.S1;
      if (v != null) ec.textContent = String(v);
    }
  }

  function updateStrokesFromSse(o) {
    lastStrokes = o;
    applyStrokeDisplay(o);
  }

  function attachStrokeBeakerObserver() {
    var beakerEl = document.getElementById('stroke-beaker');
    if (!beakerEl || typeof MutationObserver === 'undefined') return;
    var mo = new MutationObserver(function () {
      if (lastStrokes) applyStrokeDisplay(lastStrokes);
    });
    mo.observe(beakerEl, { childList: true, characterData: true, subtree: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', attachStrokeBeakerObserver);
  } else {
    attachStrokeBeakerObserver();
  }

  function applyTempsFromSse(o) {
    function fmt(x) {
      if (x == null || isNaN(Number(x))) return '';
      return parseFloat(x).toFixed(1) + '\u00B0C';
    }
    var ir = o.IR1 != null ? o.IR1 : o.IR2;
    if (ir != null) {
      var s = fmt(ir);
      var t1 = document.getElementById('temp1');
      var t2 = document.getElementById('temp2');
      if (t1) t1.textContent = s;
      if (t2) t2.textContent = s;
    }
    var irIn = document.getElementById('calibration-internal-temp-input');
    var e1 = document.getElementById('calibration-external-temp1-input');
    var e2 = document.getElementById('calibration-external-temp2-input');
    if (irIn && o.IR1 != null) irIn.value = parseFloat(o.IR1).toFixed(1);
    if (e1 && o.EXT1 != null) e1.value = parseFloat(o.EXT1).toFixed(1);
    if (e2 && o.EXT2 != null) e2.value = parseFloat(o.EXT2).toFixed(1);
  }

  function onStreamMessage(ev) {
    try {
      var o = JSON.parse(ev.data);
      if (o && o.type === 'strokes') {
        updateStrokesFromSse(o);
        return;
      }
      if (o && o.type === 'temps') {
        applyTempsFromSse(o);
      }
    } catch (ignore) {}
  }

  var OrigES = window.EventSource;
  if (typeof OrigES !== 'function') return;

  function PatchedEventSource(url, eventSourceInitDict) {
    var es = new OrigES(url, eventSourceInitDict);
    var u = url == null ? '' : String(url);
    if (u.indexOf('/api/stream') !== -1 || u.indexOf('api/stream') !== -1) {
      es.addEventListener('message', onStreamMessage);
    }
    return es;
  }

  PatchedEventSource.prototype = OrigES.prototype;
  ['CONNECTING', 'OPEN', 'CLOSED'].forEach(function (k) {
    if (k in OrigES) PatchedEventSource[k] = OrigES[k];
  });

  window.EventSource = PatchedEventSource;

  var _fetch = window.fetch;
  window.fetch = function () {
    var reqUrl = arguments[0];
    var p = _fetch.apply(this, arguments);
    if (typeof reqUrl === 'string' && (reqUrl.indexOf('stroke-validation/done') !== -1 || reqUrl.indexOf('stroke-validation/start') !== -1)) {
      p = p.then(function (r) {
        try {
          if (r && r.ok) resetStrokeValidationDisplay();
        } catch (e) {}
        return r;
      });
    }
    return p;
  };

  window.resetStrokeValidationDisplay = resetStrokeValidationDisplay;
})();
