/* ============================================
   English Quest 3D - Application Controller
   ============================================ */

(function () {
    'use strict';

    // --- Core References ---
    let scene3D = null;
    let game = null;
    let currentQuestion = null;
    let currentGameMode = null;

    // --- DOM Elements ---
    const $ = (id) => document.getElementById(id);
    const loadingScreen = $('loading-screen');
    const loaderProgress = $('loader-progress');
    const mainMenu = $('main-menu');
    const gameHud = $('game-hud');
    const feedbackOverlay = $('feedback-overlay');
    const feedbackContent = $('feedback-content');
    const resultsScreen = $('results-screen');

    // Game UI panels
    const wordMatchUI = $('word-match-ui');
    const spellingUI = $('spelling-ui');
    const sentenceUI = $('sentence-ui');
    const speedUI = $('speed-ui');

    // HUD elements
    const gameScore = $('game-score');
    const comboDisplay = $('combo-display');
    const comboValue = $('combo-value');
    const timerDisplay = $('timer-display');
    const timerValue = $('timer-value');
    const streakFire = $('streak-fire');
    const streakValue = $('streak-value');
    const progressFill = $('progress-fill');
    const progressText = $('progress-text');

    // Menu elements
    const totalScoreEl = $('total-score');
    const wordsLearnedEl = $('words-learned');
    const currentLevelEl = $('current-level');

    // --- Audio Context for Sound Effects ---
    let audioCtx = null;

    function getAudioContext() {
        if (!audioCtx) {
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        }
        return audioCtx;
    }

    function playTone(frequency, duration, type = 'sine', volume = 0.15) {
        try {
            const ctx = getAudioContext();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();

            osc.type = type;
            osc.frequency.setValueAtTime(frequency, ctx.currentTime);
            gain.gain.setValueAtTime(volume, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + duration);

            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start(ctx.currentTime);
            osc.stop(ctx.currentTime + duration);
        } catch (e) {
            // Audio not available
        }
    }

    function playCorrectSound() {
        playTone(523.25, 0.1, 'sine', 0.12);
        setTimeout(() => playTone(659.25, 0.1, 'sine', 0.12), 100);
        setTimeout(() => playTone(783.99, 0.15, 'sine', 0.12), 200);
    }

    function playWrongSound() {
        playTone(200, 0.15, 'square', 0.08);
        setTimeout(() => playTone(180, 0.2, 'square', 0.08), 150);
    }

    function playClickSound() {
        playTone(800, 0.05, 'sine', 0.06);
    }

    function playComboSound() {
        playTone(523.25, 0.08, 'sine', 0.1);
        setTimeout(() => playTone(659.25, 0.08, 'sine', 0.1), 80);
        setTimeout(() => playTone(783.99, 0.08, 'sine', 0.1), 160);
        setTimeout(() => playTone(1046.50, 0.15, 'sine', 0.1), 240);
    }

    function playGameOverSound() {
        playTone(784, 0.2, 'sine', 0.1);
        setTimeout(() => playTone(659, 0.2, 'sine', 0.1), 200);
        setTimeout(() => playTone(523, 0.3, 'sine', 0.1), 400);
    }

    function playStarSound(index) {
        const notes = [523.25, 659.25, 783.99];
        setTimeout(() => playTone(notes[index] || 523, 0.3, 'sine', 0.1), index * 300);
    }

    // --- Particle Effects ---
    function createParticles(x, y, color, count = 12) {
        for (let i = 0; i < count; i++) {
            const particle = document.createElement('div');
            particle.className = 'particle';
            const size = 4 + Math.random() * 8;
            const dx = (Math.random() - 0.5) * 200;
            const dy = (Math.random() - 0.5) * 200 - 50;

            particle.style.cssText = `
                width: ${size}px;
                height: ${size}px;
                background: ${color};
                left: ${x}px;
                top: ${y}px;
                --dx: ${dx}px;
                --dy: ${dy}px;
                box-shadow: 0 0 ${size}px ${color};
            `;

            document.body.appendChild(particle);
            setTimeout(() => particle.remove(), 1000);
        }
    }

    function showScorePopup(x, y, points) {
        const popup = document.createElement('div');
        popup.className = 'score-popup';
        popup.textContent = `+${points}`;
        popup.style.left = `${x}px`;
        popup.style.top = `${y}px`;
        document.body.appendChild(popup);
        setTimeout(() => popup.remove(), 1000);
    }

    // --- Feedback ---
    function showFeedback(correct, correctAnswer) {
        feedbackOverlay.classList.remove('hidden');

        if (correct) {
            feedbackContent.innerHTML = `
                <span class="feedback-correct">✓</span>
                <span class="feedback-text feedback-correct">!נכון</span>
            `;
        } else {
            feedbackContent.innerHTML = `
                <span class="feedback-wrong">✗</span>
                <span class="feedback-text feedback-wrong">${correctAnswer || ''} :התשובה הנכונה</span>
            `;
        }

        setTimeout(() => {
            feedbackOverlay.classList.add('hidden');
        }, 800);
    }

    // --- Screen Management ---
    function hideAllScreens() {
        mainMenu.classList.add('hidden');
        gameHud.classList.add('hidden');
        wordMatchUI.classList.add('hidden');
        spellingUI.classList.add('hidden');
        sentenceUI.classList.add('hidden');
        speedUI.classList.add('hidden');
        resultsScreen.classList.add('hidden');
    }

    function showScreen(screen) {
        hideAllScreens();
        screen.classList.remove('hidden');
    }

    function showMainMenu() {
        hideAllScreens();
        mainMenu.classList.remove('hidden');
        if (scene3D) scene3D.setTheme('menu');

        // Update menu stats
        totalScoreEl.textContent = game.totalScore.toLocaleString();
        wordsLearnedEl.textContent = game.wordsLearned;
        currentLevelEl.textContent = game.level;
    }

    // --- HUD Updates ---
    function updateHUD() {
        gameScore.textContent = game.score.toLocaleString();
        streakValue.textContent = game.streak;

        // Combo display
        if (game.combo > 1) {
            comboDisplay.classList.remove('hidden');
            comboValue.textContent = `x${game.combo}`;
        } else {
            comboDisplay.classList.add('hidden');
        }

        // Streak fire animation
        if (game.streak >= 3) {
            streakFire.classList.add('active');
            setTimeout(() => streakFire.classList.remove('active'), 400);
        }

        // Progress
        const progress = game.getProgress();
        progressFill.style.width = `${progress.percentage}%`;
        progressText.textContent = `${progress.current}/${progress.total}`;
    }

    // --- Game Mode: Word Match ---
    function startWordMatch() {
        currentGameMode = 'match';
        const question = game.startGame('match');
        if (!question) return;

        hideAllScreens();
        gameHud.classList.remove('hidden');
        wordMatchUI.classList.remove('hidden');
        timerDisplay.classList.add('hidden');
        if (scene3D) scene3D.setTheme('game-match');

        updateHUD();
        renderMatchQuestion(question);
    }

    function renderMatchQuestion(question) {
        currentQuestion = question;

        $('match-word').textContent = question.word;
        $('match-phonetic').textContent = question.phonetic;

        const optionsGrid = $('match-options');
        optionsGrid.innerHTML = '';

        question.options.forEach(option => {
            const btn = document.createElement('button');
            btn.className = 'option-btn';
            btn.textContent = option;
            btn.addEventListener('click', (e) => handleMatchAnswer(option, btn, e));
            optionsGrid.appendChild(btn);
        });

        // Animate card entrance
        const card = wordMatchUI.querySelector('.game-card');
        card.style.animation = 'none';
        card.offsetHeight; // trigger reflow
        card.style.animation = 'float 3s ease-in-out infinite';
    }

    function handleMatchAnswer(answer, btn, event) {
        if (!game.isAnswering) return;

        const result = game.processAnswer(answer, currentQuestion);
        const rect = btn.getBoundingClientRect();
        const cx = rect.left + rect.width / 2;
        const cy = rect.top + rect.height / 2;

        // Disable all buttons
        const buttons = $('match-options').querySelectorAll('.option-btn');
        buttons.forEach(b => b.style.pointerEvents = 'none');

        if (result.correct) {
            btn.classList.add('correct');
            playCorrectSound();
            createParticles(cx, cy, '#55efc4', 15);
            showScorePopup(cx, cy - 30, result.points);
            if (scene3D) scene3D.triggerCorrectEffect();
            if (result.combo > 1) {
                playComboSound();
                if (scene3D) scene3D.triggerComboEffect();
            }
        } else {
            btn.classList.add('wrong');
            playWrongSound();
            createParticles(cx, cy, '#ff7675', 8);
            if (scene3D) scene3D.triggerWrongEffect();
            // Highlight correct
            buttons.forEach(b => {
                if (b.textContent === result.correctAnswer) b.classList.add('correct');
            });
        }

        showFeedback(result.correct, result.correctAnswer);
        updateHUD();

        setTimeout(() => {
            const next = game.getNextQuestion();
            if (next) {
                renderMatchQuestion(next);
            } else {
                showResults();
            }
        }, 1200);
    }

    // --- Game Mode: Spelling ---
    let spellingSlots = [];
    let spellingLetterBtns = [];

    function startSpelling() {
        currentGameMode = 'spelling';
        const question = game.startGame('spelling');
        if (!question) return;

        hideAllScreens();
        gameHud.classList.remove('hidden');
        spellingUI.classList.remove('hidden');
        timerDisplay.classList.add('hidden');
        if (scene3D) scene3D.setTheme('game-spell');

        updateHUD();
        renderSpellingQuestion(question);
    }

    function renderSpellingQuestion(question) {
        currentQuestion = question;
        spellingSlots = [];

        $('spell-hebrew').textContent = question.hebrew;
        $('spell-hint').textContent = question.hint;

        // Create letter slots
        const slotsContainer = $('letter-slots');
        slotsContainer.innerHTML = '';
        for (let i = 0; i < question.correct.length; i++) {
            const slot = document.createElement('div');
            slot.className = 'letter-slot';
            slot.dataset.index = i;
            slot.addEventListener('click', () => removeLetterFromSlot(i));
            slotsContainer.appendChild(slot);
            spellingSlots.push({ element: slot, letter: '' });
        }

        // Create letter bank
        const bankContainer = $('letter-bank');
        bankContainer.innerHTML = '';
        spellingLetterBtns = [];
        question.letters.forEach((letter, i) => {
            const btn = document.createElement('button');
            btn.className = 'letter-btn';
            btn.textContent = letter;
            btn.dataset.index = i;
            btn.addEventListener('click', () => addLetterToSlot(letter, i));
            bankContainer.appendChild(btn);
            spellingLetterBtns.push(btn);
        });
    }

    function addLetterToSlot(letter, bankIndex) {
        // Find first empty slot
        const emptySlot = spellingSlots.find(s => s.letter === '');
        if (!emptySlot) return;

        playClickSound();
        emptySlot.letter = letter;
        emptySlot.element.textContent = letter;
        emptySlot.element.classList.add('filled');
        emptySlot.bankIndex = bankIndex;

        spellingLetterBtns[bankIndex].classList.add('used');
    }

    function removeLetterFromSlot(index) {
        const slot = spellingSlots[index];
        if (!slot || slot.letter === '') return;

        playClickSound();
        if (slot.bankIndex !== undefined) {
            spellingLetterBtns[slot.bankIndex].classList.remove('used');
        }
        slot.letter = '';
        slot.element.textContent = '';
        slot.element.classList.remove('filled');
        slot.bankIndex = undefined;
    }

    function clearSpelling() {
        spellingSlots.forEach((slot, i) => removeLetterFromSlot(i));
    }

    function checkSpelling() {
        const answer = spellingSlots.map(s => s.letter).join('');
        if (answer.length !== currentQuestion.correct.length) return;
        if (spellingSlots.some(s => s.letter === '')) return;

        const result = game.processSpellingAnswer(answer, currentQuestion);

        // Animate each letter
        spellingSlots.forEach((slot, i) => {
            setTimeout(() => {
                if (answer[i].toLowerCase() === currentQuestion.correct[i].toLowerCase()) {
                    slot.element.classList.add('correct-letter');
                } else {
                    slot.element.classList.add('wrong-letter');
                }
            }, i * 100);
        });

        if (result.correct) {
            playCorrectSound();
            const slotsEl = $('letter-slots');
            const rect = slotsEl.getBoundingClientRect();
            createParticles(rect.left + rect.width / 2, rect.top, '#55efc4', 20);
            showScorePopup(rect.left + rect.width / 2, rect.top - 20, result.points);
            if (scene3D) scene3D.triggerCorrectEffect();
            if (result.combo > 1) {
                playComboSound();
                if (scene3D) scene3D.triggerComboEffect();
            }
        } else {
            playWrongSound();
            if (scene3D) scene3D.triggerWrongEffect();
        }

        showFeedback(result.correct, result.correctAnswer);
        updateHUD();

        setTimeout(() => {
            const next = game.getNextQuestion();
            if (next) {
                renderSpellingQuestion(next);
            } else {
                showResults();
            }
        }, 1500);
    }

    // --- Game Mode: Sentence Completion ---
    function startSentence() {
        currentGameMode = 'sentence';
        const question = game.startGame('sentence');
        if (!question) return;

        hideAllScreens();
        gameHud.classList.remove('hidden');
        sentenceUI.classList.remove('hidden');
        timerDisplay.classList.add('hidden');
        if (scene3D) scene3D.setTheme('game-sentence');

        updateHUD();
        renderSentenceQuestion(question);
    }

    function renderSentenceQuestion(question) {
        currentQuestion = question;

        // Replace blank in sentence
        const sentenceHTML = question.sentence.replace('___',
            '<span class="sentence-blank">?</span>'
        );
        $('sentence-text').innerHTML = sentenceHTML;
        $('sentence-hebrew').textContent = question.sentenceHe;

        const optionsGrid = $('sentence-options');
        optionsGrid.innerHTML = '';

        question.options.forEach(option => {
            const btn = document.createElement('button');
            btn.className = 'option-btn english-option';
            btn.textContent = option;
            btn.addEventListener('click', (e) => handleSentenceAnswer(option, btn, e));
            optionsGrid.appendChild(btn);
        });
    }

    function handleSentenceAnswer(answer, btn, event) {
        if (!game.isAnswering) return;

        const result = game.processAnswer(answer, currentQuestion);
        const rect = btn.getBoundingClientRect();
        const cx = rect.left + rect.width / 2;
        const cy = rect.top + rect.height / 2;

        const buttons = $('sentence-options').querySelectorAll('.option-btn');
        buttons.forEach(b => b.style.pointerEvents = 'none');

        if (result.correct) {
            btn.classList.add('correct');
            playCorrectSound();
            createParticles(cx, cy, '#55efc4', 15);
            showScorePopup(cx, cy - 30, result.points);
            // Update the blank in the sentence
            const blank = sentenceUI.querySelector('.sentence-blank');
            if (blank) {
                blank.textContent = answer;
                blank.style.color = '#55efc4';
            }
            if (scene3D) scene3D.triggerCorrectEffect();
            if (result.combo > 1) {
                playComboSound();
                if (scene3D) scene3D.triggerComboEffect();
            }
        } else {
            btn.classList.add('wrong');
            playWrongSound();
            createParticles(cx, cy, '#ff7675', 8);
            if (scene3D) scene3D.triggerWrongEffect();
            buttons.forEach(b => {
                if (b.textContent === result.correctAnswer) b.classList.add('correct');
            });
            const blank = sentenceUI.querySelector('.sentence-blank');
            if (blank) {
                blank.textContent = result.correctAnswer;
                blank.style.color = '#ff7675';
            }
        }

        showFeedback(result.correct, result.correctAnswer);
        updateHUD();

        setTimeout(() => {
            const next = game.getNextQuestion();
            if (next) {
                renderSentenceQuestion(next);
            } else {
                showResults();
            }
        }, 1200);
    }

    // --- Game Mode: Speed Challenge ---
    function startSpeed() {
        currentGameMode = 'speed';
        const question = game.startGame('speed');
        if (!question) return;

        hideAllScreens();
        gameHud.classList.remove('hidden');
        speedUI.classList.remove('hidden');
        timerDisplay.classList.remove('hidden');
        timerValue.textContent = '60';
        timerValue.classList.remove('warning');
        if (scene3D) scene3D.setTheme('game-speed');

        updateHUD();
        renderSpeedQuestion(question);

        // Start countdown
        game.startTimer((timeLeft, expired) => {
            timerValue.textContent = timeLeft;
            if (timeLeft <= 10) {
                timerValue.classList.add('warning');
            }
            if (expired) {
                playGameOverSound();
                showResults();
            }
        });
    }

    function renderSpeedQuestion(question) {
        currentQuestion = question;

        $('speed-word').textContent = question.word;

        const optionsContainer = $('speed-options');
        optionsContainer.innerHTML = '';

        question.options.forEach(option => {
            const btn = document.createElement('button');
            btn.className = 'option-btn';
            btn.textContent = option;
            btn.addEventListener('click', (e) => handleSpeedAnswer(option, btn, e));
            optionsContainer.appendChild(btn);
        });
    }

    function handleSpeedAnswer(answer, btn, event) {
        if (!game.isAnswering) return;

        const result = game.processAnswer(answer, currentQuestion);
        const rect = btn.getBoundingClientRect();
        const cx = rect.left + rect.width / 2;
        const cy = rect.top + rect.height / 2;

        if (result.correct) {
            btn.classList.add('correct');
            playCorrectSound();
            createParticles(cx, cy, '#55efc4', 10);
            showScorePopup(cx, cy - 30, result.points);
            if (scene3D) scene3D.triggerCorrectEffect();
            if (result.combo > 1) {
                playComboSound();
                if (scene3D) scene3D.triggerComboEffect();
            }
        } else {
            btn.classList.add('wrong');
            playWrongSound();
            if (scene3D) scene3D.triggerWrongEffect();
        }

        updateHUD();

        // Quick transition for speed mode
        setTimeout(() => {
            const next = game.getNextQuestion();
            if (next) {
                renderSpeedQuestion(next);
            }
        }, 400);
    }

    // --- Results ---
    function showResults() {
        game.stopTimer();
        const results = game.getResults();

        hideAllScreens();
        resultsScreen.classList.remove('hidden');
        if (scene3D) scene3D.setTheme('results');

        // Title based on performance
        const titles = {
            3: '!מדהים! כל הכבוד',
            2: '!עבודה טובה',
            1: '!אל תוותר, נסה שוב'
        };
        $('results-title').textContent = titles[results.stars];

        // Stars
        const starsContainer = $('results-stars');
        starsContainer.innerHTML = '';
        for (let i = 0; i < 3; i++) {
            const star = document.createElement('span');
            star.className = `star ${i < results.stars ? '' : 'empty'}`;
            star.textContent = '⭐';
            starsContainer.appendChild(star);
            if (i < results.stars) playStarSound(i);
        }

        // Stats
        $('result-score').textContent = results.score.toLocaleString();
        $('result-correct').textContent = `${results.correctCount}/${results.totalQuestions}`;
        $('result-streak').textContent = results.bestStreak;
        $('result-accuracy').textContent = `${results.accuracy}%`;

        // Word list
        const wordsContainer = $('results-words');
        wordsContainer.innerHTML = '';
        results.wordResults.forEach(item => {
            const div = document.createElement('div');
            div.className = 'result-word-item';
            div.innerHTML = `
                <span class="result-word-en">${item.word.en}</span>
                <span class="result-word-he">${item.word.he}</span>
                <span class="result-word-status">${item.correct ? '✅' : '❌'}</span>
            `;
            wordsContainer.appendChild(div);
        });

        // Update menu stats for next time
        totalScoreEl.textContent = results.totalScore.toLocaleString();
        wordsLearnedEl.textContent = results.wordsLearned;
        currentLevelEl.textContent = results.level;
    }

    // --- Event Listeners ---
    function setupEventListeners() {
        // Difficulty buttons
        document.querySelectorAll('.diff-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.diff-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                game.setDifficulty(btn.dataset.level);
                playClickSound();
            });
        });

        // Game mode buttons
        $('btn-word-match').addEventListener('click', () => { playClickSound(); startWordMatch(); });
        $('btn-spelling').addEventListener('click', () => { playClickSound(); startSpelling(); });
        $('btn-sentence').addEventListener('click', () => { playClickSound(); startSentence(); });
        $('btn-speed').addEventListener('click', () => { playClickSound(); startSpeed(); });

        // HUD back button
        $('btn-back').addEventListener('click', () => {
            playClickSound();
            game.stopTimer();
            showMainMenu();
        });

        // Spelling buttons
        $('btn-clear-spelling').addEventListener('click', () => { playClickSound(); clearSpelling(); });
        $('btn-check-spelling').addEventListener('click', () => { playClickSound(); checkSpelling(); });

        // Results buttons
        $('btn-play-again').addEventListener('click', () => {
            playClickSound();
            switch (currentGameMode) {
                case 'match': startWordMatch(); break;
                case 'spelling': startSpelling(); break;
                case 'sentence': startSentence(); break;
                case 'speed': startSpeed(); break;
                default: showMainMenu();
            }
        });

        $('btn-back-menu').addEventListener('click', () => {
            playClickSound();
            showMainMenu();
        });

        // Keyboard support
        document.addEventListener('keydown', (e) => {
            if (currentGameMode === 'match' || currentGameMode === 'sentence' || currentGameMode === 'speed') {
                const key = parseInt(e.key);
                if (key >= 1 && key <= 4) {
                    const activeUI = currentGameMode === 'match' ? 'match-options'
                        : currentGameMode === 'sentence' ? 'sentence-options'
                        : 'speed-options';
                    const buttons = $(activeUI).querySelectorAll('.option-btn');
                    if (buttons[key - 1]) {
                        buttons[key - 1].click();
                    }
                }
            }
            if (e.key === 'Escape') {
                game.stopTimer();
                showMainMenu();
            }
            if (e.key === 'Enter' && currentGameMode === 'spelling') {
                checkSpelling();
            }
        });
    }

    // --- Loading & Initialization ---
    function simulateLoading() {
        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.random() * 15 + 5;
            if (progress >= 100) {
                progress = 100;
                clearInterval(interval);
                loaderProgress.style.width = '100%';
                setTimeout(() => {
                    loadingScreen.classList.add('hidden');
                    mainMenu.classList.remove('hidden');
                }, 400);
            }
            loaderProgress.style.width = `${progress}%`;
        }, 200);
    }

    function init() {
        // Initialize 3D scene
        const canvas = $('game-canvas');
        try {
            scene3D = new Scene3D(canvas);
        } catch (e) {
            console.warn('3D scene failed to initialize:', e);
        }

        // Initialize game engine
        game = new GameEngine();

        // Setup events
        setupEventListeners();

        // Start loading
        simulateLoading();
    }

    // Start when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
