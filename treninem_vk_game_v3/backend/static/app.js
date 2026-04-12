const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));

const state = {
  token: localStorage.getItem('beast_token') || '',
  meta: null,
  user: null,
  currentScreen: 'profile',
  sound: true,
  adminUnlocked: false,
  inventory: [],
  shop: [],
  recipes: [],
  market: [],
  leaderboard: { level: [], pvp: [], gold: [] },
  itemDefs: [],
  bank: null,
  daily: null,
  quests: [],
  activity: [],
  adminUsers: [],
  adminLogs: [],
  filters: { inventory: '', market: '', marketRarity: '', craft: '' },
};

let audioCtx = null;

function tone(freq = 440, len = 0.05, type = 'sine', gainValue = 0.04) {
  if (!state.sound) return;
  try {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = type;
    osc.frequency.value = freq;
    gain.gain.value = gainValue;
    osc.connect(gain).connect(audioCtx.destination);
    osc.start();
    osc.stop(audioCtx.currentTime + len);
  } catch {}
}

function toast(message, ok = true) {
  const el = $('#toast');
  el.textContent = message;
  el.style.borderColor = ok ? 'rgba(124,226,167,.24)' : 'rgba(241,123,123,.28)';
  el.classList.remove('hidden');
  tone(ok ? 660 : 220, 0.08, ok ? 'triangle' : 'sawtooth');
  clearTimeout(window.__toast);
  window.__toast = setTimeout(() => el.classList.add('hidden'), 2600);
}

function rarityCls(r) { return `rarity-${r}`; }
function safe(str) { return String(str ?? '').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); }
function fmtDate(s) { try { return new Date(s).toLocaleString('ru-RU'); } catch { return s || '—'; } }
function percent(a, b) { return Math.max(0, Math.min(100, Math.round((a / Math.max(1, b)) * 100))); }

async function api(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(state.token ? { Authorization: `Bearer ${state.token}` } : {}),
      ...(options.headers || {}),
    },
  });
  let data = {};
  try { data = await res.json(); } catch {}
  if (!res.ok) throw new Error(data.detail || 'Ошибка запроса');
  return data;
}

function setScreen(screen) {
  state.currentScreen = screen;
  const titles = {
    profile: 'Профиль', inventory: 'Инвентарь', shop: 'Магазин', expedition: 'Экспедиции', dungeon: 'Подземелья',
    craft: 'Крафт', market: 'Рынок', bank: 'Банк', social: 'Друзья и синхронизация', leaderboard: 'Рейтинг', admin: 'Секретная админ-панель',
  };
  $('#screenTitle').textContent = titles[screen] || 'Beast Legends';
  $$('.nav-btn, .mobile-nav button').forEach(btn => btn.classList.toggle('active', btn.dataset.screen === screen));
  $$('.subscreen').forEach(el => el.classList.add('hidden'));
  const current = document.getElementById(`${screen}Screen`);
  if (current) current.classList.remove('hidden');
  tone(520, 0.04, 'triangle');
}

function itemCard(item, buttons = '') {
  const qty = item.quantity ?? 1;
  return `
    <div class="list-item">
      <div>
        <div class="list-item-title">${safe(item.icon || '✨')} ${safe(item.name)} <span class="${rarityCls(item.rarity)}">${safe(item.rarity)}</span></div>
        <div class="muted">${safe(item.category)} · вес ${item.weight ?? '?'} · цена ${item.price ?? '?'}</div>
        <div class="footer-note">${safe(item.description || '')}</div>
        <div class="actions-row">${buttons}</div>
      </div>
      <div style="text-align:right">
        <div class="tag">x${qty}</div>
        ${item.equipped ? '<div class="tag">экипировано</div>' : ''}
      </div>
    </div>`;
}

function activityText(a) {
  const p = a.payload || {};
  const map = {
    account_created: 'Создан новый профиль',
    character_selected: 'Выбран персонаж',
    level_up: `Новый уровень: ${p.level}`,
    expedition_win: 'Успешная экспедиция',
    expedition_fail: 'Провал в экспедиции',
    dungeon_win: 'Подземелье пройдено',
    dungeon_fail: 'Подземелье не пройдено',
    item_used: `Использован предмет ${p.item_code || ''}`,
    equipment_changed: 'Изменена экипировка',
    craft_done: `Крафт по рецепту ${p.recipe_code || ''}`,
    shop_buy: 'Покупка в магазине',
    market_sell: 'Лот выставлен на рынок',
    market_buy: 'Лот куплен на рынке',
    bank_credit: 'Получен кредит',
    bank_repay: 'Погашение кредита',
    pvp_win: `Победа над ${p.opponent_name || 'соперником'}`,
    pvp_loss: `Поражение от ${p.opponent_name || 'соперника'}`,
    gift_send: 'Отправлен подарок',
    gift_receive: 'Получен подарок',
    daily_claim: 'Получена ежедневная награда',
    quest_claim: 'Получена награда за квест',
    admin_gold: 'Админ выдал золото',
    admin_item: 'Админ выдал предмет',
    admin_item_removed: 'Админ удалил предмет',
    admin_level: 'Админ изменил уровень',
  };
  return map[a.kind] || a.kind;
}

async function loadMeta() { state.meta = await api('/api/meta'); }

async function tryAutoLogin() {
  if (state.token) {
    try {
      state.user = await api('/api/me');
      afterLogin();
      return;
    } catch {
      state.token = '';
      localStorage.removeItem('beast_token');
    }
  }
  $('#loginScreen').classList.remove('hidden');
}

