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
            console.log("[DEBUG] User avatar loaded from Telegram");
        } else {
            // Если фото нет - убираем аватарку совсем (скрываем кнопку)
            avatarBtn.style.display = 'none';
            console.log("[DEBUG] No user avatar available, hiding avatar button");
        }
    } catch (error) {
        console.warn("[DEBUG] Error loading avatar:", error);
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
    // #region agent log
    fetch('http://127.0.0.1:7245/ingest/1a99addc-056e-429d-b318-75f0bb966d8b',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'script.js:172',message:'hideLoader entry',data:{hasLoader:!!loader,hasMainContent:!!mainContent},timestamp:Date.now(),sessionId:'debug-loader',hypothesisId:'D'})}).catch(()=>{});
    // #endregion
    console.log("[DEBUG] Hiding loader");
    
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

// #region agent log
fetch('http://127.0.0.1:7245/ingest/1a99addc-056e-429d-b318-75f0bb966d8b',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'script.js:192',message:'window.onload entry',data:{hasTg:!!tg,hasLoader:!!loader,hasMainContent:!!mainContent},timestamp:Date.now(),sessionId:'debug-loader',hypothesisId:'A'})}).catch(()=>{});
// #endregion
window.onload = async () => {
    console.log("[DEBUG] Window onload started");
    
    // Засекаем время начала загрузки для гарантированного минимума
    const loadStartTime = Date.now();
    const MIN_LOADER_TIME = 2000; // Минимум 2 секунды для анимации
    
    try {
        // #region agent log
        fetch('http://127.0.0.1:7245/ingest/1a99addc-056e-429d-b318-75f0bb966d8b',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'script.js:203',message:'Starting init functions',timestamp:Date.now(),sessionId:'debug-loader',hypothesisId:'A'})}).catch(()=>{});
        // #endregion
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
        
        // #region agent log
        fetch('http://127.0.0.1:7245/ingest/1a99addc-056e-429d-b318-75f0bb966d8b',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'script.js:220',message:'Functions initialized, starting promises',timestamp:Date.now(),sessionId:'debug-loader',hypothesisId:'B'})}).catch(()=>{});
        // #endregion

        // Загружаем контент и профиль НЕЗАВИСИМО
        // Если один упадет, другой все равно загрузится
        const loadPromises = [];
        
        // Загружаем контент (не требует авторизации)
        loadPromises.push(
            loadContent().catch(error => {
                console.error("[DEBUG] Error loading content:", error);
                // Показываем пустые списки
                renderPromotions([]);
                renderServices([]);
                renderMasters([]);
            })
        );
        
        // Загружаем профиль (требует авторизации, может упасть)
        loadPromises.push(
            loadProfile().catch(error => {
                console.error("[DEBUG] Error loading profile:", error);
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
        
        // #region agent log
        fetch('http://127.0.0.1:7245/ingest/1a99addc-056e-429d-b318-75f0bb966d8b',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'script.js:260',message:'Promises settled',timestamp:Date.now(),sessionId:'debug-loader',hypothesisId:'B'})}).catch(()=>{});
        // #endregion
        console.log("[DEBUG] All loads completed");
        
        
    } catch (error) {
        // #region agent log
        fetch('http://127.0.0.1:7245/ingest/1a99addc-056e-429d-b318-75f0bb966d8b',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'script.js:267',message:'Error in window.onload',data:{error:error.message,stack:error.stack},timestamp:Date.now(),sessionId:'debug-loader',hypothesisId:'A'})}).catch(()=>{});
        // #endregion
        console.error("[DEBUG] Init Error:", error);
        
        // Все равно показываем интерфейс
    } finally {
        // #region agent log
        fetch('http://127.0.0.1:7245/ingest/1a99addc-056e-429d-b318-75f0bb966d8b',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'script.js:274',message:'Finally block reached',timestamp:Date.now(),sessionId:'debug-loader',hypothesisId:'C'})}).catch(()=>{});
        // #endregion
        // Гарантируем минимум 2 секунды отображения лоадера для анимации
        const elapsedTime = Date.now() - loadStartTime;
        const remainingTime = Math.max(0, MIN_LOADER_TIME - elapsedTime);
        
        setTimeout(() => {
            // #region agent log
            fetch('http://127.0.0.1:7245/ingest/1a99addc-056e-429d-b318-75f0bb966d8b',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'script.js:282',message:'Calling hideLoader',data:{remainingTime},timestamp:Date.now(),sessionId:'debug-loader',hypothesisId:'D'})}).catch(()=>{});
            // #endregion
            hideLoader();
        }, remainingTime);
    }
};

async function apiFetch(endpoint) {
    const baseUrl = window.location.origin;
    const url = new URL(`${baseUrl}${endpoint}`);
    // Добавляем timestamp для предотвращения кеширования
    url.searchParams.append('_t', Date.now());
    
    console.log(`[DEBUG] Fetching: ${url.toString()}`);
    
    
    try {
        const response = await fetch(url.toString(), {
            headers: { 'X-Tg-Init-Data': tg?.initData || '' }
        });
        
        console.log(`[DEBUG] Response status: ${response.status} for ${endpoint}`);
        
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error(`[DEBUG] API Error ${response.status}: ${errorText}`);
            
            throw new Error(`API Error ${response.status}: ${errorText}`);
        }
        
        const data = await response.json();
        console.log(`[DEBUG] Successfully fetched ${endpoint}`);
        
        return data;
    } catch (error) {
        console.error(`[DEBUG] Fetch error for ${endpoint}:`, error);
        
        throw error;
    }
}

// ---- Render Functions ----

