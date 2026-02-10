// Инициализация

// Проверяем наличие Telegram WebApp, если нет - создаем заглушку
if (!window.Telegram?.WebApp) {
    // Создаем заглушку для тестирования вне Telegram
    window.Telegram = {
        WebApp: {
            expand: () => {},
            setHeaderColor: () => {},
            setBackgroundColor: () => {},
            HapticFeedback: {
                impactOccurred: () => {},
                notificationOccurred: () => {}
            },
            openLink: (url) => window.open(url, '_blank'),
            initData: '',
            initDataUnsafe: { user: { first_name: 'Тест', photo_url: null } }
        }
    };
}

// Объявляем tg один раз после проверки/создания
const tg = window.Telegram?.WebApp || {};
let storagePublicUrlBase = '';


const HTML_ESCAPE_MAP = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
};

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, (char) => HTML_ESCAPE_MAP[char]);
}

function escapeAttr(value) {
    return escapeHtml(value);
}

function safeUrl(value, allowRelative = true) {
    const raw = String(value ?? '').trim();
    if (!raw) return '';
    try {
        const parsed = new URL(raw, window.location.origin);
        const protocol = parsed.protocol.toLowerCase();
        if (storagePublicUrlBase && parsed.pathname.startsWith('/storage/v1/object/public/')) {
            const base = storagePublicUrlBase.replace(/\/$/, '');
            return `${base}${parsed.pathname}`;
        }
        if (protocol === 'http:' || protocol === 'https:') {
            return parsed.href;
        }
    } catch (error) {
        // ignore invalid URL
    }
    if (storagePublicUrlBase && raw.startsWith('/storage/v1/object/public/')) {
        const base = storagePublicUrlBase.replace(/\/$/, '');
        return `${base}${raw}`;
    }
    if (allowRelative && (raw.startsWith('/') || raw.startsWith('./') || raw.startsWith('../'))) {
        return raw;
    }
    return '';
}

function encodeId(value) {
    try {
        return encodeURIComponent(String(value ?? ''));
    } catch (error) {
        return '';
    }
}

function decodeId(value) {
    try {
        return decodeURIComponent(String(value ?? ''));
    } catch (error) {
        return String(value ?? '');
    }
}

function safeNumber(value, fallback = 0) {
    const num = Number(value);
    return Number.isFinite(num) ? num : fallback;
}

const PERCENT_SETTING_KEYS = new Set([
    'loyalty_percentage',
    'loyalty_max_spend_percentage'
]);

function normalizePercentValue(value) {
    const num = safeNumber(value, 0);
    return num <= 1 ? num * 100 : num;
}

/** Возвращает понятное пользователю сообщение об ошибке (без технических деталей). */
function friendlyErrorMessage(err, fallback) {
    const msg = (err && err.message) ? String(err.message) : '';
    const fallbackText = fallback || 'Что-то пошло не так. Попробуйте позже.';
    if (!msg) return fallbackText;
    if (/^API Error 401/i.test(msg)) return 'Нужно войти снова. Откройте приложение из Telegram.';
    if (/^API Error 403/i.test(msg)) return 'Недостаточно прав.';
    if (/^API Error 404/i.test(msg)) return 'Не найдено.';
    if (/^API Error 5\d\d/i.test(msg)) return 'Временная ошибка. Попробуйте позже.';
    if (/Reorder error|Save error|Delete error|Upload failed/i.test(msg)) return fallbackText;
    if (msg.length > 80 || msg.includes('detail') || msg.includes('Database')) return fallbackText;
    return msg;
}

// Инициализируем Telegram WebApp
if (tg && tg.expand) {
    tg.expand();
    
}

// Элементы
const loader = document.getElementById('loader');
const mainContent = document.getElementById('main-content');
const screens = {
    home: document.getElementById('home-section'),
    services: document.getElementById('services-section'),
    masters: document.getElementById('masters-section'),
    profile: document.getElementById('profile-section'),
    admin: document.getElementById('admin-section')
};
const navItems = document.querySelectorAll('.nav-item');

// Навигация
navItems.forEach(item => {
    item.addEventListener('click', () => {
        const sectionId = item.getAttribute('data-section');
        switchSection(sectionId);
    });
});