async function loginWithVK() {
  try {
    const bridge = window.vkBridge;
    if (!bridge) throw new Error('VK Bridge не найден');
    await bridge.send('VKWebAppInit');
    const info = await bridge.send('VKWebAppGetUserInfo');
    const data = await api('/api/auth/vk-login', {
      method: 'POST',
      body: JSON.stringify({
        launch_params: window.location.search,
        display_name: `${info.first_name} ${info.last_name}`.trim(),
        avatar_url: info.photo_200 || info.photo_100 || '',
      }),
    });
    completeLogin(data);
  } catch (err) {
    toast(err.message || 'Ошибка входа через VK', false);
  }
}

async function devLogin() {
  try {
    const dev_vk_user_id = Number($('#devVkId').value || 1);
    const display_name = $('#devDisplayName').value || `Dev User ${dev_vk_user_id}`;
    const data = await api('/api/auth/vk-login', {
      method: 'POST', body: JSON.stringify({ dev_vk_user_id, display_name }),
    });
    completeLogin(data);
  } catch (err) { toast(err.message, false); }
}

function completeLogin(data) {
  state.token = data.token;
  localStorage.setItem('beast_token', state.token);
  state.user = data.user;
  afterLogin();
}

function afterLogin() {
  $('#loginScreen').classList.add('hidden');
  if (!state.user.character_key) {
    renderCharacters();
    $('#characterScreen').classList.remove('hidden');
    $('#appScreen').classList.add('hidden');
  } else {
    $('#characterScreen').classList.add('hidden');
    $('#appScreen').classList.remove('hidden');
    loadAll();
  }
}

function renderCharacters() {
  const grid = $('#characterGrid');
  grid.innerHTML = Object.entries(state.meta.characters).map(([key, ch]) => `
    <div class="character-card glow-card">
      <div class="tag">${safe(ch.label)}</div>
      <h4>${safe(ch.label)}</h4>
      <div class="muted">${Object.entries(ch.stats).map(([k,v]) => `${k}: ${v}`).join(' · ')}</div>
      <div class="footer-note">Способности: ${safe(ch.abilities.join(', '))}</div>
      <div class="actions-row"><button class="primary-btn" onclick="selectCharacter('${key}')">Выбрать</button></div>
    </div>`).join('');
}

async function selectCharacter(character_key) {
  try {
    await api('/api/character/select', { method: 'POST', body: JSON.stringify({ character_key }) });
    state.user = await api('/api/me');
    $('#characterScreen').classList.add('hidden');
    $('#appScreen').classList.remove('hidden');
    toast(`Выбран персонаж: ${state.meta.characters[character_key].label}`);
    await loadAll();
  } catch (err) { toast(err.message, false); }
}
window.selectCharacter = selectCharacter;

async function loadAll() {
  try {
    const reqs = [
      api('/api/me'), api('/api/inventory'), api('/api/shop'), api('/api/recipes'), api('/api/market'),
      api('/api/leaderboard'), api('/api/items/all'), api('/api/bank/status'), api('/api/daily'), api('/api/quests'), api('/api/activity'),
    ];
    if (state.adminUnlocked) reqs.push(api('/api/admin/users'), api('/api/admin/logs'));
    const data = await Promise.all(reqs);
    [state.user, state.inventory, state.shop, state.recipes, state.market, state.leaderboard, state.itemDefs, state.bank, state.daily, state.quests, state.activity] = data;
    if (state.adminUnlocked) {
      state.adminUsers = data[data.length - 2];
      state.adminLogs = data[data.length - 1];
    }
    renderAll();
  } catch (err) { toast(err.message, false); }
}

function renderAll() {
  renderProfile();
  renderInventory();
  renderShop();
  renderExpeditions();
  renderDungeons();
  renderCrafts();
  renderMarket();
  renderBank();
  renderSocial();
  renderLeaderboard();
  renderAdmin();
  setScreen(state.currentScreen);
}

