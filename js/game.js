/* ============================================
   English Quest 3D - Game Logic
   ============================================ */

class GameEngine {
    constructor() {
        this.currentMode = null;
        this.difficulty = 'beginner';
        this.score = 0;
        this.totalScore = 0;
        this.wordsLearned = 0;
        this.level = 1;
        this.streak = 0;
        this.bestStreak = 0;
        this.combo = 1;
        this.correctCount = 0;
        this.totalQuestions = 0;
        this.currentQuestionIndex = 0;
        this.questionsPerRound = 10;
        this.gameWords = [];
        this.wordResults = [];
        this.timer = null;
        this.timeLeft = 60;
        this.isAnswering = false;

        this.loadProgress();
    }

    // --- Progress Management ---
    loadProgress() {
        try {
            const saved = localStorage.getItem('englishQuest3D_progress');
            if (saved) {
                const data = JSON.parse(saved);
                this.totalScore = data.totalScore || 0;
                this.wordsLearned = data.wordsLearned || 0;
                this.level = data.level || 1;
            }
        } catch (e) {
            // Start fresh
        }
    }

    saveProgress() {
        try {
            localStorage.setItem('englishQuest3D_progress', JSON.stringify({
                totalScore: this.totalScore,
                wordsLearned: this.wordsLearned,
                level: this.level
            }));
        } catch (e) {
            // Silent fail
        }
    }

    // --- Game Setup ---
    setDifficulty(level) {
        this.difficulty = level;
    }

    getWordPool() {
        return WORD_DATABASE[this.difficulty] || WORD_DATABASE.beginner;
    }

    shuffleArray(array) {
        const arr = [...array];
        for (let i = arr.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [arr[i], arr[j]] = [arr[j], arr[i]];
        }
        return arr;
    }

    startGame(mode) {
        this.currentMode = mode;
        this.score = 0;
        this.streak = 0;
        this.bestStreak = 0;
        this.combo = 1;
        this.correctCount = 0;
        this.totalQuestions = 0;
        this.currentQuestionIndex = 0;
        this.wordResults = [];
        this.isAnswering = false;

        const pool = this.getWordPool();
        this.gameWords = this.shuffleArray(pool).slice(0, this.questionsPerRound);

        if (mode === 'speed') {
            this.timeLeft = 60;
            this.gameWords = this.shuffleArray(pool); // Use all words for speed mode
        }

        return this.getNextQuestion();
    }

    stopTimer() {
        if (this.timer) {
            clearInterval(this.timer);
            this.timer = null;
        }
    }

    startTimer(callback) {
        this.stopTimer();
        this.timer = setInterval(() => {
            this.timeLeft--;
            if (callback) callback(this.timeLeft);
            if (this.timeLeft <= 0) {
                this.stopTimer();
                if (callback) callback(0, true);
            }
        }, 1000);
    }

    // --- Question Generation ---
    getNextQuestion() {
        if (this.currentMode === 'speed') {
            if (this.currentQuestionIndex >= this.gameWords.length) {
                this.gameWords = this.shuffleArray(this.getWordPool());
                this.currentQuestionIndex = 0;
            }
        } else {
            if (this.currentQuestionIndex >= this.gameWords.length) {
                return null;
            }
        }

        const word = this.gameWords[this.currentQuestionIndex];
        this.currentQuestionIndex++;
        this.isAnswering = true;

        switch (this.currentMode) {
            case 'match':
                return this.generateMatchQuestion(word);
            case 'spelling':
                return this.generateSpellingQuestion(word);
            case 'sentence':
                return this.generateSentenceQuestion(word);
            case 'speed':
                return this.generateSpeedQuestion(word);
            default:
                return null;
        }
    }

    generateMatchQuestion(word) {
        const pool = this.getWordPool().filter(w => w.en !== word.en);
        const wrongAnswers = this.shuffleArray(pool).slice(0, 3).map(w => w.he);
        const options = this.shuffleArray([word.he, ...wrongAnswers]);

        return {
            type: 'match',
            word: word.en,
            phonetic: word.phonetic,
            correct: word.he,
            options: options,
            wordData: word
        };
    }

    generateSpellingQuestion(word) {
        const letters = word.en.split('');
        // Add some extra random letters as distractors
        const extraLetters = 'abcdefghijklmnopqrstuvwxyz'
            .split('')
            .filter(l => !letters.includes(l));
        const numExtra = Math.min(Math.ceil(letters.length * 0.5), 4);
        const distractors = this.shuffleArray(extraLetters).slice(0, numExtra);
        const allLetters = this.shuffleArray([...letters, ...distractors]);

        return {
            type: 'spelling',
            hebrew: word.he,
            correct: word.en,
            letters: allLetters,
            hint: `${word.en.length} אותיות`,
            wordData: word
        };
    }

