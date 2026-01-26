console.log('[script.js] LOADED', location.pathname);
document.addEventListener("DOMContentLoaded", () => {
  // =================== LOCATION BAR (TOP BAR) ===================
  const locWrap = document.getElementById("location-wrap");
  const locDisplay = document.getElementById("location-display");
  const locInput = document.getElementById("location-input");
  const locSuggest = document.getElementById("location-suggest");

  if (!locWrap || !locDisplay || !locInput || !locSuggest) return;

  const LS_KEY = "site_location";
  const isAuth = () => locWrap.dataset.auth === "1";

  const getCookie = (name) => {
    const m = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
    return m ? m.pop() : "";
  };

  const setDisplay = (text) => {
    const t = (text ?? "").toString().trim();
    locDisplay.textContent = t ? t : "Нажмите, чтобы указать";
  };

  const getAuthDefaultLocation = () => {
    if (!isAuth()) return "";
    const city = (locWrap.dataset.userCity || "").trim();
    const country = (locWrap.dataset.userCountry || "").trim();
    if (city && country) return `${city}, ${country}`;
    return city || country || "";
  };

  const getSavedLocation = () => (localStorage.getItem(LS_KEY) || "").trim();
  const saveLocal = (text) => localStorage.setItem(LS_KEY, (text || "").trim());

  const hideSuggest = () => {
    locSuggest.style.display = "none";
    locSuggest.innerHTML = "";
  };

  const enterEdit = () => {
    locInput.value = "";
    locDisplay.style.display = "none";
    locInput.style.display = "inline-block";
    locInput.focus();
    hideSuggest();
  };

  const exitEdit = () => {
    locInput.style.display = "none";
    locDisplay.style.display = "inline";
    hideSuggest();
  };

  // ---- API suggest ----
  let t = null;

  const fetchSuggest = async (q) => {
    const res = await fetch(`/api/location/suggest/?q=${encodeURIComponent(q)}`, {
      headers: { "Accept": "application/json" },
    });
    const data = await res.json().catch(() => ({}));
    return (data && data.ok && data.results) ? data.results : [];
  };

  // ---- SAVE (важно: по IDs) ----
  const saveByIds = async (it) => {
    const label = (it?.label || "").trim();
    if (!label) return;

    // UI всегда обновляем сразу
    setDisplay(label);
    saveLocal(label);

    // dataset (чтобы после refresh было дефолтом)
    locWrap.dataset.userCity = (it.city || "").trim();
    locWrap.dataset.userCountry = (it.country || "").trim();

    // гостю — только local
    if (!isAuth()) return;

    // сохраняем в профиль только если есть ids
    const country_id = it.country_id;
    const city_id = it.city_id;

    if (!country_id || !city_id) {
      console.warn("[LOCATION] Нет country_id/city_id в suggest. Профиль не обновлён.", it);
      return;
    }

    try {
      const res = await fetch("/api/location/set/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
          "Accept": "application/json",
        },
        body: JSON.stringify({ country_id, city_id }),
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.ok) {
        console.warn("[LOCATION] save failed", data);
        return;
      }

      // сервер может вернуть красивый формат
      const pretty = (data.location || label).trim();
      setDisplay(pretty);
      saveLocal(pretty);
    } catch (e) {
      console.warn("[LOCATION] network error", e);
    }
  };

  const renderSuggest = (items) => {
    locSuggest.innerHTML = "";
    if (!items || !items.length) return hideSuggest();

    items.forEach((it) => {
      const div = document.createElement("div");
      div.className = "suggest-item";
      div.textContent = (it.label || it.name || "").trim();

      div.addEventListener("mousedown", (e) => {
        e.preventDefault();
        locInput.value = "";
        hideSuggest();
        exitEdit();
        saveByIds(it);
      });

      locSuggest.appendChild(div);
    });

    locSuggest.style.display = "block";
  };

  // init display
  (() => {
    const authDef = getAuthDefaultLocation();
    if (authDef) return setDisplay(authDef);

    const saved = getSavedLocation();
    if (saved) return setDisplay(saved);

    setDisplay("Нажмите, чтобы указать");
  })();

  // events
  locDisplay.addEventListener("click", enterEdit);

  locInput.addEventListener("input", () => {
    clearTimeout(t);
    const q = (locInput.value || "").trim();

    t = setTimeout(async () => {
      if (!q) return hideSuggest();
      const items = await fetchSuggest(q);
      renderSuggest(items);
    }, 160);
  });

  locInput.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      exitEdit();
      const fallback = getAuthDefaultLocation() || getSavedLocation() || "Нажмите, чтобы указать";
      setDisplay(fallback);
    }
    // Enter — не сохраняем текстом, только выбор из подсказок
    if (e.key === "Enter") {
      e.preventDefault();
      hideSuggest();
    }
  });

  locInput.addEventListener("blur", () => setTimeout(() => {
    exitEdit();
    const fallback = getAuthDefaultLocation() || getSavedLocation() || "Нажмите, чтобы указать";
    setDisplay(fallback);
  }, 120));
});


document.addEventListener("DOMContentLoaded", () => {
  const menuBtn  = document.querySelector(".menu-btn");
  const sidebar  = document.getElementById("sidebar");
  const overlay  = document.getElementById("overlay");
  const closeBtn = document.getElementById("close-sidebar");

  if (!menuBtn || !sidebar || !overlay) return;

  const openMenu = () => {
    sidebar.classList.add("open");
    overlay.classList.add("active");
    document.body.style.overflow = "hidden";
  };

  const closeMenu = () => {
    sidebar.classList.remove("open");
    overlay.classList.remove("active");
    document.body.style.overflow = "";
  };

  menuBtn.addEventListener("click", (e) => {
    e.preventDefault();
    openMenu();
  });

  overlay.addEventListener("click", closeMenu);
  if (closeBtn) closeBtn.addEventListener("click", closeMenu);

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeMenu();
  });
});

// ================= Ошибки (tooltip) =====================
const FIELD_ERROR_HIDE_MS = 1500;
const fieldErrorTimers = new Map();
const fieldErrorNodes = new Map();

function clearFieldErrors(form) {
  if (!form) return;
  form.querySelectorAll('.field-error-tooltip').forEach((el) => el.remove());
  form.querySelectorAll('.field-error').forEach((el) => el.remove());
  form.querySelectorAll('.error').forEach((el) => el.classList.remove('error'));
  form.querySelectorAll('[data-has-error="1"]').forEach((el) => {
    el.dataset.hasError = '0';
  });
  fieldErrorTimers.forEach((timerId) => clearTimeout(timerId));
  fieldErrorTimers.clear();
  fieldErrorNodes.clear();
}

function clearFieldError(inputEl, { keepTouched = true } = {}) {
  if (!inputEl) return;

  inputEl.dataset.lockError = '0';

  const timerId = fieldErrorTimers.get(inputEl);
  if (timerId) {
    clearTimeout(timerId);
    fieldErrorTimers.delete(inputEl);
  }

  const tooltipNode = fieldErrorNodes.get(inputEl);
  if (tooltipNode) {
      tooltipNode.remove();
      fieldErrorNodes.delete(inputEl);
  }

  inputEl.classList.remove('error');
  inputEl.dataset.hasError = '0';

  const wrap = inputEl.closest('.input-with-error');
  if (wrap) {
    wrap.querySelectorAll('.field-error-tooltip').forEach((el) => el.remove());
    wrap.querySelectorAll('.field-error').forEach((el) => el.remove());
  } else if (inputEl.parentElement) {
    inputEl.parentElement
      .querySelectorAll('.field-error-tooltip')
      .forEach((el) => {
        if (el.dataset.forInput === (inputEl.id || inputEl.name || '')) {
          el.remove();
        }
      });
  }

  if (!keepTouched) {
    inputEl.dataset.touched = '0';
  }
}