async function loadContent() {
    console.log("[DEBUG] Loading content...");
    const data = await apiFetch('/api/app/content');
    if (data.booking_url) bookingUrl = data.booking_url;
    
    renderPromotions(data.promotions || []);
    renderServices(data.services || []);
    renderMasters(data.masters || []);
    console.log("[DEBUG] Content loaded successfully");
}

async function loadProfile() {
    console.log("[DEBUG] Loading profile...");
    
    // Проверяем, есть ли initData
    if (!tg.initData) {
        console.warn("[DEBUG] No initData from Telegram, skipping profile load");
        throw new Error("No Telegram initData");
    }
    
    const data = await apiFetch('/api/app/profile');
    const user = data.user;
    const isAdmin = data.is_admin;
    
    document.getElementById('user-name').innerText = `Привет, ${user.name || 'Красотка'}!`;
    document.getElementById('user-balance').innerText = user.balance || 0;
    document.getElementById('profile-phone').innerText = user.phone || '-';
    
    // Показываем кнопку админки, если пользователь админ
    const adminEntry = document.getElementById('admin-entry');
    if (isAdmin && adminEntry) {
        adminEntry.classList.remove('hidden');
    }

    // Стилизация бейджа статуса
    if (user.level === 'vip') {
        levelEl.className = "inline-flex px-3 py-1 rounded-full bg-gradient-to-r from-yellow-100 to-yellow-200 text-yellow-800 text-xs font-bold uppercase tracking-wide border border-yellow-300";
    }

    renderHistory(data.history || []);
    console.log("[DEBUG] Profile loaded successfully");
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
    
    list.innerHTML = promos.map(p => `
        <div class="min-w-[300px] h-[200px] relative rounded-[28px] overflow-hidden shadow-card active:scale-[0.98] transition-transform snap-center group border border-white/40">
            ${p.image_url ? `
                <img src="${p.image_url}" class="w-full h-full object-cover transition-transform duration-700 group-hover:scale-105" loading="lazy">
                <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent"></div>
            ` : `
                <div class="absolute inset-0 bg-gradient-to-br from-[#E8A8B4] via-[#F5CED6] to-[#FCE4EC]"></div>
                <div class="absolute top-0 right-0 w-32 h-32 bg-white/10 rounded-full -mr-16 -mt-16 blur-2xl"></div>
                <div class="absolute bottom-0 left-0 w-24 h-24 bg-white/10 rounded-full -ml-12 -mb-12 blur-xl"></div>
            `}
            <div class="relative h-full flex flex-col justify-between p-6 z-10">
                <div>
                    <h3 class="text-white font-serif text-2xl font-bold leading-tight mb-2 drop-shadow-md">${p.title}</h3>
                    ${p.description ? `<p class="text-white/90 text-sm leading-relaxed line-clamp-2 drop-shadow-sm font-medium">${p.description}</p>` : ''}
                </div>
                <button onclick="openPromotionDetail(${p.id})" class="bg-white/20 backdrop-blur-md hover:bg-white/30 text-white px-5 py-2.5 rounded-full text-xs font-bold w-fit transition-all flex items-center gap-2 shadow-sm border border-white/30">
                    <span>Узнать больше</span>
                </button>
            </div>
        </div>
    `).join('');
}

