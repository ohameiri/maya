/* ============================================
   App controller — מאיה
   ============================================ */

const SCREENS = ['welcome', 'wizard', 'suggestions', 'plan', 'saved'];
const $ = (id) => document.getElementById(id);

let LAST_FILTERED = [];
let CURRENT_PLAN = null;

function showScreen(name) {
    SCREENS.forEach(s => {
        const el = $('screen-' + s);
        if (el) el.classList.toggle('hidden', s !== name);
    });
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function toast(message) {
    const el = $('toast');
    el.textContent = message;
    el.classList.add('show');
    clearTimeout(el._t);
    el._t = setTimeout(() => el.classList.remove('show'), 2200);
}

/* ---------- Suggestions ---------- */
function showSuggestions(state) {
    const profile = {
        ages: state.ages,
        stroller: state.stroller,
        pet: state.pet,
        limits: state.limits
    };
    const prefs = {
        region: state.region,
        type: state.type,
        date: state.date,
        time: state.time,
        duration: state.duration
    };
    LAST_FILTERED = filterTrails(profile, prefs);
    renderSuggestions(profile, prefs);
    showScreen('suggestions');
}

function renderSuggestions(profile, prefs) {
    const grid = $('suggestions-grid');
    const sub = $('suggestions-sub');
    if (LAST_FILTERED.length === 0) {
        grid.innerHTML = `
            <div class="glass" style="padding:30px;text-align:center;grid-column:1/-1">
                <p style="font-size:1.1rem;color:var(--ink-soft);margin-bottom:14px">
                    לא מצאנו מסלול שעונה על כל ההגדרות 😬
                </p>
                <p style="color:var(--ink-mute)">נסה להוריד מגבלה אחת או לשנות אזור.</p>
            </div>`;
        sub.textContent = '';
        return;
    }
    const count = LAST_FILTERED.length;
    sub.textContent = `מצאנו ${count} מסלולים שמתאימים. לחץ/י על אחד כדי לבנות לו תוכנית מלאה.`;
    grid.innerHTML = LAST_FILTERED.map((entry, idx) => {
        const t = entry.trail;
        const reasonTags = entry.reasons
            .slice(0, 3)
            .map(r => `<span class="tag ${r.kind}">${r.tag}</span>`)
            .join('');
        return `
            <div class="suggestion-card" data-idx="${idx}">
                <div class="sc-region">${t.regionName}</div>
                <div class="sc-name">${t.name}</div>
                <div class="sc-desc">${truncate(t.description, 110)}</div>
                <div class="sc-meta">
                    <span>📏 ${t.distance_km} ק"מ</span>
                    <span>⛰ ${t.ascent_m} מ' עלייה</span>
                    <span>⏱ ${formatDuration(t.duration_min)}</span>
                    <span>${'🟢'.repeat(t.difficulty)}${'⚪'.repeat(5 - t.difficulty)}</span>
                </div>
                <div class="sc-tags">${reasonTags}</div>
                <div class="sc-pick">לתכנן את הטיול הזה →</div>
            </div>`;
    }).join('');

    grid.querySelectorAll('.suggestion-card').forEach(card => {
        card.addEventListener('click', async () => {
            const idx = Number(card.dataset.idx);
            const trail = LAST_FILTERED[idx].trail;
            await openPlan(trail, profile, prefs);
        });
    });
}

/* ---------- Plan ---------- */
async function openPlan(trail, profile, prefs) {
    showScreen('plan');
    // Show loading skeleton
    $('plan-explain').innerHTML = `<div class="loading-line"><div class="spinner"></div> בונה את התוכנית — מושך מזג אוויר חי...</div>`;
    $('card-trail').innerHTML = '';
    $('card-weather').innerHTML = '';
    $('card-restaurant').innerHTML = '';
    $('card-equipment').innerHTML = '';

    try {
        const plan = await buildPlan(trail, profile, prefs);
        CURRENT_PLAN = plan;
        renderPlan(plan);
    } catch (err) {
        console.error(err);
        $('plan-explain').innerHTML = `⚠️ לא הצלחנו לטעון את מזג האוויר. נסה שוב או בחר תאריך אחר.`;
    }
}

function renderPlan(plan) {
    $('plan-explain').innerHTML = plan.explanation;
    $('card-trail').innerHTML = renderTrailCard(plan);
    $('card-weather').innerHTML = renderWeatherCard(plan);
    $('card-restaurant').innerHTML = renderRestaurantCard(plan);
    $('card-equipment').innerHTML = renderEquipmentCard(plan);
    bindEquipmentCheckboxes();
}

function renderTrailCard(plan) {
    const t = plan.trail;
    const pips = Array.from({ length: 5 }, (_, i) =>
        `<span class="pip ${i < t.difficulty ? 'on' : ''}"></span>`
    ).join('');
    return `
        <div class="card-title">🥾 המסלול</div>
        <div class="trail-hero">
            <div>
                <div class="trail-name">${t.name}</div>
                <div class="trail-region">${t.regionName}</div>
            </div>
            <div class="trail-difficulty" title="דרגת קושי">
                ${pips}
            </div>
        </div>
        <div class="trail-stats">
            <div class="trail-stat"><div class="v">${t.distance_km}</div><div class="l">ק"מ</div></div>
            <div class="trail-stat"><div class="v">${t.ascent_m}</div><div class="l">מ' עלייה</div></div>
            <div class="trail-stat"><div class="v">${formatDuration(t.duration_min)}</div><div class="l">משך</div></div>
            <div class="trail-stat"><div class="v">${t.flags.circular ? 'מעגלי' : 'לינארי'}</div><div class="l">סוג</div></div>
        </div>
        <p class="trail-desc">${t.description}</p>
        <div class="trail-actions">
            <a class="waze-btn" href="${wazeLink(t.start.lat, t.start.lon)}" target="_blank" rel="noopener">
                <span class="wi">🧭</span> Waze לנקודת התחלה
            </a>
            ${t.flags.circular ? '' : `
                <a class="waze-btn" href="${wazeLink(t.end.lat, t.end.lon)}" target="_blank" rel="noopener">
                    <span class="wi">🏁</span> Waze לנקודת סיום
                </a>`}
        </div>
    `;
}

function renderWeatherCard(plan) {
    const w = plan.weather;
    const hourly = w.hourly.map(h => `
        <div class="hr">
            <div class="h">${String(h.hour).padStart(2,'0')}:00</div>
            <div class="t">${h.temp}°</div>
            ${h.precip > 10 ? `<div class="p">${h.precip}%</div>` : '<div class="p">&nbsp;</div>'}
        </div>
    `).join('');
    const alerts = w.alerts.length
        ? `<div class="weather-alert">${w.alerts.join('<br>')}</div>`
        : '';
    return `
        <div class="card-title">🌤️ מזג אוויר ל-${prettyDate(plan.prefs.date)}</div>
        <div class="weather-now">
            <div class="w-icon">${w.icon}</div>
            <div>
                <div class="w-temp">${w.maxTemp}° / ${w.minTemp}°</div>
                <div class="w-meta">${w.label}</div>
            </div>
        </div>
        <div class="weather-grid">
            <div class="wg"><div class="v">${w.precipMax}%</div><div class="l">סיכוי גשם</div></div>
            <div class="wg"><div class="v">${w.wind}</div><div class="l">רוח קמ"ש</div></div>
            <div class="wg"><div class="v">UV ${w.uv}</div><div class="l">קרינה</div></div>
        </div>
        <div class="w-meta" style="margin-bottom:10px">🌅 ${w.sunrise} · 🌇 ${w.sunset}</div>
        <div class="weather-hourly">${hourly}</div>
        ${alerts}
    `;
}

function renderRestaurantCard(plan) {
    const r = plan.restaurant;
    if (!r) {
        return `<div class="card-title">🍽️ מסעדה לסיום</div><p style="color:var(--ink-soft)">לא מצאנו המלצה מתאימה באזור.</p>`;
    }
    const distance = r.distance ? `<span>📍 ${r.distance.toFixed(1)} ק"מ מסיום המסלול</span>` : '';
    const phoneNum = r.phone.replace(/[^0-9]/g, '');
    return `
        <div class="card-title">🍽️ מסעדה לסיום</div>
        <div class="rest-name">${r.name}</div>
        <div class="rest-cuisine">${r.cuisine}</div>
        <div class="rest-meta">
            ${distance}
            <span>🕒 ${r.hours}</span>
            ${r.kosher ? '<span>✡ כשר</span>' : ''}
            ${r.kidFriendly ? '<span>👶 ידידותי לילדים</span>' : ''}
            ${r.vegan ? '<span>🌱 אופציות טבעוניות</span>' : ''}
            <span>${'💰'.repeat(r.priceTier)}</span>
        </div>
        <p class="rest-desc">${r.notes}</p>
        <div class="rest-actions">
            <a class="waze-btn" href="${wazeLink(r.lat, r.lon)}" target="_blank" rel="noopener">
                <span class="wi">🧭</span> Waze למסעדה
            </a>
            <a class="call-btn" href="tel:${phoneNum}">
                <span>📞</span> ${r.phone}
            </a>
        </div>
    `;
}

function renderEquipmentCard(plan) {
    const groups = plan.equipment;
    const groupsHtml = groups.map(g => `
        <div class="eq-group">
            <h4>${g.title}</h4>
            <ul class="eq-list">
                ${g.items.map((it, idx) => `
                    <li class="eq-item ${it.urgent ? 'urgent' : ''}">
                        <input type="checkbox" data-eq="${g.title}-${idx}">
                        <label>${it.name}</label>
                        ${it.reason ? `<span class="eq-reason">${it.reason}</span>` : ''}
                    </li>
                `).join('')}
            </ul>
        </div>
    `).join('');
    return `
        <div class="card-title">🧳 רשימת הציוד</div>
        <div class="eq-groups">${groupsHtml}</div>
        <p style="margin-top:14px;color:var(--ink-mute);font-size:0.85rem">
            הרשימה התאמנו לפי הפרופיל שלך, מזג האוויר וסוג המסלול. סימון מציין שזה חיוני מאוד.
        </p>
    `;
}

function bindEquipmentCheckboxes() {
    document.querySelectorAll('.eq-item input[type=checkbox]').forEach(cb => {
        cb.addEventListener('change', () => {
            cb.closest('.eq-item').classList.toggle('checked', cb.checked);
        });
    });
}

/* ---------- Saved trips ---------- */
function renderSavedScreen() {
    const list = loadSavedTrips();
    const wrap = $('saved-list');
    if (list.length === 0) {
        wrap.innerHTML = `<div class="saved-empty glass" style="grid-column:1/-1;padding:30px">
            עדיין לא שמרת אף טיול. תכנן אחד וסמן "שמור" 🌿
        </div>`;
        return;
    }
    wrap.innerHTML = list.map(it => `
        <div class="saved-item glass" data-id="${it.id}">
            <div class="si-date">${prettyDate(it.prefs.date)} · נשמר ${prettyDateTime(it.savedAt)}</div>
            <div class="si-name">${it.trail.name}</div>
            <div class="si-region">${it.trail.regionName} · ${it.restaurant ? it.restaurant.name : 'ללא מסעדה'}</div>
            <div class="saved-actions">
                <button data-action="open">פתח שוב</button>
                <button data-action="delete">מחק</button>
            </div>
        </div>
    `).join('');

    wrap.querySelectorAll('.saved-item').forEach(card => {
        const id = card.dataset.id;
        const entry = list.find(t => t.id === id);
        card.querySelector('[data-action=open]').addEventListener('click', async () => {
            await openPlan(entry.trail, entry.profile, entry.prefs);
        });
        card.querySelector('[data-action=delete]').addEventListener('click', () => {
            if (confirm('למחוק את הטיול השמור?')) {
                deleteSavedTrip(id);
                renderSavedScreen();
                toast('הטיול נמחק');
            }
        });
    });
}

/* ---------- Utils ---------- */
function truncate(s, n) {
    if (!s) return '';
    return s.length > n ? s.slice(0, n - 1).trim() + '…' : s;
}
function formatDuration(min) {
    if (min < 60) return `${min} דק'`;
    const h = Math.floor(min / 60);
    const m = min % 60;
    return m === 0 ? `${h} שע'` : `${h}:${String(m).padStart(2,'0')} שע'`;
}
function prettyDate(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    return d.toLocaleDateString('he-IL', { weekday: 'long', day: 'numeric', month: 'long' });
}
function prettyDateTime(iso) {
    const d = new Date(iso);
    return d.toLocaleDateString('he-IL', { day: 'numeric', month: 'numeric' }) + ' ' +
           d.toLocaleTimeString('he-IL', { hour: '2-digit', minute: '2-digit' });
}

/* ---------- Wire up ---------- */
function init() {
    wizardInit();

    $('btn-start').addEventListener('click', () => {
        wizardReset();
        showScreen('wizard');
    });
    $('btn-saved-from-hero').addEventListener('click', () => {
        renderSavedScreen();
        showScreen('saved');
    });
    $('nav-saved').addEventListener('click', () => {
        renderSavedScreen();
        showScreen('saved');
    });
    $('brand-home').addEventListener('click', () => showScreen('welcome'));

    $('btn-back-to-wizard').addEventListener('click', () => showScreen('wizard'));
    $('btn-back-to-suggestions').addEventListener('click', () => showScreen('suggestions'));
    $('btn-new-from-saved').addEventListener('click', () => {
        wizardReset();
        showScreen('wizard');
    });

    $('btn-save-trip').addEventListener('click', () => {
        if (!CURRENT_PLAN) return;
        saveTripToStore(CURRENT_PLAN);
        toast('הטיול נשמר ✨');
    });

    showScreen('welcome');
}

document.addEventListener('DOMContentLoaded', init);
