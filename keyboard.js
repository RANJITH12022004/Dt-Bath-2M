/**
 * On-Screen Keyboard Module
 * Handles virtual keyboard for touch input with password support and visual feedback
 */

(function() {
  'use strict';

  // Keyboard state
  var currentInput = null;
  var capsLockActive = false;
  var shiftActive = false;
  var numbersActive = false;
  
  // Keyboard layout - letter layout (lowercase when caps not active)
  var letterLayout = [
    ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
    ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l'],
    ['Caps', 'z', 'x', 'c', 'v', 'b', 'n', 'm', 'back'],
    ['123', 'Space', ',', 'Enter']
  ];
  
  // Keyboard layout - uppercase version (when caps is active)
  var letterLayoutUpper = [
    ['Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'],
    ['A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L'],
    ['Caps', 'Z', 'X', 'C', 'V', 'B', 'N', 'M', 'back'],
    ['123', 'Space', ',', 'Enter']
  ];
  
  // Keyboard layout - number layout
  var numberLayout = [
    ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
    ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')'],
    ['-', '_', '+', '=', '{', '}', '[', ']', '|', 'back'],
    ['ABC', 'Space', '.', ':', 'Enter']
  ];
  
  // Initialize keyboard
  function init() {
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/905604f3-2798-499f-a892-696c27f300f3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'keyboard.js:41',message:'init() called',data:{readyState:document.readyState,hasKeyboardRoot:!!document.getElementById('keyboard-root')},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
    // #endregion agent log
    var keyboardRoot = document.getElementById('keyboard-root');
    if (!keyboardRoot) {
      console.error('[OSK] keyboard-root element not found');
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/905604f3-2798-499f-a892-696c27f300f3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'keyboard.js:45',message:'keyboard-root not found',data:{readyState:document.readyState},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
      // #endregion agent log
      return;
    }
    
    // Create keyboard structure
    keyboardRoot.innerHTML = `
      <!-- Input Preview Popup -->
      <div id="osk-popup" class="osk-popup" style="display: none;">
        <div class="osk-popup-content">
          <div class="osk-popup-label" id="osk-popup-label">Enter Value</div>
          <div class="osk-popup-value" id="osk-popup-value"></div>
        </div>
      </div>
      
      <!-- Keyboard Container -->
      <div id="osk" class="keyboard" aria-hidden="true">
        <div class="flex flex-col p-3 gap-2" id="osk-rows"></div>
      </div>
      
      <!-- Footer bar - captures clicks on blank space under keyboard -->
      <div id="osk-footer" class="osk-footer" tabindex="0" aria-hidden="true"></div>
    `;
    
    buildKeyboard();
  }
  
  // Build keyboard layout
  function buildKeyboard() {
    var container = document.getElementById('osk-rows');
    if (!container) return;
    
    // Select layout based on state
    var layout;
    if (numbersActive) {
      layout = numberLayout;
    } else {
      // Use uppercase layout when caps is active, lowercase otherwise
      layout = (capsLockActive || shiftActive) ? letterLayoutUpper : letterLayout;
    }
    
    container.innerHTML = '';
    
    layout.forEach(function(row) {
      var rowDiv = document.createElement('div');
      rowDiv.className = 'osk-row';
      
      row.forEach(function(key) {
        var keyBtn = document.createElement('button');
        keyBtn.className = 'osk-key';
        
        // Map display keys to internal key names
        var internalKey = key;
        if (key === 'Caps') {
          internalKey = 'shift';
        } else if (key === 'Numbers') {
          internalKey = '123';
        } else if (key === 'ABC') {
          internalKey = 'abc';
        } else if (key === 'Enter') {
          internalKey = 'enter';
        } else if (key === 'Space') {
          internalKey = 'space';
        }
        
        keyBtn.setAttribute('data-key', internalKey);
        
        // Add special classes and styling
        if (internalKey === 'space') {
          keyBtn.classList.add('space');
          keyBtn.textContent = 'Space';
        } else if (internalKey === 'back') {
          keyBtn.classList.add('back', 'wide');
          keyBtn.innerHTML = '<i data-lucide="delete" style="width: 24px; height: 24px;"></i>';
        } else if (internalKey === 'enter') {
          keyBtn.classList.add('enter', 'wide');
          keyBtn.innerHTML = '<i data-lucide="corner-down-left" style="width: 24px; height: 24px;"></i>';
        } else if (internalKey === 'shift') {
          keyBtn.classList.add('shift', 'wide');
          if (capsLockActive) keyBtn.classList.add('active');
          keyBtn.textContent = 'Caps';
        } else if (internalKey === '123') {
          keyBtn.classList.add('numbers', 'wide');
          if (numbersActive) keyBtn.classList.add('active');
          keyBtn.textContent = 'Numbers';
        } else if (internalKey === 'abc') {
          keyBtn.classList.add('numbers', 'wide');
          if (!numbersActive) keyBtn.classList.add('active');
          keyBtn.textContent = 'ABC';
        } else {
          keyBtn.textContent = key;
        }
        
        // Add pointerdown for Chromium touch (more reliable than click on touch)
        keyBtn.addEventListener('pointerdown', function(e) {
          e.preventDefault();
          e.stopPropagation();
          handleKeyPress(internalKey);
        });
        
        rowDiv.appendChild(keyBtn);
      });
      
      container.appendChild(rowDiv);
    });
    
    // Initialize lucide icons
    if (window.lucide && typeof lucide.createIcons === 'function') {
      lucide.createIcons();
    }
  }
  
  // Handle key press
  function handleKeyPress(key) {
    // Click shield: prevents "click-through" to underlying UI when OSK closes on touch.
    // Some touch stacks may dispatch a click/pointerup onto the element beneath after we hide OSK.
    function armClickShield(durationMs) {
      try {
        var until = Date.now() + (Number(durationMs) || 250);
        window._oskClickShieldUntil = until;
        if (window._oskClickShieldInstalled) return;
        window._oskClickShieldInstalled = true;
        var handler = function(e) {
          try {
            if (Date.now() < (window._oskClickShieldUntil || 0)) {
              e.preventDefault();
              e.stopPropagation();
              if (typeof e.stopImmediatePropagation === 'function') e.stopImmediatePropagation();
              return false;
            }
          } catch (_) {}
        };
        document.addEventListener('click', handler, true);
        document.addEventListener('pointerup', handler, true);
        document.addEventListener('touchend', handler, true);
        setTimeout(function() {
          try {
            document.removeEventListener('click', handler, true);
            document.removeEventListener('pointerup', handler, true);
            document.removeEventListener('touchend', handler, true);
          } catch (_) {}
          window._oskClickShieldInstalled = false;
        }, (Number(durationMs) || 250) + 120);
      } catch (_) {}
    }

    // Layout switching works even without focused input (Chromium touch can blur input before click)
    if (key === '123') {
      numbersActive = true;
      buildKeyboard();
      if (currentInput) currentInput.focus();
      return;
    }
    if (key === 'abc') {
      numbersActive = false;
      buildKeyboard();
      if (currentInput) currentInput.focus();
      return;
    }

    if (!currentInput) return;
    
    var isPasswordField = currentInput.type === 'password';
    
    if (key === 'back') {
      // Backspace
      var val = currentInput.value;
      currentInput.value = val.substring(0, val.length - 1);
      updatePopup();
    } else if (key === 'enter') {
      // Enter - close keyboard and move to next input field
      var currentInp = currentInput;
      // Prevent the Enter tap from clicking the underlying UI (e.g., SAVE button).
      armClickShield(300);
      closeOSK();
      
      // Find next focusable input field
      setTimeout(function() {
        if (!currentInp) return;
        
        // Find all focusable inputs in the same form or screen
        var form = currentInp.closest('form');
        var screen = currentInp.closest('.screen');
        var container = form || screen || document;
        
        var allInputs = Array.from(container.querySelectorAll('input[type="text"], input[type="password"], input[type="number"], input:not([type]), textarea, select'));
        
        // Filter out checkboxes, radios, buttons, submits, datetime-local
        var focusableInputs = allInputs.filter(function(i) {
          if (i.tagName === 'SELECT') return true;
          if (i.type === 'checkbox' || i.type === 'radio' || i.type === 'button' || i.type === 'submit' || i.type === 'datetime-local') return false;
          if (i.disabled || i.style.display === 'none' || i.offsetParent === null) return false;
          return true;
        });
        
        var currentIndex = focusableInputs.indexOf(currentInp);
        if (currentIndex >= 0 && currentIndex < focusableInputs.length - 1) {
          // Move to next field
          var nextInput = focusableInputs[currentIndex + 1];
          if (nextInput) {
            setTimeout(function() {
              nextInput.focus();
              nextInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
              // Optionally reopen keyboard for next field
              if (typeof openOSKForInput === 'function') {
                openOSKForInput(nextInput);
              }
            }, 50);
          }
        } else if (currentIndex === focusableInputs.length - 1) {
          // Last field: do NOT auto-focus arbitrary action buttons (like SAVE).
          // Only focus an explicit submit button when inside an actual <form>.
          if (form) {
            var submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
              setTimeout(function() { submitBtn.focus(); }, 50);
              return;
            }
          }
          // Otherwise just blur so Enter can't trigger SAVE.
          currentInp.blur();
        }
      }, 100);
    } else if (key === 'space') {
      // Space
      currentInput.value += ' ';
      updatePopup();
    } else if (key === 'shift') {
      capsLockActive = !capsLockActive;
      shiftActive = capsLockActive;
      buildKeyboard();
      if (currentInput) currentInput.focus();
    } else {
      // Regular key
      currentInput.value += key;
      updatePopup();
      
      // Auto-disable shift after typing (but not caps lock) - defer rebuild to avoid input buffering
      if (shiftActive && !capsLockActive) {
        shiftActive = false;
        if (window.requestAnimationFrame) {
          requestAnimationFrame(function() { buildKeyboard(); });
        } else {
          setTimeout(function() { buildKeyboard(); }, 0);
        }
        // Don't refocus - input already has focus, refocus causes buffering
      }
    }
    
    // Trigger input event for any listeners
    var event = new Event('input', { bubbles: true });
    currentInput.dispatchEvent(event);
  }
  
  // Update popup display
  function updatePopup() {
    if (!currentInput) return;
    
    var popup = document.getElementById('osk-popup');
    var valueEl = document.getElementById('osk-popup-value');
    var labelEl = document.getElementById('osk-popup-label');
    
    if (!popup || !valueEl || !labelEl) return;
    
    var isPasswordField = currentInput.type === 'password';
    var displayValue = currentInput.value;
    
    // Show asterisks for password fields
    if (isPasswordField && displayValue) {
      displayValue = '*'.repeat(displayValue.length);
    }
    
    // Update label - prefer associated form label over placeholder
    var label = 'Enter Value';
    var formGroup = currentInput.closest('.form-group') || currentInput.closest('[class*="form"]') || currentInput.parentElement;
    var associatedLabel = formGroup ? formGroup.querySelector('label') : null;
    if (associatedLabel && associatedLabel.textContent && associatedLabel.textContent.trim()) {
      label = associatedLabel.textContent.trim();
    } else {
      label = currentInput.getAttribute('placeholder') || currentInput.getAttribute('aria-label') || 'Enter Value';
    }
    labelEl.textContent = label;
    
    // Update value display (no cursor - input field has its own)
    valueEl.textContent = displayValue || '';
  }
  
  // Open keyboard for input
  function openOSKForInput(inputElement) {
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/905604f3-2798-499f-a892-696c27f300f3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'keyboard.js:205',message:'openOSKForInput called',data:{hasInput:!!inputElement,inputId:inputElement?.id,inputType:inputElement?.type},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
    // #endregion agent log
    if (!inputElement) return;
    
    currentInput = inputElement;
    
    // Open in number layout for temperature/duration inputs (avoids needing to tap 123)
    var inputId = inputElement.id || '';
    if (inputId === 'recipe-temp' || inputId === 'recipe-duration' || inputId === 'temp-validation-set-temp-input') {
      numbersActive = true;
    } else {
      numbersActive = false;
    }
    buildKeyboard();
    
    // Show keyboard
    var osk = document.getElementById('osk');
    var popup = document.getElementById('osk-popup');
    
    if (osk) {
      osk.classList.add('visible');
      osk.setAttribute('aria-hidden', 'false');
    }
    
    // Show popup overlay
    if (popup) {
      popup.style.display = 'flex';
      updatePopup();
      
      // FIX: Add click handler to close keyboard and popup when clicking outside popup content
      if (!popup._oskPopupClickHandler) {
        popup._oskPopupClickHandler = function(e) {
          // Only close if clicking on the popup overlay itself, not on the content or its children
          var popupContent = popup.querySelector('.osk-popup-content');
          if (e.target === popup || (popupContent && !popupContent.contains(e.target))) {
            closeOSK();
          }
        };
        popup.addEventListener('click', popup._oskPopupClickHandler);
      }
    }
    
    // Add body class to prevent scrolling
    document.body.classList.add('keyboard-open');
    
    // FIX: Guard against spurious blur on first few clicks (login flicker)
    window._lastOSKOpenTime = Date.now();
    
    // Focus the input (but keyboard stays visible)
    if (currentInput) {
      currentInput.focus();
      
      // FIX: Add event listeners to sync external keyboard input with popup
      // Remove any existing listeners first to avoid duplicates
      if (currentInput._oskInputListener) {
        currentInput.removeEventListener('input', currentInput._oskInputListener);
        currentInput.removeEventListener('keydown', currentInput._oskKeydownListener);
      }
      
      // Sync popup when input value changes (from external keyboard)
      currentInput._oskInputListener = function() {
        updatePopup();
      };
      currentInput.addEventListener('input', currentInput._oskInputListener);
      
      // Handle Enter key from external keyboard
      currentInput._oskKeydownListener = function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          // Close keyboard and move to next field (same as OSK Enter behavior)
          closeOSK();
          setTimeout(function() {
            var form = currentInput.closest('form');
            var screen = currentInput.closest('.screen');
            var container = form || screen || document;
            var allInputs = Array.from(container.querySelectorAll('input[type="text"], input[type="password"], input[type="number"], input:not([type]), textarea, select'));
            var focusableInputs = allInputs.filter(function(i) {
              if (i.tagName === 'SELECT') return true;
              if (i.type === 'checkbox' || i.type === 'radio' || i.type === 'button' || i.type === 'submit' || i.type === 'datetime-local') return false;
              if (i.disabled || i.style.display === 'none' || i.offsetParent === null) return false;
              return true;
            });
            var currentIndex = focusableInputs.indexOf(currentInput);
            if (currentIndex >= 0 && currentIndex < focusableInputs.length - 1) {
              var nextInput = focusableInputs[currentIndex + 1];
              if (nextInput) {
                setTimeout(function() {
                  nextInput.focus();
                  nextInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
                  if (typeof openOSKForInput === 'function') {
                    openOSKForInput(nextInput);
                  }
                }, 50);
              }
            } else if (currentIndex === focusableInputs.length - 1) {
              // Last field: do NOT focus last action button (can trigger SAVE).
              // Only focus an explicit submit button when inside an actual <form>.
              if (form) {
                var submitBtn = form.querySelector('button[type="submit"]');
                if (submitBtn) {
                  setTimeout(function() { submitBtn.focus(); }, 50);
                  return;
                }
              }
              if (currentInput && typeof currentInput.blur === 'function') currentInput.blur();
            }
          }, 100);
        }
      };
      currentInput.addEventListener('keydown', currentInput._oskKeydownListener);
    }
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/905604f3-2798-499f-a892-696c27f300f3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'keyboard.js:232',message:'openOSKForInput completed',data:{oskVisible:osk?.classList.contains('visible'),popupDisplay:popup?.style.display},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
    // #endregion agent log
  }
  
  // Close keyboard
  function closeOSK() {
    var osk = document.getElementById('osk');
    var popup = document.getElementById('osk-popup');
    
    if (osk) {
      osk.classList.remove('visible');
      osk.setAttribute('aria-hidden', 'true');
    }
    
    if (popup) {
      popup.style.display = 'none';
      // FIX: Remove click handler when closing
      if (popup._oskPopupClickHandler) {
        popup.removeEventListener('click', popup._oskPopupClickHandler);
        popup._oskPopupClickHandler = null;
      }
    }
    
    document.body.classList.remove('keyboard-open');
    
    // Remove event listeners from current input
    if (currentInput) {
      if (currentInput._oskInputListener) {
        currentInput.removeEventListener('input', currentInput._oskInputListener);
        currentInput._oskInputListener = null;
      }
      if (currentInput._oskKeydownListener) {
        currentInput.removeEventListener('keydown', currentInput._oskKeydownListener);
        currentInput._oskKeydownListener = null;
      }
      currentInput.blur();
      currentInput = null;
    }
    
    // Reset keyboard state
    capsLockActive = false;
    shiftActive = false;
    numbersActive = false;
    buildKeyboard();
  }
  
  // Hide keyboard (alias for closeOSK)
  function hideOSK() {
    closeOSK();
  }
  
  // Initialize on load
  // #region agent log
  fetch('http://127.0.0.1:7242/ingest/905604f3-2798-499f-a892-696c27f300f3',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'keyboard.js:269',message:'keyboard.js script loaded',data:{readyState:document.readyState,hasKeyboardRoot:!!document.getElementById('keyboard-root')},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
  // #endregion agent log
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
  
  // Export functions to global scope
  window.openOSKForInput = openOSKForInput;
  window.closeOSK = closeOSK;
  window.hideOSK = hideOSK;
  
})();

