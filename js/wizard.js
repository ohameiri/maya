/* ============================================
   Wizard — שלבי השאלות
   ============================================ */

const WIZARD = {
    totalSteps: 4,
    currentStep: 1,
    state: {
        ages: [],
        stroller: false,
        pet: false,
        limits: [],
        date: '',
        duration: 'half',
        time: '08:00',
        region: 'any',
        type: 'any'
    }
};

function wizardInit() {
    // Default the date to tomorrow
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    const isoDate = tomorrow.toISOString().slice(0, 10);
    const dateInput = document.getElementById('trip-date');
    dateInput.value = isoDate;
    dateInput.min = new Date().toISOString().slice(0, 10);
    const maxDate = new Date();
    maxDate.setDate(maxDate.getDate() + 14);
    dateInput.max = maxDate.toISOString().slice(0, 10);
    WIZARD.state.date = isoDate;

    // Restore saved profile preferences
    const saved = loadProfile();
    if (saved) {
        WIZARD.state.ages = saved.ages || [];
        WIZARD.state.stroller = !!saved.stroller;
        WIZARD.state.pet = !!saved.pet;
        WIZARD.state.limits = saved.limits || [];
    }

    wizardApplyStateToDOM();
    wizardBindEvents();
    wizardRender();
}

function wizardApplyStateToDOM() {
    document.querySelectorAll('[data-group]').forEach(group => {
        const key = group.dataset.group;
        const val = WIZARD.state[key];
        group.querySelectorAll('.chip-select').forEach(btn => {
            const v = btn.dataset.value;
            const isMulti = Array.isArray(val);
            const isOn = isMulti ? val.includes(v) : val === v;
            btn.classList.toggle('selected', isOn);
        });
    });
    document.getElementById('opt-stroller').checked = WIZARD.state.stroller;
    document.getElementById('opt-pet').checked = WIZARD.state.pet;
    document.querySelectorAll('[data-limit]').forEach(cb => {
        cb.checked = WIZARD.state.limits.includes(cb.dataset.limit);
    });
    document.getElementById('trip-time').value = WIZARD.state.time;
}

function wizardBindEvents() {
    // Chip groups
    document.querySelectorAll('[data-group]').forEach(group => {
        const key = group.dataset.group;
        const isMulti = Array.isArray(WIZARD.state[key]);
        group.querySelectorAll('.chip-select').forEach(btn => {
            btn.addEventListener('click', () => {
                const v = btn.dataset.value;
                if (isMulti) {
                    const arr = WIZARD.state[key];
                    const idx = arr.indexOf(v);
                    if (idx > -1) arr.splice(idx, 1);
                    else arr.push(v);
                } else {
                    WIZARD.state[key] = v;
                }
                wizardApplyStateToDOM();
            });
        });
    });

    // Toggles
    document.getElementById('opt-stroller').addEventListener('change', e => {
        WIZARD.state.stroller = e.target.checked;
    });
    document.getElementById('opt-pet').addEventListener('change', e => {
        WIZARD.state.pet = e.target.checked;
    });
    document.querySelectorAll('[data-limit]').forEach(cb => {
        cb.addEventListener('change', () => {
            const key = cb.dataset.limit;
            const arr = WIZARD.state.limits;
            const idx = arr.indexOf(key);
            if (cb.checked && idx === -1) arr.push(key);
            if (!cb.checked && idx > -1) arr.splice(idx, 1);
        });
    });

    document.getElementById('trip-date').addEventListener('change', e => {
        WIZARD.state.date = e.target.value;
    });
    document.getElementById('trip-time').addEventListener('change', e => {
        WIZARD.state.time = e.target.value;
    });

    document.getElementById('btn-prev').addEventListener('click', wizardPrev);
    document.getElementById('btn-next').addEventListener('click', wizardNext);
}

function wizardRender() {
    document.querySelectorAll('.step').forEach(s => {
        s.classList.toggle('hidden', Number(s.dataset.step) !== WIZARD.currentStep);
    });
    const pct = (WIZARD.currentStep / WIZARD.totalSteps) * 100;
    document.getElementById('wp-fill').style.width = pct + '%';

    const dots = document.getElementById('wp-dots');
    dots.innerHTML = ['מי בא', 'מגבלות', 'מתי וכמה', 'איפה וסוג']
        .map((label, idx) => `<span class="${idx + 1 === WIZARD.currentStep ? 'active' : ''}">${idx + 1}. ${label}</span>`)
        .join('');

    document.getElementById('btn-prev').textContent = WIZARD.currentStep === 1 ? '← לדף הבית' : 'חזרה';
    document.getElementById('btn-next').textContent = WIZARD.currentStep === WIZARD.totalSteps ? 'הצג הצעות →' : 'הבא →';
}

function wizardPrev() {
    if (WIZARD.currentStep === 1) {
        showScreen('welcome');
        return;
    }
    WIZARD.currentStep--;
    wizardRender();
}

function wizardNext() {
    if (WIZARD.currentStep < WIZARD.totalSteps) {
        WIZARD.currentStep++;
        wizardRender();
        return;
    }
    finishWizard();
}

function finishWizard() {
    // Persist profile fields
    saveProfile({
        ages: WIZARD.state.ages,
        stroller: WIZARD.state.stroller,
        pet: WIZARD.state.pet,
        limits: WIZARD.state.limits
    });
    // Hand off to app
    showSuggestions(WIZARD.state);
}

function wizardReset() {
    WIZARD.currentStep = 1;
    wizardRender();
}

window.wizardInit = wizardInit;
window.wizardReset = wizardReset;
