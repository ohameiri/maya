/* ============================================
   רשימת ציוד דינמית
   ============================================ */

function buildEquipment(profile, weather, trail) {
    const groups = {
        essentials: { title: 'בסיס לכל יציאה', items: [] },
        water: { title: 'מים ואוכל', items: [] },
        clothing: { title: 'לבוש', items: [] },
        safety: { title: 'בטיחות ועזרה ראשונה', items: [] },
        comfort: { title: 'נוחות והתאמה אישית', items: [] },
        kids: { title: 'לילדים ולעגלה', items: [] },
        pet: { title: 'לכלב', items: [] }
    };

    // --- Essentials ---
    groups.essentials.items.push(
        { name: 'תעודת זהות', urgent: false },
        { name: 'טלפון נייד טעון', urgent: false },
        { name: 'סוללת גיבוי לטלפון', urgent: false },
        { name: 'מפה / מסלול במכשיר', urgent: false }
    );

    // --- Water/food (base + temp adjustments) ---
    const hot = weather && weather.maxTemp >= 30;
    const veryHot = weather && weather.maxTemp >= 34;
    const cold = weather && weather.maxTemp <= 15;
    const longTrip = trail.duration_min >= 180;

    let waterLiters = 2;
    if (hot) waterLiters += 1;
    if (veryHot) waterLiters += 0.5;
    if (longTrip) waterLiters += 0.5;

    groups.water.items.push({
        name: `מים — ${waterLiters} ליטר לאדם`,
        urgent: hot,
        reason: hot ? 'חם — שתייה מרובה חיונית' : null
    });
    if (hot) groups.water.items.push({ name: 'מלחים / אלקטרוליטים', urgent: true, reason: 'מניעת ייבוש' });
    groups.water.items.push({ name: 'חטיפי אנרגיה / חטיפי גרנולה', urgent: false });
    if (longTrip) groups.water.items.push({ name: 'סנדוויץ\' או ארוחה קלה', urgent: false });
    groups.water.items.push({ name: 'פירות (תפוח / בננה)', urgent: false });

    // --- Clothing ---
    groups.clothing.items.push({ name: 'נעלי הליכה סגורות', urgent: false });
    groups.clothing.items.push({ name: 'כובע רחב שוליים', urgent: hot, reason: hot ? 'הגנה מהשמש' : null });
    if (cold) {
        groups.clothing.items.push({ name: 'שכבת חימום (פליז / סופטשל)', urgent: true, reason: `קר — צפי ${weather.maxTemp}°C` });
        groups.clothing.items.push({ name: 'כובע צמר', urgent: true });
        groups.clothing.items.push({ name: 'כפפות', urgent: false });
    }
    if (weather && weather.precipMax >= 30) {
        groups.clothing.items.push({ name: 'מעיל גשם / שכמייה', urgent: true, reason: `סיכוי גשם ${weather.precipMax}%` });
        groups.clothing.items.push({ name: 'נעליים יבשות להחלפה', urgent: false });
    }
    if (trail.flags.water) {
        groups.clothing.items.push({ name: 'בגד ים', urgent: false });
        groups.clothing.items.push({ name: 'סנדלי מים / נעלי קרוקס', urgent: true, reason: 'מסלול רטוב' });
        groups.clothing.items.push({ name: 'מגבת', urgent: false });
        groups.clothing.items.push({ name: 'תחליף בגדים יבש', urgent: false });
    }

    // --- Safety ---
    groups.safety.items.push({ name: 'ערכת עזרה ראשונה', urgent: false });
    groups.safety.items.push({ name: 'קרם הגנה SPF 50+', urgent: true, reason: 'הגנה מקרינה' });
    if (hot || trail.flags.exposure === 'high') {
        groups.safety.items.push({ name: 'משקפי שמש UV', urgent: true });
    }
    if (longTrip || trail.difficulty >= 3) {
        groups.safety.items.push({ name: 'שריקה', urgent: false });
        groups.safety.items.push({ name: 'פנס ראש (במקרה של עיכוב)', urgent: false });
    }

    // --- Comfort / personal limitations ---
    if (profile.limits.includes('backPain')) {
        groups.comfort.items.push({ name: 'מקלות הליכה (טרקינג)', urgent: true, reason: 'לכאב הגב — מפחית עומס' });
        groups.comfort.items.push({ name: 'חגורת תמיכה לגב', urgent: true, reason: 'מייצב חוליות מותניות' });
        groups.comfort.items.push({ name: 'תיק קל במיוחד עד 5 ק"ג', urgent: true });
    }
    if (profile.limits.includes('kneeIssues')) {
        groups.comfort.items.push({ name: 'מגן ברכיים', urgent: true, reason: 'תמיכה לברכיים' });
        if (!profile.limits.includes('backPain')) {
            groups.comfort.items.push({ name: 'מקלות הליכה', urgent: true, reason: 'מפחית עומס מהברכיים' });
        }
    }
    if (profile.limits.includes('asthma')) {
        groups.comfort.items.push({ name: 'משאף — ונטולין / מרחיב סימפונות', urgent: true, reason: 'חיוני לאסטמה' });
    }
    if (profile.limits.includes('heatSensitive')) {
        groups.comfort.items.push({ name: 'מטפחת רטובה לצוואר', urgent: false, reason: 'התקררות מהירה' });
        groups.comfort.items.push({ name: 'מאוורר נייד / כובע עם מאוורר', urgent: false });
    }

    // --- Kids / stroller ---
    if (profile.ages && profile.ages.includes('kids')) {
        groups.kids.items.push({ name: 'חטיפים נוספים לילדים', urgent: false });
        groups.kids.items.push({ name: 'תחליף בגדים יבש', urgent: false });
        groups.kids.items.push({ name: 'פלסטרים בצבעים', urgent: false });
        groups.kids.items.push({ name: 'משחק קצר לתורי המתנה', urgent: false });
    }
    if (profile.stroller) {
        groups.kids.items.push({ name: 'כיסוי שמש לעגלה', urgent: hot });
        groups.kids.items.push({ name: 'מי שתייה לתינוק', urgent: true });
        groups.kids.items.push({ name: 'חיתולים + מגבונים', urgent: false });
    }

    // --- Pet ---
    if (profile.pet) {
        groups.pet.items.push({ name: 'מים לכלב + קערה מתקפלת', urgent: true });
        groups.pet.items.push({ name: 'רצועה', urgent: true });
        groups.pet.items.push({ name: 'שקיות לאיסוף', urgent: false });
        if (hot) groups.pet.items.push({ name: 'הגנת כפות / מגף לאספלט חם', urgent: true, reason: 'אספלט יכול לגרום לכוויות' });
    }

    // Drop empty groups
    return Object.values(groups).filter(g => g.items.length > 0);
}

window.buildEquipment = buildEquipment;