function showFieldError(inputEl, message, { autoHide = true } = {}) {
  if (!inputEl) return;
  const msg = (message || '').toString().trim();
  if (!msg) return;

  clearFieldError(inputEl);

  inputEl.classList.add('error');
  inputEl.dataset.hasError = '1';

  // ✅ если ошибка из submit — не даём ей исчезать от programmatic focus
  if (!autoHide) inputEl.dataset.lockError = '1';

  const wrap = inputEl.closest('.input-with-error');
  const host = wrap || inputEl.parentElement;
  if (!host) return;

  const tooltip = document.createElement('div');
  tooltip.className = 'field-error-tooltip';
  tooltip.innerHTML = `<div class="field-error-tooltip-content">${msg}</div>`;
  const inputKey = inputEl.id || inputEl.name || '';
  tooltip.dataset.forInput = inputKey;

  if (wrap) wrap.appendChild(tooltip);
  else inputEl.insertAdjacentElement('afterend', tooltip);

  fieldErrorNodes.set(inputEl, tooltip);

  if (!autoHide) return;

  const timerId = setTimeout(() => clearFieldError(inputEl), FIELD_ERROR_HIDE_MS);
  fieldErrorTimers.set(inputEl, timerId);
}


function debounce(fn, wait = 350) {
  let timeoutId = null;
  return (...args) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), wait);
  };
}

function collapseInnerSpaces(value) {
  return value.replace(/\s{2,}/g, ' ');
}

function preventLeadingSpace(inputEl, message = 'Не начинайте с пробела') {
  if (!inputEl) return;

  inputEl.addEventListener('keydown', (e) => {
    if (e.key === ' ' && !inputEl.value) {
      e.preventDefault();
      showFieldError(inputEl, message);
    }
  });

  inputEl.addEventListener('input', () => {
    const original = inputEl.value || '';
    const withoutLeading = original.replace(/^\s+/, '');
    const normalized = collapseInnerSpaces(withoutLeading);

    if (normalized !== original) {
      const pos = inputEl.selectionStart ?? normalized.length;
      inputEl.value = normalized;
      const nextPos = Math.min(pos, normalized.length);
      inputEl.setSelectionRange(nextPos, nextPos);
    }
  });
}

function attachBlurOnlyValidation(inputEl, validator) {
  if (!inputEl || typeof validator !== 'function') return;

  inputEl.addEventListener('focus', () => {
    // ✅ не чистим submit-ошибку от программного focus()
    if (inputEl.dataset.lockError === '1') return;
    clearFieldError(inputEl);
  });

  inputEl.addEventListener('input', () => {
    // ✅ как только пользователь реально вводит — снимаем лок и чистим
    if (inputEl.dataset.lockError === '1') inputEl.dataset.lockError = '0';
    if (inputEl.dataset.hasError === '1') clearFieldError(inputEl);
  });

  inputEl.addEventListener('blur', () => {
    inputEl.dataset.touched = '1';
    validator(inputEl.value, { fromBlur: true, fromSubmit: false });
  });
}


function scrollToFirstError(form) {
  if (!form) return;
  const firstError = form.querySelector('.error');
  if (!firstError) return;
  firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function getCookie(name) {
  const match = document.cookie.match(new RegExp('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)'));
  return match ? match.pop() : '';
}

function parseAcceptsJson(request) {
  const accept = request.headers.get('Accept') || '';
  return accept.includes('application/json');
}

// ================= Валидаторы =====================
const validateName = (name) => {
  const trimmed = (name || '').trim();
  if (!trimmed) return false;

  // буквы (RU/EN), пробелы, дефисы
  const rx = /^[A-Za-zА-Яа-яЁё]+(?:[\s-][A-Za-zА-Яа-яЁё]+)*$/;

  if (trimmed.length < 2) return false;
  if (trimmed.startsWith('-') || trimmed.endsWith('-')) return false;
  if (trimmed.includes('--')) return false;

  return rx.test(trimmed);
};

// email + разрешенные домены
const validateEmail = (email) => {
  if (/\s/.test(email)) return false;
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) return false;

  const allowedDomains = [
    'gmail.com','outlook.com','hotmail.com','yahoo.com',
    'icloud.com','me.com','mac.com','proton.me','protonmail.com',
    'aol.com','yandex.ru','ya.ru','mail.ru','list.ru',
    'bk.ru','inbox.ru','rambler.ru','dvfu.ru'
  ];

  const domain = (email.split('@')[1] || '').toLowerCase();
  return allowedDomains.includes(domain);
};

const validatePassword = (password) => password && password.length >= 6 && !/\s/.test(password);

const validateBirthDate = (dateString) => {
  if (!dateString) return false;
  const birthDate = new Date(dateString);
  if (Number.isNaN(birthDate.getTime())) return false;

  const today = new Date();
  const minAgeDate = new Date(today.getFullYear() - 14, today.getMonth(), today.getDate());
  return birthDate <= minAgeDate && birthDate > new Date(1900, 0, 1);
};
// нормализация: оставляем + и цифры, приводим к виду +123456...
const normalizePhoneAny = (phone) => {
  const raw = (phone || '').trim();
  if (!raw) return null;

  const digits = raw.replace(/\D/g, '');
  if (!digits) return null;

  // всегда делаем с плюсом
  return '+' + digits;
};

// базовая валидация E.164: + и 10..15 цифр (очень распространённый стандарт)
const validatePhoneAny = (phone) => {
  const p = normalizePhoneAny(phone);
  return !!p && /^\+\d{11,15}$/.test(p);
};

// спец: под выбранный phone_code (например +7 / +40)
const validatePhoneByCountryCode = (phone, phoneCode) => {
  const p = normalizePhoneAny(phone);
  if (!p) return false;

  const code = (phoneCode || '').trim();
  if (!code) return validatePhoneAny(p);

  // телефон должен начинаться с кода страны
  if (!p.startsWith(code)) return false;

  // минимально: длина в E.164 + цифры 10..15
  return /^\+\d{11,15}$/.test(p);
};

const phoneMasks = {
  '+7': {
    placeholder: '+7 (999) 999-99-99',
    groups: [3, 3, 2, 2],
    separators: [' (', ') ', '-', '-'],
    end: '',
  },
  '+40': {
    placeholder: '+40 999 999 999',
    groups: [3, 3, 3],
    separators: [' ', ' ', ''],
    end: '',
  },
};

function getDigits(value) {
  return (value || '').replace(/\D/g, '');
}

function stripPhoneCode(digits, phoneCode) {
  const codeDigits = getDigits(phoneCode);
  if (!codeDigits) return digits;
  return digits.startsWith(codeDigits) ? digits.slice(codeDigits.length) : digits;
}

function applyGroupedMask(baseCode, restDigits, maskConfig) {
  const digits = restDigits.slice(0, maskConfig.groups.reduce((a, b) => a + b, 0));
  let out = baseCode;
  let idx = 0;

  maskConfig.groups.forEach((size, groupIdx) => {
    if (idx >= digits.length) return;
    const chunk = digits.slice(idx, idx + size);
    if (!chunk) return;
    out += (maskConfig.separators[groupIdx] || '') + chunk;
    idx += chunk.length;
  });

  if (idx >= digits.length && maskConfig.end) {
    out += maskConfig.end;
  }

  return out.trim();
}

function formatPhoneForCode(rawValue, phoneCode) {
  const code = (phoneCode || '').trim();
  const digits = getDigits(rawValue);
  const maskConfig = phoneMasks[code];

  if (!digits && code) return code;
  if (!digits) return '';

  const baseCode = code || '+';
  const baseDigits = getDigits(baseCode);

  if (maskConfig && baseDigits) {
    const codeDigits = getDigits(code);
    let restDigits = stripPhoneCode(digits, code);
    while (codeDigits && restDigits.startsWith(codeDigits)) {
      restDigits = restDigits.slice(codeDigits.length);
    }
    return applyGroupedMask(code, restDigits, maskConfig);
  }

  // fallback: просто + и группы по 3
  const capped = digits.slice(0, 15);
  const chunks = capped.match(/.{1,3}/g) || [];
  return '+' + chunks.join(' ').trim();
}

