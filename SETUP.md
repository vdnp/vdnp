# Dynamic README — Kurulum

Bu klasör `vdnp/vdnp` reponun kökünü birebir yansıtıyor — içindekileri
doğrudan repona kopyalayabilir ya da klasörü olduğu gibi GitHub'ın
"Upload files" sayfasına sürükleyebilirsin (`.github` klasörü için "yeni
dosya oluştur" yöntemini kullanman daha garanti — ayrıca anlatıyorum).

## 1) Tek zorunlu adım: Actions'a yazma izni ver

Repo → **Settings → Actions → General → Workflow permissions** →
**"Read and write permissions"** seçeneğini işaretle ve kaydet. Bu olmadan
workflow ürettiği SVG'leri commit'leyemez.

## 2) Otomatik üretilen 5 kart

Hepsi `scripts/` altındaki Python dosyalarıyla, GitHub'ın herkese açık REST
API'sinden besleniyor. Rate limit için workflow'daki hazır `GITHUB_TOKEN`'ı
otomatik kullanıyorlar — ekstra secret eklemene gerek yok (Spotify hariç,
aşağıda anlatıyorum).

| Dosya                              | İçerik                                                          |
|-------------------------------------|--------------------------------------------------------------------|
| `dark/light.svg`                    | Hero: karşılama, dönen rol yazısı, skill etiketleri, Spotify şeridi |
| `stats-dark/light.svg`              | Repo/yıldız/takipçi/PR/issue/fork sayıları (kendi ürettiğimiz, servis değil) |
| `working-on-dark/light.svg`         | En son push ettiğin 3 public repo                                   |
| `langs-dark/light.svg`              | Tüm public repoların dil dağılımı                                   |
| `activity-dark/light.svg`           | Son commit/PR/star/fork hareketlerin + güne göre renk paleti        |

Her biri API'ye ulaşamazsa çökmeden yerel bir yedek içeriğe düşer, workflow
hiçbir zaman kırmızıya düşmez.

## 3) Spotify "Şu An Dinliyorum" (opsiyonel)

Bu artık üçüncü parti bir servise değil, doğrudan senin kendi Spotify
uygulamana bağlanıyor — o yüzden kapanma riski yok, ama tek seferlik bir
kurulum gerekiyor:

1. https://developer.spotify.com/dashboard → **Create app**. İsim/açıklama
   istediğin gibi, **Redirect URI** kutusuna `http://127.0.0.1:8888/callback`
   yaz. Kaydettikten sonra **Client ID** ve **Client Secret**'ı not al.
2. Tarayıcıda şu adresi aç (CLIENT_ID kısmını kendi Client ID'inle değiştir):
   ```
   https://accounts.spotify.com/authorize?client_id=CLIENT_ID&response_type=code&redirect_uri=http://127.0.0.1:8888/callback&scope=user-read-currently-playing%20user-read-recently-played
   ```
   Spotify hesabınla giriş yapıp izin ver. Sayfa hataya düşecek (localhost'ta
   sunucu yok, normal) ama adres çubuğundaki URL'de `?code=...` kısmını
   kopyala.
3. Aşağıdaki komutu **kendi bilgisayarında** çalıştır (CLIENT_ID,
   CLIENT_SECRET, CODE'u kendi değerlerinle değiştir):
   ```bash
   curl -X POST https://accounts.spotify.com/api/token \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d grant_type=authorization_code \
     -d code=CODE \
     -d redirect_uri=http://127.0.0.1:8888/callback \
     -u CLIENT_ID:CLIENT_SECRET
   ```
   Dönen JSON içindeki `refresh_token` değerini kopyala.
4. Repo → **Settings → Secrets and variables → Actions** → şu üç secret'ı
   ekle: `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REFRESH_TOKEN`.

Bu üçü yoksa hero kartında sadece "Spotify henüz bağlanmadı" yazar, hiçbir
şey bozulmaz — istediğin zaman kurabilirsin.

## 4) Private repoları sayıma dahil etmek (opsiyonel)

Varsayılan `GITHUB_TOKEN` sadece bu reponun kendisini görebiliyor, private
repolarına erişemiyor. İstersen **stats** ve **dil dağılımı** kartlarına
private repolarını da (sadece toplam sayı/dil oranı olarak, isim
gösterilmeden) dahil edebilirsin. Bilinçli olarak **sadece bu iki karta**
uygulandı — canlı aktivite ve "şu an çalıştıklarım" kartları hâlâ yalnızca
public verinle çalışıyor, böylece private repo push zamanlaman hiçbir yerde
görünmüyor.

1. https://github.com/settings/tokens?type=beta → **Generate new token**
   (Fine-grained token).
2. **Resource owner**: kendi hesabın (`vdnp`) — bir organizasyon **değil**.
   Bu önemli: token'ı sadece kendi private repolarını görecek şekilde
   sınırlıyor, herhangi bir organizasyona ait private koda asla erişemiyor.
3. **Repository access** → "All repositories" (ya da sadece istediklerini
   seç).
4. **Permissions** → sadece şunları **Read-only** yap: `Contents` ve
   `Metadata`. Başka hiçbir izin gerekmiyor.
5. Token'ı oluştur, değerini kopyala.
6. Repo → **Settings → Secrets and variables → Actions** → yeni secret:
   `PRIVATE_REPO_PAT` adıyla ekle, değerine token'ı yapıştır.

Bu secret yoksa iki kart da sorunsuz şekilde sadece public verinle çalışmaya
devam eder — hiçbir şey kırılmaz.

## 5) Ziyaretçi sayacı

`README.md`'deki komarev.com rozeti kurulum istemiyor, direkt çalışır.

---

### İlk çalıştırma

Dosyaları repoya push'ladıktan sonra workflow otomatik tetiklenmeyebilir
(cron'un ilk turu 3 saate kadar sürebilir) — bu yüzden Actions sekmesinden
elle bir kere **Run workflow** demeni öneririm; böylece kartlar gerçek
verinle hemen dolar, yoksa bu pakette gelen (yerel olarak internetsiz
üretilmiş) yedek içerikler görünür kalır.