function renderProfile() {
  const u = state.user;
  const ch = state.meta.characters[u.character_key] || { label: 'Не выбран', abilities: [] };
  const eq = Object.values(u.equipment || {});
  const nextLevelExp = u.level >= 100 ? 1 : (80 + Math.min(50, u.level) * 22);
  $('#profileScreen').innerHTML = `
    <div class="stack">
      <div class="panel glow-card" style="padding:20px;">
        <div class="split-hero">
          <div>
            <div class="tag">${safe(ch.label)}</div>
            <h3 style="margin:.45rem 0">${safe(u.display_name)}</h3>
            <div class="muted">ID игрока: ${u.id} · VK ID: ${u.vk_user_id || '—'} · автор мира: Treninem</div>
            <div class="footer-note">${safe((ch.abilities || []).join(' · '))}</div>
          </div>
          <div class="small-card">
            <div class="muted">Основная валюта</div>
            <div class="value" style="font-size:1.5rem;font-weight:800;">🪙 ${u.gold}</div>
            <div class="footer-note">Кредит: ${state.bank?.debt || 0}</div>
          </div>
        </div>
        <hr />
        <div class="kpi-grid">
          <div class="kpi"><div class="muted">Уровень</div><div class="value">${u.level}</div></div>
          <div class="kpi"><div class="muted">PvP победы</div><div class="value">${u.pvp_wins}</div></div>
          <div class="kpi"><div class="muted">Слоты</div><div class="value">${u.inventory_slots}</div></div>
          <div class="kpi"><div class="muted">Лимит веса</div><div class="value">${u.weight_limit}</div></div>
        </div>
        <hr />
        <div class="stat-grid">
          <div class="stat-box"><span>HP</span><strong>${u.hp}/${u.max_hp}</strong></div>
          <div class="stat-box"><span>Энергия</span><strong>${u.energy}/${u.max_energy}</strong></div>
          <div class="stat-box"><span>Атака</span><strong>${u.attack}</strong></div>
          <div class="stat-box"><span>Защита</span><strong>${u.defense}</strong></div>
          <div class="stat-box"><span>Скорость</span><strong>${u.speed}</strong></div>
          <div class="stat-box"><span>Этаж подземелья</span><strong>${u.dungeon_level}</strong></div>
        </div>
        <div class="footer-note" style="margin-top:16px;">Опыт до следующего уровня</div>
        <div class="progress"><i style="width:${percent(u.exp, nextLevelExp)}%"></i></div>
      </div>

      <div class="section-grid">
        <div class="panel" style="padding:20px;">
          <h3>Ежедневная награда и задания</h3>
          <div class="stats-strip">
            <div class="small-card">
              <div class="muted">Дневной вход</div>
              <div class="value" style="font-weight:800;font-size:1.25rem;">${state.daily?.claimed ? 'Получено' : 'Готово'}</div>
              <div class="footer-note">Серия: ${state.daily?.streak || 0}</div>
              <div class="actions-row"><button class="primary-btn" ${state.daily?.claimed ? 'disabled' : ''} onclick="claimDaily()">Забрать</button></div>
            </div>
            <div class="small-card">
              <div class="muted">Сегодняшний бонус</div>
              <div class="footer-note">🪙 ${state.daily?.reward?.gold || 0} · XP ${state.daily?.reward?.exp || 0}</div>
              <div class="footer-note">Предмет: ${state.daily?.reward?.item_code || '—'}</div>
            </div>
            <div class="small-card">
              <div class="muted">События сегодня</div>
              <div class="footer-note">Экспедиций: ${u.activity_today?.expedition_win || 0}</div>
              <div class="footer-note">Крафт: ${u.activity_today?.craft_done || 0}</div>
              <div class="footer-note">Торговля: ${(u.activity_today?.market_sell || 0) + (u.activity_today?.market_buy || 0)}</div>
            </div>
            <div class="small-card">
              <div class="muted">Следующий сброс</div>
              <div class="footer-note">${fmtDate(state.daily?.next_reset_at)}</div>
            </div>
          </div>
          <hr />
          <div class="stack">
            ${state.quests.map(q => `
              <div class="list-item">
                <div>
                  <div class="list-item-title">${safe(q.title)}</div>
                  <div class="muted">Прогресс: ${q.progress}/${q.need}</div>
                  <div class="progress"><i style="width:${percent(q.progress, q.need)}%"></i></div>
                  <div class="footer-note">Награда: 🪙 ${q.reward_gold} · XP ${q.reward_exp}</div>
                </div>
                <div>
                  <button class="secondary-btn" ${(!q.completed || q.claimed) ? 'disabled' : ''} onclick="claimQuest('${q.code}')">${q.claimed ? 'Получено' : 'Забрать'}</button>
                </div>
              </div>`).join('') || '<div class="muted">Квесты скоро появятся.</div>'}
          </div>
        </div>
        <div class="panel" style="padding:20px;">
          <h3>Экипировка и события</h3>
          <div class="stack">
            ${eq.length ? eq.map(item => `<div class="list-item"><div><div class="list-item-title">${safe(item.icon)} ${safe(item.name)}</div><div class="muted">${safe(item.equip_slot)} · +${item.effect_value} ${safe(item.effect_stat)}</div></div></div>`).join('') : '<div class="muted">Экипировка пока не надета.</div>'}
          </div>
          <hr />
          <div class="stack">
            ${(state.activity || []).slice(0, 6).map(a => `<div class="list-item"><div><div class="list-item-title">${safe(activityText(a))}</div><div class="muted">${fmtDate(a.created_at)}</div></div></div>`).join('') || '<div class="muted">Пока нет событий.</div>'}
          </div>
        </div>
      </div>
    </div>`;
}

async function claimDaily() {
  try { const res = await api('/api/daily/claim', { method: 'POST' }); toast(res.message); await loadAll(); } catch (e) { toast(e.message, false); }
}
window.claimDaily = claimDaily;

async function claimQuest(quest_code) {
  try { const res = await api('/api/quests/claim', { method: 'POST', body: JSON.stringify({ quest_code }) }); toast(res.message); await loadAll(); } catch (e) { toast(e.message, false); }
}
window.claimQuest = claimQuest;

function renderInventory() {
  const q = state.filters.inventory.trim().toLowerCase();
  const items = state.inventory.filter(i => !q || [i.name, i.item_code, i.category, i.rarity].join(' ').toLowerCase().includes(q));
  $('#inventoryScreen').innerHTML = `
    <div class="panel" style="padding:20px;">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;">
        <h3>Инвентарь</h3>
        <div style="min-width:260px;"><input id="inventorySearch" placeholder="Поиск по названию, ID, редкости" value="${safe(state.filters.inventory)}" /></div>
      </div>
      <div class="footer-note">Всего записей: ${state.inventory.length}</div>
      <div class="list" style="margin-top:14px;">
        ${items.map(item => itemCard(item, `
          ${item.category !== 'material' ? `<button class="secondary-btn" onclick="useItem('${item.item_code}')">Использовать</button>` : ''}
          ${item.category === 'equipment' ? `<button class="secondary-btn" onclick="equipItem('${item.item_code}')">Экипировать</button>` : ''}
          <button class="secondary-btn" onclick="prepareMarket('${item.item_code}')">На рынок</button>
        `)).join('') || '<div class="muted">Ничего не найдено.</div>'}
      </div>
    </div>`;
  const input = $('#inventorySearch');
  if (input) input.oninput = (e) => { state.filters.inventory = e.target.value; renderInventory(); };
}

async function useItem(item_code) { try { const res = await api('/api/items/use', { method: 'POST', body: JSON.stringify({ item_code }) }); toast(res.message); await loadAll(); } catch (e) { toast(e.message, false); } }
async function equipItem(item_code) { try { const res = await api('/api/items/equip', { method: 'POST', body: JSON.stringify({ item_code }) }); toast(res.message); await loadAll(); } catch (e) { toast(e.message, false); } }
window.useItem = useItem; window.equipItem = equipItem;

