/**
 * input-focus.js - Keyboard and input focus handlers
 * Extracted from app.js to reduce bundle size.
 * Depends on: keyboard.js (closeOSK, openOSKForInput)
 */
(function(){
  function setKeyboardOpen(flag){
    if(flag) {
      document.body.classList.add('keyboard-open');
      const osk = document.getElementById('osk');
      if(osk) osk.classList.add('visible');
    } else {
      document.body.classList.remove('keyboard-open');
      const osk = document.getElementById('osk');
      if(osk) osk.classList.remove('visible');
    }
  }

  function onInputFocus(e){
    const el = e.target;
    if(el.tagName === 'SELECT') return;
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  function onInputBlur(e){
    setTimeout(()=>{
      if (window._lastOSKOpenTime && (Date.now() - window._lastOSKOpenTime) < 200) return;
      const ae = document.activeElement;
      const oskEl = document.getElementById('osk');
      const keyboardRoot = document.getElementById('keyboard-root');
      if (ae && (ae.tagName === 'INPUT' || ae.tagName === 'TEXTAREA')) return;
      if (oskEl && ae && oskEl.contains(ae)) return;
      if (keyboardRoot && ae && keyboardRoot.contains(ae)) return;
      if (typeof closeOSK === 'function') {
        closeOSK();
      } else {
        setKeyboardOpen(false);
      }
    }, 120);
  }

  function attachOSKDoubleTapHandlers(root){
    root = root || document;
    const inputs = root.querySelectorAll('input[type="text"], input[type="password"], input[type="number"], textarea');
    inputs.forEach(inp => {
      if (inp.tagName === 'SELECT') return;
      if (inp.type === 'checkbox' || inp.type === 'radio' || inp.type === 'button' || inp.type === 'submit' || inp.type === 'datetime-local') return;
      if (inp._osk_doubletap_bound) return;
      inp._osk_doubletap_bound = true;
    });
  }

  function attachHandlers(root){
    root = root || document;
    const inputs = root.querySelectorAll('input, textarea');
    inputs.forEach(inp=>{
      if(inp._cursor_kbd_bound) return;
      inp._cursor_kbd_bound = true;
      inp.addEventListener('focus', (e) => {
        onInputFocus(e);
        if(inp.setSelectionRange && inp.value) {
          setTimeout(() => inp.setSelectionRange(inp.value.length, inp.value.length), 10);
        }
      }, { passive: true });
      inp.addEventListener('blur', onInputBlur, { passive: true });
    });
    const selects = root.querySelectorAll('select');
    selects.forEach(sel => {
      if(sel._cursor_kbd_bound) return;
      sel._cursor_kbd_bound = true;
      sel.setAttribute('inputmode', 'none');
    });
  }

  document.addEventListener('DOMContentLoaded', ()=> {
    attachHandlers(document);
    attachOSKDoubleTapHandlers(document);
    const observer = new MutationObserver((mutations)=>{
      for(const m of mutations){
        if(m.addedNodes && m.addedNodes.length){
          m.addedNodes.forEach(node=>{
            if(node.nodeType===1) {
              attachHandlers(node);
              attachOSKDoubleTapHandlers(node);
            }
          });
        }
      }
    });
    observer.observe(document.body, { childList:true, subtree:true });
  });
})();

function attachInputFocusHandlers(root){
  root = root || document;
  const inputs = root.querySelectorAll('input[type="text"], input[type="password"], input[type="number"], input:not([type]), textarea');
  inputs.forEach(inp=>{
    if(inp.tagName === 'SELECT') return;
    if(inp.type === 'checkbox' || inp.type === 'radio' || inp.type === 'button' || inp.type === 'submit' || inp.type === 'datetime-local') return;
    if(inp._cursor_focus_bound) return;
    inp._cursor_focus_bound = true;
    inp.addEventListener('focus', (ev)=>{
      const loginScreen = document.getElementById('screen-login');
      const loginActive = loginScreen && loginScreen.classList.contains('active');
      if (loginActive) {
        window._activeOSKInput = inp;
        document.body.classList.add('keyboard-open');
        const osk = document.getElementById('osk');
        if(osk) osk.classList.add('visible');
        window._lastOSKOpenTime = Date.now();
        if (typeof openOSKForInput === 'function') openOSKForInput(inp);
        return;
      }
      if(ev.target.tagName !== 'SELECT') ev.target.scrollIntoView({ behavior: 'smooth', block: 'center' });
      const setCursorToEnd = () => {
        if (inp.setSelectionRange) {
          const len = inp.value ? inp.value.length : 0;
          try { inp.setSelectionRange(len, len); } catch(e) {}
        }
      };
      setCursorToEnd();
      setTimeout(setCursorToEnd, 50);
      if (typeof openOSKForInput === 'function') openOSKForInput(inp);
      window._activeOSKInput = inp;
      document.body.classList.add('keyboard-open');
      const osk = document.getElementById('osk');
      if(osk) osk.classList.add('visible');
      window._lastOSKOpenTime = Date.now();
    }, { passive:true });
    inp.addEventListener('blur', ()=>{
      setTimeout(()=>{
        if (window._lastOSKOpenTime && (Date.now() - window._lastOSKOpenTime) < 200) return;
        const ae = document.activeElement;
        const osk = document.getElementById('osk');
        const keyboardRoot = document.getElementById('keyboard-root');
        if (ae && (ae.tagName === 'INPUT' || ae.tagName === 'TEXTAREA')) return;
        if (osk && ae && osk.contains(ae)) return;
        if (keyboardRoot && ae && keyboardRoot.contains(ae)) return;
        document.body.classList.remove('keyboard-open');
        if(osk) osk.classList.remove('visible');
      }, 120);
    });
    if(!inp._enter_key_bound) {
      inp._enter_key_bound = true;
      inp.addEventListener('keydown', (ev) => {
        if (ev.key === 'Enter' && !ev.shiftKey) {
          ev.preventDefault();
          const form = inp.closest('form');
          const screen = inp.closest('.screen');
          const container = form || screen || root;
          const allInputs = Array.from(container.querySelectorAll('input[type="text"], input[type="password"], input[type="number"], input:not([type]), textarea, select'));
          const focusableInputs = allInputs.filter(i => {
            if (i.tagName === 'SELECT') return true;
            if (i.type === 'checkbox' || i.type === 'radio' || i.type === 'button' || i.type === 'submit' || i.type === 'datetime-local') return false;
            if (i.disabled || i.style.display === 'none' || i.offsetParent === null) return false;
            return true;
          });
          const currentIndex = focusableInputs.indexOf(inp);
          if (currentIndex >= 0 && currentIndex < focusableInputs.length - 1) {
            const nextInput = focusableInputs[currentIndex + 1];
            if (nextInput) setTimeout(() => { nextInput.focus(); nextInput.scrollIntoView({ behavior: 'smooth', block: 'center' }); }, 10);
          } else if (currentIndex === focusableInputs.length - 1) {
            // Last field: don't focus arbitrary action buttons (like SAVE).
            // Only focus an explicit submit button when inside an actual <form>.
            if (form) {
              const submitBtn = form.querySelector('button[type="submit"]');
              if (submitBtn) {
                setTimeout(() => submitBtn.focus(), 10);
                return;
              }
            }
            inp.blur();
          }
        }
      });
    }
  });
  const selects = root.querySelectorAll('select');
  selects.forEach(sel => {
    if(sel._cursor_focus_bound) return;
    sel._cursor_focus_bound = true;
    sel.setAttribute('inputmode', 'none');
  });
  if (root === document || root === document.body) {
    const observer = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (node.nodeType === 1) {
            if (node.tagName === 'INPUT' || node.tagName === 'TEXTAREA') attachInputFocusToSingle(node);
            const inputs = node.querySelectorAll?.('input[type="text"], input[type="password"], input[type="number"], textarea');
            if (inputs) inputs.forEach(inp => attachInputFocusToSingle(inp));
          }
        });
      });
    });
    observer.observe(root, { childList: true, subtree: true });
  }
}