    generateSentenceQuestion(word) {
        const pool = this.getWordPool().filter(w => w.en !== word.en);
        const wrongAnswers = this.shuffleArray(pool).slice(0, 3).map(w => w.en);
        const options = this.shuffleArray([word.en, ...wrongAnswers]);

        return {
            type: 'sentence',
            sentence: word.example,
            sentenceHe: word.exampleHe,
            correct: word.en,
            options: options,
            wordData: word
        };
    }

    generateSpeedQuestion(word) {
        const pool = this.getWordPool().filter(w => w.en !== word.en);
        const wrongAnswers = this.shuffleArray(pool).slice(0, 3).map(w => w.he);
        const options = this.shuffleArray([word.he, ...wrongAnswers]);

        return {
            type: 'speed',
            word: word.en,
            correct: word.he,
            options: options,
            wordData: word
        };
    }

    // --- Answer Processing ---
    processAnswer(answer, question) {
        if (!this.isAnswering) return null;
        this.isAnswering = false;
        this.totalQuestions++;

        const isCorrect = answer === question.correct;

        if (isCorrect) {
            this.streak++;
            if (this.streak > this.bestStreak) {
                this.bestStreak = this.streak;
            }

            // Combo multiplier
            if (this.streak >= 5) {
                this.combo = 3;
            } else if (this.streak >= 3) {
                this.combo = 2;
            } else {
                this.combo = 1;
            }

            // Score calculation
            let baseScore = 100;
            if (this.difficulty === 'intermediate') baseScore = 150;
            if (this.difficulty === 'advanced') baseScore = 200;

            const points = baseScore * this.combo;
            this.score += points;
            this.correctCount++;

            // Track word as learned
            this.wordResults.push({
                word: question.wordData,
                correct: true,
                points: points
            });

            return {
                correct: true,
                points: points,
                streak: this.streak,
                combo: this.combo
            };
        } else {
            this.streak = 0;
            this.combo = 1;

            this.wordResults.push({
                word: question.wordData,
                correct: false,
                points: 0
            });

            return {
                correct: false,
                points: 0,
                streak: 0,
                combo: 1,
                correctAnswer: question.correct
            };
        }
    }

    processSpellingAnswer(answer, question) {
        if (!this.isAnswering) return null;
        this.isAnswering = false;
        this.totalQuestions++;

        const isCorrect = answer.toLowerCase() === question.correct.toLowerCase();

        if (isCorrect) {
            this.streak++;
            if (this.streak > this.bestStreak) {
                this.bestStreak = this.streak;
            }

            if (this.streak >= 5) this.combo = 3;
            else if (this.streak >= 3) this.combo = 2;
            else this.combo = 1;

            let baseScore = 150;
            if (this.difficulty === 'intermediate') baseScore = 200;
            if (this.difficulty === 'advanced') baseScore = 300;

            const points = baseScore * this.combo;
            this.score += points;
            this.correctCount++;

            this.wordResults.push({ word: question.wordData, correct: true, points });

            return { correct: true, points, streak: this.streak, combo: this.combo };
        } else {
            this.streak = 0;
            this.combo = 1;

            this.wordResults.push({ word: question.wordData, correct: false, points: 0 });

            return {
                correct: false,
                points: 0,
                streak: 0,
                combo: 1,
                correctAnswer: question.correct
            };
        }
    }

    // --- Results ---
    getResults() {
        const accuracy = this.totalQuestions > 0
            ? Math.round((this.correctCount / this.totalQuestions) * 100)
            : 0;

        // Calculate stars (1-3)
        let stars = 1;
        if (accuracy >= 80) stars = 3;
        else if (accuracy >= 50) stars = 2;

        // Update global progress
        this.totalScore += this.score;
        const newWords = this.wordResults.filter(w => w.correct).length;
        this.wordsLearned += newWords;

        // Level up every 500 points
        this.level = Math.floor(this.totalScore / 500) + 1;

        this.saveProgress();

        return {
            score: this.score,
            correctCount: this.correctCount,
            totalQuestions: this.totalQuestions,
            bestStreak: this.bestStreak,
            accuracy: accuracy,
            stars: stars,
            wordResults: this.wordResults,
            totalScore: this.totalScore,
            wordsLearned: this.wordsLearned,
            level: this.level
        };
    }

    // --- Utility ---
    getProgress() {
        if (this.currentMode === 'speed') {
            return {
                current: this.totalQuestions,
                total: '∞',
                percentage: (this.timeLeft / 60) * 100
            };
        }
        return {
            current: this.currentQuestionIndex,
            total: this.gameWords.length,
            percentage: (this.currentQuestionIndex / this.gameWords.length) * 100
        };
    }
}
