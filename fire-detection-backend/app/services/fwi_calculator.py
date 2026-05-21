"""
Canadian Forest Fire Weather Index (FWI) System
Van Wagner, C.E. (1987) hesaplamalarına dayalı gerçek FWI indeks hesaplayıcı.

Referans:
  Van Wagner, C.E. 1987. Development and structure of the Canadian Forest Fire
  Weather Index System. Forestry Technical Report 35. Ottawa: Canadian Forestry Service.
"""

import math


# Ay bazlı gün uzunluğu ayar faktörleri (DMC için)
DMC_DAY_LENGTH = [6.5, 7.5, 9.0, 12.8, 13.9, 13.9, 12.4, 10.9, 9.4, 8.0, 7.0, 6.0]

# Ay bazlı gün uzunluğu ayar faktörleri (DC için)
DC_DAY_LENGTH = [-1.6, -1.6, -1.6, 0.9, 3.8, 5.8, 6.4, 5.0, 2.4, 0.4, -1.6, -1.6]


def ffmc_calc(temp: float, rh: float, wind: float, rain: float, ffmc_prev: float = 85.0) -> float:
    """
    Fine Fuel Moisture Code (FFMC) hesaplama.
    İnce yakıt nemini temsil eder. 0-101 aralığında.

    Args:
        temp: Sıcaklık (°C)
        rh: Bağıl nem (%)
        wind: Rüzgar hızı (km/h)
        rain: 24 saatlik yağış (mm)
        ffmc_prev: Önceki günün FFMC değeri (varsayılan 85)
    """
    # Önceki FFMC'den nem içeriği (moisture content) hesapla
    mo = 147.2 * (101.0 - ffmc_prev) / (59.5 + ffmc_prev)

    # Yağış etkisi
    if rain > 0.5:
        rf = rain - 0.5

        if mo <= 150.0:
            mr = mo + 42.5 * rf * math.exp(-100.0 / (251.0 - mo)) * (1.0 - math.exp(-6.93 / rf))
        else:
            mr = (mo + 42.5 * rf * math.exp(-100.0 / (251.0 - mo)) * (1.0 - math.exp(-6.93 / rf))
                  + 0.0015 * (mo - 150.0) ** 2 * rf ** 0.5)

        if mr > 250.0:
            mr = 250.0
        mo = mr

    # Denge nem içeriği (Equilibrium Moisture Content)
    ed = (0.942 * rh ** 0.679 + 11.0 * math.exp((rh - 100.0) / 10.0)
          + 0.18 * (21.1 - temp) * (1.0 - math.exp(-0.115 * rh)))

    if mo > ed:
        # Kuruma aşaması
        ew = ed  # kullanılmıyor ama referans için
        ko = 0.424 * (1.0 - (rh / 100.0) ** 1.7) + 0.0694 * wind ** 0.5 * (1.0 - (rh / 100.0) ** 8)
        kd = ko * 0.581 * math.exp(0.0365 * temp)
        m = ed + (mo - ed) * 10.0 ** (-kd)
    else:
        # Islak aşama
        ew = (0.618 * rh ** 0.753 + 10.0 * math.exp((rh - 100.0) / 10.0)
              + 0.18 * (21.1 - temp) * (1.0 - math.exp(-0.115 * rh)))

        if mo < ew:
            k1 = 0.424 * (1.0 - ((100.0 - rh) / 100.0) ** 1.7) + 0.0694 * wind ** 0.5 * (1.0 - ((100.0 - rh) / 100.0) ** 8)
            kw = k1 * 0.581 * math.exp(0.0365 * temp)
            m = ew - (ew - mo) * 10.0 ** (-kw)
        else:
            m = mo

    # Nem içeriğinden FFMC'ye dönüştür
    ffmc = 59.5 * (250.0 - m) / (147.2 + m)
    ffmc = max(0.0, min(101.0, ffmc))

    return ffmc


def dmc_calc(temp: float, rh: float, rain: float, dmc_prev: float = 6.0, month: int = 7) -> float:
    """
    Duff Moisture Code (DMC) hesaplama.
    Orta derinlikteki organik tabakanın nemini temsil eder.

    Args:
        temp: Sıcaklık (°C)
        rh: Bağıl nem (%)
        rain: 24 saatlik yağış (mm)
        dmc_prev: Önceki günün DMC değeri (varsayılan 6)
        month: Ay (1-12)
    """
    if temp < -1.1:
        temp = -1.1

    # Gün uzunluğu faktörü
    dl = DMC_DAY_LENGTH[month - 1]

    # Yağış etkisi
    if rain > 1.5:
        re = 0.92 * rain - 1.27

        mo = 20.0 + math.exp(5.6348 - dmc_prev / 43.43)

        if dmc_prev <= 33.0:
            b = 100.0 / (0.5 + 0.3 * dmc_prev)
        elif dmc_prev <= 65.0:
            b = 14.0 - 1.3 * math.log(dmc_prev)
        else:
            b = 6.2 * math.log(dmc_prev) - 17.2

        mr = mo + 1000.0 * re / (48.77 + b * re)
        pr = 244.72 - 43.43 * math.log(mr - 20.0)
        dmc_prev = max(0.0, pr)

    # Kuru hava etkisi
    if temp > -1.1:
        k = 1.894 * (temp + 1.1) * (100.0 - rh) * dl * 1e-6
    else:
        k = 0.0

    dmc = dmc_prev + 100.0 * k
    return max(0.0, dmc)