function syncPhoneMaskWithCode(phoneEl, phoneCodeEl) {
  if (!phoneEl || !phoneCodeEl) return;

  const ensurePrefix = (code) => {
    const maskConfig = phoneMasks[code];
    if (!code) return;
    // для +7 хотим прямо "+7 (" как старт
    if (code === '+7') {
      if (!phoneEl.value || phoneEl.value === '+7') phoneEl.value = '+7 (';
      return;
    }
    // для остальных просто код
    if (!phoneEl.value) phoneEl.value = code;
  };

  const rebuildPhoneWithCode = (newCode, oldCode) => {
    const nextCode = (newCode || '').trim();
    const prevCode = (oldCode || '').trim();
    const digits = getDigits(phoneEl.value);
    const prevDigits = getDigits(prevCode);
    const nextDigits = getDigits(nextCode);

    let restDigits = digits;

    // убираем старый код из цифр
    if (prevDigits && restDigits.startsWith(prevDigits)) {
      restDigits = restDigits.slice(prevDigits.length);
    } else if (nextDigits && restDigits.startsWith(nextDigits)) {
      restDigits = restDigits.slice(nextDigits.length);
    }

    // защита от "дублирования" кода, если он прилепился дважды
    while (nextDigits && restDigits.startsWith(nextDigits)) {
      restDigits = restDigits.slice(nextDigits.length);
    }

    // если после удаления нет номера — покажем хотя бы префикс/код
    if (!restDigits) {
      phoneEl.value = '';
      ensurePrefix(nextCode);
      return;
    }

    const rebuiltRaw = nextCode ? `${nextCode}${restDigits}` : `+${restDigits}`;
    phoneEl.value = formatPhoneForCode(rebuiltRaw, nextCode);
  };

  const setPlaceholder = (code) => {
    const maskConfig = phoneMasks[code];
    phoneEl.placeholder = maskConfig?.placeholder || (code ? `${code}...` : '+...');
  };

  const update = (oldCodeOverride = '') => {
    const code = (phoneCodeEl.value || '').trim();
    setPlaceholder(code);

    const prevCode = oldCodeOverride || phoneCodeEl.dataset.prevCode || '';
    const codeChanged = prevCode !== code;

    if (codeChanged) {
      rebuildPhoneWithCode(code, prevCode);
    } else {
      // обычное форматирование
      phoneEl.value = formatPhoneForCode(phoneEl.value, code);
      // если получилось пусто — восстановим префикс
      if (!phoneEl.value) ensurePrefix(code);
    }

    phoneCodeEl.dataset.prevCode = code;
  };

  // ✅ ВАЖНО: если пользователь стер всё — на фокусе вернём префикс
  phoneEl.addEventListener('focus', () => {
    const code = (phoneCodeEl.value || '').trim();
    if (!phoneEl.value) ensurePrefix(code);
  });

  // ✅ ВАЖНО: форматирование всегда после ввода, но если пусто — возвращаем префикс
  phoneEl.addEventListener('input', () => {
    const code = (phoneCodeEl.value || '').trim();

    // если пользователь удалил всё (или оставил мусор типа "+")
    const digits = getDigits(phoneEl.value);
    if (!digits) {
      phoneEl.value = '';
      ensurePrefix(code);
      return;
    }

    phoneEl.value = formatPhoneForCode(phoneEl.value, code);

    // если после форматтера пусто — тоже восстановим
    if (!phoneEl.value) ensurePrefix(code);
  });

  // ✅ смена страны: пересобираем номер без удвоения кода
  phoneCodeEl.addEventListener('change', (e) => {
    const oldCode = e?.detail?.oldCode || phoneCodeEl.dataset.prevCode || '';
    update(oldCode);
  });

  update();
}


function validateGenderValue(form) {
  const genderValue = form.querySelector('input[name="gender"]:checked')?.value || '';
  return ['male', 'female'].includes(genderValue) ? genderValue : '';
}

// =================== SUGGEST HELPERS ===================
function hideBox(box) {
  if (!box) return;
  box.style.display = 'none';
  box.innerHTML = '';
}

function renderSuggest(box, items, onPick) {
  if (!box) return;
  box.innerHTML = '';
  if (!items || !items.length) return hideBox(box);

  items.forEach((item) => {
    const div = document.createElement('div');
    div.className = 'suggest-item';
    div.textContent = item.name;

    div.addEventListener('mousedown', (e) => {
      e.preventDefault();
      onPick(item);
      hideBox(box);
    });

    box.appendChild(div);
  });

  box.style.display = 'block';
}

