# Legacy Manual Checks

Bu klasordeki dosyalar pytest test suite'inin parcasi degildir.

Bu scriptler eski manuel dogrulama amaciyla yazilmistir:

- Bazi scriptler calisan local API'ye istek atar.
- Bazi scriptler gercek/local database ayarlari ister.
- Bazi scriptler model dosyalarini dogrudan yukler.
- Bazi scriptler dis servis veya production benzeri akislara baglidir.

Resmi test suite icin proje kokunden su komut kullanilir:

```bash
pytest
```

Pytest sadece `tests/` altindaki testleri toplar; bu davranis `pytest.ini` icindeki `testpaths = tests` ayariyla sabittir.

Bu dosyalardan biri tekrar otomatik teste donusturulecekse `tests/` altina fixture, mock ve `TEST_DATABASE_URL` uyumuyla tasinmalidir.