function renderShop() {
  $('#shopScreen').innerHTML = `
    <div class="panel" style="padding:20px;">
      <h3>Магазин звериного мира</h3>
      <div class="table-like">
        <div class="table-head"><div>Предмет</div><div>Категория</div><div>Цена</div><div>Действие</div></div>
        ${state.shop.map(item => `
          <div class="table-row">
            <div><div class="list-item-title">${safe(item.icon)} ${safe(item.name)}</div><div class="muted">${safe(item.rarity)} · x${item.quantity}</div></div>
            <div>${safe(item.category)}</div>
            <div>🪙 ${item.price}</div>
            <div><button class="primary-btn" onclick="buyShop(${item.id})">Купить</button></div>
          </div>`).join('')}
      </div>
    </div>`;
}

async function buyShop(id) { try { const res = await api(`/api/shop/buy/${id}`, { method: 'POST' }); toast(res.message); await loadAll(); } catch (e) { toast(e.message, false); } }
window.buyShop = buyShop;

function renderExpeditions() {
  const cards = [
    ['easy', 'Лёгкая', 'Безопасный маршрут, быстрый откат'],
    ['normal', 'Нормальная', 'Хороший баланс наград'],
    ['hard', 'Сложная', 'Высокий риск, сильный лут'],
    ['nightmare', 'Кошмарная', 'Самые жирные награды'],
  ];
  $('#expeditionScreen').innerHTML = `<div class="card-grid">${cards.map(([key, label, text]) => `
    <div class="panel glow-card" style="padding:20px;">
      <div class="tag">${label}</div>
      <h3>${label} экспедиция</h3>
      <div class="footer-note">${text}</div>
      <div class="actions-row"><button class="primary-btn" onclick="runExpedition('${key}')">Отправиться</button></div>
    </div>`).join('')}</div>`;
}

async function runExpedition(difficulty) {
  try {
    const res = await api('/api/expedition', { method: 'POST', body: JSON.stringify({ difficulty }) });
    const msg = res.success ? `Успех! Шанс ${res.chance}. Награда: 🪙${res.reward.gold}, XP ${res.reward.exp}` : `Провал. Шанс был ${res.chance}`;
    toast(msg, res.success);
    await loadAll();
  } catch (e) { toast(e.message, false); }
}
window.runExpedition = runExpedition;

function renderDungeons() {
  const cards = [
    ['easy', 'Лёгкая', 'Рекомендуется с 25 уровня'],
    ['medium', 'Средняя', 'Рекомендуется с 50 уровня'],
    ['hard', 'Сложная', 'Рекомендуется с 75 уровня'],
  ];
  $('#dungeonScreen').innerHTML = `
    <div class="panel" style="padding:20px;">
      <div class="two-col">
        <label class="field"><span>Этаж подземелья</span><input id="dungeonFloorInput" type="number" min="1" max="15" value="${Math.min(15, state.user.dungeon_level || 1)}" /></label>
        <div class="small-card"><div class="muted">Личный рекорд</div><div class="value" style="font-size:1.35rem;font-weight:800;">${state.user.dungeon_level}</div></div>
      </div>
      <div class="card-grid" style="margin-top:14px;">
        ${cards.map(([key, label, note]) => `
          <div class="mini-card">
            <div class="tag">${label}</div>
            <h4>${label} режим</h4>
            <div class="footer-note">${note}</div>
            <div class="actions-row"><button class="primary-btn" onclick="runDungeon('${key}')">Войти</button></div>
          </div>`).join('')}
      </div>
    </div>`;
}

async function runDungeon(difficulty) {
  try {
    const floor = Number($('#dungeonFloorInput').value || 1);
    const res = await api('/api/dungeon', { method: 'POST', body: JSON.stringify({ floor, difficulty }) });
    const msg = res.success ? `Подземелье пройдено! Шанс ${res.chance}. Лут: 🪙${res.reward.gold}, XP ${res.reward.exp}` : `Не удалось пройти. Шанс ${res.chance}`;
    toast(msg, res.success);
    await loadAll();
  } catch (e) { toast(e.message, false); }
}
window.runDungeon = runDungeon;

function renderCrafts() {
  const q = state.filters.craft.trim().toLowerCase();
  const recipes = state.recipes.filter(r => !q || [r.recipe_code, r.name, r.result_item_code].join(' ').toLowerCase().includes(q));
  $('#craftScreen').innerHTML = `
    <div class="panel" style="padding:20px;">
      <div style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:center;">
        <h3>Крафт и алхимия</h3>
        <div style="min-width:260px;"><input id="craftSearch" placeholder="Поиск по рецепту или результату" value="${safe(state.filters.craft)}" /></div>
      </div>
      <div class="stack" style="margin-top:14px;">
        ${recipes.map(r => `
          <div class="list-item">
            <div>
              <div class="list-item-title">${safe(r.name)} <span class="tag">${safe(r.recipe_code)}</span></div>
              <div class="muted">Сложность: ${safe(r.difficulty)} · Результат: ${safe(r.result_item_code)} x${r.result_qty}</div>
              <div class="footer-note">Ингредиенты: ${r.ingredients.map(i => `${i.item_code} x${i.qty}`).join(' · ')}</div>
            </div>
            <div><button class="primary-btn" onclick="craftRecipe('${r.recipe_code}')">Создать</button></div>
          </div>`).join('') || '<div class="muted">Рецепты не найдены.</div>'}
      </div>
    </div>`;
  const input = $('#craftSearch');
  if (input) input.oninput = (e) => { state.filters.craft = e.target.value; renderCrafts(); };
}

