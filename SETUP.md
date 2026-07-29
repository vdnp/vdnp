# Dynamic README — Kurulum

Bu klasör `vdnp/vdnp` reponun kökünü birebir yansıtıyor — içindekileri
doğrudan repona kopyalayabilir ya da klasörü olduğu gibi GitHub'ın
"Upload files" sayfasına sürükleyebilirsin. Sadece GitHub'ın kendi verisini
kullanıyor, harici hesap/API key gerekmiyor.

## 1) Tek gereken adım: Actions'a yazma izni ver

Repo → **Settings → Actions → General → Workflow permissions** →
**"Read and write permissions"** seçeneğini işaretle ve kaydet. Bu olmadan
workflow ürettiği SVG'leri commit'leyemez.

## 2) Otomatik üretilen 3 kart

Hepsi `scripts/` altındaki Python dosyalarıyla, GitHub'ın herkese açık REST
API'sinden (repo listesi, `/languages`, `events/public`) besleniyor. Rate
limit için workflow'daki hazır `GITHUB_TOKEN`'ı otomatik kullanıyorlar —
ekstra secret eklemene gerek yok.

| Dosya                              | İçerik                                                        |
|-------------------------------------|----------------------------------------------------------------|
| `working-on-dark/light.svg`         | En son push ettiğin 3 public repo (isim, açıklama, dil, yıldız)|
| `langs-dark/light.svg`              | Tüm public repoların dil dağılımı (byte ağırlıklı, yığın bar)  |
| `activity-dark/light.svg`           | Son commit/PR/star/fork hareketlerin + güne göre renk paleti   |

Her biri API'ye ulaşamazsa (rate limit, ağ sorunu) çökmeden yerel bir yedek
içeriğe düşer, workflow hiçbir zaman kırmızıya düşmez.

## 3) Otomatik çalışma sıklığı

Workflow her 3 saatte bir (`0 */3 * * *`) ve her `main`'e push'ta çalışıyor.
Manuel tetiklemek için: Actions sekmesi → **"Dynamic README"** →
**Run workflow**.

## 4) Ziyaretçi sayacı

`README.md`'deki komarev.com rozeti kurulum istemiyor, direkt çalışır.

---

### İlk çalıştırma

Dosyaları repoya push'ladıktan sonra workflow otomatik tetiklenmeyebilir
(cron'un ilk turu 3 saate kadar sürebilir) — bu yüzden Actions sekmesinden
elle bir kere **Run workflow** demeni öneririm; böylece kartlar gerçek
verinle hemen dolar, yoksa bu pakette gelen (yerel olarak internetsiz
üretilmiş) yedek içerikler görünür kalır.
