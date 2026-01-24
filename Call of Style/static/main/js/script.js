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
function clearFieldErrors(form) {
  if (!form) return;
  form.querySelectorAll('.field-error-tooltip').forEach((el) => el.remove());
  form.querySelectorAll('.field-error').forEach((el) => el.remove());
  form.querySelectorAll('.error').forEach((el) => el.classList.remove('error'));
}

function showFieldError(inputEl, message) {
  if (!inputEl) return;

  inputEl.classList.add('error');

  // обертка для tooltip
  let wrap = inputEl.closest('.input-with-error');
  if (!wrap) {
    wrap = document.createElement('div');
    wrap.className = 'input-with-error';
    inputEl.parentNode.insertBefore(wrap, inputEl);
    wrap.appendChild(inputEl);
  }

  const tooltip = document.createElement('div');
  tooltip.className = 'field-error-tooltip';
  tooltip.innerHTML = `<div class="field-error-tooltip-content">${message}</div>`;
  wrap.appendChild(tooltip);
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
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!emailRegex.test(email)) return false;

  const allowedDomains = [
    'gmail.com','outlook.com','hotmail.com','yahoo.com',
    'icloud.com','me.com','mac.com','proton.me','protonmail.com',
    'aol.com','yandex.ru','ya.ru','mail.ru','list.ru',
    'bk.ru','inbox.ru','rambler.ru'
  ];

  const domain = (email.split('@')[1] || '').toLowerCase();
  return allowedDomains.includes(domain);
};

const validatePassword = (password) => password && password.length >= 6;

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
  return !!p && /^\+\d{10,15}$/.test(p);
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
  return /^\+\d{10,15}$/.test(p);
};

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

// =================== COUNTRY SUGGEST ===================
let selectedCountryId = null;
let selectedCountryPhoneCode = '';
const countryInput = document.getElementById('country-input');
const countryIdInput = document.getElementById('country-id');
const phoneCodeInput = document.getElementById('phone-code');
const countrySuggestBox = document.getElementById('country-suggest');

const cityInput = document.getElementById('city-input');
const cityIdInput = document.getElementById('city-id');
const citySuggestBox = document.getElementById('city-suggest');

const phoneInput = document.getElementById('phone-input');

let tCountry = null;

async function fetchCountries(q) {
  const res = await fetch(`/api/countries/?q=${encodeURIComponent(q)}`);
  const data = await res.json().catch(() => ({ results: [] }));
  return data.results || [];
}

function resetCountryBinding() {
  if (countryIdInput) countryIdInput.value = '';
  if (phoneCodeInput) phoneCodeInput.value = '';

  // сбрасываем город (потому что без страны город невалиден)
  if (cityInput) cityInput.value = '';
  if (cityIdInput) cityIdInput.value = '';
  hideBox(citySuggestBox);
}

if (countryInput && countrySuggestBox) {
  countryInput.addEventListener('input', () => {
    clearTimeout(tCountry);
    const q = (countryInput.value || '').trim();

    resetCountryBinding();

    if (q.length < 1) return hideBox(countrySuggestBox);

    tCountry = setTimeout(async () => {
      try {
        const items = await fetchCountries(q);

        renderSuggest(countrySuggestBox, items, (item) => {
          countryInput.value = item.name;

          // фиксируем id + phone_code
          if (countryIdInput) countryIdInput.value = String(item.id || '');
          if (phoneCodeInput) phoneCodeInput.value = (item.phone_code || '').trim();

          // улучшаем UX телефона
          const pc = (item.phone_code || '').trim();
          if (phoneInput) {
            phoneInput.placeholder = pc ? `${pc}...` : '+...';

            const current = (phoneInput.value || '').trim();
            // если пусто — подставим код
            if (!current && pc) phoneInput.value = pc;
          }
        });

      } catch {
        hideBox(countrySuggestBox);
      }
    }, 150);
  });

  countryInput.addEventListener('blur', () => setTimeout(() => hideBox(countrySuggestBox), 150));
}

// =================== CITY SUGGEST (фильтр по стране) ===================
let tCity = null;

