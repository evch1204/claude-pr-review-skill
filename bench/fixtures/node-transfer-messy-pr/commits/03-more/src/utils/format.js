function formatCents(cents) {
    const sign = cents < 0 ? '-' : ''
    const abs = Math.abs(cents)
    return `${sign}$${Math.floor(abs / 100)}.${String(abs % 100).padStart(2, '0')}`
}

function parseCents(str) {
    const m = /^(-)?\$?(\d+)(?:\.(\d{1,2}))?$/.exec(String(str).trim())
    if (!m) return null
    const cents = Number(m[2]) * 100 + Number((m[3] || '0').padEnd(2, '0'))
    return m[1] ? -cents : cents
}

module.exports = { formatCents, parseCents }