// =================== COUNTRY / CITY / REGISTER ===================
document.addEventListener('DOMContentLoaded', () => {
  const regForm = document.getElementById('register-form');
  if (!regForm) return;

  const nameInput = regForm.querySelector('input[name="name"]');
  const emailInput = regForm.querySelector('input[name="email"]');
  const countryInput = document.getElementById('country-input');
  const cityInput = document.getElementById('city-input');
  const phoneInput = document.getElementById('phone-input');
  const birthDateInput = regForm.querySelector('input[name="birth_date"]');
  const passwordInput = regForm.querySelector('input[name="password"]');
  const genderInputs = Array.from(regForm.querySelectorAll('input[name="gender"]'));

  const countryIdInput = document.getElementById('country-id');
  const cityIdInput = document.getElementById('city-id');
  const phoneCodeInput = document.getElementById('phone-code');

  const countrySuggestBox = document.getElementById('country-suggest');
  const citySuggestBox = document.getElementById('city-suggest');

  const countryErrorMessage = 'Выберите страну (можно ввести полностью как в подсказке)';
  const cityErrorMessage = 'Выберите город (можно ввести полностью как в подсказке)';
  const emailSpaceMessage = 'Email не должен содержать пробелы';
  const passwordSpaceMessage = 'Пароль не должен содержать пробелы';

  // ============ helpers ============
  const hasSpaces = (v) => /\s/.test(v || '');
  const normalizeEq = (s) => (s || '').trim().toLowerCase();

  function getCookie(name) {
    const match = document.cookie.match(new RegExp('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)'));
    return match ? match.pop() : '';
  }

  // запрет первого пробела и нормализация (для текстовых)
  [nameInput, countryInput, cityInput].forEach((el) => preventLeadingSpace(el));

  // блокируем пробелы в email/пароле (и показываем ошибку)
  const attachSpaceBlocker = (inputEl, message) => {
    if (!inputEl) return;
    inputEl.addEventListener('keydown', (e) => {
      if (e.key !== ' ') return;
      e.preventDefault();
      showFieldError(inputEl, message, { autoHide: true });
    });
  };
  attachSpaceBlocker(emailInput, emailSpaceMessage);
  attachSpaceBlocker(passwordInput, passwordSpaceMessage);

  const normalizeTextInput = (inputEl) => {
    if (!inputEl) return '';
    const withoutLeading = (inputEl.value || '').replace(/^\s+/, '');
    const collapsed = collapseInnerSpaces(withoutLeading);
    inputEl.value = collapsed;
    return collapsed.trim();
  };

  // ============ API ============
  let tCountry = null;
  let tCity = null;

  async function fetchCountries(q) {
    const res = await fetch(`/api/countries/?q=${encodeURIComponent(q)}`, {
      headers: { Accept: 'application/json' },
    });
    const data = await res.json().catch(() => ({ results: [] }));
    return data.results || [];
  }

  async function fetchCities(q, countryId) {
    const url = `/api/cities/?q=${encodeURIComponent(q)}&country_id=${encodeURIComponent(countryId || '')}`;
    const res = await fetch(url, { headers: { Accept: 'application/json' } });
    const data = await res.json().catch(() => ({ results: [] }));
    return data.results || [];
  }

  async function resolveCountryByText() {
    if (!countryInput || !countryIdInput) return false;
    const text = normalizeEq(countryInput.value);
    if (!text) return false;
    if (countryIdInput.value) return true;

    const items = await fetchCountries(countryInput.value);
    const hit = items.find((it) => normalizeEq(it.name) === text);
    if (!hit) return false;

    countryInput.value = hit.name;
    countryIdInput.value = String(hit.id || '');

    // phone_code update (с корректной пересборкой телефона)
    if (phoneCodeInput) {
      const prev = (phoneCodeInput.value || '').trim();
      phoneCodeInput.value = (hit.phone_code || '').trim();
      phoneCodeInput.dispatchEvent(new CustomEvent('change', { detail: { oldCode: prev } }));
    }
    return !!countryIdInput.value;
  }

  async function resolveCityByText() {
    if (!cityInput || !cityIdInput) return false;
    const text = normalizeEq(cityInput.value);
    if (!text) return false;
    if (cityIdInput.value) return true;

    const countryId = countryIdInput?.value || '';
    if (!countryId) return false;

    const items = await fetchCities(cityInput.value, countryId);
    const hit = items.find((it) => normalizeEq(it.name) === text);
    if (!hit) return false;

    cityInput.value = hit.name;
    cityIdInput.value = String(hit.id || '');
    return !!cityIdInput.value;
  }

  // ============ masks (phone) ============
  // ВАЖНО: в твоей syncPhoneMaskWithCode добавим поведение:
  // - можно стереть полностью
  // - на blur вернёт код страны
  // - при смене страны пересоберёт телефон без удвоения кода
  // Мы не трогаем твою функцию глобально, просто навешиваем нужные обработчики поверх.

  syncPhoneMaskWithCode(phoneInput, phoneCodeInput);

  if (phoneInput && phoneCodeInput) {
    phoneInput.addEventListener('input', () => {
      // если полностью стёр — не мешаем
      if (!phoneInput.value) return;
    });

    phoneInput.addEventListener('blur', () => {
      const code = (phoneCodeInput.value || '').trim();
      if (!phoneInput.value.trim() && code) {
        phoneInput.value = code;
      }
    });
  }

  // ============ suggest UI ============
  function hideBox(box) {
    if (!box) return;
    box.style.display = 'none';
    box.innerHTML = '';
  }

  function renderSuggest(box, items, onPick) {
    if (!box) return;
    box.innerHTML = '';
    if (!items || !items.length) return hideBox(box);

    items.forEach((item) => {
      const div = document.createElement('div');
      div.className = 'suggest-item';
      div.textContent = item.name;

      div.addEventListener('mousedown', (e) => {
        e.preventDefault();
        onPick(item);
        hideBox(box);
      });

      box.appendChild(div);
    });

    box.style.display = 'block';
  }

  // reset bindings when country changes manually
  function resetCountryBinding({ keepCountryText = true } = {}) {
    const prevCode = (phoneCodeInput?.value || '').trim();

    if (countryIdInput) countryIdInput.value = '';
    if (phoneCodeInput) phoneCodeInput.value = '';
    if (cityInput) cityInput.value = '';
    if (cityIdInput) cityIdInput.value = '';

    hideBox(citySuggestBox);

    // просим телефон пересобраться (убрать старый код)
    if (phoneCodeInput) {
      phoneCodeInput.dispatchEvent(new CustomEvent('change', { detail: { oldCode: prevCode } }));
    }

    if (!keepCountryText && countryInput) countryInput.value = '';
  }

  // ============ binding validators (async, auto-resolve) ============
  const validateCountryBinding = async ({ show = true } = {}) => {
    if (!countryInput || !countryIdInput) return true;
    normalizeTextInput(countryInput);

    if (!countryIdInput.value && countryInput.value.trim()) {
      try { await resolveCountryByText(); } catch {}
    }

    const ok = !!countryIdInput.value && !!countryInput.value.trim();
    if (!ok && show) showFieldError(countryInput, countryErrorMessage);
    if (ok) clearFieldError(countryInput);
    return ok;
  };

  const validateCityBinding = async ({ show = true } = {}) => {
    if (!cityInput || !cityIdInput) return true;
    normalizeTextInput(cityInput);

    if (!cityIdInput.value && cityInput.value.trim()) {
      try { await resolveCityByText(); } catch {}
    }

    const ok = !!cityIdInput.value && !!cityInput.value.trim();
    if (!ok && show) showFieldError(cityInput, cityErrorMessage);
    if (ok) clearFieldError(cityInput);
    return ok;
  };

  // ============ field validators (live) ============
  const validators = new Map([
    [nameInput, (_, ctx = {}) => {
      const value = normalizeTextInput(nameInput);

      if (!value) {
        if (ctx.fromSubmit) {
          showFieldError(nameInput, 'Введите имя');
          return false;
        }
        return true;
      }

      if (value.length > 30) {
        showFieldError(nameInput, 'Имя слишком длинное (до 30 символов)');
        return false;
      }

      if (!validateName(value)) {
        showFieldError(nameInput, 'Имя: только буквы, пробел, дефис (от 2 символов)');
        return false;
      }

      clearFieldError(nameInput);
      return true;
    }],

    [emailInput, (_, ctx = {}) => {
      const value = (emailInput.value || '').toLowerCase();
      emailInput.value = value;

      if (!value) {
        if (ctx.fromSubmit) {
          showFieldError(emailInput, 'Введите email');
          return false;
        }
        return true;
      }

      if (hasSpaces(value)) {
        showFieldError(emailInput, emailSpaceMessage);
        return false;
      }

      if (!validateEmail(value)) {
        showFieldError(emailInput, 'Введите корректный email');
        return false;
      }

      clearFieldError(emailInput);
      return true;
    }],

    [phoneInput, () => {
      const phoneCode = (phoneCodeInput?.value || '').trim();
      const value = phoneInput?.value || '';
      if (!value.trim()) {
        showFieldError(phoneInput, 'Введите номер телефона');
        return false;
      }


      if (!validatePhoneByCountryCode(value, phoneCode)) {
        showFieldError(
          phoneInput,
          phoneCode
            ? `Телефон должен начинаться с ${phoneCode} и быть корректным`
            : 'Введите корректный телефон (+ и 11–15 цифр)'
        );
        return false;
      }
      clearFieldError(phoneInput);
      return true;
    }],

    [birthDateInput, (_, ctx = {}) => {
      const raw = (birthDateInput?.value || '').trim();

      // ОБЯЗАТЕЛЬНО при submit
      if (!raw) {
        if (ctx.fromSubmit) {
          showFieldError(birthDateInput, 'Введите дату рождения');
          return false;
        }
        return true;
      }

      // input[type=date] должен отдавать YYYY-MM-DD
      if (!/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
        showFieldError(birthDateInput, 'Введите дату через календарь', { autoHide: !ctx.fromSubmit });
        return false;
      }

      const year = Number(raw.slice(0, 4));
      if (!Number.isFinite(year) || raw.slice(0, 4).length !== 4) {
        showFieldError(birthDateInput, 'Год должен быть из 4 цифр', { autoHide: !ctx.fromSubmit });
        return false;
      }

      // ограничение по диапазону + возраст 14+
      const d = new Date(raw + 'T00:00:00');
      if (Number.isNaN(d.getTime())) {
        showFieldError(birthDateInput, 'Некорректная дата', { autoHide: !ctx.fromSubmit });
        return false;
      }

      const today = new Date();
      const min = new Date(1900, 0, 1);
      const max = new Date(today.getFullYear() - 14, today.getMonth(), today.getDate());

      if (d < min) {
        showFieldError(birthDateInput, 'Дата слишком ранняя', { autoHide: !ctx.fromSubmit });
        return false;
      }
      if (d > max) {
        showFieldError(birthDateInput, 'Возраст должен быть 14+', { autoHide: !ctx.fromSubmit });
        return false;
      }

      clearFieldError(birthDateInput);
      return true;
    }],


    [passwordInput, (_, ctx = {}) => {
      const value = passwordInput.value || '';

      if (!value) {
        if (ctx.fromSubmit) {
          showFieldError(passwordInput, 'Введите пароль');
          return false;
        }
        return true;
      }

      if (hasSpaces(value)) {
        showFieldError(passwordInput, passwordSpaceMessage);
        return false;
      }

      if (value.length < 6) {
        showFieldError(passwordInput, 'Пароль минимум 6 символов');
        return false;
      }

      clearFieldError(passwordInput);
      return true;
    }],
  ]);

  // ВАЖНО: чтобы ошибки появлялись по ходу ввода — меняем attachLiveValidation поведение:
  // attachLiveValidation уже есть у тебя глобально, но она валидирует по input только после touched.
  // Мы не переписываем твою функцию, а добавим принудительный "touched=1" после первого ввода.
  function makeLiveNow(inputEl) {
    if (!inputEl) return;
    inputEl.addEventListener('input', () => {
      if (inputEl.dataset.touched !== '1') inputEl.dataset.touched = '1';
    });
  }

  validators.forEach((validator, inputEl) => {
    attachBlurOnlyValidation(inputEl, validator);
    makeLiveNow(inputEl);
  });

  // ============ country input handlers ============
  if (countryInput && countrySuggestBox) {
    countryInput.addEventListener('focus', () => clearFieldError(countryInput));

    countryInput.addEventListener('input', () => {
      clearTimeout(tCountry);
      const q = (countryInput.value || '').trim();

      // как только руками меняем — сбрасываем привязки
      resetCountryBinding({ keepCountryText: true });

      if (q.length < 1) return hideBox(countrySuggestBox);

      tCountry = setTimeout(async () => {
        try {
          const items = await fetchCountries(q);
          renderSuggest(countrySuggestBox, items, (item) => {
            countryInput.value = item.name;

            if (countryIdInput) countryIdInput.value = String(item.id || '');

            if (phoneCodeInput) {
              const prev = (phoneCodeInput.value || '').trim();
              phoneCodeInput.value = (item.phone_code || '').trim();
              phoneCodeInput.dispatchEvent(new CustomEvent('change', { detail: { oldCode: prev } }));
            }

            clearFieldError(countryInput);
          });
        } catch {
          hideBox(countrySuggestBox);
        }
      }, 150);
    });

    // при уходе с поля — пытаемся авто-совпадение
    countryInput.addEventListener('blur', async () => {
      setTimeout(() => hideBox(countrySuggestBox), 150);
      await validateCountryBinding({ show: true });
    });
  }

  // ============ city input handlers ============
  if (cityInput && citySuggestBox) {
    cityInput.addEventListener('focus', () => clearFieldError(cityInput));

    cityInput.addEventListener('input', () => {
      clearTimeout(tCity);
      const q = (cityInput.value || '').trim();

      if (cityIdInput) cityIdInput.value = '';

      const countryId = countryIdInput ? countryIdInput.value : '';
      if (!countryId) {
        hideBox(citySuggestBox);
        return;
      }

      if (q.length < 1) return hideBox(citySuggestBox);

      tCity = setTimeout(async () => {
        try {
          const items = await fetchCities(q, countryId);
          renderSuggest(citySuggestBox, items, (item) => {
            cityInput.value = item.name;
            if (cityIdInput) cityIdInput.value = String(item.id || '');
            clearFieldError(cityInput);
          });
        } catch {
          hideBox(citySuggestBox);
        }
      }, 150);
    });

    cityInput.addEventListener('blur', async () => {
      setTimeout(() => hideBox(citySuggestBox), 150);
      await validateCityBinding({ show: true });
    });
  }

  // gender
  genderInputs.forEach((inputEl) => {
    inputEl.addEventListener('change', () => {
      const genderWrap = document.getElementById('gender-group');
      if (genderWrap) genderWrap.classList.remove('error');
      clearFieldError(genderInputs[0]);
    });
    inputEl.addEventListener('focus', () => {
      const genderWrap = document.getElementById('gender-group');
      if (genderWrap) genderWrap.classList.remove('error');
      clearFieldError(genderInputs[0]);
    });
  });

  function validateGenderValue(form) {
    const v = form.querySelector('input[name="gender"]:checked')?.value || '';
    return ['male', 'female'].includes(v) ? v : '';
  }

  // ============ submit ============
  async function validateAllOnSubmit(validators) {
  let ok = true;

  for (const [inputEl, validator] of validators.entries()) {
    if (!inputEl) continue;

    inputEl.dataset.touched = '1';

    const res = await validator(inputEl.value, {
      fromSubmit: true,
      fromBlur: false,
      fromInput: false,
    });

    if (!res) ok = false;
  }

  return ok;
}

  function showErrorsFromServer(errors) {
    if (!errors) return;

    const fieldMap = {
      name: nameInput,
      email: emailInput,
      country: countryInput,
      country_id: countryInput,
      city: cityInput,
      city_id: cityInput,
      phone: phoneInput,
      birth_date: birthDateInput,
      password: passwordInput,
    };

    Object.entries(errors).forEach(([field, messages]) => {
      const msg = Array.isArray(messages) ? messages[0] : messages;
      if (!msg) return;

      if (field === '__all__') {
        showFieldError(emailInput, msg);
        return;
      }

      if (field === 'gender') {
        const genderWrap = document.getElementById('gender-group');
        if (genderWrap) genderWrap.classList.add('error');
        showFieldError(genderInputs[0], msg, { autoHide: true });
        return;
      }

      const target = fieldMap[field] || regForm.querySelector(`[name="${field}"]`);
      showFieldError(target, msg);
    });
  }

  regForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearFieldErrors(regForm);

    let ok = true;

    const clientOk = await validateAllOnSubmit(validators);
    if (!clientOk) ok = false;

    if (!await validateCountryBinding({ show: true })) ok = false;
    if (!await validateCityBinding({ show: true })) ok = false;

    const gender = validateGenderValue(regForm);
    if (!gender) {
      const genderWrap = document.getElementById('gender-group');
      if (genderWrap) genderWrap.classList.add('error');
      showFieldError(genderInputs[0], 'Выберите пол');
      ok = false;
    }

    if (!ok) {
      scrollToFirstError(regForm);
      return;
    }


    const payload = {
      email: (emailInput?.value || '').trim().toLowerCase(),
      password: passwordInput?.value || '',
      name: (nameInput?.value || '').trim(),
      phone: phoneInput?.value || '',
      country_id: countryIdInput?.value || '',
      city_id: cityIdInput?.value || '',
      birth_date: birthDateInput?.value || '',
      gender: validateGenderValue(regForm),
    };

    const csrfToken =
      regForm.querySelector('input[name="csrfmiddlewaretoken"]')?.value || getCookie('csrftoken');

    try {
      const res = await fetch('/api/register/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify(payload),
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok || data.ok === false || data.success === false) {
        showErrorsFromServer(data.errors);
        if (!data.errors && data.message) showFieldError(emailInput, data.message);
        scrollToFirstError(regForm);
        return;
      }

      window.location.href = data.redirect || '/index/';
    } catch (err) {
      showFieldError(emailInput, 'Ошибка сети. Попробуйте ещё раз.');
      scrollToFirstError(regForm);
    }
  });
});

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('login-form');
  console.log('[LOGIN] form=', !!form);
  if (!form) return;

  const emailInput = form.querySelector('input[name="email"]');
  const passInput  = form.querySelector('input[name="password"]');
  const nextInput  = form.querySelector('input[name="next"]');

  const emailSpaceMessage = 'Email не должен содержать пробелы';
  const passwordSpaceMessage = 'Пароль не должен содержать пробелы';

  const hasSpaces = (v) => /\s/.test(v || '');
  const validateEmail = (email) => {
    if (/\s/.test(email)) return false;
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  };

  // блок пробела (как у тебя)
  const attachSpaceBlocker = (inputEl, message) => {
    if (!inputEl) return;
    inputEl.addEventListener('keydown', (e) => {
      if (e.key !== ' ') return;
      e.preventDefault();
      showFieldError(inputEl, message, { autoHide: true });
    });
  };
  attachSpaceBlocker(emailInput, emailSpaceMessage);
  attachSpaceBlocker(passInput, passwordSpaceMessage);

  const validators = new Map([
    [emailInput, (_, ctx = {}) => {
      const value = (emailInput.value || '').trim().toLowerCase();
      emailInput.value = value;

      if (!value) {
        if (ctx.fromSubmit) {
          showFieldError(emailInput, 'Введите email', { autoHide: false });
          return false;
        }
        return true;
      }
      if (hasSpaces(value)) {
        showFieldError(emailInput, emailSpaceMessage, { autoHide: !ctx.fromSubmit });
        return false;
      }
      if (!validateEmail(value)) {
        showFieldError(emailInput, 'Введите корректный email', { autoHide: !ctx.fromSubmit });
        return false;
      }

      clearFieldError(emailInput);
      return true;
    }],

    [passInput, (_, ctx = {}) => {
      const value = passInput.value || '';

      if (!value) {
        if (ctx.fromSubmit) {
          showFieldError(passInput, 'Введите пароль', { autoHide: false });
          return false;
        }
        return true;
      }
      if (hasSpaces(value)) {
        showFieldError(passInput, passwordSpaceMessage, { autoHide: !ctx.fromSubmit });
        return false;
      }
      if (value.length < 6) {
        // если хочешь такую же политику, как при регистрации
        showFieldError(passInput, 'Пароль минимум 6 символов', { autoHide: !ctx.fromSubmit });
        return false;
      }

      clearFieldError(passInput);
      return true;
    }],
  ]);

  validators.forEach((validator, inputEl) => attachBlurOnlyValidation(inputEl, validator));

  async function validateAllOnSubmit(map) {
    let ok = true;
    for (const [inputEl, validator] of map.entries()) {
      if (!inputEl) continue;
      inputEl.dataset.touched = '1';
      const res = await validator(inputEl.value, { fromSubmit: true, fromBlur: false, fromInput: false });
      if (!res) ok = false;
    }
    return ok;
  }

  function showErrorsFromServer(errors) {
    if (!errors) return;
    Object.entries(errors).forEach(([field, messages]) => {
      const msg = Array.isArray(messages) ? messages[0] : messages;
      if (!msg) return;

      if (field === '__all__') {
        showFieldError(emailInput, msg, { autoHide: false });
        return;
      }
      const target =
        field === 'email' ? emailInput :
        field === 'password' ? passInput :
        form.querySelector(`[name="${field}"]`);

      showFieldError(target, msg, { autoHide: false });
    });
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearFieldErrors(form);

    const clientOk = await validateAllOnSubmit(validators);
    if (!clientOk) {
      scrollToFirstError(form);
      return;
    }

    const payload = {
      email: (emailInput.value || '').trim().toLowerCase(),
      password: passInput.value || '',
      next: (nextInput?.value || '').trim(),
    };

    const csrfToken =
      form.querySelector('input[name="csrfmiddlewaretoken"]')?.value || getCookie('csrftoken');

    try {
      const res = await fetch('/api/login/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify(payload),
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok || data.ok === false) {
        showErrorsFromServer(data.errors);
        if (!data.errors && data.message) showFieldError(emailInput, data.message, { autoHide: false });
        scrollToFirstError(form);
        return;
      }

      window.location.href = data.redirect || '/index/';
    } catch {
      showFieldError(emailInput, 'Ошибка сети. Попробуйте ещё раз.', { autoHide: false });
      scrollToFirstError(form);
    }
  });
});
// =================== SEARCH SUGGEST (API) ===================
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("search-form");
  const input = document.getElementById("search-input");
  const box = document.getElementById("search-suggest");

  console.log("[SEARCH] init", { form: !!form, input: !!input, box: !!box });

  if (!form || !input || !box) return;

  let t = null;
  let activeIndex = -1;
  let current = [];

  const hide = () => {
    box.style.display = "none";
    box.innerHTML = "";
    activeIndex = -1;
    current = [];
  };

  const setActive = (idx) => {
    const nodes = Array.from(box.querySelectorAll(".suggest-item"));
    nodes.forEach((n) => n.classList.remove("is-active"));
    if (idx >= 0 && idx < nodes.length) {
      nodes[idx].classList.add("is-active");
      nodes[idx].scrollIntoView({ block: "nearest" });
    }
  };

  const render = (items) => {
    box.innerHTML = "";
    if (!items || !items.length) return hide();

    current = items.slice(0, 10);
    current.forEach((it, idx) => {
      const div = document.createElement("div");
      div.className = "suggest-item";
      div.textContent = (it.label || "").trim();

      div.addEventListener("mousedown", (e) => {
        e.preventDefault();
        input.value = div.textContent;
        hide();
        form.submit();
      });

      box.appendChild(div);
    });

    box.style.display = "block";
  };

  const fetchSuggest = async (q) => {
    const url = `/api/search/suggest/?q=${encodeURIComponent(q)}`;
    console.log("[SEARCH] fetch", url);

    const res = await fetch(url, { headers: { Accept: "application/json" } });
    const data = await res.json().catch(() => ({}));

    console.log("[SEARCH] response", data);
    return (data && data.ok && Array.isArray(data.results)) ? data.results : [];
  };

  input.addEventListener("input", () => {
    clearTimeout(t);
    const q = (input.value || "").trim();

    t = setTimeout(async () => {
      if (q.length < 2) return hide();
      try {
        const items = await fetchSuggest(q);
        render(items);
      } catch (e) {
        console.warn("[SEARCH] suggest error", e);
        hide();
      }
    }, 150);
  });

  input.addEventListener("keydown", (e) => {
    if (box.style.display !== "block") return;

    const max = current.length - 1;
    if (max < 0) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      activeIndex = Math.min(max, activeIndex + 1);
      setActive(activeIndex);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      activeIndex = Math.max(0, activeIndex - 1);
      setActive(activeIndex);
    } else if (e.key === "Enter") {
      if (activeIndex >= 0 && current[activeIndex]) {
        e.preventDefault();
        input.value = current[activeIndex].label;
        hide();
        form.submit();
      }
    } else if (e.key === "Escape") {
      e.preventDefault();
      hide();
    }
  });

  document.addEventListener("mousedown", (e) => {
    if (e.target === input) return;
    if (box.contains(e.target)) return;
    hide();
  });

  input.addEventListener("blur", () => setTimeout(hide, 120));
});

