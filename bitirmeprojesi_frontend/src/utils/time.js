export function formatRelativeTimestamp(isoString) {
  if (!isoString) return "Bekleniyor";

  const value = String(isoString).trim();
  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value);
  const normalized = hasTimezone ? value : `${value}Z`;
  const date = new Date(normalized);

  if (Number.isNaN(date.getTime())) {
    return "Geçersiz tarih";
  }

  const diffMinutes = Math.round((Date.now() - date.getTime()) / 60000);

  if (diffMinutes <= 0) return "Az önce";
  if (diffMinutes < 60) return `${diffMinutes} dk önce`;
  if (diffMinutes < 1440) return `${Math.round(diffMinutes / 60)} saat önce`;

  return `${Math.round(diffMinutes / 1440)} gün önce`;
}

export function formatLocalTimestamp(isoString) {
  if (!isoString) return "Bilinmiyor";

  const value = String(isoString).trim();
  const hasTimezone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value);
  const normalized = hasTimezone ? value : `${value}Z`;
  const date = new Date(normalized);

  if (Number.isNaN(date.getTime())) {
    return "Geçersiz tarih";
  }

  return new Intl.DateTimeFormat("tr-TR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}