function attachInputFocusToSingle(inp) {
  if (!inp || inp._cursor_focus_bound) return;
  if (inp.tagName === 'SELECT') return;
  if (inp.type === 'checkbox' || inp.type === 'radio' || inp.type === 'button' || inp.type === 'submit') return;
  inp._cursor_focus_bound = true;
  inp.addEventListener('focus', function(ev) {
    const input = ev.target;
    if(input.tagName !== 'SELECT') input.scrollIntoView({ behavior: 'smooth', block: 'center' });
    const setCursorToEnd = () => {
      if (!input || typeof input.setSelectionRange !== 'function') return;
      try { const len = input.value ? input.value.length : 0; input.setSelectionRange(len, len); } catch(e) {}
    };
    setCursorToEnd();
    setTimeout(setCursorToEnd, 50);
    if (typeof openOSKForInput === 'function') openOSKForInput(input);
    document.body.classList.add('keyboard-open');
    const osk = document.getElementById('osk');
    if(osk) osk.classList.add('visible');
    window._lastOSKOpenTime = Date.now();
  }, { passive: true });
  inp.addEventListener('blur', function() {
    setTimeout(()=>{
      if (window._lastOSKOpenTime && (Date.now() - window._lastOSKOpenTime) < 200) return;
      const ae = document.activeElement;
      const osk = document.getElementById('osk');
      const keyboardRoot = document.getElementById('keyboard-root');
      if(ae && (ae.tagName === 'INPUT' || ae.tagName === 'TEXTAREA')) return;
      if (osk && ae && osk.contains(ae)) return;
      if (keyboardRoot && ae && keyboardRoot.contains(ae)) return;
      document.body.classList.remove('keyboard-open');
      if(osk) osk.classList.remove('visible');
    }, 120);
  });
  if (!inp._enter_key_bound) {
    inp._enter_key_bound = true;
    inp.addEventListener('keydown', function(ev) {
      if (ev.key === 'Enter' && !ev.shiftKey) {
        ev.preventDefault();
        const form = inp.closest('form');
        const screen = inp.closest('.screen');
        const container = form || screen || document;
        const allInputs = Array.from(container.querySelectorAll('input[type="text"], input[type="password"], input[type="number"], input:not([type]), textarea, select'));
        const focusableInputs = allInputs.filter(function(i) {
          if (i.tagName === 'SELECT') return true;
          if (i.type === 'checkbox' || i.type === 'radio' || i.type === 'button' || i.type === 'submit' || i.type === 'datetime-local') return false;
          if (i.disabled || i.style.display === 'none' || i.offsetParent === null) return false;
          return true;
        });
        const currentInput = ev.target;
        const currentIndex = focusableInputs.indexOf(currentInput);
        if (currentIndex >= 0 && currentIndex < focusableInputs.length - 1) {
          const nextInput = focusableInputs[currentIndex + 1];
          if (nextInput) setTimeout(function() { nextInput.focus(); nextInput.scrollIntoView({ behavior: 'smooth', block: 'center' }); }, 10);
        } else if (currentIndex === focusableInputs.length - 1) {
          // Last field: don't focus arbitrary action buttons (like SAVE).
          // Only focus an explicit submit button when inside an actual <form>.
          if (form) {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
              setTimeout(() => submitBtn.focus(), 10);
              return;
            }
          }
          currentInput.blur();
        }
      }
    });
  }
}

window.attachInputFocusHandlers = attachInputFocusHandlers;
window.attachInputFocusToSingle = attachInputFocusToSingle;