def dc_calc(temp: float, rain: float, dc_prev: float = 15.0, month: int = 7) -> float:
    """
    Drought Code (DC) hesaplama.
    Derin organik tabakanın kuraklık durumunu temsil eder.

    Args:
        temp: Sıcaklık (°C)
        rain: 24 saatlik yağış (mm)
        dc_prev: Önceki günün DC değeri (varsayılan 15)
        month: Ay (1-12)
    """
    if temp < -2.8:
        temp = -2.8

    # Gün uzunluğu ayarlama faktörü
    lf = DC_DAY_LENGTH[month - 1]

    # Yağış etkisi
    if rain > 2.8:
        rd = 0.83 * rain - 1.27
        qo = 800.0 * math.exp(-dc_prev / 400.0)
        qr = qo + 3.937 * rd
        dr = 400.0 * math.log(800.0 / qr)
        dc_prev = max(0.0, dr)

    # Potansiyel buharlaşma
    if temp > -2.8:
        v = 0.36 * (temp + 2.8) + lf
        v = max(0.0, v)
    else:
        v = 0.0

    dc = dc_prev + 0.5 * v
    return max(0.0, dc)


def isi_calc(ffmc: float, wind: float) -> float:
    """
    Initial Spread Index (ISI) hesaplama.
    Yangının yayılma hızını temsil eder.

    Args:
        ffmc: Fine Fuel Moisture Code
        wind: Rüzgar hızı (km/h)
    """
    m = 147.2 * (101.0 - ffmc) / (59.5 + ffmc)
    fw = math.exp(0.05039 * wind)
    ff = 91.9 * math.exp(-0.1386 * m) * (1.0 + m ** 5.31 / (4.93 * 1e7))
    isi = 0.208 * fw * ff
    return isi


def bui_calc(dmc: float, dc: float) -> float:
    """
    Buildup Index (BUI) hesaplama.
    Yanabilir madde miktarını temsil eder.

    Args:
        dmc: Duff Moisture Code
        dc: Drought Code
    """
    if dmc <= 0.4 * dc:
        bui = 0.8 * dmc * dc / (dmc + 0.4 * dc) if (dmc + 0.4 * dc) > 0 else 0.0
    else:
        bui = dmc - (1.0 - 0.8 * dc / (dmc + 0.4 * dc)) * (0.92 + (0.0114 * dmc) ** 1.7) if (dmc + 0.4 * dc) > 0 else 0.0

    return max(0.0, bui)


def fwi_calc(isi: float, bui: float) -> float:
    """
    Fire Weather Index (FWI) hesaplama.
    Genel yangın yoğunluğunu temsil eder.

    Args:
        isi: Initial Spread Index
        bui: Buildup Index
    """
    if bui <= 80.0:
        fd = 0.626 * bui ** 0.809 + 2.0
    else:
        fd = 1000.0 / (25.0 + 108.64 * math.exp(-0.023 * bui))

    b = 0.1 * isi * fd

    if b > 1.0:
        fwi = math.exp(2.72 * (0.434 * math.log(b)) ** 0.647)
    else:
        fwi = b

    return fwi


def calculate_all_fwi(
    temp: float,
    rh: float,
    wind: float,
    rain: float,
    month: int = 7,
    ffmc_prev: float = 85.0,
    dmc_prev: float = 6.0,
    dc_prev: float = 15.0
) -> dict:
    """
    Tüm FWI bileşenlerini tek seferde hesapla.

    Args:
        temp: Sıcaklık (°C)
        rh: Bağıl nem (%)
        wind: Rüzgar hızı (km/h). OpenWeather m/s verir, çağırmadan önce dönüştür.
        rain: 24 saatlik yağış (mm)
        month: Ay (1-12)
        ffmc_prev: Önceki FFMC (varsayılan 85)
        dmc_prev: Önceki DMC (varsayılan 6)
        dc_prev: Önceki DC (varsayılan 15)

    Returns:
        dict: FFMC, DMC, DC, ISI, BUI, FWI değerleri
    """
    ffmc = ffmc_calc(temp, rh, wind, rain, ffmc_prev)
    dmc = dmc_calc(temp, rh, rain, dmc_prev, month)
    dc = dc_calc(temp, rain, dc_prev, month)
    isi = isi_calc(ffmc, wind)
    bui = bui_calc(dmc, dc)
    fwi = fwi_calc(isi, bui)

    return {
        "ffmc": round(ffmc, 2),
        "dmc": round(dmc, 2),
        "dc": round(dc, 2),
        "isi": round(isi, 2),
        "bui": round(bui, 2),
        "fwi": round(fwi, 2)
    }