// =================== PROFILE / VALIDATION ===================
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('profile-form');
  if (!form) return;

  // inputs
  const nameInput   = form.querySelector('input[name="name"]');
  const emailInput  = form.querySelector('input[name="email"]');

  const countryInput = document.getElementById('country-input');
  const cityInput    = document.getElementById('city-input');
  const phoneInput   = document.getElementById('phone-input');
  const birthInput   = form.querySelector('input[name="birth_date"]');

  const countryIdInput = document.getElementById('country-id');
  const cityIdInput    = document.getElementById('city-id');
  const phoneCodeInput = document.getElementById('phone-code');

  const countrySuggestBox = document.getElementById('country-suggest');
  const citySuggestBox    = document.getElementById('city-suggest');

  const emailSpaceMessage = 'Email не должен содержать пробелы';
  const phoneErrorMessage = 'Введите корректный телефон (+ и 11–15 цифр)';
  const nameSpaceMessage = 'Имя не должно содержать пробелы';

  const hasSpaces = (v) => /\s/.test(v || '');
  const normalizeEq = (s) => (s || '').trim().toLowerCase();

  // --- space blockers (как в логине/регистре) ---
  const attachSpaceBlocker = (inputEl, message) => {
    if (!inputEl) return;
    inputEl.addEventListener('keydown', (e) => {
      if (e.key !== ' ') return;
      e.preventDefault();
      showFieldError(inputEl, message, { autoHide: true });
    });
  };
  attachSpaceBlocker(emailInput, emailSpaceMessage);

  // --- api ---
  async function fetchCountries(q) {
    const res = await fetch(`/api/countries/?q=${encodeURIComponent(q)}`, {
      headers: { Accept: 'application/json' },
    });
    const data = await res.json().catch(() => ({ results: [] }));
    return data.results || [];
  }

  async function fetchCities(q, countryId) {
    const url = `/api/cities/?q=${encodeURIComponent(q)}&country_id=${encodeURIComponent(countryId || '')}`;
    const res = await fetch(url, { headers: { Accept: 'application/json' } });
    const data = await res.json().catch(() => ({ results: [] }));
    return data.results || [];
  }

  async function resolveCountryByText() {
    if (!countryInput || !countryIdInput) return false;
    const text = normalizeEq(countryInput.value);
    if (!text) return false;
    if (countryIdInput.value) return true;

    const items = await fetchCountries(countryInput.value);
    const hit = items.find((it) => normalizeEq(it.name) === text);
    if (!hit) return false;

    countryInput.value = hit.name;
    countryIdInput.value = String(hit.id || '');

    // phone_code sync
    if (phoneCodeInput) {
      const prev = (phoneCodeInput.value || '').trim();
      phoneCodeInput.value = (hit.phone_code || '').trim();
      phoneCodeInput.dispatchEvent(new CustomEvent('change', { detail: { oldCode: prev } }));
    }
    return !!countryIdInput.value;
  }

  async function resolveCityByText() {
    if (!cityInput || !cityIdInput) return false;
    const text = normalizeEq(cityInput.value);
    if (!text) return false;
    if (cityIdInput.value) return true;

    const countryId = countryIdInput?.value || '';
    if (!countryId) return false;

    const items = await fetchCities(cityInput.value, countryId);
    const hit = items.find((it) => normalizeEq(it.name) === text);
    if (!hit) return false;

    cityInput.value = hit.name;
    cityIdInput.value = String(hit.id || '');
    return !!cityIdInput.value;
  }

  // --- suggest ui (используем твои функции если они есть выше; если нет — вот минималка)
  const hideBox = (box) => { if (!box) return; box.style.display = 'none'; box.innerHTML=''; };
  const renderSuggest = (box, items, onPick) => {
    if (!box) return;
    box.innerHTML = '';
    if (!items || !items.length) return hideBox(box);
    items.forEach((item) => {
      const div = document.createElement('div');
      div.className = 'suggest-item';
      div.textContent = item.name;
      div.addEventListener('mousedown', (e) => {
        e.preventDefault();
        onPick(item);
        hideBox(box);
      });
      box.appendChild(div);
    });
    box.style.display = 'block';
  };

  // --- phone mask ---
  if (phoneInput && phoneCodeInput) {
    syncPhoneMaskWithCode(phoneInput, phoneCodeInput);
  }

  // --- binding validators (country/city обязательные в профиле) ---
  const validateCountryBinding = async ({ show = true } = {}) => {
    if (!countryInput || !countryIdInput) return true;

    if (!countryIdInput.value && countryInput.value.trim()) {
      try { await resolveCountryByText(); } catch {}
    }

    const ok = !!countryIdInput.value && !!countryInput.value.trim();
    if (!ok && show) showFieldError(countryInput, 'Выберите страну из подсказки');
    if (ok) clearFieldError(countryInput);
    return ok;
  };

  const validateCityBinding = async ({ show = true } = {}) => {
    if (!cityInput || !cityIdInput) return true;

    if (!cityIdInput.value && cityInput.value.trim()) {
      try { await resolveCityByText(); } catch {}
    }

    const ok = !!cityIdInput.value && !!cityInput.value.trim();
    if (!ok && show) showFieldError(cityInput, 'Выберите город из подсказки');
    if (ok) clearFieldError(cityInput);
    return ok;
  };

  // --- live validators ---
  const validateEmailLocal = (email) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

  const validators = new Map([
    [nameInput, (_, ctx = {}) => {
      const value = (nameInput?.value || '').trim();
      if (!value) {
        if (ctx.fromSubmit) { showFieldError(nameInput, 'Введите имя', { autoHide: false }); return false; }
        if (hasSpaces(value)) { showFieldError(nameInput, nameSpaceMessage, { autoHide: !ctx.fromSubmit }); return false; }
        return true;
      }

      if (value.length < 2) { showFieldError(nameInput, 'Имя минимум 2 символа', { autoHide: !ctx.fromSubmit }); return false; }
      clearFieldError(nameInput);
      return true;
    }],

    [emailInput, (_, ctx = {}) => {
      const value = (emailInput?.value || '').trim().toLowerCase();
      emailInput.value = value;

      if (!value) {
        if (ctx.fromSubmit) { showFieldError(emailInput, 'Введите email', { autoHide: false }); return false; }
        return true;
      }
      if (hasSpaces(value)) { showFieldError(emailInput, emailSpaceMessage, { autoHide: !ctx.fromSubmit }); return false; }
      if (!validateEmailLocal(value)) { showFieldError(emailInput, 'Введите корректный email', { autoHide: !ctx.fromSubmit }); return false; }
      clearFieldError(emailInput);
      return true;
    }],

    [phoneInput, (_, ctx = {}) => {
      const raw = (phoneInput?.value || '').trim();
      if (!raw) { clearFieldError(phoneInput); return true; } // в профиле телефон можно сделать НЕобязательным

      const code = (phoneCodeInput?.value || '').trim();
      if (!validatePhoneByCountryCode(raw, code)) {
        showFieldError(
          phoneInput,
          code ? `Телефон должен начинаться с ${code} и быть корректным` : phoneErrorMessage,
          { autoHide: !ctx.fromSubmit }
        );
        return false;
      }
      clearFieldError(phoneInput);
      return true;
    }],

    [birthInput, (_, ctx = {}) => {
      const raw = (birthInput?.value || '').trim();
      if (!raw) { clearFieldError(birthInput); return true; } // необязательное

      if (!/^\d{4}-\d{2}-\d{2}$/.test(raw)) {
        showFieldError(birthInput, 'Введите дату через календарь', { autoHide: !ctx.fromSubmit });
        return false;
      }

      const d = new Date(raw + 'T00:00:00');
      if (Number.isNaN(d.getTime())) {
        showFieldError(birthInput, 'Некорректная дата', { autoHide: !ctx.fromSubmit });
        return false;
      }
      clearFieldError(birthInput);
      return true;
    }],
  ]);

  validators.forEach((validator, inputEl) => attachBlurOnlyValidation(inputEl, validator));

  // --- suggest handlers ---
  let tCountry = null;
  let tCity = null;

  if (countryInput && countrySuggestBox) {
    countryInput.addEventListener('input', () => {
      clearTimeout(tCountry);
      const q = (countryInput.value || '').trim();

      // сбрасываем привязки при ручном вводе
      if (countryIdInput) countryIdInput.value = '';
      if (cityInput) cityInput.value = '';
      if (cityIdInput) cityIdInput.value = '';
      hideBox(citySuggestBox);

      if (!q) return hideBox(countrySuggestBox);

      tCountry = setTimeout(async () => {
        const items = await fetchCountries(q);
        renderSuggest(countrySuggestBox, items, (item) => {
          countryInput.value = item.name;
          if (countryIdInput) countryIdInput.value = String(item.id || '');

          if (phoneCodeInput) {
            const prev = (phoneCodeInput.value || '').trim();
            phoneCodeInput.value = (item.phone_code || '').trim();
            phoneCodeInput.dispatchEvent(new CustomEvent('change', { detail: { oldCode: prev } }));
          }

          clearFieldError(countryInput);
        });
      }, 150);
    });

    countryInput.addEventListener('blur', async () => {
      setTimeout(() => hideBox(countrySuggestBox), 150);
      await validateCountryBinding({ show: true });
    });
  }

  if (cityInput && citySuggestBox) {
    cityInput.addEventListener('input', () => {
      clearTimeout(tCity);
      const q = (cityInput.value || '').trim();

      if (cityIdInput) cityIdInput.value = '';

      const countryId = countryIdInput?.value || '';
      if (!countryId || !q) {
        hideBox(citySuggestBox);
        return;
      }

      tCity = setTimeout(async () => {
        const items = await fetchCities(q, countryId);
        renderSuggest(citySuggestBox, items, (item) => {
          cityInput.value = item.name;
          if (cityIdInput) cityIdInput.value = String(item.id || '');
          clearFieldError(cityInput);
        });
      }, 150);
    });

    cityInput.addEventListener('blur', async () => {
      setTimeout(() => hideBox(citySuggestBox), 150);
      await validateCityBinding({ show: true });
    });
  }

  // --- submit ---
  async function validateAllOnSubmit(map) {
    let ok = true;
    for (const [inputEl, validator] of map.entries()) {
      if (!inputEl) continue;
      inputEl.dataset.touched = '1';
      const res = await validator(inputEl.value, { fromSubmit: true, fromBlur: false, fromInput: false });
      if (!res) ok = false;
    }
    return ok;
  }

  form.addEventListener('submit', async (e) => {
    // это обычный POST (не fetch), но ошибки показываем до отправки
    clearFieldErrors(form);

    let ok = true;

    const clientOk = await validateAllOnSubmit(validators);
    if (!clientOk) ok = false;

    if (!await validateCountryBinding({ show: true })) ok = false;
    if (!await validateCityBinding({ show: true })) ok = false;

    if (!ok) {
      e.preventDefault();
      scrollToFirstError(form);
    }
  });
});