async function craftRecipe(recipe_code) { try { const res = await api('/api/craft', { method: 'POST', body: JSON.stringify({ recipe_code }) }); toast(res.message); await loadAll(); } catch (e) { toast(e.message, false); } }
window.craftRecipe = craftRecipe;

function renderMarket() {
  const q = state.filters.market.trim().toLowerCase();
  const rarity = state.filters.marketRarity;
  const items = state.market.filter(i => {
    const hitsText = !q || [i.name, i.item_code, i.category, i.seller_name].join(' ').toLowerCase().includes(q);
    const hitsRarity = !rarity || i.rarity === rarity;
    return hitsText && hitsRarity;
  });
  const rarities = ['', 'trash', 'common', 'rare', 'epic', 'legendary', 'mythic'];
  $('#marketScreen').innerHTML = `
    <div class="section-grid">
      <div class="panel" style="padding:20px;">
        <div style="display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap;">
          <h3>Рынок игроков</h3>
          <div class="two-col" style="min-width:min(560px,100%);">
            <input id="marketSearch" placeholder="Поиск по имени, продавцу, ID" value="${safe(state.filters.market)}" />
            <select id="marketRarityFilter">${rarities.map(r => `<option value="${r}" ${r===rarity?'selected':''}>${r || 'Все редкости'}</option>`).join('')}</select>
          </div>
        </div>
        <div class="stack" style="margin-top:14px;">
          ${items.map(m => `
            <div class="list-item">
              <div>
                <div class="list-item-title">${safe(m.icon)} ${safe(m.name)} <span class="${rarityCls(m.rarity)}">${safe(m.rarity)}</span></div>
                <div class="muted">Продавец: ${safe(m.seller_name)} · Кол-во ${m.quantity} · ${safe(m.category)}</div>
                <div class="footer-note">${safe(m.description || '')}</div>
              </div>
              <div style="text-align:right;">
                <div class="tag">🪙 ${m.price}</div>
                <button class="primary-btn" onclick="buyListing(${m.id})">Купить</button>
              </div>
            </div>`).join('') || '<div class="muted">Нет доступных лотов.</div>'}
        </div>
      </div>
      <div class="panel" style="padding:20px;">
        <h3>Выставить предмет</h3>
        <label class="field"><span>ID предмета</span><input id="marketItemCode" placeholder="ID201001" /></label>
        <label class="field"><span>Количество</span><input id="marketQty" type="number" value="1" min="1" /></label>
        <label class="field"><span>Цена</span><input id="marketPrice" type="number" value="100" min="1" /></label>
        <button class="primary-btn" onclick="createListing()">Выставить лот</button>
        <div class="footer-note">Подсказка: в инвентаре можно нажать «На рынок», чтобы ID подставился автоматически.</div>
      </div>
    </div>`;
  $('#marketSearch').oninput = e => { state.filters.market = e.target.value; renderMarket(); };
  $('#marketRarityFilter').onchange = e => { state.filters.marketRarity = e.target.value; renderMarket(); };
}

function prepareMarket(item_code) { setScreen('market'); setTimeout(() => { const el = $('#marketItemCode'); if (el) el.value = item_code; }, 10); }
window.prepareMarket = prepareMarket;
async function createListing() { try { const res = await api('/api/market/create', { method: 'POST', body: JSON.stringify({ item_code: $('#marketItemCode').value.trim(), quantity: Number($('#marketQty').value), price: Number($('#marketPrice').value) }) }); toast(res.message); await loadAll(); } catch (e) { toast(e.message, false); } }
async function buyListing(listing_id) { try { const res = await api('/api/market/buy', { method: 'POST', body: JSON.stringify({ listing_id }) }); toast(res.message); await loadAll(); } catch (e) { toast(e.message, false); } }
window.createListing = createListing; window.buyListing = buyListing;

function renderBank() {
  const b = state.bank || { debt: 0, due_at: '', credit_limit: 0, can_take_credit: true };
  $('#bankScreen').innerHTML = `
    <div class="section-grid">
      <div class="panel" style="padding:20px;">
        <h3>Игровой банк</h3>
        <div class="kpi-grid">
          <div class="kpi"><div class="muted">Лимит кредита</div><div class="value">🪙 ${b.credit_limit}</div></div>
          <div class="kpi"><div class="muted">Текущий долг</div><div class="value">🪙 ${b.debt}</div></div>
          <div class="kpi"><div class="muted">Срок возврата</div><div class="value" style="font-size:1rem;">${b.due_at ? fmtDate(b.due_at) : '—'}</div></div>
          <div class="kpi"><div class="muted">Статус</div><div class="value" style="font-size:1rem;">${b.overdue ? 'Просрочен' : b.debt ? 'Активен' : 'Чисто'}</div></div>
        </div>
        <div class="actions-row" style="margin-top:16px;">
          <button class="primary-btn" ${b.can_take_credit ? '' : 'disabled'} onclick="takeCredit()">Взять кредит</button>
          <button class="secondary-btn" ${b.debt > 0 ? '' : 'disabled'} onclick="repayCredit()">Погасить полностью</button>
        </div>
      </div>
      <div class="panel" style="padding:20px;">
        <h3>Частичное погашение</h3>
        <label class="field"><span>Сумма</span><input id="bankRepayAmount" type="number" value="100" min="1" /></label>
        <button class="secondary-btn" ${b.debt > 0 ? '' : 'disabled'} onclick="repayCreditPartial()">Погасить часть</button>
        <div class="footer-note">В этой версии кредит выдаётся на 3 дня под фиксированный процент, один активный кредит за раз.</div>
      </div>
    </div>`;
}