function renderServices(services) {
    const list = document.getElementById('services-list');
    if (!list) return;
    
    if (!services || !services.length) {
        list.innerHTML = '<div class="col-span-2 text-center py-10 text-stone-400 text-sm">Услуги скоро появятся</div>';
        return;
    }
    
    list.innerHTML = services.map(s => `
        <div onclick="openBooking()" class="bg-white rounded-[28px] shadow-card border border-white/50 active:scale-[0.98] transition-transform min-h-[280px] flex flex-col group relative overflow-hidden">
            <!-- Изображение услуги -->
            ${s.image_url ? `
                <div class="h-[140px] w-full bg-stone-100 relative overflow-hidden flex-shrink-0">
                    <img src="${s.image_url}" class="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110" loading="lazy">
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
                    <h3 class="font-serif text-lg font-bold leading-tight text-stone-800 group-hover:text-brand-dark transition-colors line-clamp-2">${s.title}</h3>
                    ${s.description ? `<p class="text-xs text-stone-500 leading-relaxed mt-1.5 line-clamp-3">${s.description}</p>` : ''}
                </div>

                <div class="pt-3 border-t border-stone-100 flex items-center justify-between mt-auto flex-shrink-0">
                    <span class="text-brand-dark font-bold text-lg font-serif">${s.price} ₽</span>
                    <div class="w-8 h-8 rounded-full bg-brand-bg flex items-center justify-center text-brand-dark group-hover:scale-110 group-hover:bg-brand-primary group-hover:text-white transition-all shadow-sm">
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-4 h-4">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                        </svg>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

function renderMasters(masters) {
    const list = document.getElementById('masters-list');
    if (!list) return;
    
    if (!masters || !masters.length) {
        list.innerHTML = '<div class="min-w-full text-center py-10 text-stone-400 text-sm">Список мастеров пуст</div>';
        return;
    }
    
    list.innerHTML = masters.map((m, index) => `
        <div onclick="openBooking()" class="min-w-[260px] h-[380px] relative rounded-[32px] overflow-visible shadow-card active:scale-[0.98] transition-all duration-300 snap-center group cursor-pointer">
            <!-- Фото мастера с ореолом -->
            <div class="absolute inset-0 bg-stone-200 rounded-[32px] overflow-hidden" style="box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.8), 0 15px 35px -10px rgba(232, 168, 180, 0.5), 0 10px 20px -5px rgba(0, 0, 0, 0.1);">
                ${m.photo_url ? `
                    <img src="${m.photo_url}" class="w-full h-full object-cover transition-transform duration-1000 group-hover:scale-110" loading="lazy">
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
                <h4 class="font-serif text-2xl font-bold mb-1 leading-tight drop-shadow-lg">${m.name}</h4>
                <p class="text-sm opacity-90 font-medium tracking-wide drop-shadow-md mb-4">${m.specialization || 'Специалист'}</p>
                
                <!-- Кнопка записи -->
                <button onclick="openBooking()" class="mt-4 w-full bg-white/20 backdrop-blur-md hover:bg-white/30 text-white px-4 py-2.5 rounded-full text-xs font-bold transition-all flex items-center justify-center gap-2 shadow-lg border border-white/30 active:scale-95">
                    <span>Записаться</span>
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" class="w-4 h-4">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                    </svg>
                </button>
            </div>
        </div>
    `).join('');
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
        const date = new Date(h.created_at);
        const expiresAt = h.expires_at ? new Date(h.expires_at) : null;
        const isExpired = expiresAt && expiresAt < new Date();
        const daysLeft = expiresAt ? Math.ceil((expiresAt - new Date()) / (1000 * 60 * 60 * 24)) : null;
        
        return `
        <div class="flex justify-between items-center p-5 bg-white rounded-[28px] border border-white/50 shadow-card mb-3">
            <div class="flex-1">
                <div class="text-sm font-semibold text-stone-800 mb-1">${h.description}</div>
                <div class="text-xs text-stone-500 font-medium mb-1">${date.toLocaleDateString('ru-RU')}</div>
                ${h.transaction_type === 'earn' && expiresAt ? `
                    <div class="text-xs ${isExpired ? 'text-rose-500' : daysLeft <= 7 ? 'text-orange-500' : 'text-stone-400'} font-medium">
                        ${isExpired ? '⏰ Истекли' : daysLeft <= 7 ? `⏰ Осталось ${daysLeft} ${daysLeft === 1 ? 'день' : daysLeft < 5 ? 'дня' : 'дней'}` : `Действуют до ${expiresAt.toLocaleDateString('ru-RU')}`}
                    </div>
                ` : ''}
            </div>
            <div class="text-right ml-4">
                <div class="font-bold text-lg ${h.amount > 0 ? 'text-green-600' : 'text-stone-600'}">
                    ${h.amount > 0 ? '+' : ''}${h.amount}
                </div>
                ${h.transaction_type === 'earn' && h.remaining_amount !== undefined ? `
                    <div class="text-xs text-stone-400 mt-1">Остаток: ${h.remaining_amount}</div>
                ` : ''}
            </div>
        </div>
        `;
    }).join('');
}

function openBooking() {
    if (tg?.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
    if (tg?.openLink) {
        tg.openLink(bookingUrl);
    } else {
        window.open(bookingUrl, '_blank');
    }
}

// --- Admin Logic ---

let currentAdminTab = 'users';
let adminItems = [];
let currentUserTransactions = [];

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
    
    loadAdminData();
}

async function loadAdminData() {
    const listEl = document.getElementById('admin-list');
    if (listEl) listEl.innerHTML = '<div class="h-20 skeleton w-full"></div><div class="h-20 skeleton w-full"></div>';
    
    try {
        console.log(`[DEBUG] Loading admin data for tab: ${currentAdminTab}`);
        
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
        
        console.log(`[DEBUG] Loaded ${adminItems.length} items for ${currentAdminTab}`);
        renderAdminList();
    } catch (error) {
        
        console.error(`[DEBUG] Admin data load error for ${currentAdminTab}:`, error);
        if (listEl) {
            listEl.innerHTML = `<div class="text-center py-10 text-rose-500">
                <div class="font-semibold mb-2">Ошибка загрузки</div>
                <div class="text-xs text-stone-400">${error.message || 'Неизвестная ошибка'}</div>
            </div>`;
        }
    }
}

function renderAdminList() {
    const listEl = document.getElementById('admin-list');
    if (!listEl) return;
    
    
    
    if (!adminItems.length) {
        listEl.innerHTML = '<div class="text-center py-10 text-stone-400">Список пуст</div>';
        return;
    }
    
    if (currentAdminTab === 'users') {
        listEl.innerHTML = adminItems.map(item => `
            <div class="bg-white p-5 rounded-[28px] border border-white/50 shadow-card active:scale-[0.98] transition-transform" onclick="openUserModal(${item.id})">
                <div class="flex items-center gap-4 mb-3">
                    <div class="w-12 h-12 rounded-xl bg-stone-50 flex items-center justify-center text-xl shadow-sm">
                        👤
                    </div>
                    <div class="flex-1 min-w-0">
                        <h4 class="font-semibold text-stone-800 text-sm truncate mb-1">${item.name || 'Без имени'}</h4>
                        <p class="text-xs text-stone-500 truncate font-medium">${item.phone || ''}</p>
                    </div>
                    <div class="text-right">
                        <div class="font-bold text-brand-primary text-lg font-serif">${item.balance || 0}</div>
                        <div class="text-xs text-stone-400 font-medium">баллов</div>
                    </div>
                </div>
                <div class="flex items-center gap-2 pt-3 border-t border-stone-100">
                    <span class="text-xs px-2.5 py-1 rounded-full font-medium ${item.level === 'vip' ? 'bg-yellow-100 text-yellow-800' : item.level === 'regular' ? 'bg-blue-100 text-blue-800' : 'bg-stone-100 text-stone-600'}">${item.level === 'vip' ? 'VIP' : item.level === 'regular' ? 'Regular' : 'New'}</span>
                    ${item.active ? '' : '<span class="text-xs px-2.5 py-1 rounded-full bg-rose-100 text-rose-600 font-medium">Неактивен</span>'}
                </div>
            </div>
        `).join('');
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
                
                // #region agent log
                fetch('http://127.0.0.1:7245/ingest/1a99addc-056e-429d-b318-75f0bb966d8b',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'script.js:renderAdminList',message:'Displaying scheduled time',data:{scheduled_at:item.scheduled_at,utcTime:scheduled.toISOString(),localTime:scheduled.toString(),scheduledDate:scheduledDate,utcOffset:scheduled.getTimezoneOffset()},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
                // #endregion
            }
            
            return `
                <div class="bg-white p-5 rounded-[28px] border border-white/50 shadow-card">
                    <div class="flex items-start gap-4 mb-3">
                        ${item.image_url ? `
                            <img src="${item.image_url}" class="w-16 h-16 rounded-xl object-cover bg-stone-100 shadow-sm">
                        ` : `
                            <div class="w-12 h-12 rounded-xl bg-stone-50 flex items-center justify-center text-xl shadow-sm">
                                📢
                            </div>
                        `}
                        <div class="flex-1 min-w-0">
                            <h4 class="font-semibold text-stone-800 text-sm mb-2 line-clamp-2">${item.message.substring(0, 100)}${item.message.length > 100 ? '...' : ''}</h4>
                            <p class="text-xs text-stone-500 mb-1">Создана: ${date}</p>
                            ${scheduledDate ? `<p class="text-xs text-purple-600 mb-1">📅 Запланирована: ${scheduledDate}</p>` : ''}
                            <div class="flex items-center gap-2 flex-wrap">
                                <span class="text-xs px-2.5 py-1 rounded-full font-medium ${statusColors[item.status] || 'bg-stone-100 text-stone-600'}">${statusText[item.status] || item.status}</span>
                                ${item.sent_count > 0 ? `<span class="text-xs text-stone-600">✓ ${item.sent_count} отправлено</span>` : ''}
                                ${item.failed_count > 0 ? `<span class="text-xs text-rose-600">✗ ${item.failed_count} ошибок</span>` : ''}
                            </div>
                        </div>
                    </div>
                    <div class="flex gap-2 mt-3">
                        <button onclick="viewBroadcast(${item.id})" class="px-4 bg-stone-100 text-stone-700 py-2.5 rounded-xl font-semibold text-sm active:scale-[0.98] transition-all">
                            Просмотр
                        </button>
                        ${item.status === 'pending' || item.status === 'failed' || item.status === 'scheduled' ? `
                            ${item.status === 'scheduled' ? '' : `
                                <button onclick="sendBroadcast(${item.id})" class="flex-1 bg-stone-800 text-white py-2.5 rounded-xl font-semibold text-sm active:scale-[0.98] transition-all">
                                    ${item.status === 'failed' ? 'Повторить отправку' : 'Отправить'}
                                </button>
                            `}
                            <button onclick="deleteBroadcast(${item.id})" class="px-4 bg-rose-500 text-white py-2.5 rounded-xl font-semibold text-sm active:scale-[0.98] transition-all">
                                Удалить
                            </button>
                        ` : ''}
                    </div>
                </div>
            `;
        }).join('');
    } else if (currentAdminTab === 'bot-buttons') {
        listEl.innerHTML = adminItems.map((item, index) => `
            <div class="bg-white p-4 rounded-[28px] border border-white/50 shadow-card flex items-center gap-3">
                <div class="flex-1 flex items-center gap-4 active:scale-[0.98] transition-transform rounded-xl p-2" onclick="openAdminModal(${item.id})">
                    <div class="w-12 h-12 rounded-xl bg-stone-50 flex items-center justify-center text-xl shadow-sm">
                        🔘
                    </div>
                    <div class="flex-1 min-w-0">
                        <h4 class="font-semibold text-stone-800 text-sm truncate mb-1">${item.button_text || 'Без названия'}</h4>
                        <p class="text-xs text-stone-500 truncate font-medium">Строка ${item.row_number}, порядок ${item.order_in_row} • ${item.handler_type || 'не указан'}</p>
                    </div>
                    <div class="flex items-center gap-2">
                        ${item.is_admin_only ? '<span class="text-xs px-2 py-1 rounded-full bg-purple-100 text-purple-600 font-medium">Админ</span>' : ''}
                        ${!item.is_active ? '<span class="text-xs px-2 py-1 rounded-full bg-rose-100 text-rose-600 font-medium">Неактивна</span>' : ''}
                    </div>
                    <div class="text-stone-300 text-lg">→</div>
                </div>
            </div>
        `).join('');
    } else if (currentAdminTab === 'settings') {
        listEl.innerHTML = adminItems.map(item => `
            <div class="bg-white p-5 rounded-[28px] border border-white/50 shadow-card active:scale-[0.98] transition-transform flex items-center gap-4" onclick="openSettingModal('${item.key}')">
                <div class="w-12 h-12 rounded-xl bg-stone-50 flex items-center justify-center text-xl shadow-sm">
                    ⚙️
                </div>
                <div class="flex-1 min-w-0">
                    <h4 class="font-semibold text-stone-800 text-sm truncate mb-1">${item.description || item.key}</h4>
                    <p class="text-xs text-stone-500 font-medium">${item.value}</p>
                </div>
                <div class="text-stone-300 text-lg">→</div>
            </div>
        `).join('');
    } else {
        // Для остальных вкладок (masters, services, promotions)
        listEl.innerHTML = adminItems.map((item, index) => `
            <div class="bg-white p-4 rounded-[28px] border border-white/50 shadow-card flex items-center gap-3">
                <div class="flex flex-col gap-1">
                    <button onclick="event.stopPropagation(); moveItem(${item.id}, 'up')" 
                            class="w-8 h-8 rounded-lg bg-stone-50 text-stone-600 flex items-center justify-center text-xs font-bold active:bg-stone-100 transition-colors shadow-sm ${index === 0 ? 'opacity-30 cursor-not-allowed' : ''}"
                            ${index === 0 ? 'disabled' : ''}>
                        ↑
                    </button>
                    <button onclick="event.stopPropagation(); moveItem(${item.id}, 'down')" 
                            class="w-8 h-8 rounded-lg bg-stone-50 text-stone-600 flex items-center justify-center text-xs font-bold active:bg-stone-100 transition-colors shadow-sm ${index === adminItems.length - 1 ? 'opacity-30 cursor-not-allowed' : ''}"
                            ${index === adminItems.length - 1 ? 'disabled' : ''}>
                        ↓
                    </button>
                </div>
                <div class="flex-1 flex items-center gap-4 active:scale-[0.98] transition-transform rounded-xl p-2" onclick="openAdminModal(${item.id})">
                    ${item.photo_url || item.image_url ? 
                        `<img src="${item.photo_url || item.image_url}" class="w-12 h-12 rounded-xl object-cover bg-stone-100 shadow-sm">` : 
                        `<div class="w-12 h-12 rounded-xl bg-stone-50 flex items-center justify-center text-xl shadow-sm">
                            ${currentAdminTab === 'masters' ? '👩‍⚕️' : currentAdminTab === 'services' ? '✨' : '🎁'}
                        </div>`
                    }
                    <div class="flex-1 min-w-0">
                        <h4 class="font-semibold text-stone-800 text-sm truncate mb-1">${item.name || item.title}</h4>
                        <p class="text-xs text-stone-500 truncate font-medium">${item.specialization || item.price + ' ₽' || item.description || ''}</p>
                    </div>
                    <div class="text-stone-300 text-lg">→</div>
                </div>
            </div>
        `).join('');
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
    
    // Скрываем кнопку добавить на вкладке настроек
    const addBtn = document.querySelector('.fixed.bottom-24.left-1\/2');
    if (addBtn) {
        if (currentAdminTab === 'settings') {
            addBtn.classList.add('hidden');
        } else {
            addBtn.classList.remove('hidden');
        }
    }
    
    // Для рассылок не поддерживаем редактирование, только создание
    if (currentAdminTab === 'broadcasts' && id) {
        alert('Редактирование рассылок не поддерживается. Создайте новую рассылку.');
        return;
    }
    
    form.reset();
    formId.value = id || '';
    
    if (id && currentAdminTab !== 'broadcasts') {
        const item = adminItems.find(i => i.id === id);
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
    
    form.reset();
    formId.value = id;
    
    // Восстанавливаем стандартный обработчик submit
    form.onsubmit = handleAdminSubmit;
    
    try {
        const user = await apiFetch(`/api/admin/users/${id}`);
        title.innerText = user.name || user.phone || 'Пользователь';
        deleteBtn.classList.add('hidden');
        
        // Загружаем транзакции
        currentUserTransactions = await apiFetch(`/api/admin/users/${id}/transactions`);
        
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
    const html = `
        <div>
            <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Имя</label>
            <input type="text" name="name" value="${user.name || ''}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">
        </div>
        <div>
            <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Телефон</label>
            <input type="text" name="phone" value="${user.phone || ''}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" readonly>
        </div>
        <div>
            <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Баланс баллов</label>
            <input type="number" name="balance" value="${user.balance || 0}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" required>
        </div>
        <div>
            <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Уровень</label>
            <select name="level" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">
                <option value="new" ${user.level === 'new' ? 'selected' : ''}>New</option>
                <option value="regular" ${user.level === 'regular' ? 'selected' : ''}>Regular</option>
                <option value="vip" ${user.level === 'vip' ? 'selected' : ''}>VIP</option>
            </select>
        </div>
        <div class="flex items-center gap-2 px-1">
            <input type="checkbox" name="active" ${user.active !== false ? 'checked' : ''} class="w-4 h-4 rounded">
            <label class="text-sm font-semibold text-stone-600">Активен</label>
        </div>
        
        <div class="pt-4 border-t border-stone-200 mt-4">
            <h4 class="text-sm font-bold text-stone-700 mb-3">История транзакций</h4>
            <div id="user-transactions-list" class="space-y-2 max-h-48 overflow-y-auto">
                ${currentUserTransactions.length ? currentUserTransactions.map(t => `
                    <div class="flex justify-between items-center p-2 bg-stone-50 rounded-lg text-xs">
                        <div>
                            <div class="font-semibold text-stone-800">${t.description || 'Транзакция'}</div>
                            <div class="text-stone-400">${new Date(t.created_at).toLocaleString('ru-RU')}</div>
                        </div>
                        <div class="font-bold ${t.amount > 0 ? 'text-green-600' : 'text-rose-600'}">
                            ${t.amount > 0 ? '+' : ''}${t.amount}
                        </div>
                    </div>
                `).join('') : '<div class="text-center py-4 text-stone-400 text-xs">Нет транзакций</div>'}
            </div>
            <button type="button" onclick="openTransactionModal(${user.id})" class="w-full mt-3 bg-stone-100 text-stone-700 py-2 rounded-xl text-sm font-semibold active:opacity-80">
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
    
    form.reset();
    formId.value = userId;
    
    title.innerText = 'Добавить транзакцию';
    deleteBtn.classList.add('hidden');
    
    const html = `
        <input type="hidden" name="user_id" value="${userId}">
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
        await handleTransactionSubmit(e, userId);
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
        
        if (!response.ok) throw new Error('Transaction error');
        
        tg.HapticFeedback.notificationOccurred('success');
        closeAdminModal();
        
        // Небольшая задержка перед открытием формы пользователя
        setTimeout(() => {
            openUserModal(userId);
        }, 350);
    } catch (error) {
        console.error("Transaction error:", error);
        alert("Ошибка при создании транзакции");
    }
}

function renderFormFields(item = {}) {
    const fieldsEl = document.getElementById('form-fields');
    let html = '';
    
    if (currentAdminTab === 'users') {
        html = `
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Имя</label>
                <input type="text" name="name" value="${item.name || ''}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" required>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Телефон</label>
                <input type="text" name="phone" value="${item.phone || ''}" placeholder="79991234567" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" required>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Баланс баллов</label>
                <input type="number" name="balance" value="${item.balance || 0}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Уровень</label>
                <select name="level" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">
                    <option value="new" ${item.level === 'new' ? 'selected' : ''}>New</option>
                    <option value="regular" ${item.level === 'regular' ? 'selected' : ''}>Regular</option>
                    <option value="vip" ${item.level === 'vip' ? 'selected' : ''}>VIP</option>
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
                <input type="text" name="name" value="${item.name || ''}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" required>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Специализация</label>
                <input type="text" name="specialization" value="${item.specialization || ''}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Фото мастера</label>
                <input type="file" accept="image/*" id="master-photo-input" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">
                <input type="hidden" name="photo_url" id="master-photo-url" value="${item.photo_url || ''}">
                ${item.photo_url ? `<div class="mt-2"><img src="${item.photo_url}" class="w-20 h-20 object-cover rounded-lg" id="master-photo-preview"></div>` : ''}
                <div id="master-photo-upload-status" class="mt-2 text-xs text-stone-500 hidden"></div>
            </div>
        `;
    } else if (currentAdminTab === 'services') {
        html = `
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Название услуги</label>
                <input type="text" name="title" value="${item.title || ''}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" required>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Цена (₽)</label>
                <input type="number" name="price" value="${item.price || ''}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" required>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Категория</label>
                <input type="text" name="category" value="${item.category || ''}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Описание</label>
                <textarea name="description" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm h-24">${item.description || ''}</textarea>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Изображение услуги</label>
                <input type="file" accept="image/*" id="service-image-input" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">
                <input type="hidden" name="image_url" id="service-image-url" value="${item.image_url || ''}">
                ${item.image_url ? `<div class="mt-2"><img src="${item.image_url}" class="w-32 h-32 object-cover rounded-lg" id="service-image-preview"></div>` : ''}
                <div id="service-image-upload-status" class="mt-2 text-xs text-stone-500 hidden"></div>
            </div>
            <div class="flex items-center gap-2 px-1">
                <input type="checkbox" name="is_active" ${item.is_active !== false ? 'checked' : ''} class="w-4 h-4 rounded">
                <label class="text-sm font-semibold text-stone-600">Активна</label>
            </div>
        `;
    } else if (currentAdminTab === 'promotions') {
        html = `
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Заголовок акции</label>
                <input type="text" name="title" value="${item.title || ''}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" required>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Краткое описание</label>
                <textarea name="description" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm h-24" placeholder="Краткое описание для карточки акции">${item.description || ''}</textarea>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Детальное описание</label>
                <textarea name="detail_text" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm h-32" placeholder="Полное описание акции, которое будет показано при нажатии 'Узнать больше'">${item.detail_text || ''}</textarea>
                <p class="text-xs text-stone-400 mt-1 px-1">Поддерживается перенос строк. Будет отображено в модальном окне</p>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Условия акции</label>
                <textarea name="conditions" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm h-24" placeholder="Условия участия в акции (необязательно)">${item.conditions || ''}</textarea>
                <p class="text-xs text-stone-400 mt-1 px-1">Условия будут отображены в отдельном блоке</p>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Изображение акции</label>
                <input type="file" accept="image/*" id="promotion-image-input" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">
                <input type="hidden" name="image_url" id="promotion-image-url" value="${item.image_url || ''}">
                ${item.image_url ? `<div class="mt-2"><img src="${item.image_url}" class="w-32 h-32 object-cover rounded-lg" id="promotion-image-preview"></div>` : ''}
                <div id="promotion-image-upload-status" class="mt-2 text-xs text-stone-500 hidden"></div>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Дата окончания (гггг-мм-дд)</label>
                <input type="date" name="end_date" value="${item.end_date || ''}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">URL кнопки действия (необязательно)</label>
                <input type="text" name="action_url" value="${item.action_url || ''}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" placeholder="https://example.com или оставьте пустым для записи">
                <p class="text-xs text-stone-400 mt-1 px-1">Если не указано, будет использована ссылка на запись</p>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Текст кнопки действия</label>
                <input type="text" name="action_text" value="${item.action_text || 'Записаться'}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" placeholder="Записаться">
                <p class="text-xs text-stone-400 mt-1 px-1">Текст на кнопке в детальном просмотре (по умолчанию "Записаться")</p>
            </div>
            <div class="flex items-center gap-2 px-1">
                <input type="checkbox" name="is_active" ${item.is_active !== false ? 'checked' : ''} class="w-4 h-4 rounded">
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
            
            // #region agent log
            fetch('http://127.0.0.1:7245/ingest/1a99addc-056e-429d-b318-75f0bb966d8b',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'script.js:renderFormFields',message:'Formatting scheduled_at for datetime-local',data:{scheduled_at:item.scheduled_at,utcTime:date.toISOString(),localTime:date.toString(),scheduledAtValue:scheduledAtValue,utcOffset:date.getTimezoneOffset()},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
            // #endregion
        }
        
        html = `
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Текст сообщения</label>
                <textarea name="message" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm h-32" required>${item.message || ''}</textarea>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Изображение</label>
                <input type="file" accept="image/*" id="broadcast-image-input" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">
                <input type="hidden" name="image_url" id="broadcast-image-url" value="${item.image_url || ''}">
                ${item.image_url ? `<div class="mt-2"><img src="${item.image_url}" class="w-32 h-32 object-cover rounded-lg" id="broadcast-image-preview"></div>` : ''}
                <div id="broadcast-image-upload-status" class="mt-2 text-xs text-stone-500 hidden"></div>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Получатели</label>
                <select name="recipient_type" id="broadcast-recipient-type" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" required>
                    <option value="all" ${item.recipient_type === 'all' ? 'selected' : ''}>Все пользователи</option>
                    <option value="selected" ${item.recipient_type === 'selected' ? 'selected' : ''}>Выбранные пользователи</option>
                    <option value="by_balance" ${item.recipient_type === 'by_balance' ? 'selected' : ''}>По балансу баллов</option>
                </select>
            </div>
            <div id="selected-users-container" class="hidden">
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Выберите пользователей</label>
                <div id="users-list" class="max-h-48 overflow-y-auto border border-stone-100 rounded-xl p-3 bg-stone-50">
                    <div class="text-sm text-stone-500">Загрузка пользователей...</div>
                </div>
                <input type="hidden" name="recipient_ids" id="broadcast-recipient-ids" value="${JSON.stringify(item.recipient_ids || [])}">
            </div>
            <div id="balance-filter" class="hidden">
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Минимальный баланс</label>
                <input type="number" name="filter_balance_min" value="${item.filter_balance_min || ''}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" placeholder="Не указано">
            </div>
            <div id="balance-filter-max" class="hidden">
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Максимальный баланс</label>
                <input type="number" name="filter_balance_max" value="${item.filter_balance_max || ''}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" placeholder="Не указано">
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Запланировать отправку (необязательно)</label>
                <input type="datetime-local" name="scheduled_at" value="${scheduledAtValue}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">
                <p class="text-xs text-stone-400 mt-1 px-1">Оставьте пустым для немедленной отправки</p>
            </div>
        `;
    } else if (currentAdminTab === 'bot-buttons') {
        html = `
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Текст кнопки</label>
                <input type="text" name="button_text" value="${item.button_text || ''}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" required>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Текст ответа</label>
                <textarea name="response_text" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm h-32" required>${item.response_text || ''}</textarea>
                <p class="text-xs text-stone-400 mt-1 px-1">Поддерживается Markdown. Можно использовать {YCLIENTS_BOOKING_URL} и {LOYALTY_PERCENTAGE}</p>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Тип обработчика</label>
                <select name="handler_type" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">
                    <option value="book" ${item.handler_type === 'book' ? 'selected' : ''}>Запись</option>
                    <option value="info" ${item.handler_type === 'info' ? 'selected' : ''}>Информация</option>
                    <option value="profile" ${item.handler_type === 'profile' ? 'selected' : ''}>Профиль</option>
                    <option value="admin" ${item.handler_type === 'admin' ? 'selected' : ''}>Админка</option>
                </select>
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Номер строки</label>
                    <input type="number" name="row_number" value="${item.row_number || 1}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" min="1" required>
                </div>
                <div>
                    <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Порядок в строке</label>
                    <input type="number" name="order_in_row" value="${item.order_in_row || 0}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" min="0" required>
                </div>
            </div>
            <div>
                <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">WebApp URL (необязательно)</label>
                <input type="text" name="web_app_url" value="${item.web_app_url || ''}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" placeholder="https://example.com/webapp">
            </div>
            <div class="flex items-center gap-2 px-1">
                <input type="checkbox" name="is_admin_only" ${item.is_admin_only ? 'checked' : ''} class="w-4 h-4 rounded">
                <label class="text-sm font-semibold text-stone-600">Только для админов</label>
            </div>
            <div class="flex items-center gap-2 px-1">
                <input type="checkbox" name="is_active" ${item.is_active !== false ? 'checked' : ''} class="w-4 h-4 rounded">
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
        const selectedSet = new Set(selectedIds);
        
        usersListEl.innerHTML = users.map(user => `
            <label class="flex items-center gap-3 p-2 rounded-lg hover:bg-stone-100 cursor-pointer">
                <input type="checkbox" value="${user.id}" ${selectedSet.has(user.id) ? 'checked' : ''} 
                       class="w-4 h-4 rounded" onchange="updateBroadcastRecipients()">
                <div class="flex-1">
                    <div class="text-sm font-semibold text-stone-800">${user.name || 'Без имени'}</div>
                    <div class="text-xs text-stone-500">${user.phone || ''}</div>
                </div>
                <div class="text-xs text-stone-400">${user.balance || 0} баллов</div>
            </label>
        `).join('');
    } catch (error) {
        console.error("Error loading users:", error);
        usersListEl.innerHTML = '<div class="text-sm text-rose-500">Ошибка загрузки пользователей</div>';
    }
}

function updateBroadcastRecipients() {
    const checkboxes = document.querySelectorAll('#users-list input[type="checkbox"]:checked');
    const selectedIds = Array.from(checkboxes).map(cb => parseInt(cb.value));
    const hiddenInput = document.getElementById('broadcast-recipient-ids');
    if (hiddenInput) {
        hiddenInput.value = JSON.stringify(selectedIds);
    }
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
        // Создаем FormData для отправки файла
        const formData = new FormData();
        formData.append('file', file);
        
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
            throw new Error('Upload failed');
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
            statusEl.textContent = '✗ Ошибка загрузки';
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
        const actionUrl = promotion.action_url || contentData.booking_url || bookingUrl || '#';
        
        // Базовое экранирование HTML для безопасности
        const escapeHtml = (text) => {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        };
        
        // Формируем HTML контента с экранированием
        content.innerHTML = `
            ${promotion.image_url ? `
                <div class="mb-6 -mx-6 -mt-6">
                    <img src="${escapeHtml(promotion.image_url)}" class="w-full h-48 object-cover" alt="${escapeHtml(promotion.title)}">
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
                <button onclick="window.open('${escapeHtml(actionUrl)}', '_blank'); closePromotionDetail();" 
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
    
    const setting = adminItems.find(s => s.key === key);
    if (!setting) return;
    
    form.reset();
    formId.value = key;
    title.innerText = 'Настройка';
    deleteBtn.classList.add('hidden');
    
    // Переопределяем submit для настроек
    form.onsubmit = async (e) => {
        e.preventDefault();
        await handleSettingSubmit(e, key);
    };
    
    let inputHtml = '';
    if (setting.type === 'number' || setting.type === 'float') {
        inputHtml = `<input type="number" name="value" value="${setting.value}" step="${setting.type === 'float' ? '0.01' : '1'}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" required>`;
    } else if (setting.type === 'boolean') {
        inputHtml = `
            <select name="value" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">
                <option value="true" ${setting.value === true || setting.value === 'true' ? 'selected' : ''}>Да</option>
                <option value="false" ${setting.value === false || setting.value === 'false' ? 'selected' : ''}>Нет</option>
            </select>
        `;
    } else {
        inputHtml = `<input type="text" name="value" value="${setting.value}" class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm" required>`;
    }

    fields.innerHTML = `
        <div>
            <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">${setting.description || key}</label>
            ${inputHtml}
            <p class="text-[10px] text-stone-400 mt-2 px-1">Ключ: ${key} | Тип: ${setting.type}</p>
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
            } else if (key === 'balance') {
                data[key] = parseInt(value) || 0;
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
            
            if (!response.ok) throw new Error('Save error');
            
            tg.HapticFeedback.notificationOccurred('success');
            closeAdminModal();
            loadAdminData();
            return;
        } catch (error) {
            console.error("Save error:", error);
            alert("Ошибка при сохранении");
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
        
        // #region agent log
        fetch('http://127.0.0.1:7245/ingest/1a99addc-056e-429d-b318-75f0bb966d8b',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'script.js:handleAdminSubmit',message:'Broadcast form data prepared',data:{has_image_url:!!data.image_url,image_url:data.image_url,recipient_type:data.recipient_type},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
        // #endregion
        
        // Обработка scheduled_at
        const scheduledAt = formData.get('scheduled_at');
        if (scheduledAt) {
            // datetime-local возвращает время в локальном часовом поясе без указания TZ
            // Нужно создать Date объект, который интерпретирует это как локальное время
            // и затем конвертировать в ISO (UTC)
            const date = new Date(scheduledAt);
            
            // #region agent log
            fetch('http://127.0.0.1:7245/ingest/1a99addc-056e-429d-b318-75f0bb966d8b',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'script.js:handleAdminSubmit',message:'Scheduled time conversion',data:{scheduledAt:scheduledAt,localTime:date.toString(),isoTime:date.toISOString(),utcOffset:date.getTimezoneOffset()},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
            // #endregion
            
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
    if (!confirm('Отправить рассылку? Это действие нельзя отменить.')) {
        return;
    }
    
    try {
        const response = await fetch(`${window.location.origin}/api/admin/broadcasts/${id}/send`, {
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
        const response = await fetch(`${window.location.origin}/api/admin/broadcasts/${id}?_t=${Date.now()}`, {
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
        const fieldsEl = document.getElementById('admin-form-fields');
        const titleEl = document.getElementById('admin-modal-title');
        
        titleEl.textContent = 'Детали рассылки';
        fieldsEl.innerHTML = `
            <div class="space-y-4">
                <div>
                    <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Текст сообщения</label>
                    <div class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm whitespace-pre-wrap">${broadcast.message || ''}</div>
                </div>
                ${broadcast.image_url ? `
                    <div>
                        <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Изображение</label>
                        <img src="${broadcast.image_url}" class="w-full max-w-md rounded-xl object-cover bg-stone-100 shadow-sm">
                    </div>
                ` : ''}
                <div>
                    <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Получатели</label>
                    <div class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">${recipientInfo}</div>
                </div>
                <div>
                    <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Статус</label>
                    <div class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">${broadcast.status}</div>
                </div>
                <div>
                    <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Создана</label>
                    <div class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">${createdDate}</div>
                </div>
                ${scheduledDate ? `
                    <div>
                        <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Запланирована на</label>
                        <div class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">${scheduledDate}</div>
                    </div>
                ` : ''}
                ${broadcast.sent_count > 0 || broadcast.failed_count > 0 ? `
                    <div>
                        <label class="block text-xs font-bold text-stone-400 uppercase mb-1 px-1">Статистика</label>
                        <div class="w-full bg-stone-50 border border-stone-100 rounded-xl px-4 py-3 text-sm">
                            Отправлено: ${broadcast.sent_count || 0}<br>
                            Ошибок: ${broadcast.failed_count || 0}
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
    if (!confirm('Удалить эту рассылку? Это действие нельзя отменить.')) {
        return;
    }
    
    try {
        const response = await fetch(`${window.location.origin}/api/admin/broadcasts/${id}`, {
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
        alert(`Ошибка при удалении рассылки: ${error.message}`);
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
    
    const url = `${window.location.origin}/api/admin/${currentAdminTab}/${id}/move?direction=${direction}`;
    
    
    
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
