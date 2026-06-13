/* ============================================
   Planner — סינון מסלולים ובניית תוכנית
   ============================================ */

function haversine(lat1, lon1, lat2, lon2) {
    const R = 6371;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat/2)**2 +
              Math.cos(lat1 * Math.PI/180) * Math.cos(lat2 * Math.PI/180) *
              Math.sin(dLon/2)**2;
    return 2 * R * Math.asin(Math.sqrt(a));
}

function filterTrails(profile, prefs) {
    const hardLimits = (profile.limits || []);
    const reduceDifficulty = hardLimits.includes('backPain') ||
                              hardLimits.includes('kneeIssues') ||
                              hardLimits.includes('walkingDifficulty') ||
                              hardLimits.includes('asthma');

    return TRAILS.map(trail => {
        let score = 0;
        const reasons = [];
        const blockers = [];

        // Hard limit: stroller
        if (profile.stroller && !trail.flags.strollerFriendly) {
            blockers.push('לא נגיש לעגלה');
        }
        // Hard limit: pet
        if (profile.pet && !trail.flags.petFriendly) {
            blockers.push('כלבים לא מורשים');
        }

        // Region preference
        if (prefs.region && prefs.region !== 'any') {
            if (trail.region !== prefs.region) {
                blockers.push('אזור אחר');
            } else {
                score += 5;
            }
        }
        // Type preference
        if (prefs.type && prefs.type !== 'any') {
            if (trail.type === prefs.type) {
                score += 5;
                reasons.push({ tag: 'מתאים לסוג שביקשת', kind: 'good' });
            }
        }

        // Difficulty filtering
        if (reduceDifficulty && trail.difficulty > 2) {
            blockers.push('דרגת קושי מעל היכולת שצוינה');
        }
        if (hardLimits.includes('walkingDifficulty') && trail.distance_km > 4) {
            blockers.push('מסלול ארוך מדי');
        }
        if (hardLimits.includes('backPain') && trail.ascent_m > 150) {
            blockers.push('עלייה תלולה');
        }
        if (hardLimits.includes('kneeIssues') && trail.ascent_m > 200) {
            blockers.push('ירידה / עלייה חזקה לברכיים');
        }
        if (hardLimits.includes('vertigo') && trail.flags.exposure === 'high' && (trail.difficulty >= 3 || trail.ascent_m >= 200)) {
            blockers.push('חשוף מדי למצוקים');
        }

        // Duration preference
        if (prefs.duration === 'short' && trail.duration_min > 120) blockers.push('ארוך מהזמן שביקשת');
        if (prefs.duration === 'half' && trail.duration_min > 240) blockers.push('ארוך מהזמן שביקשת');
        if (prefs.duration === 'full' && trail.duration_min < 90) score -= 2;

        // Positive scoring
        if (hardLimits.includes('backPain') && trail.flags.backFriendly) {
            score += 4; reasons.push({ tag: 'מתאים לכאב גב', kind: 'good' });
        }
        if (hardLimits.includes('kneeIssues') && trail.flags.kneeFriendly) {
            score += 4; reasons.push({ tag: 'עדין על הברכיים', kind: 'good' });
        }
        if (hardLimits.includes('heatSensitive') && trail.flags.shade === 'high') {
            score += 3; reasons.push({ tag: 'הרבה צל', kind: 'good' });
        }
        if (profile.stroller && trail.flags.strollerFriendly) {
            score += 4; reasons.push({ tag: 'נגיש לעגלה', kind: 'good' });
        }
        if (profile.ages && profile.ages.includes('kids') && trail.flags.kidsFriendly) {
            score += 3; reasons.push({ tag: 'ידידותי לילדים', kind: 'good' });
        }
        if (profile.pet && trail.flags.petFriendly) {
            reasons.push({ tag: 'מותר עם כלבים', kind: 'info' });
        }
        if (trail.flags.water && (prefs.type === 'water' || prefs.type === 'any')) {
            reasons.push({ tag: 'מים זורמים', kind: 'info' });
        }

        // Season relevance
        const month = new Date().getMonth();
        const seasonNow = (month <= 1 || month === 11) ? 'winter'
                        : (month <= 4) ? 'spring'
                        : (month <= 7) ? 'summer'
                        : 'autumn';
        if (trail.season.includes(seasonNow)) score += 2;

        return { trail, score, reasons, blockers };
    })
    .filter(x => x.blockers.length === 0)
    .sort((a,b) => b.score - a.score)
    .slice(0, 6);
}

function pickRestaurant(trail) {
    const list = RESTAURANTS[trail.region];
    if (!list || list.length === 0) {
        // Fall back to any restaurant in nearby region
        const allLists = Object.values(RESTAURANTS).flat();
        return allLists.sort((a,b) =>
            haversine(trail.end.lat, trail.end.lon, a.lat, a.lon) -
            haversine(trail.end.lat, trail.end.lon, b.lat, b.lon)
        )[0];
    }
    return list.map(r => ({
        ...r,
        distance: haversine(trail.end.lat, trail.end.lon, r.lat, r.lon)
    })).sort((a,b) => a.distance - b.distance)[0];
}

function buildExplanation(trail, profile, prefs, weather) {
    const reasons = [];
    if ((profile.limits || []).includes('backPain'))
        reasons.push('בחרנו מסלול עדין על הגב');
    if ((profile.limits || []).includes('kneeIssues'))
        reasons.push('הימנענו מירידות תלולות');
    if ((profile.limits || []).includes('walkingDifficulty'))
        reasons.push('שמרנו על אורך נוח');
    if ((profile.limits || []).includes('heatSensitive') && trail.flags.shade === 'high')
        reasons.push('בחרנו אזור עם הרבה צל');
    if (profile.stroller)
        reasons.push('בדקנו שהמסלול נגיש לעגלה');
    if (profile.pet && trail.flags.petFriendly)
        reasons.push('המסלול מאפשר טיול עם הכלב');
    if (profile.ages && profile.ages.includes('kids') && trail.flags.kidsFriendly)
        reasons.push('המסלול ידידותי לילדים');
    if (weather && weather.maxTemp >= 30)
        reasons.push(`הוספנו מים ואלקטרוליטים בגלל ${weather.maxTemp}°C צפויים`);
    if (weather && weather.precipMax >= 30)
        reasons.push(`הוספנו מעיל כי יש סיכוי ${weather.precipMax}% לגשם`);

    if (reasons.length === 0) {
        return `<strong>${trail.name}</strong> נבחר בהתאם להעדפות שלך ולמזג האוויר הצפוי.`;
    }
    return `<strong>למה ${trail.name}?</strong> ` + reasons.join(', ') + '.';
}

async function buildPlan(trail, profile, prefs) {
    const weather = await fetchWeather(trail.start.lat, trail.start.lon, prefs.date);
    const restaurant = pickRestaurant(trail);
    const equipment = buildEquipment(profile, weather, trail);
    const explanation = buildExplanation(trail, profile, prefs, weather);
    return { trail, profile, prefs, weather, restaurant, equipment, explanation };
}

function wazeLink(lat, lon) {
    return `https://waze.com/ul?ll=${lat}%2C${lon}&navigate=yes`;
}

window.filterTrails = filterTrails;
window.pickRestaurant = pickRestaurant;
window.buildPlan = buildPlan;
window.wazeLink = wazeLink;