async function takeCredit() { try { const res = await api('/api/bank/credit', { method: 'POST' }); toast(res.message); await loadAll(); } catch (e) { toast(e.message, false); } }
async function repayCredit() { try { const res = await api('/api/bank/repay', { method: 'POST', body: JSON.stringify({ amount: null }) }); toast(res.message); await loadAll(); } catch (e) { toast(e.message, false); } }
async function repayCreditPartial() { try { const res = await api('/api/bank/repay', { method: 'POST', body: JSON.stringify({ amount: Number($('#bankRepayAmount').value || 0) }) }); toast(res.message); await loadAll(); } catch (e) { toast(e.message, false); } }
window.takeCredit = takeCredit; window.repayCredit = repayCredit; window.repayCreditPartial = repayCreditPartial;

function renderSocial() {
  $('#socialScreen').innerHTML = `
    <div class="section-grid">
      <div class="panel" style="padding:20px;">
        <h3>Друзья VK и подарки</h3>
        <div class="actions-row">
          <button class="primary-btn" onclick="requestInvite()">Открыть приглашения VK</button>
          <button class="secondary-btn" onclick="pickVkFriend()">Выбрать друга VK</button>
          <button class="secondary-btn" onclick="sendVkRequest()">Отправить VK-запрос</button>
        </div>
        <hr />
        <div class="two-col">
          <label class="field"><span>ID игрока</span><input id="socialUserId" type="number" placeholder="2" /></label>
          <label class="field"><span>ID предмета</span><input id="socialItemCode" placeholder="ID101001" /></label>
        </div>
        <div class="two-col">
          <label class="field"><span>Количество</span><input id="socialQty" type="number" value="1" min="1" /></label>
          <div class="field"><span>&nbsp;</span><button class="primary-btn" onclick="sendGift()">Подарить</button></div>
        </div>
      </div>
      <div class="panel" style="padding:20px;">
        <h3>Android синхронизация</h3>
        <div class="footer-note">Сгенерируй одноразовый код, затем введи его в Android-приложении. Этот же код покажется в левой панели.</div>
        <div class="actions-row">
          <button class="primary-btn" onclick="generateAndroidCode()">Получить код</button>
        </div>
        <div id="androidCodeBox2" class="hint-box hidden" style="margin-top:12px;"></div>
      </div>
    </div>`;
}

async function sendGift() {
  try {
    const res = await api('/api/gift', { method: 'POST', body: JSON.stringify({
      to_user_id: Number($('#socialUserId').value), item_code: $('#socialItemCode').value.trim(), quantity: Number($('#socialQty').value || 1),
    }) });
    toast(res.message); await loadAll();
  } catch (e) { toast(e.message, false); }
}
window.sendGift = sendGift;

async function generateAndroidCode() {
  try {
    const res = await api('/api/link-code', { method: 'POST' });
    const text = `Код: ${res.code} · действует ${res.expires_minutes} мин.`;
    ['#androidCodeBox', '#androidCodeBox2'].forEach(sel => {
      const el = $(sel); if (el) { el.textContent = text; el.classList.remove('hidden'); }
    });
    toast('Код синхронизации создан');
  } catch (e) { toast(e.message, false); }
}
window.generateAndroidCode = generateAndroidCode;

async function requestInvite() {
  try { await window.vkBridge.send('VKWebAppShowInviteBox'); toast('Открыт список приглашений'); }
  catch { toast('Не удалось открыть список приглашений VK', false); }
}
window.requestInvite = requestInvite;

async function pickVkFriend() {
  try {
    const friends = await window.vkBridge.send('VKWebAppGetFriends');
    const friend = (friends?.users && friends.users[0]) || null;
    if (!friend) return toast('Друг не выбран', false);
    $('#socialUserId').value = friend.id;
    toast(`Выбран друг VK: ${friend.first_name || ''} ${friend.last_name || ''}`.trim());
  } catch { toast('Не удалось получить список друзей VK', false); }
}
window.pickVkFriend = pickVkFriend;

async function sendVkRequest() {
  try {
    const friendId = Number($('#socialUserId').value || 0);
    if (!friendId) return toast('Сначала укажи VK ID друга или выбери его', false);
    await window.vkBridge.send('VKWebAppShowRequestBox', { uid: friendId, message: 'Пойдём в Beast Legends!' });
    toast('VK-запрос отправлен');
  } catch { toast('Не удалось отправить VK-запрос', false); }
}
window.sendVkRequest = sendVkRequest;