function switchSection(sectionId) {
    if (sectionId === 'admin') {
        const nav = document.querySelector('nav');
        if (nav) nav.classList.add('hidden');
        loadAdminData();
    } else {
        const nav = document.querySelector('nav');
        if (nav) nav.classList.remove('hidden');
    }

    // Nav styles
    navItems.forEach(item => {
        const isTarget = item.getAttribute('data-section') === sectionId;
        const icon = item.querySelector('svg');
        
        if (isTarget) {
            item.classList.add('active', 'text-brand-primary');
            item.classList.remove('text-stone-400');
            // Animate Icon
            icon.classList.add('-translate-y-1');
            icon.style.stroke = "#E8A8B4"; // Brand primary color
        } else {
            item.classList.remove('active', 'text-brand-primary');
            item.classList.add('text-stone-400');
            icon.classList.remove('-translate-y-1');
            icon.style.stroke = "currentColor";
        }
    });

    // Screen switching
    Object.keys(screens).forEach(key => {
        const screen = screens[key];
        if (key === sectionId) {
            screen.classList.remove('hidden');
            screen.classList.add('block', 'animate-fade-in');
        } else {
            screen.classList.add('hidden');
            screen.classList.remove('block', 'animate-fade-in');
        }
    });

    tg.HapticFeedback.impactOccurred('light');
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Данные
let bookingUrl = "https://yclients.com";

// Функция для загрузки аватара пользователя из Telegram
function loadUserAvatar() {
    try {
        const avatarBtn = document.getElementById('avatar-btn');
        const avatarIcon = document.getElementById('avatar-icon');
        const avatarImg = document.getElementById('avatar-img');
        
        if (!avatarBtn || !avatarIcon || !avatarImg) return;
        
        // Пытаемся получить данные пользователя из Telegram
        const user = tg.initDataUnsafe?.user;
        
        if (user?.photo_url) {
            // Если есть фото - показываем его
            avatarImg.src = user.photo_url;
            avatarImg.classList.remove('hidden');
            avatarIcon.classList.add('hidden');
            avatarBtn.classList.remove('bg-stone-100');
        } else {
            // Если фото нет - убираем аватарку совсем (скрываем кнопку)
            avatarBtn.style.display = 'none';
        }
    } catch (error) {
        // В случае ошибки просто скрываем аватарку
        const avatarBtn = document.getElementById('avatar-btn');
        if (avatarBtn) avatarBtn.style.display = 'none';
    }
}

// Функция для поддержки горизонтального скролла колесом мыши
function setupHorizontalScroll() {
    const promotionsList = document.getElementById('promotions-list');
    const mastersList = document.getElementById('masters-list');
    
    [promotionsList, mastersList].forEach(list => {
        if (!list) return;
        
        list.addEventListener('wheel', (e) => {
            // Если зажат Shift, всегда прокручиваем горизонтально
            if (e.shiftKey) {
                e.preventDefault();
                list.scrollBy({
                    left: e.deltaY,
                    behavior: 'auto'
                });
                return;
            }
            
            // Если мышь над элементом и есть горизонтальный скролл, преобразуем вертикальный в горизонтальный
            const hasHorizontalScroll = list.scrollWidth > list.clientWidth;
            if (hasHorizontalScroll && Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
                // Проверяем, находимся ли мы в начале или конце горизонтального скролла
                const isAtStart = list.scrollLeft <= 0;
                const isAtEnd = list.scrollLeft >= list.scrollWidth - list.clientWidth - 1;
                
                // Если не на границе, преобразуем вертикальный скролл в горизонтальный
                if (!isAtStart && !isAtEnd) {
                    e.preventDefault();
                    list.scrollBy({
                        left: e.deltaY,
                        behavior: 'auto'
                    });
                }
            }
        }, { passive: false });
    });
}

// Функция для скрытия лоадера (гарантированно вызывается)
function hideLoader() {
    if (loader) {
        loader.classList.add('opacity-0');
        setTimeout(() => {
            loader.style.display = 'none';
            loader.style.visibility = 'hidden';
            
        }, 500);
    }
    if (mainContent) {
        mainContent.classList.remove('opacity-0');
        mainContent.style.display = 'block';
        
    } else {
        
    }
}

window.onload = async () => {
    // Засекаем время начала загрузки для гарантированного минимума
    const loadStartTime = Date.now();
    const MIN_LOADER_TIME = 2000; // Минимум 2 секунды для анимации
    
    try {
        // Устанавливаем цвета хедера TG
        if (tg) {
            tg.setHeaderColor('#FFF8F9');
            tg.setBackgroundColor('#FFF8F9');
            
        }
        
        // Загружаем аватар пользователя из Telegram
        loadUserAvatar();
        
        // Добавляем поддержку горизонтального скролла колесом мыши
        setupHorizontalScroll();
        
        // Инициализируем свайп для закрытия модалок
        initModalSwipe();

        // Инициализируем панель кнопок бота
        initBotButtonsPanel();
        
        // Загружаем контент и профиль НЕЗАВИСИМО
        // Если один упадет, другой все равно загрузится
        const loadPromises = [];
        
        // Загружаем контент (не требует авторизации)
        loadPromises.push(
            loadContent().catch(error => {
                // Показываем пустые списки
                renderPromotions([]);
                renderServices([]);
                renderMasters([]);
            })
        );
        
        // Загружаем профиль (требует авторизации, может упасть)
        loadPromises.push(
            loadProfile().catch(error => {
                // Устанавливаем дефолтные значения
                const nameEl = document.getElementById('user-name');
                const balanceEl = document.getElementById('user-balance');
                const phoneEl = document.getElementById('profile-phone');
                const levelEl = document.getElementById('profile-level');
                
                if (nameEl) {
                    const userName = tg.initDataUnsafe?.user?.first_name || 'Красотка';
                    nameEl.innerText = `Привет, ${userName}!`;
                }
                if (balanceEl) balanceEl.innerText = '0';
                if (phoneEl) phoneEl.innerText = '-';
                if (levelEl) levelEl.innerText = 'NEW';
                
                renderHistory([]);
            })
        );
        
        // Ждем завершения всех загрузок (даже с ошибками)
        await Promise.allSettled(loadPromises);
        
    } catch (error) {
        // Все равно показываем интерфейс
    } finally {
        // Гарантируем минимум 2 секунды отображения лоадера для анимации
        const elapsedTime = Date.now() - loadStartTime;
        const remainingTime = Math.max(0, MIN_LOADER_TIME - elapsedTime);
        
        setTimeout(() => {
            hideLoader();
        }, remainingTime);
    }
};

async function apiFetch(endpoint) {
    const baseUrl = window.location.origin;
    const url = new URL(`${baseUrl}${endpoint}`);
    // Добавляем timestamp для предотвращения кеширования
    url.searchParams.append('_t', Date.now());
    
    try {
        const response = await fetch(url.toString(), {
            headers: { 'X-Tg-Init-Data': tg?.initData || '' }
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            let detail = '';
            try {
                const parsed = JSON.parse(errorText);
                detail = (parsed && parsed.detail) ? String(parsed.detail) : errorText.slice(0, 100);
            } catch (_) {
                detail = errorText.slice(0, 100);
            }
            const friendly = response.status === 401 ? 'Нужно войти снова.' :
                response.status === 403 ? 'Недостаточно прав.' :
                response.status >= 500 ? 'Временная ошибка. Попробуйте позже.' : detail;
            throw new Error(friendly);
        }
        
        const data = await response.json();
        return data;
    } catch (error) {
        throw error;
    }
}

// ---- Render Functions ----

async function loadContent() {
    const data = await apiFetch('/api/app/content');
    if (data.booking_url) {
        const safeBookingUrl = safeUrl(data.booking_url);
        if (safeBookingUrl) bookingUrl = safeBookingUrl;
    }
    if (data.storage_public_url_base) {
        storagePublicUrlBase = String(data.storage_public_url_base || '');
    }

    const maxSpendEl = document.getElementById('loyalty-max-spend');
    const expirationEl = document.getElementById('loyalty-expiration-days');
    if (maxSpendEl) {
        const value = normalizePercentValue(data.loyalty_max_spend_percentage ?? 0.3);
        maxSpendEl.textContent = String(Math.round(value));
    }
    if (expirationEl) {
        const value = Number(data.loyalty_expiration_days ?? 90);
        expirationEl.textContent = String(Math.max(0, Math.round(value)));
    }
    
    renderPromotions(data.promotions || []);
    renderServices(data.services || []);
    renderMasters(data.masters || []);
}

async function loadProfile() {
    // Проверяем, есть ли initData
    if (!tg.initData) {
        throw new Error("No Telegram initData");
    }
    
    const data = await apiFetch('/api/app/profile');
    const user = data.user;
    const isAdmin = data.is_admin;
    
    document.getElementById('user-name').innerText = `Привет, ${user.name || 'Красотка'}!`;
    document.getElementById('user-balance').innerText = user.balance || 0;
    document.getElementById('profile-phone').innerText = user.phone || '-';
    const levelEl = document.getElementById('profile-level');
    if (levelEl) {
        const levelText = user.level ? String(user.level).toUpperCase() : 'NEW';
        levelEl.innerText = levelText;
    }
    
    // Показываем кнопку админки, если пользователь админ
    const adminEntry = document.getElementById('admin-entry');
    if (isAdmin && adminEntry) {
        adminEntry.classList.remove('hidden');
    }

    // Стилизация бейджа статуса
    if (levelEl && user.level === 'vip') {
        levelEl.className = "inline-flex px-3 py-1 rounded-full bg-gradient-to-r from-yellow-100 to-yellow-200 text-yellow-800 text-xs font-bold uppercase tracking-wide border border-yellow-300";
    }

    const mergedHistory = mergeHistoryItems(data.history || [], data.visits || [], 10);
    renderHistory(mergedHistory);
}

function renderPromotions(promos) {
    const list = document.getElementById('promotions-list');
    if (!list) return;
    
    if (!promos || !promos.length) {
        list.innerHTML = `
            <div class="min-w-full h-[200px] rounded-[28px] bg-white border border-stone-100 flex items-center justify-center text-stone-400 text-sm shadow-card">
                Скоро здесь появятся акции
            </div>`;
        return;
    }
    
    list.innerHTML = promos.map(p => {
        const imageUrl = safeUrl(p.image_url);
        const title = escapeHtml(p.title);
        const description = escapeHtml(p.description);
        const promotionId = safeNumber(p.id, 0);
        return `
        <div class="min-w-[300px] h-[200px] relative rounded-[28px] overflow-hidden shadow-card active:scale-[0.98] transition-transform snap-center group border border-white/40">
            ${imageUrl ? `
                <img src="${escapeAttr(imageUrl)}" class="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105" loading="lazy" alt="${title}">
                <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent"></div>
            ` : `
                <div class="absolute inset-0 bg-gradient-to-br from-[#E8A8B4] via-[#F5CED6] to-[#FCE4EC]"></div>
                <div class="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -mr-16 -mt-16 blur-2xl"></div>
                <div class="absolute bottom-0 left-0 w-24 h-24 bg-white/10 rounded-full -ml-12 -mb-12 blur-xl"></div>
            `}
            <div class="relative h-full flex flex-col justify-between p-6 z-10">
                <div>
                    <h3 class="text-white font-serif text-2xl font-bold leading-tight mb-2 drop-shadow-md">${title}</h3>
                    ${description ? `<p class="text-white/90 text-sm leading-relaxed line-clamp-2 drop-shadow-sm font-medium">${description}</p>` : ''}
                </div>
                <button onclick="openPromotionDetail(${promotionId})" class="bg-white/20 backdrop-blur-md hover:bg-white/30 text-white px-5 py-2.5 rounded-full text-xs font-bold w-fit transition-all flex items-center gap-2 shadow-sm border border-white/30">
                    <span>Узнать больше</span>
                </button>
            </div>
        </div>
        `;
    }).join('');
}

function renderServices(services) {
    const list = document.getElementById('services-list');
    if (!list) return;
    
    if (!services || !services.length) {
        list.innerHTML = '<div class="col-span-2 text-center py-10 text-stone-400 text-sm">Услуги скоро появятся</div>';
        return;
    }
    
    list.innerHTML = services.map(s => {
        const imageUrl = safeUrl(s.image_url);
        const title = escapeHtml(s.title);
        const description = escapeHtml(s.description);
        const price = safeNumber(s.price, 0);
        return `
        <div onclick="openBooking()" class="bg-white rounded-[28px] shadow-card border border-white/50 active:scale-[0.98] transition-transform min-h-[280px] flex flex-col group relative overflow-hidden">
            <!-- Изображение услуги -->
            ${imageUrl ? `
                <div class="h-[140px] w-full bg-stone-100 relative overflow-hidden flex-shrink-0">
                    <img src="${escapeAttr(imageUrl)}" class="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110" loading="lazy" alt="${title}">
                    <div class="absolute inset-0 bg-gradient-to-t from-white/10 to-transparent"></div>
                </div>
            ` : `
                <div class="h-[100px] w-full bg-gradient-to-br from-brand-light/20 to-brand-bg flex items-center justify-center text-3xl flex-shrink-0">
                    ✨
                </div>
            `}
            
            <div class="p-5 flex flex-col flex-1 relative z-10 min-h-0">
                <div class="absolute inset-0 bg-gradient-to-br from-white via-white to-stone-50 opacity-0 group-hover:opacity-100 transition-opacity duration-500 -z-10"></div>
                
                <div class="mb-3 flex-shrink-0">
                    <h3 class="font-serif text-lg font-bold leading-tight text-stone-800 group-hover:text-brand-dark transition-colors line-clamp-2">${title}</h3>
                    ${description ? `<p class="text-xs text-stone-500 leading-relaxed mt-1.5 line-clamp-3">${description}</p>` : ''}
                </div>

                <div class="pt-3 border-t border-stone-100 flex items-center justify-between mt-auto flex-shrink-0">
                    <span class="text-brand-dark font-bold text-lg font-serif">${price} ₽</span>
                    <div class="w-8 h-8 rounded-full bg-brand-bg flex items-center justify-center text-brand-dark group-hover:scale-110 group-hover:bg-brand-primary group-hover:text-white transition-all shadow-sm">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-4 h-4">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                        </svg>
                    </div>
                </div>
            </div>
        </div>
        `;
    }).join('');
}

function renderMasters(masters) {
    const list = document.getElementById('masters-list');
    if (!list) return;
    
    if (!masters || !masters.length) {
        list.innerHTML = '<div class="min-w-full text-center py-10 text-stone-400 text-sm">Список мастеров пуст</div>';
        return;
    }
    
    list.innerHTML = masters.map((m, index) => {
        const photoUrl = safeUrl(m.photo_url);
        const name = escapeHtml(m.name);
        const specialization = escapeHtml(m.specialization || 'Специалист');
        return `
        <div onclick="openBooking()" class="min-w-[260px] h-[380px] relative rounded-[32px] overflow-visible shadow-card active:scale-[0.98] transition-all duration-300 snap-center group cursor-pointer">
            <!-- Фото мастера с ореолом -->
            <div class="absolute inset-0 bg-stone-200 rounded-[32px] overflow-hidden" style="box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.8), 0 15px 35px -10px rgba(232, 168, 180, 0.5), 0 10px 20px -5px rgba(0, 0, 0, 0.1);">
                ${photoUrl ? `
                    <img src="${escapeAttr(photoUrl)}" class="w-full h-full object-cover transition-transform duration-1000 group-hover:scale-110" loading="lazy" alt="${name}">
                    <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent opacity-90 group-hover:opacity-80 transition-opacity duration-500"></div>
                ` : `
                    <div class="w-full h-full flex items-center justify-center text-5xl bg-gradient-to-br from-brand-light/30 via-brand-bg to-brand-primary/20">
                        <div class="text-6xl opacity-50">👩‍⚕️</div>
                    </div>
                    <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-black/40 to-transparent opacity-90"></div>
                `}
            </div>
            
            <!-- Инфо мастера -->
            <div class="absolute bottom-0 left-0 right-0 p-8 text-white z-20">
                <h4 class="font-serif text-2xl font-bold mb-1 leading-tight drop-shadow-lg">${name}</h4>
                <p class="text-sm opacity-90 font-medium tracking-wide drop-shadow-md mb-4">${specialization}</p>
                
                <!-- Кнопка записи -->
                <button onclick="openBooking()" class="mt-4 w-full bg-white/20 backdrop-blur-md hover:bg-white/30 text-white px-4 py-2.5 rounded-full text-xs font-bold transition-all flex items-center justify-center gap-2 shadow-lg border border-white/30 active:scale-95">
                    <span>Записаться</span>
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-4 h-4">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                    </svg>
                </button>
            </div>
        </div>
        `;
    }).join('');
}

function getHistoryItemDate(item) {
    if (!item || typeof item !== 'object') return null;
    const rawDate = item.item_type === 'visit'
        ? (item.visit_datetime || item.datetime || item.created_at)
        : item.created_at;
    if (!rawDate) return null;
    const parsed = new Date(rawDate);
    return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function getHistoryItemTimestamp(item) {
    const date = getHistoryItemDate(item);
    return date ? date.getTime() : 0;
}

function mergeHistoryItems(history, visits, limit = 10) {
    const merged = [];
    if (Array.isArray(history)) {
        history.forEach((entry) => {
            if (!entry || typeof entry !== 'object') return;
            merged.push({ ...entry, item_type: entry.item_type || 'transaction' });
        });
    }
    if (Array.isArray(visits)) {
        visits.forEach((visit) => {
            if (!visit || typeof visit !== 'object') return;
            merged.push({ ...visit, item_type: 'visit' });
        });
    }
    merged.sort((a, b) => getHistoryItemTimestamp(b) - getHistoryItemTimestamp(a));
    return merged.slice(0, limit);
}

function formatVisitAmount(value) {
    const amount = Number(value);
    if (!Number.isFinite(amount) || amount <= 0) return '—';
    return `${Math.round(amount).toLocaleString('ru-RU')} ₽`;
}

function getVisitStatusClass(status) {
    const normalized = String(status || '').toLowerCase();
    if (normalized.includes('отмен') || normalized.includes('не приш')) {
        return 'text-rose-500';
    }
    if (normalized.includes('ожида')) {
        return 'text-orange-500';
    }
    if (normalized.includes('подтверж') || normalized.includes('состоял')) {
        return 'text-green-600';
    }
    return 'text-stone-400';
}

function renderVisitHistoryItem(visit) {
    const visitDate = getHistoryItemDate(visit);
    const dateText = visitDate
        ? visitDate.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
        : '—';
    const services = Array.isArray(visit.services) ? visit.services.filter(Boolean).map(escapeHtml) : [];
    const servicesText = services.length ? services.join(', ') : 'Посещение';
    const masterText = visit.master ? escapeHtml(visit.master) : '';
    const rawStatus = visit.status || 'Запись';
    const statusText = escapeHtml(rawStatus);
    const statusClass = getVisitStatusClass(rawStatus);
    const amountText = formatVisitAmount(visit.amount);

    return `
        <div class="flex justify-between items-center p-5 bg-white rounded-[28px] border border-white/50 shadow-card mb-3">
            <div class="flex-1">
                <div class="text-sm font-semibold text-stone-800 mb-1">${servicesText}</div>
                <div class="text-xs text-stone-500 font-medium mb-1">${dateText}</div>
                ${masterText ? `<div class="text-xs text-stone-500 font-medium mb-1">Мастер: ${masterText}</div>` : ''}
                <div class="text-xs ${statusClass} font-medium">${statusText}</div>
            </div>
            <div class="text-right ml-4">
                <div class="font-bold text-lg text-stone-800">${amountText}</div>
                <div class="text-[10px] uppercase tracking-wide text-stone-400 mt-1">визит</div>
            </div>
        </div>
        `;
}

function renderTransactionHistoryItem(h) {
    const date = new Date(h.created_at);
    const expiresAt = h.expires_at ? new Date(h.expires_at) : null;
    const isExpired = expiresAt && expiresAt < new Date();
    const daysLeft = expiresAt ? Math.ceil((expiresAt - new Date()) / (1000 * 60 * 60 * 24)) : null;
    const description = escapeHtml(h.description);
    const amount = safeNumber(h.amount, 0);
    const remainingAmount = Number.isFinite(Number(h.remaining_amount)) ? Number(h.remaining_amount) : null;

    return `
        <div class="flex justify-between items-center p-5 bg-white rounded-[28px] border border-white/50 shadow-card mb-3">
            <div class="flex-1">
                <div class="text-sm font-semibold text-stone-800 mb-1">${description}</div>
                <div class="text-xs text-stone-500 font-medium mb-1">${date.toLocaleDateString('ru-RU')}</div>
                ${h.transaction_type === 'earn' && expiresAt ? `
                    <div class="text-xs ${isExpired ? 'text-rose-500' : daysLeft <= 7 ? 'text-orange-500' : 'text-stone-400'} font-medium">
                        ${isExpired ? '⏰ Истекли' : daysLeft <= 7 ? `⏰ Осталось ${daysLeft} ${daysLeft === 1 ? 'день' : daysLeft < 5 ? 'дня' : 'дней'}` : `Действуют до ${expiresAt.toLocaleDateString('ru-RU')}`}
                    </div>
                ` : ''}
            </div>
            <div class="text-right ml-4">
                <div class="font-bold text-lg ${amount > 0 ? 'text-green-600' : 'text-stone-600'}">
                    ${amount > 0 ? '+' : ''}${amount}
                </div>
                ${h.transaction_type === 'earn' && remainingAmount !== null ? `
                    <div class="text-xs text-stone-400 mt-1">Остаток: ${remainingAmount}</div>
                ` : ''}
            </div>
        </div>
        `;
}

function renderHistory(history) {
    const list = document.getElementById('history-list');
    if (!list) return;
    
    if (!history || !history.length) {
        list.innerHTML = `
            <div class="text-center py-8 text-stone-400 text-sm">
                История операций пуста
            </div>`;
        return;
    }
    
    list.innerHTML = history.map(h => {
        if (h?.item_type === 'visit') {
            return renderVisitHistoryItem(h);
        }
        return renderTransactionHistoryItem(h);
    }).join('');
}

function openBooking() {
    if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
    const safeBookingUrl = safeUrl(bookingUrl) || 'https://yclients.com';
    if (tg?.openLink) {
        tg.openLink(safeBookingUrl);
    } else {
        window.open(safeBookingUrl, '_blank');
    }
}

// --- Admin Logic ---

let currentAdminTab = 'users';
let adminItems = [];
let currentUserTransactions = [];
let botButtonsState = {
    selectedId: null,
    draft: null,
    rows: [],
    extraRows: [],
    dirtyOrder: false,
    dragId: null,
    pendingSelectId: null
};

// Pull-to-close variables
let touchStartY = 0;
let touchStartTime = 0;
let currentTranslateY = 0;
let isDraggingModal = false;
let initialScrollTop = 0;

function initModalSwipe() {
    const modalContainer = document.getElementById('modal-container');
    const modal = document.getElementById('admin-modal');
    if (!modalContainer || !modal) return;

    // Обработчик для области заголовка и ручки
    const handleArea = modalContainer.querySelector('.bg-stone-200');
    const titleArea = document.getElementById('modal-title');
    
    function canStartDrag(e) {
        const form = document.getElementById('admin-form');
        const target = e.target;
        
        // Можно начинать драг если:
        // 1. Клик по ручке (серый прямоугольник)
        // 2. Клик по заголовку
        // 3. Клик по контейнеру (но не по форме)
        // 4. Форма прокручена в самый верх
        if (target === handleArea || target === titleArea || 
            (target === modalContainer && form.scrollTop <= 0)) {
            return true;
        }
        
        // Если форма прокручена, не начинаем драг
        if (form.scrollTop > 0) {
            return false;
        }
        
        return false;
    }

    modalContainer.addEventListener('touchstart', (e) => {
        if (!canStartDrag(e)) return;
        
        touchStartY = e.touches[0].clientY;
        touchStartTime = Date.now();
        isDraggingModal = true;
        initialScrollTop = document.getElementById('admin-form').scrollTop;
        
        modalContainer.style.transition = 'none';
    }, { passive: true });

    modalContainer.addEventListener('touchmove', (e) => {
        if (!isDraggingModal) return;

        const form = document.getElementById('admin-form');
        const touchY = e.touches[0].clientY;
        const deltaY = touchY - touchStartY;

        // Если форма прокручена, не позволяем драг
        if (form.scrollTop > initialScrollTop) {
            isDraggingModal = false;
            return;
        }

        if (deltaY > 0) {
            // Dragging down - закрываем модалку
            currentTranslateY = deltaY;
            modalContainer.style.transform = `translateY(${deltaY}px)`;
            
            // Добавляем прозрачность фона при драге
            const backdrop = modal.querySelector('.bg-black\\/40');
            if (backdrop) {
                const opacity = Math.max(0, 0.4 - (deltaY / 500));
                backdrop.style.opacity = opacity;
            }
            
            // Prevent scrolling when dragging modal down
            if (e.cancelable) e.preventDefault();
        } else {
            // Dragging up - сбрасываем
            currentTranslateY = 0;
            modalContainer.style.transform = `translateY(0)`;
        }
    }, { passive: false });

    modalContainer.addEventListener('touchend', () => {
        if (!isDraggingModal) return;
        isDraggingModal = false;

        const backdrop = modal.querySelector('.bg-black\\/40');
        if (backdrop) {
            backdrop.style.opacity = '';
        }

        modalContainer.style.transition = 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
        
        // Закрываем если протащили больше 100px или быстро свайпнули
        const dragDistance = currentTranslateY;
        const dragDuration = Date.now() - touchStartTime;
        const dragSpeed = dragDistance / dragDuration;
        
        if (dragDistance > 100 || (dragDistance > 50 && dragSpeed > 0.5)) {
            closeAdminModal();
        } else {
            // Возвращаем на место
            modalContainer.style.transform = `translateY(0)`;
        }
        currentTranslateY = 0;
    });
}

// Call init on load
window.addEventListener('DOMContentLoaded', () => {
    // initModalSwipe is now called in window.onload
});

async function switchAdminTab(tab) {
    currentAdminTab = tab;
    
    // Update tab UI
    document.querySelectorAll('.admin-tab').forEach(btn => {
        if (btn.getAttribute('data-tab') === tab) {
            btn.classList.add('bg-stone-800', 'text-white', 'shadow-card');
            btn.classList.remove('bg-white', 'text-stone-500');
        } else {
            btn.classList.remove('bg-stone-800', 'text-white', 'shadow-card');
            btn.classList.add('bg-white', 'text-stone-500');
        }
    });
    toggleAdminPanels();
    loadAdminData();
}

async function loadAdminData() {
    const listEl = document.getElementById('admin-list');
    if (listEl) listEl.innerHTML = '<div class="h-20 skeleton w-full"></div><div class="h-20 skeleton w-full"></div>';
    
    try {
        if (currentAdminTab === 'broadcasts') {
            adminItems = await apiFetch(`/api/admin/broadcasts`);
        } else if (currentAdminTab === 'bot-buttons') {
            adminItems = await apiFetch(`/api/admin/bot-buttons`);
        } else if (currentAdminTab === 'settings') {
            const data = await apiFetch(`/api/settings`);
            // Сервер теперь возвращает полные объекты { value, type, description }
            // Мы просто мапим их в удобный формат
            adminItems = Object.entries(data.settings).map(([key, setting]) => ({
                id: key, // Используем ключ как ID
                key: key,
                value: setting.value,
                type: setting.type,
                description: setting.description
            }));
        } else {
            adminItems = await apiFetch(`/api/admin/${currentAdminTab}`);
        }
        
        renderAdminList();
    } catch (error) {
        if (listEl) {
            listEl.innerHTML = `<div class="text-center py-10 text-rose-500">
                <div class="font-semibold mb-2">Ошибка загрузки</div>
                <div class="text-xs text-stone-400">${escapeHtml(friendlyErrorMessage(error, 'Не удалось загрузить данные.'))}</div>
            </div>`;
        }
    }
}

function toggleAdminPanels() {
    const listEl = document.getElementById('admin-list');
    const panelEl = document.getElementById('bot-buttons-panel');
    const addBtn = document.getElementById('admin-add-button');
    if (!listEl || !panelEl) return;

    if (currentAdminTab === 'bot-buttons') {
        listEl.classList.add('hidden');
        panelEl.classList.remove('hidden');
        if (addBtn) addBtn.classList.add('hidden');
    } else {
        listEl.classList.remove('hidden');
        panelEl.classList.add('hidden');
        if (addBtn) addBtn.classList.remove('hidden');
    }
}

function initBotButtonsPanel() {
    const addRowBtn = document.getElementById('bot-buttons-add-row');
    const addButtonBtn = document.getElementById('bot-buttons-add-button');
    const saveOrderBtn = document.getElementById('bot-buttons-save-order');
    const rowsEl = document.getElementById('bot-buttons-rows');
    const form = document.getElementById('bot-buttons-editor-form');
    const deleteBtn = document.getElementById('bot-buttons-delete');

    if (addRowBtn) {
        addRowBtn.addEventListener('click', () => {
            addBotButtonsRow();
        });
    }
    if (addButtonBtn) {
        addButtonBtn.addEventListener('click', () => {
            let targetRow = 1;
            if (botButtonsState.selectedId && botButtonsState.selectedId !== 'new') {
                const selectedItem = adminItems.find(item => String(item.id) === String(botButtonsState.selectedId));
                if (selectedItem) targetRow = safeNumber(selectedItem.row_number, 1);
            } else if (botButtonsState.rows.length) {
                targetRow = botButtonsState.rows[botButtonsState.rows.length - 1].rowNumber;
            }
            createBotButtonDraft(targetRow);
        });
    }
    if (saveOrderBtn) {
        saveOrderBtn.addEventListener('click', () => {
            saveBotButtonsOrder();
        });
    }
    if (form) {
        form.addEventListener('submit', handleBotButtonsSave);
    }
    if (deleteBtn) {
        deleteBtn.addEventListener('click', handleBotButtonsDelete);
    }
    if (rowsEl) {
        rowsEl.addEventListener('click', handleBotButtonsRowClick);
        rowsEl.addEventListener('dragstart', handleBotButtonsDragStart);
        rowsEl.addEventListener('dragover', handleBotButtonsDragOver);
        rowsEl.addEventListener('drop', handleBotButtonsDrop);
        rowsEl.addEventListener('dragend', () => {
            botButtonsState.dragId = null;
        });
    }
}

function buildBotButtonsRows(items, extraRows) {
    const rowsMap = new Map();
    items.forEach(item => {
        const rowNumber = safeNumber(item.row_number, 1);
        if (!rowsMap.has(rowNumber)) rowsMap.set(rowNumber, []);
        rowsMap.get(rowNumber).push(item);
    });
    rowsMap.forEach((rowItems, rowNumber) => {
        rowItems.sort((a, b) => safeNumber(a.order_in_row, 0) - safeNumber(b.order_in_row, 0));
    });

    const rowNumbers = Array.from(new Set([...rowsMap.keys(), ...extraRows]));
    rowNumbers.sort((a, b) => a - b);

    return rowNumbers.map(rowNumber => ({
        rowNumber,
        items: rowsMap.get(rowNumber) || []
    }));
}

function setSaveOrderButtonState() {
    const saveOrderBtn = document.getElementById('bot-buttons-save-order');
    if (!saveOrderBtn) return;
    if (botButtonsState.dirtyOrder) {
        saveOrderBtn.disabled = false;
        saveOrderBtn.classList.remove('opacity-50', 'cursor-not-allowed');
    } else {
        saveOrderBtn.disabled = true;
        saveOrderBtn.classList.add('opacity-50', 'cursor-not-allowed');
    }
}

function renderBotButtonsPanel() {
    const rowsEl = document.getElementById('bot-buttons-rows');
    const emptyEl = document.getElementById('bot-buttons-empty');
    if (!rowsEl || !emptyEl) return;

    botButtonsState.rows = buildBotButtonsRows(adminItems, botButtonsState.extraRows);

    if (botButtonsState.pendingSelectId) {
        const exists = adminItems.some(item => String(item.id) === String(botButtonsState.pendingSelectId));
        botButtonsState.selectedId = exists ? botButtonsState.pendingSelectId : null;
        botButtonsState.pendingSelectId = null;
        botButtonsState.draft = null;
    } else if (botButtonsState.selectedId && botButtonsState.selectedId !== 'new') {
        const stillExists = adminItems.some(item => String(item.id) === String(botButtonsState.selectedId));
        if (!stillExists) {
            botButtonsState.selectedId = null;
        }
    }

    if (!botButtonsState.rows.length) {
        emptyEl.classList.remove('hidden');
        rowsEl.innerHTML = '';
    } else {
        emptyEl.classList.add('hidden');
        rowsEl.innerHTML = botButtonsState.rows.map(row => {
            const buttonsHtml = row.items.map(item => {
                const safeId = encodeId(item.id);
                const buttonText = escapeHtml(item.button_text || 'Без названия');
                const isSelected = String(botButtonsState.selectedId) === String(item.id);
                const isInactive = item.is_active === false;
                const isAdminOnly = !!item.is_admin_only;
                const stateClasses = isSelected ? 'bg-stone-800 text-white' : 'bg-stone-50 text-stone-700';
                const opacityClass = isInactive ? 'opacity-60' : '';
                const badge = isAdminOnly ? '<span class="text-[10px] ml-2 px-1.5 py-0.5 rounded-full bg-purple-100 text-purple-600 font-semibold">A</span>' : '';
                return `
                    <button type="button"
                        class="bot-button px-3 py-2 rounded-xl border border-stone-100 text-xs font-semibold flex items-center ${stateClasses} ${opacityClass}"
                        draggable="true"
                        data-button-id="${safeId}"
                        data-drop-target="button">
                        <span class="truncate max-w-[120px]">${buttonText}</span>
                        ${badge}
                    </button>
                `;
            }).join('');

            return `
                <div class="bg-stone-50 rounded-[22px] p-3 border border-stone-100" data-row-number="${row.rowNumber}">
                    <div class="flex items-center justify-between mb-2">
                        <div class="text-xs font-semibold text-stone-500">Ряд ${row.rowNumber}</div>
                        <button type="button" class="text-xs font-semibold text-stone-600" data-add-button-row="${row.rowNumber}">+ Кнопка</button>
                    </div>
                    <div class="flex flex-wrap gap-2 min-h-[36px] items-center" data-drop-target="row" data-row-number="${row.rowNumber}">
                        ${buttonsHtml || '<span class="text-xs text-stone-400">Перетащите кнопку сюда</span>'}
                    </div>
                </div>
            `;
        }).join('');
    }

    renderBotButtonsEditor();
    setSaveOrderButtonState();
}

function renderBotButtonsEditor() {
    const editorEl = document.getElementById('bot-buttons-editor');
    const actionsEl = document.getElementById('bot-buttons-editor-actions');
    const deleteBtn = document.getElementById('bot-buttons-delete');
    if (!editorEl || !actionsEl || !deleteBtn) return;

    let item = null;
    if (botButtonsState.selectedId === 'new') {
        item = botButtonsState.draft;
    } else if (botButtonsState.selectedId) {
        item = adminItems.find(i => String(i.id) === String(botButtonsState.selectedId));
    }

    if (!item) {
        editorEl.innerHTML = 'Кнопка не выбрана';
        editorEl.classList.add('text-stone-400');
        actionsEl.classList.add('hidden');
        deleteBtn.classList.add('hidden');
        return;
    }

    const safeButtonText = escapeAttr(item.button_text || '');
    const safeResponseText = escapeHtml(item.response_text || '');
    const safeHandler = String(item.handler_type || 'info');
    const safeRow = safeNumber(item.row_number, 1);
    const safeOrder = safeNumber(item.order_in_row, 0);
    const safeWebAppUrl = escapeAttr(item.web_app_url || '');
    const isAdminOnly = !!item.is_admin_only;
    const isActive = item.is_active !== false;

    editorEl.classList.remove('text-stone-400');
    editorEl.innerHTML = `
        <div>
            <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Текст кнопки</label>
            <input type="text" name="button_text" value="${safeButtonText}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" required>
        </div>
        <div>
            <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Текст ответа</label>
            <textarea name="response_text" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm h-28" required>${safeResponseText}</textarea>
            <p class="text-xs text-stone-400 mt-1 px-1">Markdown + {YCLIENTS_BOOKING_URL}, {LOYALTY_PERCENTAGE}, {LOYALTY_MAX_SPEND_PERCENTAGE}, {LOYALTY_EXPIRATION_DAYS}</p>
        </div>
        <div>
            <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Тип обработчика</label>
            <select name="handler_type" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">
                <option value="book" ${safeHandler === 'book' ? 'selected' : ''}>Запись</option>
                <option value="info" ${safeHandler === 'info' ? 'selected' : ''}>Информация</option>
                <option value="profile" ${safeHandler === 'profile' ? 'selected' : ''}>Профиль</option>
                <option value="admin" ${safeHandler === 'admin' ? 'selected' : ''}>Админка</option>
            </select>
        </div>
        <div class="grid grid-cols-2 gap-3">
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Номер строки</label>
                <input type="number" name="row_number" value="${safeRow}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" min="1" required>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Порядок</label>
                <input type="number" name="order_in_row" value="${safeOrder}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" min="0" required>
            </div>
        </div>
        <div>
            <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">WebApp URL</label>
            <input type="text" name="web_app_url" value="${safeWebAppUrl}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" placeholder="https://example.com/webapp">
        </div>
        <div class="flex items-center gap-2 px-1">
            <input type="checkbox" name="is_admin_only" ${isAdminOnly ? 'checked' : ''} class="w-4 h-4 rounded">
            <label class="text-sm font-semibold text-stone-600">Только для админов</label>
        </div>
        <div class="flex items-center gap-2 px-1">
            <input type="checkbox" name="is_active" ${isActive ? 'checked' : ''} class="w-4 h-4 rounded">
            <label class="text-sm font-semibold text-stone-600">Активна</label>
        </div>
    `;

    actionsEl.classList.remove('hidden');
    deleteBtn.classList.toggle('hidden', botButtonsState.selectedId === 'new');
}

function addBotButtonsRow() {
    const rowNumbers = botButtonsState.rows.map(row => row.rowNumber);
    const maxRow = rowNumbers.length ? Math.max(...rowNumbers) : 0;
    const nextRow = maxRow + 1;
    if (!botButtonsState.extraRows.includes(nextRow)) {
        botButtonsState.extraRows.push(nextRow);
    }
    renderBotButtonsPanel();
}

function createBotButtonDraft(rowNumber) {
    const targetRow = botButtonsState.rows.find(row => row.rowNumber === rowNumber);
    const defaultOrder = targetRow ? targetRow.items.length : 0;
    botButtonsState.selectedId = 'new';
    botButtonsState.draft = {
        button_text: '',
        response_text: '',
        handler_type: 'info',
        row_number: rowNumber,
        order_in_row: defaultOrder,
        web_app_url: '',
        is_admin_only: false,
        is_active: true
    };
    renderBotButtonsPanel();
}

function handleBotButtonsRowClick(event) {
    const addButton = event.target.closest('[data-add-button-row]');
    if (addButton) {
        const rowNumber = parseInt(addButton.getAttribute('data-add-button-row'), 10) || 1;
        createBotButtonDraft(rowNumber);
        return;
    }

    const buttonEl = event.target.closest('[data-button-id]');
    if (buttonEl) {
        const decodedId = decodeId(buttonEl.getAttribute('data-button-id'));
        botButtonsState.selectedId = decodedId;
        botButtonsState.draft = null;
        renderBotButtonsPanel();
    }
}

function handleBotButtonsDragStart(event) {
    const buttonEl = event.target.closest('[data-button-id]');
    if (!buttonEl) return;
    botButtonsState.dragId = decodeId(buttonEl.getAttribute('data-button-id'));
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', String(botButtonsState.dragId));
}

function handleBotButtonsDragOver(event) {
    const target = event.target.closest('[data-drop-target]');
    if (!target) return;
    event.preventDefault();
}

function handleBotButtonsDrop(event) {
    event.preventDefault();
    if (!botButtonsState.dragId) return;
    const rowEl = event.target.closest('[data-row-number]');
    if (!rowEl) return;
    const rowNumber = parseInt(rowEl.getAttribute('data-row-number'), 10);
    if (!rowNumber) return;

    const buttonEl = event.target.closest('[data-button-id]');
    let targetIndex = 999;
    if (buttonEl) {
        const rowButtons = Array.from(rowEl.querySelectorAll('[data-button-id]'));
        targetIndex = rowButtons.indexOf(buttonEl);
    }
    moveBotButtonToRow(botButtonsState.dragId, rowNumber, targetIndex);
}

function moveBotButtonToRow(buttonId, rowNumber, targetIndex) {
    const rows = botButtonsState.rows.map(row => ({
        rowNumber: row.rowNumber,
        items: [...row.items]
    }));
    let draggedItem = null;
    rows.forEach(row => {
        const index = row.items.findIndex(item => String(item.id) === String(buttonId));
        if (index !== -1) {
            draggedItem = row.items.splice(index, 1)[0];
        }
    });
    if (!draggedItem) return;

    let targetRow = rows.find(row => row.rowNumber === rowNumber);
    if (!targetRow) {
        targetRow = { rowNumber, items: [] };
        rows.push(targetRow);
        rows.sort((a, b) => a.rowNumber - b.rowNumber);
    }

    if (!Number.isFinite(targetIndex) || targetIndex < 0) {
        targetIndex = targetRow.items.length;
    }
    if (targetIndex > targetRow.items.length) {
        targetIndex = targetRow.items.length;
    }
    targetRow.items.splice(targetIndex, 0, draggedItem);

    botButtonsState.rows = rows;
    applyBotButtonsOrderToItems();
    renderBotButtonsPanel();
}

function applyBotButtonsOrderToItems() {
    const itemsMap = new Map(adminItems.map(item => [String(item.id), item]));
    botButtonsState.rows.forEach(row => {
        row.items.forEach((item, index) => {
            const ref = itemsMap.get(String(item.id));
            if (ref) {
                ref.row_number = row.rowNumber;
                ref.order_in_row = index;
            }
        });
    });
    botButtonsState.dirtyOrder = true;
    setSaveOrderButtonState();
}

async function saveBotButtonsOrder() {
    try {
        const payload = {
            items: adminItems.map(item => ({
                id: item.id,
                row_number: safeNumber(item.row_number, 1),
                order_in_row: safeNumber(item.order_in_row, 0)
            }))
        };
        const response = await fetch(`${window.location.origin}/api/admin/bot-buttons/reorder`, {
            method: 'POST',
            headers: {
                'X-Tg-Init-Data': tg.initData || '',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        if (!response.ok) throw new Error('Reorder error');
        botButtonsState.dirtyOrder = false;
        await loadAdminData();
        tg.HapticFeedback.notificationOccurred('success');
    } catch (error) {
        console.error("Reorder error:", error);
        alert("Ошибка при сохранении порядка");
    }
}

async function handleBotButtonsSave(event) {
    event.preventDefault();
    const form = event.target;
    const formData = new FormData(form);
    const selectedId = botButtonsState.selectedId;

    const buttonText = String(formData.get('button_text') || '').trim();
    const responseText = String(formData.get('response_text') || '').trim();
    const handlerType = String(formData.get('handler_type') || 'info');
    const rowNumber = parseInt(formData.get('row_number'), 10) || 1;
    const orderInRow = parseInt(formData.get('order_in_row'), 10) || 0;
    const webAppUrl = String(formData.get('web_app_url') || '').trim();
    const isAdminOnly = form.querySelector('[name="is_admin_only"]')?.checked || false;
    const isActive = form.querySelector('[name="is_active"]')?.checked || false;

    if (!buttonText) {
        alert("Введите текст кнопки");
        return;
    }
    if (!responseText) {
        alert("Введите текст ответа");
        return;
    }

    const duplicate = adminItems.some(item => {
        if (selectedId && selectedId !== 'new' && String(item.id) === String(selectedId)) return false;
        return String(item.button_text || '').trim() === buttonText;
    });
    if (duplicate) {
        alert("Кнопка с таким текстом уже существует");
        return;
    }

    const data = {
        button_text: buttonText,
        response_text: responseText,
        handler_type: handlerType,
        row_number: rowNumber,
        order_in_row: orderInRow,
        web_app_url: webAppUrl ? webAppUrl : null,
        is_admin_only: isAdminOnly,
        is_active: isActive
    };

    const isNew = selectedId === 'new' || !selectedId;
    const url = isNew ? '/api/admin/bot-buttons' : `/api/admin/bot-buttons/${selectedId}`;
    const method = isNew ? 'POST' : 'PUT';

    try {
        const response = await fetch(window.location.origin + url, {
            method,
            headers: {
                'X-Tg-Init-Data': tg.initData || '',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error('Save error');
        const saved = await response.json();
        botButtonsState.pendingSelectId = saved?.id || (isNew ? null : selectedId);
        botButtonsState.dirtyOrder = false;
        await loadAdminData();
        tg.HapticFeedback.notificationOccurred('success');
    } catch (error) {
        console.error("Save error:", error);
        alert("Ошибка при сохранении кнопки");
    }
}

async function handleBotButtonsDelete() {
    const selectedId = botButtonsState.selectedId;
    if (!selectedId || selectedId === 'new') return;
    if (!confirm('Удалить эту кнопку?')) return;
    try {
        const response = await fetch(`${window.location.origin}/api/admin/bot-buttons/${selectedId}`, {
            method: 'DELETE',
            headers: {
                'X-Tg-Init-Data': tg.initData || '',
                'Content-Type': 'application/json'
            }
        });
        if (!response.ok) throw new Error('Delete error');
        botButtonsState.selectedId = null;
        botButtonsState.draft = null;
        await loadAdminData();
        tg.HapticFeedback.notificationOccurred('success');
    } catch (error) {
        console.error("Delete error:", error);
        alert("Ошибка при удалении кнопки");
    }
}

function renderAdminList() {
    const listEl = document.getElementById('admin-list');
    if (!listEl) return;

    toggleAdminPanels();

    if (currentAdminTab === 'bot-buttons') {
        renderBotButtonsPanel();
        return;
    }
    
    
    
    if (!adminItems.length) {
        listEl.innerHTML = '<div class="text-center py-10 text-stone-400">Список пуст</div>';
        return;
    }
    
    if (currentAdminTab === 'users') {
        listEl.innerHTML = adminItems.map(item => {
            const safeId = encodeId(item.id);
            const name = escapeHtml(item.name || 'Без имени');
            const phone = escapeHtml(item.phone || '');
            const balance = safeNumber(item.balance, 0);
            const level = String(item.level || 'new').toLowerCase();
            const levelClass = level === 'vip' ? 'bg-yellow-100 text-yellow-800' : level === 'regular' ? 'bg-blue-100 text-blue-800' : 'bg-stone-100 text-stone-600';
            const levelLabel = level === 'vip' ? 'VIP' : level === 'regular' ? 'Regular' : 'New';
            const inactiveBadge = item.active ? '' : '<span class="text-xs px-2.5 py-1 rounded-full bg-rose-100 text-rose-600 font-medium">Неактивен</span>';
            return `
            <div class="bg-white p-5 rounded-[28px] border border-white/50 shadow-card active:scale-[0.98] transition-transform" onclick="openUserModal('${safeId}')">
                <div class="flex items-center gap-4 mb-3">
                    <div class="w-12 h-12 rounded-xl bg-stone-50 flex items-center justify-center text-xl shadow-sm">
                        👤
                    </div>
                    <div class="flex-1 min-w-0">
                        <h4 class="font-semibold text-stone-800 text-sm truncate mb-1">${name}</h4>
                        <p class="text-xs text-stone-500 truncate font-medium">${phone}</p>
                    </div>
                    <div class="text-right">
                        <div class="font-bold text-brand-primary text-lg font-serif">${balance}</div>
                        <div class="text-xs text-stone-400 font-medium">баллов</div>
                    </div>
                </div>
                <div class="flex items-center gap-2 pt-3 border-t border-stone-100">
                    <span class="text-xs px-2.5 py-1 rounded-full font-medium ${levelClass}">${levelLabel}</span>
                    ${inactiveBadge}
                </div>
            </div>
            `;
        }).join('');
    } else if (currentAdminTab === 'broadcasts') {
        listEl.innerHTML = adminItems.map(item => {
            const statusColors = {
                'pending': 'bg-yellow-100 text-yellow-800',
                'scheduled': 'bg-purple-100 text-purple-800',
                'sending': 'bg-blue-100 text-blue-800',
                'completed': 'bg-green-100 text-green-800',
                'failed': 'bg-rose-100 text-rose-800'
            };
            const statusText = {
                'pending': 'Ожидает',
                'scheduled': 'Запланирована',
                'sending': 'Отправляется',
                'completed': 'Завершена',
                'failed': 'Ошибка'
            };
            const status = String(item.status || '');
            const statusClass = statusColors[status] || 'bg-stone-100 text-stone-600';
            const statusLabel = statusText[status] || escapeHtml(status);
            const message = String(item.message || item.content || item.title || '');
            const shortMessage = message.length > 100 ? `${message.slice(0, 100)}...` : message;
            const safeMessage = escapeHtml(shortMessage);
            const imageUrl = safeUrl(item.image_url);
            const sentCount = safeNumber(item.sent_count, 0);
            const failedCount = safeNumber(item.failed_count, 0);
            const safeId = encodeId(item.id);

            // created_at хранится в UTC, конвертируем в московское время
            const date = new Intl.DateTimeFormat('ru-RU', {
                day: '2-digit',
                month: '2-digit',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                timeZone: 'Europe/Moscow'
            }).format(new Date(item.created_at));
            
            let scheduledDate = '';
            if (item.scheduled_at) {
                // scheduled_at хранится в UTC, конвертируем в московское время
                scheduledDate = new Intl.DateTimeFormat('ru-RU', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                    timeZone: 'Europe/Moscow'
                }).format(new Date(item.scheduled_at));
            }
            
            return `
                <div class="bg-white p-5 rounded-[28px] border border-white/50 shadow-card">
                    <div class="flex items-start gap-4 mb-3">
                        ${imageUrl ? `
                            <img src="${escapeAttr(imageUrl)}" class="w-16 h-16 rounded-xl object-cover bg-stone-100 shadow-sm" alt="">
                        ` : `
                            <div class="w-12 h-12 rounded-xl bg-stone-50 flex items-center justify-center text-xl shadow-sm">
                                📢
                            </div>
                        `}
                        <div class="flex-1 min-w-0">
                            <h4 class="font-semibold text-stone-800 text-sm mb-2 line-clamp-2">${safeMessage}</h4>
                            <p class="text-xs text-stone-500 mb-1">Создана: ${escapeHtml(date)}</p>
                            ${scheduledDate ? `<p class="text-xs text-purple-600 mb-1">📅 Запланирована: ${escapeHtml(scheduledDate)}</p>` : ''}
                            <div class="flex items-center gap-2 flex-wrap">
                                <span class="text-xs px-2.5 py-1 rounded-full font-medium ${statusClass}">${statusLabel}</span>
                                ${sentCount > 0 ? `<span class="text-xs text-stone-600">✓ ${sentCount} отправлено</span>` : ''}
                                ${failedCount > 0 ? `<span class="text-xs text-rose-600">✗ ${failedCount} ошибок</span>` : ''}
                            </div>
                        </div>
                    </div>
                    <div class="flex gap-2 mt-3">
                        <button onclick="viewBroadcast('${safeId}')" class="px-4 bg-stone-100 text-stone-700 py-2.5 rounded-xl font-semibold text-sm active:scale-[0.98] transition-all">
                            Просмотр
                        </button>
                        ${status === 'pending' || status === 'failed' || status === 'scheduled' ? `
                            ${status === 'scheduled' ? '' : `
                                <button onclick="sendBroadcast('${safeId}')" class="flex-1 bg-stone-800 text-white py-2.5 rounded-xl font-semibold text-sm active:scale-[0.98] transition-all">
                                    ${status === 'failed' ? 'Повторить отправку' : 'Отправить'}
                                </button>
                            `}
                            <button onclick="deleteBroadcast('${safeId}')" class="px-4 bg-rose-500 text-white py-2.5 rounded-xl font-semibold text-sm active:scale-[0.98] transition-all">
                                Удалить
                            </button>
                        ` : ''}
                    </div>
                </div>
            `;
        }).join('');
    } else if (currentAdminTab === 'settings') {
        listEl.innerHTML = adminItems.map(item => {
            const safeKey = encodeId(item.key);
            const description = escapeHtml(item.description || item.key);
            const displayValue = PERCENT_SETTING_KEYS.has(item.key)
                ? `${Math.round(normalizePercentValue(item.value))}%`
                : item.value;
            const value = escapeHtml(displayValue);
            return `
            <div class="bg-white p-5 rounded-[28px] border border-white/50 shadow-card active:scale-[0.98] transition-transform flex items-center gap-4" onclick="openSettingModal('${safeKey}')">
                <div class="w-12 h-12 rounded-xl bg-stone-50 flex items-center justify-center text-xl shadow-sm">
                    ⚙️
                </div>
                <div class="flex-1 min-w-0">
                    <h4 class="font-semibold text-stone-800 text-sm truncate mb-1">${description}</h4>
                    <p class="text-xs text-stone-500 font-medium">${value}</p>
                </div>
                <div class="text-stone-300 text-lg">→</div>
            </div>
            `;
        }).join('');
    } else {
        // Для остальных вкладок (masters, services, promotions)
        listEl.innerHTML = adminItems.map((item, index) => {
            const safeId = encodeId(item.id);
            const imageUrl = safeUrl(item.photo_url || item.image_url);
            const title = escapeHtml(item.name || item.title || '');
            const price = Number.isFinite(Number(item.price)) ? `${Number(item.price)} ₽` : '';
            const subtitle = escapeHtml(item.specialization || price || item.description || '');
            return `
            <div class="bg-white p-4 rounded-[28px] border border-white/50 shadow-card flex items-center gap-3">
                <div class="flex flex-col gap-1">
                    <button onclick="event.stopPropagation(); moveItem('${safeId}', 'up')" 
                            class="w-8 h-8 rounded-lg bg-stone-50 text-stone-600 flex items-center justify-center text-xs font-bold active:bg-stone-100 transition-colors shadow-sm ${index === 0 ? 'opacity-30 cursor-not-allowed' : ''}"
                            ${index === 0 ? 'disabled' : ''}>
                        ↑
                    </button>
                    <button onclick="event.stopPropagation(); moveItem('${safeId}', 'down')" 
                            class="w-8 h-8 rounded-lg bg-stone-50 text-stone-600 flex items-center justify-center text-xs font-bold active:bg-stone-100 transition-colors shadow-sm ${index === adminItems.length - 1 ? 'opacity-30 cursor-not-allowed' : ''}"
                            ${index === adminItems.length - 1 ? 'disabled' : ''}>
                        ↓
                    </button>
                </div>
                <div class="flex-1 flex items-center gap-4 active:scale-[0.98] transition-transform rounded-xl p-2" onclick="openAdminModal('${safeId}')">
                    ${imageUrl ? 
                        `<img src="${escapeAttr(imageUrl)}" class="w-12 h-12 rounded-xl object-cover bg-stone-100 shadow-sm" alt="">` : 
                        `<div class="w-12 h-12 rounded-xl bg-stone-50 flex items-center justify-center text-xl shadow-sm">
                            ${currentAdminTab === 'masters' ? '👩‍⚕️' : currentAdminTab === 'services' ? '✨' : '🎁'}
                        </div>`
                    }
                    <div class="flex-1 min-w-0">
                        <h4 class="font-semibold text-stone-800 text-sm truncate mb-1">${title}</h4>
                        <p class="text-xs text-stone-500 truncate font-medium">${subtitle}</p>
                    </div>
                    <div class="text-stone-300 text-lg">→</div>
                </div>
            </div>
            `;
        }).join('');
    }
}

function openAdminModal(id = null) {
    const modal = document.getElementById('admin-modal');
    const container = document.getElementById('modal-container');
    const title = document.getElementById('modal-title');
    const form = document.getElementById('admin-form');
    const fields = document.getElementById('form-fields');
    const deleteBtn = document.getElementById('delete-btn');
    const formId = document.getElementById('form-id');
    const decodedId = id ? decodeId(id) : null;
    
    // Для рассылок не поддерживаем редактирование, только создание
    if (currentAdminTab === 'broadcasts' && decodedId) {
        alert('Редактирование рассылок не поддерживается. Создайте новую рассылку.');
        return;
    }
    
    form.reset();
    formId.value = decodedId || '';
    
    if (decodedId && currentAdminTab !== 'broadcasts') {
        const item = adminItems.find(i => String(i.id) === String(decodedId));
        title.innerText = 'Редактировать';
        deleteBtn.classList.remove('hidden');
        renderFormFields(item);
    } else {
        title.innerText = currentAdminTab === 'broadcasts' ? 'Создать рассылку' : 'Добавить';
        deleteBtn.classList.add('hidden');
        renderFormFields();
    }
    
    modal.classList.remove('hidden');
    // Force a reflow to ensure animation starts from translate-y-full
    container.style.transform = 'translateY(100%)';
    container.offsetHeight; 
    
    setTimeout(() => {
        container.style.transition = 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
        container.style.transform = 'translateY(0)';
    }, 10);
}

async function openUserModal(id) {
    const modal = document.getElementById('admin-modal');
    const container = document.getElementById('modal-container');
    const title = document.getElementById('modal-title');
    const form = document.getElementById('admin-form');
    const fields = document.getElementById('form-fields');
    const deleteBtn = document.getElementById('delete-btn');
    const formId = document.getElementById('form-id');
    const decodedId = decodeId(id);
    
    form.reset();
    formId.value = decodedId;
    
    // Восстанавливаем стандартный обработчик submit
    form.onsubmit = handleAdminSubmit;
    
    try {
        const user = await apiFetch(`/api/admin/users/${decodedId}`);
        title.innerText = user.name || user.phone || 'Пользователь';
        deleteBtn.classList.add('hidden');
        
        // Загружаем транзакции
        currentUserTransactions = await apiFetch(`/api/admin/users/${decodedId}/transactions`);
        
        renderUserForm(user);
        
        modal.classList.remove('hidden');
        // Force a reflow to ensure animation starts from translate-y-full
        container.style.transform = 'translateY(100%)';
        container.offsetHeight;
        
        setTimeout(() => {
            container.style.transition = 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
            container.style.transform = 'translateY(0)';
        }, 10);
    } catch (error) {
        console.error("Error loading user:", error);
        alert("Ошибка загрузки пользователя");
    }
}

function renderUserForm(user) {
    const fieldsEl = document.getElementById('form-fields');
    const safeName = escapeAttr(user.name || '');
    const safePhone = escapeAttr(user.phone || '');
    const level = String(user.level || 'new');
    const transactionsHtml = currentUserTransactions.length ? currentUserTransactions.map(t => {
        const description = escapeHtml(t.description || 'Транзакция');
        const createdAt = new Date(t.created_at).toLocaleString('ru-RU');
        const amount = safeNumber(t.amount, 0);
        return `
                    <div class="flex justify-between items-center p-2 bg-stone-50 rounded-lg text-xs">
                        <div>
                            <div class="font-semibold text-stone-800">${description}</div>
                            <div class="text-stone-400">${escapeHtml(createdAt)}</div>
                        </div>
                        <div class="font-bold ${amount > 0 ? 'text-green-600' : 'text-rose-600'}">
                            ${amount > 0 ? '+' : ''}${amount}
                        </div>
                    </div>
        `;
    }).join('') : '<div class="text-center py-4 text-stone-400 text-xs">Нет транзакций</div>';

    const html = `
        <div>
            <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Имя</label>
            <input type="text" name="name" value="${safeName}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">
        </div>
        <div>
            <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Телефон</label>
            <input type="text" name="phone" value="${safePhone}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" readonly>
        </div>
        <div>
            <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Баланс баллов</label>
            <div class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm text-stone-700">
                ${safeNumber(user.balance, 0)}
            </div>
            <div class="text-[10px] text-stone-400 mt-2 px-1">Баланс меняется только через транзакции</div>
        </div>
        <div>
            <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Уровень</label>
            <select name="level" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">
                <option value="new" ${level === 'new' ? 'selected' : ''}>New</option>
                <option value="regular" ${level === 'regular' ? 'selected' : ''}>Regular</option>
                <option value="vip" ${level === 'vip' ? 'selected' : ''}>VIP</option>
            </select>
        </div>
        <div class="flex items-center gap-2 px-1">
            <input type="checkbox" name="active" ${user.active !== false ? 'checked' : ''} class="w-4 h-4 rounded">
            <label class="text-sm font-semibold text-stone-600">Активен</label>
        </div>
        
        <div class="pt-4 border-t border-stone-200 mt-4">
            <h4 class="text-sm font-bold text-stone-700 mb-3">История транзакций</h4>
            <div id="user-transactions-list" class="space-y-2 max-h-48 overflow-y-auto">
                ${transactionsHtml}
            </div>
            <button type="button" onclick="openTransactionModal('${encodeId(user.id)}')" class="w-full mt-3 bg-stone-100 text-stone-700 py-2 rounded-xl text-sm font-semibold active:opacity-80">
                + Добавить транзакцию
            </button>
        </div>
    `;
    
    fieldsEl.innerHTML = html;
}

function openTransactionModal(userId) {
    const modal = document.getElementById('admin-modal');
    const container = document.getElementById('modal-container');
    const title = document.getElementById('modal-title');
    const form = document.getElementById('admin-form');
    const fields = document.getElementById('form-fields');
    const deleteBtn = document.getElementById('delete-btn');
    const formId = document.getElementById('form-id');
    const decodedUserId = decodeId(userId);
    
    form.reset();
    formId.value = decodedUserId;
    
    title.innerText = 'Добавить транзакцию';
    deleteBtn.classList.add('hidden');
    
    const html = `
        <input type="hidden" name="user_id" value="${escapeAttr(decodedUserId)}">
        <div>
            <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Сумма</label>
            <input type="number" name="amount" placeholder="Положительное = начисление, отрицательное = списание" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" required>
        </div>
        <div>
            <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Описание</label>
            <textarea name="description" placeholder="Причина изменения баланса" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm h-20"></textarea>
        </div>
    `;
    
    fields.innerHTML = html;
    
    // Переопределяем submit для транзакций
    form.onsubmit = async (e) => {
        e.preventDefault();
        await handleTransactionSubmit(e, decodedUserId);
    };
    
    modal.classList.remove('hidden');
    // Force a reflow to ensure animation starts from translate-y-full
    container.style.transform = 'translateY(100%)';
    container.offsetHeight;
    
    setTimeout(() => {
        container.style.transition = 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
        container.style.transform = 'translateY(0)';
    }, 10);
}

async function handleTransactionSubmit(e, userId) {
    const form = e.target;
    const formData = new FormData(form);
    const data = {
        amount: parseInt(formData.get('amount')),
        description: formData.get('description') || 'Ручное изменение баланса'
    };
    
    try {
        const response = await fetch(`${window.location.origin}/api/admin/users/${userId}/transactions`, {
            method: 'POST',
            headers: {
                'X-Tg-Init-Data': tg.initData || '',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) {
            let detail = 'Ошибка при создании транзакции';
            try {
                const body = await response.json();
                if (body && body.detail) detail = body.detail;
            } catch (e) {}
            throw new Error(detail);
        }
        
        tg.HapticFeedback.notificationOccurred('success');
        closeAdminModal();
        
        // Небольшая задержка перед открытием формы пользователя
        setTimeout(() => {
            openUserModal(userId);
        }, 350);
    } catch (error) {
        console.error("Transaction error:", error);
        alert(friendlyErrorMessage(error, "Ошибка при создании транзакции"));
    }
}

function renderFormFields(item = {}) {
    const fieldsEl = document.getElementById('form-fields');
    let html = '';

    const safe = {
        name: escapeAttr(item.name || ''),
        phone: escapeAttr(item.phone || ''),
        balance: safeNumber(item.balance, 0),
        level: String(item.level || 'new'),
        specialization: escapeAttr(item.specialization || ''),
        title: escapeAttr(item.title || ''),
        category: escapeAttr(item.category || ''),
        price: escapeAttr(item.price ?? ''),
        description: escapeHtml(item.description || ''),
        detailText: escapeHtml(item.detail_text || ''),
        conditions: escapeHtml(item.conditions || ''),
        photoUrl: safeUrl(item.photo_url),
        imageUrl: safeUrl(item.image_url),
        endDate: escapeAttr(item.end_date || ''),
        actionUrl: escapeAttr(item.action_url || ''),
        actionText: escapeAttr(item.action_text || 'Записаться'),
        message: escapeHtml(item.message || item.content || item.title || ''),
        recipientType: String(item.recipient_type || ''),
        recipientIds: escapeAttr(JSON.stringify(item.recipient_ids || [])),
        filterBalanceMin: escapeAttr(item.filter_balance_min || ''),
        filterBalanceMax: escapeAttr(item.filter_balance_max || ''),
        buttonText: escapeAttr(item.button_text || ''),
        responseText: escapeHtml(item.response_text || ''),
        handlerType: String(item.handler_type || ''),
        rowNumber: safeNumber(item.row_number, 1),
        orderInRow: safeNumber(item.order_in_row, 0),
        webAppUrl: escapeAttr(item.web_app_url || ''),
        isActive: item.is_active !== false,
        isAdminOnly: !!item.is_admin_only
    };

    if (currentAdminTab === 'users') {
        html = `
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Имя</label>
                <input type="text" name="name" value="${safe.name}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" required>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Телефон</label>
                <input type="text" name="phone" value="${safe.phone}" placeholder="79991234567" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" required>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Баланс баллов</label>
                <div class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm text-stone-700">
                    ${safe.balance}
                </div>
                <div class="text-[10px] text-stone-400 mt-2 px-1">Баланс изменяется через «Добавить транзакцию»</div>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Уровень</label>
                <select name="level" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">
                    <option value="new" ${safe.level === 'new' ? 'selected' : ''}>New</option>
                    <option value="regular" ${safe.level === 'regular' ? 'selected' : ''}>Regular</option>
                    <option value="vip" ${safe.level === 'vip' ? 'selected' : ''}>VIP</option>
                </select>
            </div>
            <div class="flex items-center gap-2 px-1">
                <input type="checkbox" name="active" ${item.active !== false ? 'checked' : ''} class="w-4 h-4 rounded">
                <label class="text-sm font-semibold text-stone-600">Активен</label>
            </div>
        `;
    } else if (currentAdminTab === 'masters') {
        html = `
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Имя мастера</label>
                <input type="text" name="name" value="${safe.name}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" required>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Специализация</label>
                <input type="text" name="specialization" value="${safe.specialization}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Фото мастера</label>
                <input type="file" accept="image/*" id="master-photo-input" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">
                <input type="hidden" name="photo_url" id="master-photo-url" value="${escapeAttr(safe.photoUrl)}">
                ${safe.photoUrl ? `<div class="mt-2"><img src="${escapeAttr(safe.photoUrl)}" class="w-20 h-20 object-cover rounded-lg" id="master-photo-preview" alt=""></div>` : ''}
                <div id="master-photo-upload-status" class="mt-2 text-xs text-stone-500 hidden"></div>
            </div>
        `;
    } else if (currentAdminTab === 'services') {
        html = `
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Название услуги</label>
                <input type="text" name="title" value="${safe.title}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" required>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Цена (₽)</label>
                <input type="number" name="price" value="${safe.price}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" required>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Категория</label>
                <input type="text" name="category" value="${safe.category}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Описание</label>
                <textarea name="description" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm h-24">${safe.description}</textarea>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Изображение услуги</label>
                <input type="file" accept="image/*" id="service-image-input" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">
                <input type="hidden" name="image_url" id="service-image-url" value="${escapeAttr(safe.imageUrl)}">
                ${safe.imageUrl ? `<div class="mt-2"><img src="${escapeAttr(safe.imageUrl)}" class="w-32 h-32 object-cover rounded-lg" id="service-image-preview" alt=""></div>` : ''}
                <div id="service-image-upload-status" class="mt-2 text-xs text-stone-500 hidden"></div>
            </div>
            <div class="flex items-center gap-2 px-1">
                <input type="checkbox" name="is_active" ${safe.isActive ? 'checked' : ''} class="w-4 h-4 rounded">
                <label class="text-sm font-semibold text-stone-600">Активна</label>
            </div>
        `;
    } else if (currentAdminTab === 'promotions') {
        html = `
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Заголовок акции</label>
                <input type="text" name="title" value="${safe.title}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" required>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Краткое описание</label>
                <textarea name="description" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm h-24" placeholder="Краткое описание для карточки акции">${safe.description}</textarea>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Детальное описание</label>
                <textarea name="detail_text" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm h-32" placeholder="Полное описание акции, которое будет показано при нажатии 'Узнать больше'">${safe.detailText}</textarea>
                <p class="text-xs text-stone-400 mt-1 px-1">Поддерживается перенос строк. Будет отображено в модальном окне</p>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Условия акции</label>
                <textarea name="conditions" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm h-24" placeholder="Условия участия в акции (необязательно)">${safe.conditions}</textarea>
                <p class="text-xs text-stone-400 mt-1 px-1">Условия будут отображены в отдельном блоке</p>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Изображение акции</label>
                <input type="file" accept="image/*" id="promotion-image-input" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">
                <input type="hidden" name="image_url" id="promotion-image-url" value="${escapeAttr(safe.imageUrl)}">
                ${safe.imageUrl ? `<div class="mt-2"><img src="${escapeAttr(safe.imageUrl)}" class="w-32 h-32 object-cover rounded-lg" id="promotion-image-preview" alt=""></div>` : ''}
                <div id="promotion-image-upload-status" class="mt-2 text-xs text-stone-500 hidden"></div>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Дата окончания (гггг-мм-дд)</label>
                <input type="date" name="end_date" value="${safe.endDate}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">URL кнопки действия (необязательно)</label>
                <input type="text" name="action_url" value="${safe.actionUrl}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" placeholder="https://example.com или оставьте пустым для записи">
                <p class="text-xs text-stone-400 mt-1 px-1">Если не указано, будет использована ссылка на запись</p>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Текст кнопки действия</label>
                <input type="text" name="action_text" value="${safe.actionText}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" placeholder="Записаться">
                <p class="text-xs text-stone-400 mt-1 px-1">Текст на кнопке в детальном просмотре (по умолчанию "Записаться")</p>
            </div>
            <div class="flex items-center gap-2 px-1">
                <input type="checkbox" name="is_active" ${safe.isActive ? 'checked' : ''} class="w-4 h-4 rounded">
                <label class="text-sm font-semibold text-stone-600">Активна</label>
            </div>
        `;
    } else if (currentAdminTab === 'broadcasts') {
        // Форматируем scheduled_at для datetime-local (если есть)
        // scheduled_at хранится в UTC, нужно конвертировать в локальное время для datetime-local
        let scheduledAtValue = '';
        if (item.scheduled_at) {
            const date = new Date(item.scheduled_at); // Date автоматически конвертирует UTC в локальное время
            // Используем локальные методы для получения времени в локальном часовом поясе
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            const hours = String(date.getHours()).padStart(2, '0'); // getHours() уже возвращает локальное время
            const minutes = String(date.getMinutes()).padStart(2, '0');
            scheduledAtValue = `${year}-${month}-${day}T${hours}:${minutes}`;
        }
        
        html = `
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Текст сообщения</label>
                <textarea name="message" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm h-32" required>${safe.message}</textarea>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Изображение</label>
                <input type="file" accept="image/*" id="broadcast-image-input" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">
                <input type="hidden" name="image_url" id="broadcast-image-url" value="${escapeAttr(safe.imageUrl)}">
                ${safe.imageUrl ? `<div class="mt-2"><img src="${escapeAttr(safe.imageUrl)}" class="w-32 h-32 object-cover rounded-lg" id="broadcast-image-preview" alt=""></div>` : ''}
                <div id="broadcast-image-upload-status" class="mt-2 text-xs text-stone-500 hidden"></div>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Получатели</label>
                <select name="recipient_type" id="broadcast-recipient-type" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" required>
                    <option value="all" ${safe.recipientType === 'all' ? 'selected' : ''}>Все пользователи</option>
                    <option value="selected" ${safe.recipientType === 'selected' ? 'selected' : ''}>Выбранные пользователи</option>
                    <option value="by_balance" ${safe.recipientType === 'by_balance' ? 'selected' : ''}>По балансу баллов</option>
                </select>
            </div>
            <div id="selected-users-container" class="hidden">
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Выберите пользователей</label>
                <div id="users-list" class="max-h-48 overflow-y-auto border border-stone-100 rounded-xl p-3 bg-stone-50">
                    <div class="text-sm text-stone-500">Загрузка пользователей...</div>
                </div>
                <input type="hidden" name="recipient_ids" id="broadcast-recipient-ids" value="${safe.recipientIds}">
            </div>
            <div id="balance-filter" class="hidden">
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Минимальный баланс</label>
                <input type="number" name="filter_balance_min" value="${safe.filterBalanceMin}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" placeholder="Не указано">
            </div>
            <div id="balance-filter-max" class="hidden">
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Максимальный баланс</label>
                <input type="number" name="filter_balance_max" value="${safe.filterBalanceMax}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" placeholder="Не указано">
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Запланировать отправку (необязательно)</label>
                <input type="datetime-local" name="scheduled_at" value="${escapeAttr(scheduledAtValue)}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">
                <p class="text-xs text-stone-400 mt-1 px-1">Оставьте пустым для немедленной отправки</p>
            </div>
        `;
    } else if (currentAdminTab === 'bot-buttons') {
        html = `
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Текст кнопки</label>
                <input type="text" name="button_text" value="${safe.buttonText}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" required>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Текст ответа</label>
                <textarea name="response_text" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm h-32" required>${safe.responseText}</textarea>
                <p class="text-xs text-stone-400 mt-1 px-1">Поддерживается Markdown. Можно использовать {YCLIENTS_BOOKING_URL}, {LOYALTY_PERCENTAGE}, {LOYALTY_MAX_SPEND_PERCENTAGE}, {LOYALTY_EXPIRATION_DAYS}</p>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Тип обработчика</label>
                <select name="handler_type" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">
                    <option value="book" ${safe.handlerType === 'book' ? 'selected' : ''}>Запись</option>
                    <option value="info" ${safe.handlerType === 'info' ? 'selected' : ''}>Информация</option>
                    <option value="profile" ${safe.handlerType === 'profile' ? 'selected' : ''}>Профиль</option>
                    <option value="admin" ${safe.handlerType === 'admin' ? 'selected' : ''}>Админка</option>
                </select>
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Номер строки</label>
                    <input type="number" name="row_number" value="${safe.rowNumber}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" min="1" required>
                </div>
                <div>
                    <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Порядок в строке</label>
                    <input type="number" name="order_in_row" value="${safe.orderInRow}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" min="0" required>
                </div>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">WebApp URL (необязательно)</label>
                <input type="text" name="web_app_url" value="${safe.webAppUrl}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" placeholder="https://example.com/webapp">
            </div>
            <div class="flex items-center gap-2 px-1">
                <input type="checkbox" name="is_admin_only" ${safe.isAdminOnly ? 'checked' : ''} class="w-4 h-4 rounded">
                <label class="text-sm font-semibold text-stone-600">Только для админов</label>
            </div>
            <div class="flex items-center gap-2 px-1">
                <input type="checkbox" name="is_active" ${safe.isActive ? 'checked' : ''} class="w-4 h-4 rounded">
                <label class="text-sm font-semibold text-stone-600">Активна</label>
            </div>
        `;
    }
    
    fieldsEl.innerHTML = html;
    
    // Добавляем обработчики для загрузки файлов
    setupImageUploadHandlers();
    
    // Показываем/скрываем фильтры по балансу и выбор пользователей
    if (currentAdminTab === 'broadcasts') {
        const recipientType = document.getElementById('broadcast-recipient-type');
        const balanceFilter = document.getElementById('balance-filter');
        const balanceFilterMax = document.getElementById('balance-filter-max');
        const selectedUsersContainer = document.getElementById('selected-users-container');
        
        const toggleFilters = async () => {
            if (recipientType.value === 'by_balance') {
                balanceFilter.classList.remove('hidden');
                balanceFilterMax.classList.remove('hidden');
                selectedUsersContainer.classList.add('hidden');
            } else if (recipientType.value === 'selected') {
                balanceFilter.classList.add('hidden');
                balanceFilterMax.classList.add('hidden');
                selectedUsersContainer.classList.remove('hidden');
                await loadUsersForSelection(item.recipient_ids || []);
            } else {
                balanceFilter.classList.add('hidden');
                balanceFilterMax.classList.add('hidden');
                selectedUsersContainer.classList.add('hidden');
            }
        };
        
        recipientType.addEventListener('change', toggleFilters);
        toggleFilters();
        
        // Обработчик загрузки изображения для рассылок
        const broadcastImageInput = document.getElementById('broadcast-image-input');
        if (broadcastImageInput) {
            broadcastImageInput.addEventListener('change', async (e) => {
                await handleImageUpload(e.target.files[0], 'broadcast-image');
            });
        }
    }
}

// Функция для обработки загрузки изображений
function setupImageUploadHandlers() {
    // Обработчик для фото мастера
    const masterPhotoInput = document.getElementById('master-photo-input');
    if (masterPhotoInput) {
        masterPhotoInput.addEventListener('change', async (e) => {
            await handleImageUpload(e.target.files[0], 'master-photo');
        });
    }
    
    // Обработчик для изображения услуги
    const serviceImageInput = document.getElementById('service-image-input');
    if (serviceImageInput) {
        serviceImageInput.addEventListener('change', async (e) => {
            await handleImageUpload(e.target.files[0], 'service-image');
        });
    }
    
    // Обработчик для изображения акции
    const promotionImageInput = document.getElementById('promotion-image-input');
    if (promotionImageInput) {
        promotionImageInput.addEventListener('change', async (e) => {
            await handleImageUpload(e.target.files[0], 'promotion-image');
        });
    }
}

async function loadUsersForSelection(selectedIds = []) {
    const usersListEl = document.getElementById('users-list');
    if (!usersListEl) return;
    
    try {
        const users = await apiFetch('/api/admin/users');
        const selectedSet = new Set(selectedIds.map((id) => String(id)));
        
        usersListEl.innerHTML = users.map(user => {
            const safeId = escapeAttr(user.id);
            const name = escapeHtml(user.name || 'Без имени');
            const phone = escapeHtml(user.phone || '');
            const balance = safeNumber(user.balance, 0);
            const isChecked = selectedSet.has(String(user.id)) ? 'checked' : '';
            return `
            <label class="flex items-center gap-3 p-2 rounded-lg hover:bg-stone-100 cursor-pointer">
                <input type="checkbox" value="${safeId}" ${isChecked} 
                       class="w-4 h-4 rounded" onchange="updateBroadcastRecipients()">
                <div class="flex-1">
                    <div class="text-sm font-semibold text-stone-800">${name}</div>
                    <div class="text-xs text-stone-500">${phone}</div>
                </div>
                <div class="text-xs text-stone-400">${balance} баллов</div>
            </label>
            `;
        }).join('');
    } catch (error) {
        console.error("Error loading users:", error);
        usersListEl.innerHTML = '<div class="text-sm text-rose-500">Ошибка загрузки пользователей</div>';
    }
}

function updateBroadcastRecipients() {
    const checkboxes = document.querySelectorAll('#users-list input[type="checkbox"]:checked');
    const selectedIds = Array.from(checkboxes).map(cb => {
        const value = cb.value;
        const num = Number(value);
        return Number.isFinite(num) ? num : value;
    });
    const hiddenInput = document.getElementById('broadcast-recipient-ids');
    if (hiddenInput) {
        hiddenInput.value = JSON.stringify(selectedIds);
    }
}

const IMAGE_MAX_DIMENSION = 2560;
const IMAGE_COMPRESS_THRESHOLD_MB = 3;
const IMAGE_COMPRESS_QUALITY = 0.86;
const IMAGE_UPLOAD_TARGET_BYTES = 5 * 1024 * 1024;

async function _loadImageFromFile(file) {
    return new Promise((resolve, reject) => {
        const img = new Image();
        const objectUrl = URL.createObjectURL(file);
        img.onload = () => {
            URL.revokeObjectURL(objectUrl);
            resolve(img);
        };
        img.onerror = () => {
            URL.revokeObjectURL(objectUrl);
            reject(new Error('Image load failed'));
        };
        img.src = objectUrl;
    });
}

async function compressImageFile(file, options = {}) {
    const {
        force = false,
        maxDimension = IMAGE_MAX_DIMENSION,
        quality = IMAGE_COMPRESS_QUALITY,
        thresholdMb = IMAGE_COMPRESS_THRESHOLD_MB
    } = options;
    const isImage = file?.type && file.type.startsWith('image/');
    if (!isImage || file.type === 'image/gif' || file.type === 'image/svg+xml') {
        return { file, compressed: false };
    }

    const sizeMb = file.size / (1024 * 1024);
    const shouldTryCompress = force || sizeMb >= thresholdMb;
    if (!shouldTryCompress) {
        return { file, compressed: false };
    }

    let source;
    try {
        if ('createImageBitmap' in window) {
            source = await createImageBitmap(file);
        } else {
            source = await _loadImageFromFile(file);
        }
    } catch (error) {
        return { file, compressed: false };
    }

    const width = source.width || source.naturalWidth;
    const height = source.height || source.naturalHeight;
    if (!width || !height) {
        if (source.close) source.close();
        return { file, compressed: false };
    }

    const scale = Math.min(1, maxDimension / Math.max(width, height));
    if (scale === 1 && !force && sizeMb < thresholdMb * 1.2) {
        if (source.close) source.close();
        return { file, compressed: false };
    }

    const targetWidth = Math.max(1, Math.round(width * scale));
    const targetHeight = Math.max(1, Math.round(height * scale));
    const canvas = document.createElement('canvas');
    canvas.width = targetWidth;
    canvas.height = targetHeight;
    const ctx = canvas.getContext('2d', { alpha: false });
    if (!ctx) {
        if (source.close) source.close();
        return { file, compressed: false };
    }
    ctx.drawImage(source, 0, 0, targetWidth, targetHeight);
    if (source.close) source.close();

    const outputType = 'image/jpeg';
    const blob = await new Promise(resolve => canvas.toBlob(resolve, outputType, quality));
    if (!blob) {
        return { file, compressed: false };
    }

    const shouldReplace = blob.size < file.size || scale < 1;
    if (!shouldReplace) {
        return { file, compressed: false };
    }

    const baseName = (file.name || 'image').replace(/\.[^/.]+$/, '') || 'image';
    const newFile = new File([blob], `${baseName}.jpg`, { type: outputType });
    return { file: newFile, compressed: true };
}

async function handleImageUpload(file, prefix) {
    if (!file) return;
    
    const statusEl = document.getElementById(`${prefix}-upload-status`);
    const urlInput = document.getElementById(`${prefix}-url`);
    const previewEl = document.getElementById(`${prefix}-preview`);

    // Показываем статус загрузки
    if (statusEl) {
        statusEl.classList.remove('hidden');
        statusEl.textContent = 'Загрузка...';
        statusEl.className = 'mt-2 text-xs text-stone-500';
    }
    
    try {
        const maxSizeMb = 50;
        if (statusEl) {
            statusEl.textContent = 'Подготовка изображения...';
            statusEl.className = 'mt-2 text-xs text-stone-500';
        }

        const { file: preparedFile, compressed } = await compressImageFile(file);
        let uploadFile = preparedFile || file;
        let recompressAttempts = 0;
        let recompressed = false;
        if (uploadFile.size > IMAGE_UPLOAD_TARGET_BYTES) {
            let maxDimension = IMAGE_MAX_DIMENSION;
            let quality = IMAGE_COMPRESS_QUALITY;
            let nextFile = uploadFile;
            while (recompressAttempts < 3 && nextFile.size > IMAGE_UPLOAD_TARGET_BYTES) {
                recompressAttempts += 1;
                maxDimension = Math.max(640, Math.round(maxDimension * 0.85));
                quality = Math.max(0.6, Math.round((quality - 0.1) * 100) / 100);
                const result = await compressImageFile(nextFile, {
                    force: true,
                    maxDimension,
                    quality,
                    thresholdMb: 0
                });
                if (!result?.file || result.file.size >= nextFile.size) {
                    break;
                }
                nextFile = result.file;
                recompressed = true;
            }
            uploadFile = nextFile;
        }
        if (compressed && statusEl) {
            statusEl.textContent = 'Сжатие завершено, загружаю...';
        }
        const sizeLimitBytes = Math.min(maxSizeMb * 1024 * 1024, IMAGE_UPLOAD_TARGET_BYTES);
        if (uploadFile.size > sizeLimitBytes) {
            const limitMb = Math.round((sizeLimitBytes / 1024 / 1024) * 10) / 10;
            throw new Error(`Файл больше ${limitMb} МБ. Уменьшите изображение.`);
        }

        // Создаем FormData для отправки файла
        const formData = new FormData();
        formData.append('file', uploadFile);
        
        // Определяем папку в зависимости от типа
        let folder = 'images';
        if (prefix === 'master-photo') folder = 'masters';
        else if (prefix === 'service-image') folder = 'services';
        else if (prefix === 'promotion-image') folder = 'promotions';
        else if (prefix === 'broadcast-image') folder = 'broadcasts';
        
        formData.append('folder', folder);
        // Отправляем файл на сервер
        const response = await fetch(`${window.location.origin}/api/admin/upload`, {
            method: 'POST',
            headers: {
                'X-Tg-Init-Data': tg.initData || ''
            },
            body: formData
        });
        
        if (!response.ok) {
            let errorDetail = `Ошибка загрузки (${response.status})`;
            if (response.status === 413) {
                errorDetail = 'Файл слишком большой для сервера. Увеличьте лимит загрузки на сервере (client_max_body_size) или уменьшите изображение.';
            }
            try {
                const rawText = await response.text();
                if (rawText) {
                    try {
                        const payload = JSON.parse(rawText);
                        if (payload?.detail) {
                            errorDetail = payload.detail;
                        }
                    } catch (err) {
                        errorDetail = `${errorDetail}: ${rawText.slice(0, 160)}`;
                    }
                }
            } catch (err) {
                // ignore json parse errors
            }
            throw new Error(errorDetail);
        }
        
        const result = await response.json();
        
        // Сохраняем URL в скрытом поле
        if (urlInput) {
            urlInput.value = result.url;
        }
        
        // Показываем превью
        if (previewEl) {
            previewEl.src = result.url;
            previewEl.classList.remove('hidden');
        } else {
            // Создаем элемент превью, если его нет
            const parent = statusEl?.parentElement;
            if (parent && !previewEl) {
                const img = document.createElement('img');
                img.id = `${prefix}-preview`;
                img.src = result.url;
                img.className = prefix === 'master-photo' ? 'mt-2 w-20 h-20 object-cover rounded-lg' : 'mt-2 w-32 h-32 object-cover rounded-lg';
                parent.insertBefore(img, statusEl);
            }
        }
        
        // Показываем успешный статус
        if (statusEl) {
            statusEl.textContent = '✓ Изображение загружено';
            statusEl.className = 'mt-2 text-xs text-green-600';
        }
        
        if (tg.HapticFeedback) {
            tg.HapticFeedback.notificationOccurred('success');
        }
        
    } catch (error) {
        console.error('Image upload error:', error);
        if (statusEl) {
            const message = error?.message && error.message !== 'Upload failed'
                ? error.message
                : 'Ошибка загрузки';
            statusEl.textContent = `✗ ${message}`;
            statusEl.className = 'mt-2 text-xs text-red-600';
        }
        if (tg.HapticFeedback) {
            tg.HapticFeedback.notificationOccurred('error');
        }
    }
}

function closeAdminModal() {
    const modal = document.getElementById('admin-modal');
    const container = document.getElementById('modal-container');
    const form = document.getElementById('admin-form');
    
    // Восстанавливаем стандартный обработчик submit
    form.onsubmit = handleAdminSubmit;
    
    container.style.transform = 'translateY(100%)';
    setTimeout(() => {
        modal.classList.add('hidden');
        // Reset transform for next open
        container.style.transform = '';
    }, 300);
}

async function openPromotionDetail(promotionId) {
    const modal = document.getElementById('promotion-detail-modal');
    const container = document.getElementById('promotion-detail-container');
    const content = document.getElementById('promotion-detail-content');
    
    if (!modal || !container || !content) return;
    
    try {
        // Загружаем данные акции
        const contentData = await apiFetch('/api/app/content');
        const promotion = contentData.promotions?.find(p => p.id === promotionId);
        
        if (!promotion) {
            alert('Акция не найдена');
            return;
        }
        
        // Форматируем дату окончания
        let endDateText = '';
        if (promotion.end_date) {
            const date = new Date(promotion.end_date);
            endDateText = new Intl.DateTimeFormat('ru-RU', {
                day: '2-digit',
                month: 'long',
                year: 'numeric'
            }).format(date);
        }
        
        // Определяем текст и URL кнопки действия
        const actionText = promotion.action_text || 'Записаться';
        const actionUrl = safeUrl(promotion.action_url) || safeUrl(contentData.booking_url) || safeUrl(bookingUrl) || '#';
        const imageUrl = safeUrl(promotion.image_url);
        
        // Формируем HTML контента с экранированием
        content.innerHTML = `
            ${imageUrl ? `
                <div class="mb-6 -mx-6 -mt-6">
                    <img src="${escapeAttr(imageUrl)}" class="w-full h-48 object-cover" alt="${escapeHtml(promotion.title)}">
                </div>
            ` : ''}
            
            <div class="mb-6">
                <h2 class="font-serif text-2xl font-bold text-stone-800 mb-3">${escapeHtml(promotion.title)}</h2>
                ${promotion.description ? `
                    <p class="text-stone-600 text-sm leading-relaxed mb-4">${escapeHtml(promotion.description)}</p>
                ` : ''}
            </div>
            
            ${promotion.detail_text ? `
                <div class="mb-6">
                    <h3 class="font-semibold text-stone-800 mb-2">Подробности</h3>
                    <div class="text-stone-600 text-sm leading-relaxed whitespace-pre-line">${escapeHtml(promotion.detail_text)}</div>
                </div>
            ` : ''}
            
            ${promotion.conditions ? `
                <div class="mb-6 p-4 bg-stone-50 rounded-xl border border-stone-100">
                    <h3 class="font-semibold text-stone-800 mb-2">Условия акции</h3>
                    <div class="text-stone-600 text-sm leading-relaxed whitespace-pre-line">${escapeHtml(promotion.conditions)}</div>
                </div>
            ` : ''}
            
            ${endDateText ? `
                <div class="mb-6 text-sm text-stone-500">
                    <span class="font-semibold">Срок действия:</span> до ${escapeHtml(endDateText)}
                </div>
            ` : ''}
            
            <div class="pt-4">
                <button onclick="window.open('${escapeAttr(actionUrl)}', '_blank'); closePromotionDetail();" 
                        class="w-full bg-stone-800 text-white py-4 rounded-[20px] font-bold shadow-card active:scale-[0.98] transition-all flex items-center justify-center gap-2">
                    <span>${escapeHtml(actionText)}</span>
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                    </svg>
                </button>
            </div>
        `;
        
        // Показываем модальное окно
        modal.classList.remove('hidden');
        container.style.transform = 'translateY(100%)';
        container.offsetHeight; // Force reflow
        
        setTimeout(() => {
            container.style.transition = 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
            container.style.transform = 'translateY(0)';
        }, 10);
        
        tg.HapticFeedback.impactOccurred('light');
    } catch (error) {
        console.error("Error loading promotion detail:", error);
        alert("Ошибка при загрузке информации об акции");
    }
}

function closePromotionDetail() {
    const modal = document.getElementById('promotion-detail-modal');
    const container = document.getElementById('promotion-detail-container');
    
    if (!modal || !container) return;
    
    container.style.transform = 'translateY(100%)';
    setTimeout(() => {
        modal.classList.add('hidden');
        container.style.transform = '';
    }, 300);
    
    tg.HapticFeedback.impactOccurred('light');
}

async function openSettingModal(key) {
    const modal = document.getElementById('admin-modal');
    const container = document.getElementById('modal-container');
    const title = document.getElementById('modal-title');
    const form = document.getElementById('admin-form');
    const fields = document.getElementById('form-fields');
    const deleteBtn = document.getElementById('delete-btn');
    const formId = document.getElementById('form-id');
    const decodedKey = decodeId(key);
    
    const setting = adminItems.find(s => String(s.key) === String(decodedKey));
    if (!setting) return;
    
    form.reset();
    formId.value = decodedKey;
    title.innerText = 'Настройка';
    deleteBtn.classList.add('hidden');
    
    // Переопределяем submit для настроек
    form.onsubmit = async (e) => {
        e.preventDefault();
        await handleSettingSubmit(e, decodedKey);
    };
    
    let inputHtml = '';
    if (setting.type === 'number' || setting.type === 'float') {
        const displayValue = PERCENT_SETTING_KEYS.has(setting.key)
            ? normalizePercentValue(setting.value)
            : setting.value;
        const step = PERCENT_SETTING_KEYS.has(setting.key) ? '0.1' : (setting.type === 'float' ? '0.01' : '1');
        inputHtml = `<input type="number" name="value" value="${escapeAttr(displayValue)}" step="${step}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" required>`;
    } else if (setting.type === 'boolean') {
        inputHtml = `
            <select name="value" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">
                <option value="true" ${setting.value === true || setting.value === 'true' ? 'selected' : ''}>Да</option>
                <option value="false" ${setting.value === false || setting.value === 'false' ? 'selected' : ''}>Нет</option>
            </select>
        `;
    } else {
        inputHtml = `<input type="text" name="value" value="${escapeAttr(setting.value)}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" required>`;
    }

    fields.innerHTML = `
        <div>
            <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">${escapeHtml(setting.description || decodedKey)}</label>
            ${inputHtml}
            <p class="text-[10px] text-stone-400 mt-2 px-1">Ключ: ${escapeHtml(decodedKey)} | Тип: ${escapeHtml(setting.type)}</p>
        </div>
    `;
    
    modal.classList.remove('hidden');
    container.style.transform = 'translateY(100%)';
    container.offsetHeight;
    
    setTimeout(() => {
        container.style.transition = 'transform 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
        container.style.transform = 'translateY(0)';
    }, 10);
}

async function handleSettingSubmit(e, key) {
    const form = e.target;
    const formData = new FormData(form);
    const setting = adminItems.find(s => s.key === key);
    
    let value = formData.get('value');
    if (setting.type === 'number') value = parseInt(value);
    else if (setting.type === 'float') value = parseFloat(value);
    else if (setting.type === 'boolean') value = value === 'true';

    if (PERCENT_SETTING_KEYS.has(key)) {
        const numeric = safeNumber(value, 0);
        value = numeric > 1 ? numeric / 100 : numeric;
    }
    
    try {
        const response = await fetch(`${window.location.origin}/api/settings/${key}`, {
            method: 'PUT',
            headers: {
                'X-Tg-Init-Data': tg.initData || '',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ value })
        });
        
        if (!response.ok) throw new Error('Save error');
        
        tg.HapticFeedback.notificationOccurred('success');
        closeAdminModal();
        loadAdminData();
    } catch (error) {
        console.error("Save error:", error);
        alert("Ошибка при сохранении настройки");
    }
}

async function handleAdminSubmit(e) {
    e.preventDefault();
    const form = e.target;
    const id = document.getElementById('form-id').value;
    const formData = new FormData(form);
    const data = {};
    
    // Если это форма пользователя
    if (currentAdminTab === 'users' && id) {
        formData.forEach((value, key) => {
            if (key === 'active') {
                // Пропускаем, обработаем отдельно
            } else if (value) {
                data[key] = value;
            }
        });
        
        // Обрабатываем чекбокс active
        const activeCheckbox = form.querySelector('[name="active"]');
        if (activeCheckbox) {
            data.active = activeCheckbox.checked;
        }
        
        try {
            const response = await fetch(`${window.location.origin}/api/admin/users/${id}`, {
                method: 'PUT',
                headers: {
                    'X-Tg-Init-Data': tg.initData || '',
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            
            if (!response.ok) {
                let detail = 'Ошибка при сохранении';
                try {
                    const body = await response.json();
                    if (body && body.detail) detail = body.detail;
                } catch (e) {}
                throw new Error(detail);
            }
            
            tg.HapticFeedback.notificationOccurred('success');
            closeAdminModal();
            loadAdminData();
            return;
        } catch (error) {
            console.error("Save error:", error);
            alert(friendlyErrorMessage(error, "Ошибка при сохранении"));
            return;
        }
    }
    
    // Обычная обработка для других вкладок
    formData.forEach((value, key) => {
        if (key === 'is_active') {
            // Пропускаем, обработаем отдельно
        } else if (value) {
            data[key] = value;
        }
    });
    
    // Специальная обработка чекбоксов
    if (currentAdminTab === 'services' || currentAdminTab === 'promotions') {
        data.is_active = form.querySelector('[name="is_active"]').checked;
    }
    
    // Обработка для promotions - детальная информация
    if (currentAdminTab === 'promotions') {
        // Обрабатываем action_url - если пусто, то null
        const actionUrl = formData.get('action_url');
        data.action_url = actionUrl && actionUrl.trim() ? actionUrl.trim() : null;
        
        // Обрабатываем action_text - если пусто, то дефолтное значение
        const actionText = formData.get('action_text');
        data.action_text = actionText && actionText.trim() ? actionText.trim() : 'Записаться';
        
        // Обрабатываем detail_text и conditions - могут быть пустыми
        const detailText = formData.get('detail_text');
        data.detail_text = detailText ? detailText.trim() : null;
        
        const conditions = formData.get('conditions');
        data.conditions = conditions ? conditions.trim() : null;
    }
    
    // Обработка для кнопок бота
    if (currentAdminTab === 'bot-buttons') {
        data.is_active = form.querySelector('[name="is_active"]').checked;
        data.is_admin_only = form.querySelector('[name="is_admin_only"]').checked;
        // Преобразуем числовые поля
        if (formData.get('row_number')) {
            data.row_number = parseInt(formData.get('row_number'));
        }
        if (formData.get('order_in_row')) {
            data.order_in_row = parseInt(formData.get('order_in_row'));
        }
        // Обрабатываем web_app_url - если пусто, то null
        const webAppUrl = formData.get('web_app_url');
        data.web_app_url = webAppUrl && webAppUrl.trim() ? webAppUrl.trim() : null;
    }
    
    // Специальная обработка для рассылок
    if (currentAdminTab === 'broadcasts') {
        data.message = formData.get('message');
        data.recipient_type = formData.get('recipient_type');
        data.image_url = formData.get('image_url') || null;
        
        // Обработка scheduled_at
        const scheduledAt = formData.get('scheduled_at');
        if (scheduledAt) {
            // datetime-local возвращает время в локальном часовом поясе без указания TZ
            // Нужно создать Date объект, который интерпретирует это как локальное время
            // и затем конвертировать в ISO (UTC)
            const date = new Date(scheduledAt);
            data.scheduled_at = date.toISOString();
        } else {
            data.scheduled_at = null;
        }
        
        // Обработка recipient_ids для выбранных пользователей
        if (data.recipient_type === 'selected') {
            const recipientIdsInput = document.getElementById('broadcast-recipient-ids');
            if (recipientIdsInput && recipientIdsInput.value) {
                try {
                    data.recipient_ids = JSON.parse(recipientIdsInput.value);
                } catch (e) {
                    data.recipient_ids = [];
                }
            } else {
                data.recipient_ids = [];
            }
        } else {
            data.recipient_ids = [];
        }

        if (data.recipient_type === 'by_balance') {
            const min = formData.get('filter_balance_min');
            const max = formData.get('filter_balance_max');
            if (min) data.filter_balance_min = parseInt(min);
            if (max) data.filter_balance_max = parseInt(max);
        }
        
        try {
            const response = await fetch(`${window.location.origin}/api/admin/broadcasts`, {
                method: 'POST',
                headers: {
                    'X-Tg-Init-Data': tg.initData || '',
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
            
            if (!response.ok) throw new Error('Broadcast creation error');
            
            tg.HapticFeedback.notificationOccurred('success');
            closeAdminModal();
            loadAdminData();
            return;
        } catch (error) {
            console.error("Broadcast error:", error);
            alert("Ошибка при создании рассылки");
            return;
        }
    }
    
    try {
        const method = id ? 'PUT' : 'POST';
        const url = id ? `/api/admin/${currentAdminTab}/${id}` : `/api/admin/${currentAdminTab}`;
        
        const response = await fetch(window.location.origin + url, {
            method,
            headers: {
                'X-Tg-Init-Data': tg.initData || '',
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        if (!response.ok) throw new Error('Save error');
        
        tg.HapticFeedback.notificationOccurred('success');
        closeAdminModal();
        loadAdminData();
        
        // Refresh main content too
        loadContent();
    } catch (error) {
        console.error("Save error:", error);
        alert("Ошибка при сохранении");
    }
}

async function sendBroadcast(id) {
    const decodedId = decodeId(id);
    if (!confirm('Отправить рассылку? Это действие нельзя отменить.')) {
        return;
    }
    
    try {
        const response = await fetch(`${window.location.origin}/api/admin/broadcasts/${decodedId}/send`, {
            method: 'POST',
            headers: {
                'X-Tg-Init-Data': tg.initData || '',
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) throw new Error('Send error');
        
        tg.HapticFeedback.notificationOccurred('success');
        alert('Рассылка запущена! Статус будет обновляться автоматически.');
        loadAdminData();
    } catch (error) {
        console.error("Send broadcast error:", error);
        alert("Ошибка при отправке рассылки");
    }
}

async function viewBroadcast(id) {
    try {
        const decodedId = decodeId(id);
        const response = await fetch(`${window.location.origin}/api/admin/broadcasts/${decodedId}?_t=${Date.now()}`, {
            headers: {
                'X-Tg-Init-Data': tg.initData || ''
            }
        });
        
        if (!response.ok) throw new Error('Failed to fetch broadcast');
        
        const broadcast = await response.json();
        
        // Форматируем даты с явным указанием московского времени
        const createdDate = new Intl.DateTimeFormat('ru-RU', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            timeZone: 'Europe/Moscow'
        }).format(new Date(broadcast.created_at));
        
        const scheduledDate = broadcast.scheduled_at ? new Intl.DateTimeFormat('ru-RU', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            timeZone: 'Europe/Moscow'
        }).format(new Date(broadcast.scheduled_at)) : null;
        
        // Определяем тип получателей
        let recipientInfo = '';
        if (broadcast.recipient_type === 'all') {
            recipientInfo = 'Все пользователи';
        } else if (broadcast.recipient_type === 'selected') {
            recipientInfo = `Выбранные пользователи (${broadcast.recipient_ids?.length || 0})`;
        } else if (broadcast.recipient_type === 'by_balance') {
            recipientInfo = `По балансу: ${broadcast.filter_balance_min || 0} - ${broadcast.filter_balance_max || '∞'} баллов`;
        } else if (broadcast.recipient_type === 'by_date') {
            recipientInfo = 'По дате регистрации';
        }
        
        // Создаем модальное окно с деталями
        const modal = document.getElementById('admin-modal');
        const container = document.getElementById('modal-container');
        const fieldsEl = document.getElementById('form-fields');
        const titleEl = document.getElementById('modal-title');
        if (!modal || !container || !fieldsEl || !titleEl) return;

        const message = escapeHtml(broadcast.message || broadcast.content || broadcast.title || '');
        const imageUrl = safeUrl(broadcast.image_url);
        const safeRecipientInfo = escapeHtml(recipientInfo);
        const safeStatus = escapeHtml(broadcast.status || '');
        const safeCreatedDate = escapeHtml(createdDate);
        const safeScheduledDate = scheduledDate ? escapeHtml(scheduledDate) : '';
        const sentCount = safeNumber(broadcast.sent_count, 0);
        const failedCount = safeNumber(broadcast.failed_count, 0);

        titleEl.textContent = 'Детали рассылки';
        fieldsEl.innerHTML = `
            <div class="space-y-4">
                <div>
                    <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Текст сообщения</label>
                    <div class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm whitespace-pre-wrap">${message}</div>
                </div>
                ${imageUrl ? `
                    <div>
                        <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Изображение</label>
                        <img src="${escapeAttr(imageUrl)}" class="w-full max-w-md rounded-xl object-cover bg-stone-100 shadow-sm" alt="">
                    </div>
                ` : ''}
                <div>
                    <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Получатели</label>
                    <div class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">${safeRecipientInfo}</div>
                </div>
                <div>
                    <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Статус</label>
                    <div class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">${safeStatus}</div>
                </div>
                <div>
                    <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Создана</label>
                    <div class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">${safeCreatedDate}</div>
                </div>
                ${scheduledDate ? `
                    <div>
                        <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Запланирована на</label>
                        <div class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">${safeScheduledDate}</div>
                    </div>
                ` : ''}
                ${sentCount > 0 || failedCount > 0 ? `
                    <div>
                        <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Статистика</label>
                        <div class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">
                            Отправлено: ${sentCount}<br>
                            Ошибок: ${failedCount}
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
        
        // Скрываем форму и показываем только кнопку закрытия
        const form = document.getElementById('admin-form');
        form.onsubmit = (e) => {
            e.preventDefault();
            closeAdminModal();
        };
        
        // Показываем модальное окно
        modal.classList.remove('hidden');
        setTimeout(() => {
            container.style.transform = 'translateY(0)';
        }, 10);
        
    } catch (error) {
        console.error("View broadcast error:", error);
        alert("Ошибка при загрузке деталей рассылки");
    }
}

async function deleteBroadcast(id) {
    const decodedId = decodeId(id);
    if (!confirm('Удалить эту рассылку? Это действие нельзя отменить.')) {
        return;
    }
    
    try {
        const response = await fetch(`${window.location.origin}/api/admin/broadcasts/${decodedId}`, {
            method: 'DELETE',
            headers: {
                'X-Tg-Init-Data': tg.initData || ''
            }
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || 'Delete error');
        }
        
        tg.HapticFeedback.notificationOccurred('success');
        loadAdminData();
    } catch (error) {
        console.error("Delete broadcast error:", error);
        alert(`Ошибка при удалении рассылки: ${friendlyErrorMessage(error, 'Не удалось удалить.')}`);
    }
}

async function handleAdminDelete() {
    const id = document.getElementById('form-id').value;
    if (!id || !confirm("Удалить этот элемент?")) return;
    
    try {
        const response = await fetch(`${window.location.origin}/api/admin/${currentAdminTab}/${id}`, {
            method: 'DELETE',
            headers: { 'X-Tg-Init-Data': tg.initData || '' }
        });
        
        if (!response.ok) throw new Error('Delete error');
        
        tg.HapticFeedback.notificationOccurred('warning');
        closeAdminModal();
        loadAdminData();
        loadContent();
    } catch (error) {
        console.error("Delete error:", error);
        alert("Ошибка при удалении");
    }
}

async function moveItem(id, direction) {
    
    
    if (currentAdminTab === 'users' || currentAdminTab === 'bot-buttons') return; // Пользователи и кнопки бота не перемещаются через эту функцию
    
    const decodedId = decodeId(id);
    const url = `${window.location.origin}/api/admin/${currentAdminTab}/${decodedId}/move?direction=${direction}`;
    
    
    
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'X-Tg-Init-Data': tg.initData || '' }
        });
        
        
        
        if (!response.ok) {
            const errorText = await response.text();
            
            throw new Error(`Move error: ${response.status} ${errorText}`);
        }
        
        const result = await response.json();
        
        
        tg.HapticFeedback.impactOccurred('light');
        
        loadAdminData();
        loadContent(); // Обновляем основной контент тоже
    } catch (error) {
        
        console.error("Move error:", error);
        alert("Ошибка при перемещении");
    }
}