document.addEventListener("DOMContentLoaded", () => {
  const input = document.getElementById("avatar-input");
  const delBtn = document.getElementById("avatar-delete-btn");
  const status = document.getElementById("avatar-status");
  const box = document.getElementById("avatar-box");
  const hint = document.getElementById("avatar-hint");

  if (!input || !box) return;

  const getCookie = (name) => {
    const m = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
    return m ? m.pop() : "";
  };

  const setStatus = (t) => { if (status) status.textContent = t || ""; };

  const setHasAvatarUI = (avatarUrl) => {
  const sidebarBox = document.getElementById("sidebar-avatar-box");
  const formBox = document.getElementById("avatar-box");

  const ensureImg = (parent, url) => {
    if (!parent) return;
    // удалить плейсхолдер только внутри parent
    parent.querySelectorAll(".js-avatar-placeholder").forEach((el) => el.remove());

    let img = parent.querySelector("img.js-avatar-img");
    if (!img) {
      img = document.createElement("img");
      img.className = "user-avatar-large js-avatar-img";
      img.alt = "Аватар";
      parent.appendChild(img);
    }
    img.src = url;
  };

  const ensurePlaceholder = (parent) => {
    if (!parent) return;
    // удалить img только внутри parent
    parent.querySelectorAll("img.js-avatar-img").forEach((el) => el.remove());

    if (!parent.querySelector(".js-avatar-placeholder")) {
      const ph = document.createElement("div");
      ph.className = "default-avatar-large js-avatar-placeholder";
      ph.textContent = "👤";
      parent.appendChild(ph);
    }
  };

  if (avatarUrl) {
    const bust = avatarUrl.includes("?") ? "&" : "?";
    const finalUrl = avatarUrl + bust + "t=" + Date.now();

    ensureImg(sidebarBox, finalUrl);
    ensureImg(formBox, finalUrl);

    // UI controls
    input.disabled = true;
    input.value = "";
    if (delBtn) delBtn.style.display = "inline-block";
    if (hint) hint.style.display = "block";
  } else {
    ensurePlaceholder(sidebarBox);
    ensurePlaceholder(formBox);

    input.disabled = false;
    input.value = "";
    if (delBtn) delBtn.style.display = "none";
    if (hint) hint.style.display = "none";
  }
};

  // upload
  input.addEventListener("change", async () => {
    if (input.disabled) return;
    const file = input.files && input.files[0];
    if (!file) return;

    setStatus("Загружаю...");

    const fd = new FormData();
    fd.append("avatar", file);

    try {
      const res = await fetch("/profile/avatar/", {
        method: "POST",
        headers: { "X-CSRFToken": getCookie("csrftoken") },
        body: fd,
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.ok) {
        setStatus(data.message || "Ошибка загрузки");
        input.value = "";
        return;
      }

      setHasAvatarUI(data.avatar_url);
      setStatus("Аватар обновлён");
      setTimeout(() => setStatus(""), 1500);
    } catch {
      setStatus("Ошибка сети");
      input.value = "";
    }
  });

  // delete
  if (delBtn) {
    delBtn.addEventListener("click", async () => {
      if (delBtn.style.display === "none") return;
      if (!confirm("Удалить аватар?")) return;

      setStatus("Удаляю...");

      try {
        const res = await fetch("/profile/avatar/delete/", {
          method: "POST",
          headers: {
            "X-CSRFToken": getCookie("csrftoken"),
            "Content-Type": "application/json",
            "Accept": "application/json",
          },
          body: "{}",
        });

        const data = await res.json().catch(() => ({}));
        if (!res.ok || !data.ok) {
          setStatus(data.message || "Ошибка удаления");
          return;
        }

        setHasAvatarUI(null);
        setStatus("Аватар удалён");
        setTimeout(() => setStatus(""), 1500);
      } catch {
        setStatus("Ошибка сети");
      }
    });
  }
});

document.addEventListener("DOMContentLoaded", () => {
  const scroll = document.getElementById("screwScroll");
  const stage  = document.getElementById("screwStage");
  const spacer = document.getElementById("screwSpacer");

  if (!scroll || !stage || !spacer) return;

  const items = Array.from(stage.querySelectorAll(".screw-item"));
  const N = items.length;
  if (!N) return;

  // ====== НАСТРОЙКИ ======
  const CFG = {
    radius: 395,        // радиус трубы (влево/вправо)
    depth: 228,         // глубина (в экран)
    pitch: 910,         // шаг по вертикали на 1 оборот
    stepAngle: 0.64,    // расстояние между карточками по витку (больше = дальше)
    minScale: 0.48,
    maxScale: 0.97,
    minOpacity: 0.22,
    maxOpacity: 1.0,

    // “бесконечный скролл”
    loopFactor: 60,     // чем больше — тем дальше “края” (обычно 40..120)
    phaseDiv: 808,      // скорость вращения от scrollLeft (меньше => быстрее)

    // авто-движение
    autoSpeed: 0.55,    // px per frame (0.3..1.2)
  };

  // один период винта — полный оборот, который содержит N карточек
  const PERIOD = Math.PI * 2;                // 2π
  const LOOP = N * CFG.stepAngle;            // длина по углу для полного круга карточек

  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

  // делаем огромную ширину (чтобы было где “крутить”)
  const setSpacer = () => {
    const w = scroll.clientWidth;
    const L = Math.max(4000, w * CFG.loopFactor);
    spacer.style.width = L + "px";
  };

  // держим scrollLeft “в середине”, чтобы не упираться в края
  const recenterIfNeeded = () => {
    const max = scroll.scrollWidth - scroll.clientWidth;
    if (max <= 0) return;

    const mid = max / 2;
    const dist = Math.abs(scroll.scrollLeft - mid);

    // если ушли слишком далеко от центра — телепортируем обратно,
    // сохраняя фазу (визуально незаметно)
    if (dist > max * 0.35) {
      const phase = scroll.scrollLeft % LOOP;
      scroll.scrollLeft = mid + phase;
    }
  };

  const render = () => {
    const w = scroll.clientWidth;
    const h = scroll.clientHeight;

    const cx = w * 0.52; // смещение винта
    const cy = h * 0.55;

    // фаза зависит от scrollLeft, но "замкнутая"
    const rawPhase = scroll.scrollLeft / CFG.phaseDiv;

    items.forEach((el, i) => {
      // замыкаем: theta всегда “ходит по кругу”
      // i задаёт место карточки на винте, phase — прокрутку
      const theta = (rawPhase + i * CFG.stepAngle);

      // замкнутый угол для позиции вокруг трубы (круговой)
      const ang = theta % PERIOD;

      // по кругу вокруг вертикальной оси
      const x = cx + Math.cos(ang) * CFG.radius;
      const z = Math.sin(ang) * CFG.depth;

      // “спуск сверху вниз” по винту — тоже можно замкнуть, чтобы было кольцо:
      // если хочешь замкнутую трубу без ухода вниз — используй sin вместо линейного y:
      // const y = cy + Math.sin(theta) * (CFG.pitch * 0.7);
      //
      // а если хочешь прям “винт” (едет вниз) — оставляем линейно,
      // но тоже замкнём по LOOP, чтобы не улетал:
      const tLoop = ((theta % LOOP) + LOOP) % LOOP; // 0..LOOP
      const y = cy + (tLoop / PERIOD) * (CFG.pitch); // 0..pitch*(LOOP/2π)

      // близость/масштаб
      const k = (z + CFG.depth) / (2 * CFG.depth); // 0..1
      const scale = CFG.minScale + (CFG.maxScale - CFG.minScale) * k;
      const opacity = CFG.minOpacity + (CFG.maxOpacity - CFG.minOpacity) * k;

      el.style.opacity = opacity.toFixed(3);
      el.style.zIndex = String(Math.round(1000 * k));

      el.style.transform =
        `translate3d(${x - cx+50}px, ${y - cy-150}px, ${z}px) translate(-50%, -50%) scale(${scale})`;
    });
  };

  // ===== авто-движение с паузой =====
  let autoOn = true;
  let raf = 0;

  const tick = () => {
    if (autoOn) {
      scroll.scrollLeft += CFG.autoSpeed;
      recenterIfNeeded();
      render();
    }
    raf = requestAnimationFrame(tick);
  };

  const pauseAuto = () => { autoOn = false; };
  const resumeAuto = () => { autoOn = true; };

  // пауза при взаимодействии
  ["pointerdown", "wheel", "touchstart", "mousedown"].forEach((evt) =>
    scroll.addEventListener(evt, pauseAuto, { passive: true })
  );

  // продолжать после отпускания/ухода мыши
  ["pointerup", "touchend", "mouseup", "mouseleave"].forEach((evt) =>
    scroll.addEventListener(evt, () => setTimeout(resumeAuto, 700), { passive: true })
  );

  // при ручном скролле — рендер и центрирование
  scroll.addEventListener("scroll", () => {
    recenterIfNeeded();
    render();
  });

  window.addEventListener("resize", () => {
    setSpacer();
    recenterIfNeeded();
    render();
  });

  // init
  setSpacer();

  // стартуем из середины сразу
  requestAnimationFrame(() => {
    const max = scroll.scrollWidth - scroll.clientWidth;
    scroll.scrollLeft = max > 0 ? max / 2 : 0;
    render();
    recenterIfNeeded();
    raf = requestAnimationFrame(tick);
  });
});