function renderLeaderboard() {
  const block = (title, arr, field, suffix = '') => `
    <div class="panel" style="padding:20px;">
      <h3>${title}</h3>
      <div class="stack">
        ${arr.map((u, idx) => `<div class="list-item"><div><div class="list-item-title">#${idx + 1} ${safe(u.display_name)}</div><div class="muted">LVL ${u.level}</div></div><div class="tag">${u[field]}${suffix}</div></div>`).join('') || '<div class="muted">Пока пусто.</div>'}
      </div>
    </div>`;
  $('#leaderboardScreen').innerHTML = `
    <div class="three-col">
      ${block('По уровню', state.leaderboard.level, 'level')}
      ${block('По победам PvP', state.leaderboard.pvp, 'pvp_wins')}
      ${block('Самые богатые', state.leaderboard.gold, 'gold', ' 🪙')}
    </div>`;
}

function fillSelect(selector, values) {
  const el = $(selector); if (!el) return;
  el.innerHTML = values.map(v => `<option value="${safe(v)}">${safe(v || '—')}</option>`).join('');
}

function renderAdmin() {
  $('#adminScreen').innerHTML = `
    <div class="stack">
      <div class="panel glow-card" style="padding:20px;">
        <h3>Секретная админ-панель</h3>
        ${state.adminUnlocked ? '<div class="tag">Доступ открыт</div>' : `
          <div class="field"><span>Пароль</span><input id="adminPassword" type="password" placeholder="секретный пароль" /></div>
          <button class="primary-btn" onclick="unlockAdmin()">Войти</button>`}
        <div class="footer-note">Через панель можно выдавать золото и предметы, банить, менять уровни, назначать админов, удалять предметы у игроков и создавать новые предметы с сохранением в базе.</div>
      </div>
      ${state.adminUnlocked ? `
        <div class="section-grid">
          <div class="panel" style="padding:20px;">
            <h3>Управление игроками</h3>
            <div class="three-col">
              <label class="field"><span>ID игрока</span><input id="adminTargetId" type="number" value="${state.user.id}" /></label>
              <label class="field"><span>Золото</span><input id="adminGoldAmount" type="number" value="1000" /></label>
              <div class="field"><span>&nbsp;</span><button class="secondary-btn" onclick="adminGiveGold()">Выдать золото</button></div>
            </div>
            <div class="three-col">
              <label class="field"><span>ID предмета</span><input id="adminGiveItemCode" placeholder="ID201001" /></label>
              <label class="field"><span>Кол-во</span><input id="adminGiveQty" type="number" value="1" /></label>
              <div class="field"><span>&nbsp;</span><button class="secondary-btn" onclick="adminGiveItem()">Выдать предмет</button></div>
            </div>
            <div class="three-col">
              <label class="field"><span>ID предмета для удаления</span><input id="adminRemoveItemCode" placeholder="ID201001" /></label>
              <label class="field"><span>Кол-во</span><input id="adminRemoveQty" type="number" value="1" /></label>
              <div class="field"><span>&nbsp;</span><button class="secondary-btn" onclick="adminRemoveItem()">Удалить предмет</button></div>
            </div>
            <div class="two-col">
              <label class="field"><span>Уровень</span><input id="adminLevel" type="number" value="50" /></label>
              <div class="field"><span>&nbsp;</span><button class="secondary-btn" onclick="adminSetLevel()">Поставить уровень</button></div>
            </div>
            <div class="actions-row">
              <button class="secondary-btn" onclick="adminBan(true)">Забанить</button>
              <button class="secondary-btn" onclick="adminBan(false)">Разбанить</button>
              <button class="secondary-btn" onclick="adminSetAdmin(true)">Выдать админку</button>
              <button class="secondary-btn" onclick="adminSetAdmin(false)">Снять админку</button>
            </div>
            <hr />
            <h3>Создание нового предмета</h3>
            <div id="adminCreateItemForm"></div>
            <hr />
            <h3>Удаление кастомного предмета</h3>
            <div class="two-col">
              <label class="field"><span>ID кастомного предмета</span><input id="adminDeleteDefCode" placeholder="ID509999" /></label>
              <div class="field"><span>&nbsp;</span><button class="secondary-btn" onclick="adminDeleteItemDef()">Удалить из игры</button></div>
            </div>
          </div>
          <div class="stack">
            <div class="panel" style="padding:20px;">
              <h3>Игроки</h3>
              <div class="stack">
                ${state.adminUsers.map(u => `<div class="list-item"><div><div class="list-item-title">${safe(u.display_name)}</div><div class="muted">ID ${u.id} · LVL ${u.level} · долг ${u.bank_debt}</div></div><div><span class="tag">🪙 ${u.gold}</span>${u.is_admin ? '<span class="tag">админ</span>' : ''}${u.is_banned ? '<span class="tag">бан</span>' : ''}</div></div>`).join('') || '<div class="muted">Пусто</div>'}
              </div>
            </div>
            <div class="panel" style="padding:20px;">
              <h3>Журнал админ-действий</h3>
              <div class="stack">
                ${state.adminLogs.map(l => `<div class="list-item"><div><div class="list-item-title">${safe(l.action)}</div><div class="muted">${safe(l.actor_name || 'system')} · ${fmtDate(l.created_at)}</div><div class="footer-note">${safe(JSON.stringify(l.details))}</div></div></div>`).join('') || '<div class="muted">Логов пока нет.</div>'}
              </div>
            </div>
          </div>
        </div>` : ''}
    </div>`;
  if (state.adminUnlocked) renderAdminItemForm();
}

function renderAdminItemForm() {
  const root = $('#adminCreateItemForm');
  if (!root) return;
  root.innerHTML = `
    <div class="two-col">
      <label class="field"><span>Новый ID</span><input id="newItemCode" placeholder="ID509999" /></label>
      <label class="field"><span>Название</span><input id="newItemName" placeholder="Свиток царской сумки" /></label>
    </div>
    <div class="two-col">
      <label class="field"><span>Категория</span><select id="newItemCategory"></select></label>
      <label class="field"><span>Редкость</span><select id="newItemRarity"></select></label>
    </div>
    <label class="field"><span>Описание</span><textarea id="newItemDescription" placeholder="Что делает предмет"></textarea></label>
    <div class="three-col">
      <label class="field"><span>Вес</span><input id="newItemWeight" type="number" step="0.1" value="0.2" /></label>
      <label class="field"><span>Цена</span><input id="newItemPrice" type="number" value="200" /></label>
      <label class="field"><span>Иконка</span><input id="newItemIcon" value="✨" /></label>
    </div>
    <div class="two-col">
      <label class="field"><span>Тип эффекта</span><select id="newItemEffectKind"></select></label>
      <label class="field"><span>Какой параметр меняет</span><select id="newItemEffectStat"></select></label>
    </div>
    <div class="three-col">
      <label class="field"><span>Значение</span><input id="newItemEffectValue" type="number" value="10" /></label>
      <label class="field"><span>Длительность</span><input id="newItemEffectDuration" type="number" value="0" /></label>
      <label class="field"><span>Слот экипировки</span><select id="newItemEquipSlot"></select></label>
    </div>
    <div class="two-col">
      <label class="field"><span>Расходуемый</span><select id="newItemConsumable"><option value="0">нет</option><option value="1">да</option></select></label>
      <label class="field"><span>Стакается</span><select id="newItemStackable"><option value="1">да</option><option value="0">нет</option></select></label>
    </div>
    <button class="primary-btn" onclick="adminCreateItem()">Создать и сохранить предмет</button>`;
  api('/api/admin/item-options').then(opts => {
    fillSelect('#newItemCategory', opts.categories);
    fillSelect('#newItemRarity', opts.rarities);
    fillSelect('#newItemEffectKind', opts.effect_kinds);
    fillSelect('#newItemEffectStat', opts.stats);
    fillSelect('#newItemEquipSlot', opts.equip_slots);
  }).catch(err => toast(err.message, false));
}

async function unlockAdmin() { try { await api('/api/admin/auth', { method: 'POST', body: JSON.stringify({ password: $('#adminPassword').value }) }); state.adminUnlocked = true; toast('Админка разблокирована'); await loadAll(); } catch (e) { toast(e.message, false); } }
window.unlockAdmin = unlockAdmin;
const adminTarget = () => Number($('#adminTargetId').value || 0);
async function adminGiveGold() { try { await api('/api/admin/give-gold', { method: 'POST', body: JSON.stringify({ target_user_id: adminTarget(), amount: Number($('#adminGoldAmount').value) }) }); toast('Золото выдано'); await loadAll(); } catch (e) { toast(e.message, false); } }
async function adminGiveItem() { try { await api('/api/admin/give-item', { method: 'POST', body: JSON.stringify({ target_user_id: adminTarget(), item_code: $('#adminGiveItemCode').value.trim(), quantity: Number($('#adminGiveQty').value) }) }); toast('Предмет выдан'); await loadAll(); } catch (e) { toast(e.message, false); } }
async function adminRemoveItem() { try { await api('/api/admin/remove-item', { method: 'POST', body: JSON.stringify({ target_user_id: adminTarget(), item_code: $('#adminRemoveItemCode').value.trim(), quantity: Number($('#adminRemoveQty').value) }) }); toast('Предмет удалён'); await loadAll(); } catch (e) { toast(e.message, false); } }
async function adminBan(banned) { try { await api('/api/admin/ban', { method: 'POST', body: JSON.stringify({ target_user_id: adminTarget(), banned }) }); toast(banned ? 'Игрок забанен' : 'Игрок разбанен'); await loadAll(); } catch (e) { toast(e.message, false); } }
async function adminSetLevel() { try { await api('/api/admin/set-level', { method: 'POST', body: JSON.stringify({ target_user_id: adminTarget(), level: Number($('#adminLevel').value) }) }); toast('Уровень изменён'); await loadAll(); } catch (e) { toast(e.message, false); } }
async function adminSetAdmin(is_admin) { try { await api('/api/admin/set-admin', { method: 'POST', body: JSON.stringify({ target_user_id: adminTarget(), is_admin }) }); toast(is_admin ? 'Админка выдана' : 'Админка снята'); await loadAll(); } catch (e) { toast(e.message, false); } }
async function adminCreateItem() {
  try {
    const payload = {
      item_code: $('#newItemCode').value.trim(), name: $('#newItemName').value.trim(), category: $('#newItemCategory').value,
      rarity: $('#newItemRarity').value, description: $('#newItemDescription').value, weight: Number($('#newItemWeight').value),
      price: Number($('#newItemPrice').value), effect_kind: $('#newItemEffectKind').value, effect_stat: $('#newItemEffectStat').value,
      effect_value: Number($('#newItemEffectValue').value), effect_duration: Number($('#newItemEffectDuration').value),
      equip_slot: $('#newItemEquipSlot').value, is_consumable: Number($('#newItemConsumable').value), is_stackable: Number($('#newItemStackable').value),
      icon: $('#newItemIcon').value || '✨',
    };
    await api('/api/admin/create-item', { method: 'POST', body: JSON.stringify(payload) });
    toast('Новый предмет создан и сохранён в базе');
    await loadAll();
  } catch (e) { toast(e.message, false); }
}
async function adminDeleteItemDef() { try { await api('/api/admin/delete-item-def', { method: 'POST', body: JSON.stringify({ item_code: $('#adminDeleteDefCode').value.trim() }) }); toast('Кастомный предмет удалён из игры'); await loadAll(); } catch (e) { toast(e.message, false); } }
window.adminGiveGold = adminGiveGold; window.adminGiveItem = adminGiveItem; window.adminRemoveItem = adminRemoveItem; window.adminBan = adminBan; window.adminSetLevel = adminSetLevel; window.adminSetAdmin = adminSetAdmin; window.adminCreateItem = adminCreateItem; window.adminDeleteItemDef = adminDeleteItemDef;

function setupUi() {
  $('#vkLoginBtn').onclick = loginWithVK;
  $('#devLoginBtn').onclick = devLogin;
  $('#syncBtn').onclick = loadAll;
  $('#inviteFriendsBtn').onclick = requestInvite;
  $('#generateLinkBtn').onclick = generateAndroidCode;
  $('#soundToggleBtn').onclick = () => {
    state.sound = !state.sound;
    $('#soundToggleBtn').textContent = `Звук: ${state.sound ? 'Вкл' : 'Выкл'}`;
    tone(state.sound ? 720 : 180, 0.05, 'triangle');
  };
  $$('.nav-btn, .mobile-nav button').forEach(btn => btn.onclick = () => setScreen(btn.dataset.screen));
}

(async function init() {
  setupUi();
  await loadMeta();
  await tryAutoLogin();
})();
