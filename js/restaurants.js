/* ============================================
   מאגר מסעדות לפי אזור
   ============================================ */

const RESTAURANTS = {
    galilee: [
        { name: 'אצל אסף', cuisine: 'בשרים על האש בסגנון דרוזי', lat: 32.9180, lon: 35.4400, phone: '04-6989999', hours: '12:00-22:00', kosher: false, kidFriendly: true, vegan: false, priceTier: 2, notes: 'מנות גנרוזיות, מקום מקומי אותנטי בכרם בן זמרה.' },
        { name: 'מעיין הבירה', cuisine: 'פאב + בורגרים', lat: 32.9690, lon: 35.4940, phone: '04-6951330', hours: '12:00-23:30', kosher: false, kidFriendly: true, vegan: true, priceTier: 2, notes: 'במבשלת הבירה של דלתון. אחרי מסלול — הצלה אמיתית.' },
        { name: 'בכפר', cuisine: 'מטבח גלילי-מזרחי', lat: 32.7920, lon: 35.5240, phone: '04-6989900', hours: '11:00-22:00', kosher: true, kidFriendly: true, vegan: true, priceTier: 2, notes: 'תפריט עשיר, סלטים מהגינה, מרק כתום מומלץ.' }
    ],
    golan: [
        { name: 'הבקתה בבירייה', cuisine: 'גריל ובשרים', lat: 32.9920, lon: 35.5290, phone: '04-6921122', hours: '12:00-22:00', kosher: false, kidFriendly: true, vegan: false, priceTier: 3, notes: 'כריות נוף ומרפסות עץ. אווירה כפרית קסומה.' },
        { name: 'יקב באהט', cuisine: 'מטבח גורמה ויינות', lat: 32.9990, lon: 35.7350, phone: '04-6829889', hours: '10:00-18:00', kosher: false, kidFriendly: false, vegan: true, priceTier: 3, notes: 'טעימות יין + מנות שף עם תצפית גולן.' },
        { name: 'המנדרינה — כורסי', cuisine: 'דגים וים תיכוני', lat: 32.8270, lon: 35.6520, phone: '04-6731551', hours: '12:00-22:00', kosher: true, kidFriendly: true, vegan: false, priceTier: 2, notes: 'דקה מהשמורה. דגי כנרת ומבחר סלטים.' }
    ],
    carmel: [
        { name: 'אבו יוסף בדאלית', cuisine: 'דרוזי מסורתי', lat: 32.6890, lon: 35.0380, phone: '04-8392866', hours: '11:00-22:00', kosher: false, kidFriendly: true, vegan: true, priceTier: 2, notes: 'מנות פתיחה אינסופיות. דאלית אל-כרמל.' },
        { name: 'מסעדת מוקה', cuisine: 'איטלקית-ים תיכונית', lat: 32.7350, lon: 35.0080, phone: '04-8311333', hours: '12:00-23:00', kosher: false, kidFriendly: true, vegan: true, priceTier: 2, notes: 'בעין הוד — אטמוספירת אמנים, פסטות ופיצות.' },
        { name: 'נואל זיכרון', cuisine: 'בשרים יוקרתיים', lat: 32.5760, lon: 34.9510, phone: '04-6390515', hours: '12:00-23:00', kosher: false, kidFriendly: true, vegan: false, priceTier: 3, notes: 'בלב זיכרון יעקב, חצר יפהפייה.' }
    ],
    center: [
        { name: 'אומרצי בקיסריה', cuisine: 'בשרים על הים', lat: 32.5090, lon: 34.8940, phone: '04-6361555', hours: '12:00-23:00', kosher: false, kidFriendly: true, vegan: false, priceTier: 3, notes: 'מבט ישיר לים. שילוב מנצח אחרי טיול חוף.' },
        { name: 'הומוס אליהו', cuisine: 'חומוס וטחינה', lat: 31.9620, lon: 34.9670, phone: '08-9286000', hours: '08:00-16:00', kosher: true, kidFriendly: true, vegan: true, priceTier: 1, notes: 'מהומוסיות הטובות בארץ. בלוד.' },
        { name: 'הצריף של תמרה', cuisine: 'בית קפה כפרי', lat: 31.9520, lon: 34.9720, phone: '08-9180770', hours: '09:00-17:00', kosher: true, kidFriendly: true, vegan: true, priceTier: 2, notes: 'בתוך משק חקלאי — שקשוקה, סלטים וקפה מצוין.' }
    ],
    jerusalem: [
        { name: 'בורגרים אצל מוטי', cuisine: 'בורגרים', lat: 31.7790, lon: 35.2190, phone: '02-6232020', hours: '11:00-23:00', kosher: true, kidFriendly: true, vegan: true, priceTier: 2, notes: 'במרכז העיר — מקום קלאסי לסיום יום בעיר.' },
        { name: 'מחניודה', cuisine: 'שף ישראלי', lat: 31.7860, lon: 35.2100, phone: '02-5331111', hours: '12:30-23:00', kosher: false, kidFriendly: false, vegan: true, priceTier: 3, notes: 'אייקון של ירושלים. כדאי להזמין מראש.' },
        { name: 'נחת בעין כרם', cuisine: 'מטבח כפרי-צרפתי', lat: 31.7670, lon: 35.1620, phone: '02-6437044', hours: '12:00-22:00', kosher: false, kidFriendly: true, vegan: true, priceTier: 3, notes: 'מסעדה קסומה בעין כרם — דקות מעין חמד.' }
    ],
    deadSea: [
        { name: 'מסעדת ים המלח', cuisine: 'בופה ישראלי', lat: 31.4030, lon: 35.3700, phone: '08-6588888', hours: '12:00-22:00', kosher: true, kidFriendly: true, vegan: true, priceTier: 2, notes: 'במלון לוט, אחרי עין גדי או מצדה.' },
        { name: 'פונדק קומראן', cuisine: 'קפה ומאפים', lat: 31.7400, lon: 35.4580, phone: '02-9942235', hours: '08:00-18:00', kosher: true, kidFriendly: true, vegan: true, priceTier: 1, notes: 'תחנת ביניים נעימה בדרך חזרה.' }
    ],
    negev: [
        { name: 'הצריף של רקפת', cuisine: 'מטבח שטח של רועי', lat: 30.6080, lon: 34.7600, phone: '08-6586856', hours: '12:00-21:00', kosher: false, kidFriendly: true, vegan: false, priceTier: 2, notes: 'במצפה רמון. כריות, אש פתוחה, אווירה מדברית.' },
        { name: 'לאסה', cuisine: 'אסיאתי-ביסטרו', lat: 30.6100, lon: 34.7670, phone: '08-9959595', hours: '12:00-22:00', kosher: false, kidFriendly: true, vegan: true, priceTier: 2, notes: 'מצפה רמון, מטבח אסייתי בהפתעה גמורה.' },
        { name: 'בית הקפה של חוה', cuisine: 'בוקר כפרי', lat: 31.0150, lon: 34.7950, phone: '08-6555303', hours: '08:00-16:00', kosher: true, kidFriendly: true, vegan: true, priceTier: 1, notes: 'בית הקפה של חוות הבודדים. תוצרת מקומית.' }
    ],
    eilat: [
        { name: 'פאגו פאגו', cuisine: 'דגים ופירות ים', lat: 29.5520, lon: 34.9540, phone: '08-6376660', hours: '12:00-23:00', kosher: false, kidFriendly: true, vegan: false, priceTier: 3, notes: 'במרינה. דגים טריים, נוף שקיעה.' },
        { name: 'אדי ספארי', cuisine: 'בשרים', lat: 29.5550, lon: 34.9510, phone: '08-6326726', hours: '12:00-23:00', kosher: false, kidFriendly: true, vegan: false, priceTier: 3, notes: 'בשרים יבשים מיושנים. אחת הוותיקות באילת.' }
    ]
};

window.RESTAURANTS = RESTAURANTS;
