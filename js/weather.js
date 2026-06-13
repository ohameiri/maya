/* ============================================
   Open-Meteo wrapper (no API key required)
   ============================================ */

const WMO_ICONS = {
    0: { i: '☀️', label: 'בהיר' },
    1: { i: '🌤️', label: 'כמעט בהיר' },
    2: { i: '⛅', label: 'מעונן חלקית' },
    3: { i: '☁️', label: 'מעונן' },
    45: { i: '🌫️', label: 'ערפל' },
    48: { i: '🌫️', label: 'ערפל מצמרר' },
    51: { i: '🌦️', label: 'טפטוף קל' },
    53: { i: '🌦️', label: 'טפטוף' },
    55: { i: '🌧️', label: 'טפטוף חזק' },
    61: { i: '🌧️', label: 'גשם קל' },
    63: { i: '🌧️', label: 'גשם' },
    65: { i: '🌧️', label: 'גשם חזק' },
    71: { i: '🌨️', label: 'שלג קל' },
    73: { i: '🌨️', label: 'שלג' },
    75: { i: '❄️', label: 'שלג חזק' },
    80: { i: '🌦️', label: 'מטחי גשם' },
    81: { i: '🌧️', label: 'מטחים' },
    82: { i: '⛈️', label: 'מטחים עזים' },
    95: { i: '⛈️', label: 'סופת רעמים' },
    96: { i: '⛈️', label: 'רעמים + ברד' },
    99: { i: '⛈️', label: 'רעמים + ברד כבד' }
};

function wmoLabel(code) {
    return WMO_ICONS[code] || { i: '🌡️', label: '—' };
}

async function fetchWeather(lat, lon, dateStr) {
    const url = new URL('https://api.open-meteo.com/v1/forecast');
    url.searchParams.set('latitude', lat);
    url.searchParams.set('longitude', lon);
    url.searchParams.set('start_date', dateStr);
    url.searchParams.set('end_date', dateStr);
    url.searchParams.set('daily', 'temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max,sunrise,sunset,weather_code,uv_index_max');
    url.searchParams.set('hourly', 'temperature_2m,precipitation_probability,weather_code');
    url.searchParams.set('timezone', 'Asia/Jerusalem');

    const res = await fetch(url.toString());
    if (!res.ok) throw new Error('weather fetch failed');
    const data = await res.json();

    const d = data.daily;
    const h = data.hourly;

    const maxTemp = Math.round(d.temperature_2m_max[0]);
    const minTemp = Math.round(d.temperature_2m_min[0]);
    const precipMax = d.precipitation_probability_max[0] ?? 0;
    const wind = Math.round(d.wind_speed_10m_max[0]);
    const sunrise = (d.sunrise[0] || '').slice(11, 16);
    const sunset  = (d.sunset[0]  || '').slice(11, 16);
    const code = d.weather_code[0];
    const uv = Math.round((d.uv_index_max && d.uv_index_max[0]) || 0);

    // Slice hourly to 6:00-18:00 (or the user's window)
    const hourly = [];
    for (let i = 6; i <= 18; i++) {
        hourly.push({
            hour: i,
            temp: Math.round(h.temperature_2m[i]),
            precip: h.precipitation_probability[i] ?? 0,
            code: h.weather_code[i]
        });
    }

    // Build alerts based on conditions
    const alerts = [];
    if (maxTemp >= 34) alerts.push('🥵 חם מאוד! יציאה לפני 7:00, מים נוספים, הפסקות בצל.');
    else if (maxTemp >= 30) alerts.push('☀️ יום חם — כדאי לקחת ליטר מים נוסף ולצאת מוקדם.');
    if (precipMax >= 50) alerts.push('🌧️ סיכוי גבוה לגשם — קחו מעיל ותחליף בגדים.');
    else if (precipMax >= 30) alerts.push('🌦️ אפשר ויירד גשם, מומלץ מעיל קל.');
    if (wind >= 40) alerts.push('💨 רוחות חזקות — היזהרו בשבילי מצוקים.');
    if (uv >= 8) alerts.push('☢️ מדד UV גבוה — קרם הגנה כל שעתיים.');
    if (minTemp <= 5) alerts.push('🥶 קר מאוד בבוקר — שכבת חימום חיונית.');

    return {
        maxTemp, minTemp, precipMax, wind, sunrise, sunset, uv,
        code, label: wmoLabel(code).label, icon: wmoLabel(code).i,
        hourly, alerts, raw: data
    };
}

window.fetchWeather = fetchWeather;
