import { Flame, Wind, Droplet, Cloud, Navigation, X } from 'lucide-react';

function formatMetric(value, suffix = '', digits = 1) {
  if (value == null || value === 'N/A') return 'N/A';
  const number = Number(value);
  if (!Number.isFinite(number)) return 'N/A';
  const formatted = new Intl.NumberFormat('tr-TR', {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  }).format(number);
  return `${formatted}${suffix}`;
}

export function FireDetailCard({
  city,
  region,
  riskLevel,
  riskPercentage,
  temperature,
  windSpeed,
  humidity,
  timeAgo,
  mlSource,
  clusterId,
  clusterStatus,
  onShowInList,
  onClose
}) {
  
  // Risk seviyesine göre renk belirleme
  const getRiskColor = () => {
    switch (riskLevel) {
      case 'Düşük':
        return {
          text: '#cce8c9',
          bg: 'rgba(127, 188, 140, 0.16)',
          border: 'rgba(127, 188, 140, 0.56)',
          progress: '#7fbc8c',
          icon: '#7fbc8c',
        };
      case 'Orta':
        return {
          text: '#f6d28b',
          bg: 'rgba(247, 182, 56, 0.12)',
          border: 'rgba(247, 182, 56, 0.38)',
          progress: '#f7b638',
          icon: '#f7b638',
        };
      case 'Yüksek':
        return {
          text: '#f7c1b6',
          bg: 'rgba(120, 1, 21, 0.28)',
          border: 'rgba(120, 1, 21, 0.72)',
          progress: '#a90b22',
          icon: '#d42b3f',
        };
      default:
        return {
          text: '#cbbba4',
          bg: 'rgba(203, 187, 164, 0.12)',
          border: 'rgba(203, 187, 164, 0.34)',
          progress: '#cbbba4',
          icon: '#cbbba4',
        };
    }
  };

  const colors = getRiskColor();
  const displayTemperature = formatMetric(temperature, '°C');
  const displayWind = formatMetric(windSpeed, ' km/sa');
  const displayHumidity = formatMetric(humidity, '%');
  const displayRisk = formatMetric(riskPercentage, '', 1);
  const clusterStatusLabel = ['active', 'monitoring', 'resolved'].includes(clusterStatus)
    ? clusterStatus
    : null;

  return (
    <div
      className="fire-detail-card w-[280px] rounded-xl shadow-xl p-3"
      style={{
        background: 'var(--map-card-bg)',
        border: '1px solid var(--map-card-border)',
        boxShadow: 'var(--map-card-shadow)'
      }}
    >
      {/* Başlık ve Kapatma Butonu */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div
            className="w-2.5 h-2.5 rounded-full shadow-sm"
            style={{ background: colors.progress, boxShadow: `0 0 8px ${colors.progress}` }}
          />
          <div className="flex items-baseline gap-2">
            <span className="text-base font-semibold" style={{ color: 'var(--map-card-text)' }}>{city}</span>
            <span className="text-xs" style={{ color: 'var(--map-card-muted)' }}>{region}</span>
          </div>
        </div>
        {onClose && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onClose();
            }}
            className="text-gray-400 hover:text-white transition-colors p-1"
          >
            <X size={16} />
          </button>
        )}
      </div>

      {/* Risk Durumu Badge + ML Rozeti */}
      <div className="mb-3" style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
        <div
          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border"
          style={{ background: colors.bg, borderColor: colors.border }}
        >
          <Flame size={12} color={colors.icon} />
          <span className="text-xs font-medium" style={{ color: colors.text }}>
            {riskLevel} {riskPercentage != null ? `— %${displayRisk}` : ''}
          </span>
        </div>
        {/* ML Kaynak Rozeti */}
        {mlSource === 'model' && (
          <div className="fire-detail-ml-badge" style={{
            display: 'inline-flex', alignItems: 'center', gap: 4,
            padding: '2px 8px', borderRadius: 20,
            background: 'rgba(127,188,140,0.14)',
            border: '1px solid rgba(127,188,140,0.45)',
            fontSize: 9, color: '#cce8c9', letterSpacing: '0.5px', fontWeight: 600
          }}>
            🤖 ML DOĞRULANDI
          </div>
        )}
        {mlSource === 'pending' && (
          <div className="fire-detail-ml-badge" style={{
            display: 'inline-flex', alignItems: 'center', gap: 4,
            padding: '2px 8px', borderRadius: 20,
            background: 'rgba(247,182,56,0.1)',
            border: '1px solid rgba(247,182,56,0.34)',
            fontSize: 9, color: '#f6d28b', letterSpacing: '0.5px', fontWeight: 600
          }}>
            ⏳ İŞLENİYOR
          </div>
        )}
      </div>

      {/* Risk Çubuğu */}
      <div className="mb-4">
        <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--map-card-divider)' }}>
          <div
            className="h-full transition-all duration-500 shadow-sm"
            style={{ width: `${riskPercentage}%`, background: colors.progress }}
          />
        </div>
      </div>

      {/* Detay Bilgileri Grid */}
      <div className="fire-detail-metrics grid grid-cols-2 gap-3 mb-4">
        {/* Sıcaklık */}
        <div className="fire-detail-metric flex items-start gap-2">
          <div className="mt-0.5">
            <Flame size={14} color="#d42b3f" />
          </div>
          <div className="min-w-0">
            <div className="text-[10px] mb-0.5" style={{ color: 'var(--map-card-muted)' }}>Sıcaklık</div>
            <div className="fire-detail-value text-sm font-semibold" style={{ color: '#f7c1b6' }}>{displayTemperature}</div>
          </div>
        </div>

        {/* Rüzgar */}
        <div className="fire-detail-metric flex items-start gap-2">
          <div className="mt-0.5">
            <Wind size={14} color="#f7b638" />
          </div>
          <div className="min-w-0">
            <div className="text-[10px] mb-0.5" style={{ color: 'var(--map-card-muted)' }}>Rüzgar</div>
            <div className="fire-detail-value text-sm font-semibold" style={{ color: '#f6d28b' }}>{displayWind}</div>
          </div>
        </div>

        {/* Nem */}
        <div className="fire-detail-metric flex items-start gap-2">
          <div className="mt-0.5">
            <Droplet size={14} color="#85a9b2" />
          </div>
          <div className="min-w-0">
            <div className="text-[10px] mb-0.5" style={{ color: 'var(--map-card-muted)' }}>Nem</div>
            <div className="fire-detail-value text-sm font-semibold" style={{ color: '#c5dde0' }}>{displayHumidity}</div>
          </div>
        </div>

        {/* Detay */}
        <div className="fire-detail-metric flex items-end">
          <button
            type="button"
            className="fire-detail-action-button"
            onClick={(event) => {
              event.stopPropagation();
              onShowInList?.();
            }}
          >
            <Navigation size={10} />
            Detay Bak
          </button>
        </div>

      </div>

      <div className="flex items-center justify-between pt-2.5" style={{ borderTop: '1px solid var(--map-card-divider)' }}>
        <div className="flex items-center gap-1.5 text-[11px]">
          <Navigation size={12} color="#f7b638" />
          <span style={{ color: 'var(--map-card-muted)' }}>
            {clusterId ? (
              <>
                KÜME <span className="font-semibold" style={{ color: '#f6d28b' }}>#{clusterId}</span>
                {clusterStatusLabel ? ` · Durum: ${clusterStatusLabel}` : ''}
              </>
            ) : (
              'Küme bilgisi yok'
            )}
          </span>
        </div>
        <div className="text-[10px]" style={{ color: 'var(--map-card-muted)' }}>
          {timeAgo}
        </div>
      </div>
    </div>
  );
}
