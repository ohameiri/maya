/* ============================================
   Profile & saved trips — localStorage
   ============================================ */

const STORE_KEYS = {
    profile: 'maya.profile',
    saved: 'maya.savedTrips'
};

function loadProfile() {
    try {
        const raw = localStorage.getItem(STORE_KEYS.profile);
        return raw ? JSON.parse(raw) : null;
    } catch { return null; }
}

function saveProfile(profile) {
    try { localStorage.setItem(STORE_KEYS.profile, JSON.stringify(profile)); } catch {}
}

function loadSavedTrips() {
    try {
        const raw = localStorage.getItem(STORE_KEYS.saved);
        return raw ? JSON.parse(raw) : [];
    } catch { return []; }
}

function saveTripToStore(plan) {
    const list = loadSavedTrips();
    const entry = {
        id: 't_' + Date.now(),
        savedAt: new Date().toISOString(),
        trail: plan.trail,
        profile: plan.profile,
        prefs: plan.prefs,
        restaurant: plan.restaurant
    };
    list.unshift(entry);
    try { localStorage.setItem(STORE_KEYS.saved, JSON.stringify(list.slice(0, 30))); } catch {}
    return entry;
}

function deleteSavedTrip(id) {
    const list = loadSavedTrips().filter(t => t.id !== id);
    try { localStorage.setItem(STORE_KEYS.saved, JSON.stringify(list)); } catch {}
}

window.loadProfile = loadProfile;
window.saveProfile = saveProfile;
window.loadSavedTrips = loadSavedTrips;
window.saveTripToStore = saveTripToStore;
window.deleteSavedTrip = deleteSavedTrip;