async function fetchCities(q, countryId) {
  const url = `/api/cities/?q=${encodeURIComponent(q)}&country_id=${encodeURIComponent(countryId || '')}`;
  const res = await fetch(url);
  const data = await res.json().catch(() => ({ results: [] }));
  return data.results || [];
}

if (cityInput && citySuggestBox) {
  cityInput.addEventListener('input', () => {
    clearTimeout(tCity);
    const q = (cityInput.value || '').trim();

    if (cityIdInput) cityIdInput.value = '';

    const countryId = countryIdInput ? countryIdInput.value : '';

    // если страна не выбрана — не даём город
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
        });

      } catch {
        hideBox(citySuggestBox);
      }
    }, 150);
  });

  cityInput.addEventListener('blur', () => setTimeout(() => hideBox(citySuggestBox), 150));
}

// ================= Регистрация submit =====================
const regForm = document.getElementById('register-form');

if (regForm) {
  regForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    clearFieldErrors(regForm);

    const email = regForm.querySelector('[name="email"]')?.value || '';
    const password = regForm.querySelector('[name="password"]')?.value || '';
    const name = regForm.querySelector('[name="name"]')?.value || '';
    const phone = regForm.querySelector('[name="phone"]')?.value || '';
    const phoneNormalized = normalizePhoneAny(phone);
    const birth_date = regForm.querySelector('[name="birth_date"]')?.value || '';
    const gender = regForm.querySelector('input[name="gender"]:checked')?.value || '';
    const country_id = document.getElementById('country-id')?.value || '';
    const city_id = document.getElementById('city-id')?.value || '';
    const phone_code = document.getElementById('phone-code')?.value || '';

    let ok = true;

    if (!validateEmail(email)) {
      showFieldError(regForm.querySelector('[name="email"]'), 'Введите email (только разрешённые домены)');
      ok = false;
    }
    if (!validatePassword(password)) {
      showFieldError(regForm.querySelector('[name="password"]'), 'Пароль минимум 6 символов');
      ok = false;
    }
    if (!validateName(name)) {
      showFieldError(regForm.querySelector('[name="name"]'), 'Имя: только буквы, пробел, дефис (от 2 символов)');
      ok = false;
    }

    // страна/город — ТОЛЬКО из подсказки
    if (!country_id) {
      showFieldError(document.getElementById('country-input'), 'Выберите страну из подсказки');
      ok = false;
    }
    if (!city_id) {
      showFieldError(document.getElementById('city-input'), 'Выберите город из подсказки');
      ok = false;
    }

    // телефон — под выбранный код страны (если есть)
    if (!validatePhoneByCountryCode(phone, phone_code)) {
      showFieldError(regForm.querySelector('[name="phone"]'), phone_code
        ? `Телефон должен начинаться с ${phone_code} и быть корректным`
        : 'Введите корректный телефон (+ и 10–15 цифр)'
      );
      ok = false;
    }
    if (!validateBirthDate(birth_date)) {
      showFieldError(regForm.querySelector('[name="birth_date"]'), 'Возраст должен быть 14+ и дата корректная');
      ok = false;
    }
    if (!gender || !['male','female'].includes(gender)) {
      showFieldError(document.getElementById('gender-input'), 'Выберите пол');
      ok = false;
    }

    if (!ok) return;

    const payload = {
      email,
      password,
      name,
      phone: normalizePhoneAny(phone),     // важное: нормализуем
      country_id,
      city_id,
      birth_date,
      gender,
    };

    try {
      const res = await fetch('/api/register/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        const errs = data.errors || {};
        if (Object.keys(errs).length) {
          Object.keys(errs).forEach((field) => {
            // country/city у нас input не по name=country_id, поэтому обрабатываем вручную
            if (field === 'country') return showFieldError(document.getElementById('country-input'), errs[field]);
            if (field === 'city') return showFieldError(document.getElementById('city-input'), errs[field]);

            const input = regForm.querySelector(`[name="${field}"]`);
            showFieldError(input, errs[field]);
          });
        } else {
          showFieldError(regForm.querySelector('[name="email"]'), data.message || 'Ошибка регистрации');
        }
        return;
      }

      window.location.href = '/index/';
    } catch (err) {
      showFieldError(regForm.querySelector('[name="email"]'), 'Ошибка сети. Попробуйте ещё раз.');
    }
  });
}

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

