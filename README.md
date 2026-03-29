# Mustafa Android Telefon Sunucu Yönetim Paneli

Bu proje, **root yetkisi bulunmayan bir Android telefonda**, Termux uygulaması (veya içerisine kurulan PRoot Debian/Ubuntu gibi Linux dağıtımları) üzerinde çalışacak şekilde entegre edilmiş modern bir **Sunucu Yönetim Paneli**'dir.

Panelin amacı; cihazın sistem kaynaklarını (CPU, RAM, Disk, Ağ) anlık olarak görebilmek, arka planda çalışan web sunucuları veya araçları (NGINX, PHP, vb.) yönetebilmek, tek tuşla hazır paketleri kurabilmek ve bir dosya yöneticisi arayüzü sunabilmektir.

---

## 🔥 Temel Özellikler

- **Modern & Premium Tasarım:** En son trend olan *Glassmorphism* (Cam Etkisi) ve Dark/Light mode destekli, harika görünen Vanilla JS, HTML ve CSS arayüzü.
- **Canlı Sistem İzleme:** Chart.js kütüphanesi ve Rest API sayesinde her 5 saniyede bir CPU, RAM ve Disk durumunu görsel kadranlarla çekip ekrana yansıtır.
- **Çoklu Dil Desteği (i18n):** Sağ üst köşeden anında İngilizce (EN) ve Türkçe (TR) arasında geçiş yapılabilir.
- **Servis Yönetimi:** Kurulu servisleri başlatma, durdurma, çalışan servislerin portlarına hızlı bağlantı (yeni sekme) ve doğrudan Log (`tail`) ekranlarını okuyabilme özelliği.
- **Uygulama Mağazası (App Store):** Tek tıkla Nginx, PHP, File Browser, Nextcloud gibi uygulamaları Termux altyapısı üzerinden (paket yöneticileri veya komut satırı ile) otomatik kuyruğa alıp kurma işlemi yapar.
- **Dosya Yöneticisi Entegrasyonu:** Eğer port 8080 üzerinde [File Browser](https://github.com/filebrowser/filebrowser) uygulaması devredeyse, iframe aracılığıyla o sayfada pürüzsüz çalışacak şekilde entegre edilmiştir.

---

## 🛠 Kullanılan Teknolojiler

- **Arka Plan (Backend):** Python + FastAPI. Hafif ve inanılmaz hızlı asenkron (async) yapısı sayesinde sunucuyu boğmaz.
- **Veritabanı:** SQLite & SQLAlchemy. Yapılandırma veya ağır kurulumlar gerektirmeyen tek dosyalı `data/panel.db` veritabanı kullanılır.
- **Ön Yüz (Frontend):** 
  - Vanilla HTML5 ve CSS3 (Next.js, Vue, React gibi ağır yüklerden kaçınılmıştır).
  - Chart.js (Grafikler)
  - FontAwesome (İkonlar)
- **Sistem İletişimi:** `psutil` CPU/RAM okumaları için kullanılır. Root olmayan Termux'da bazen `psutil` kısıtlanabileceğinden, arka planda `/proc/stat` okuma fonksiyonu *(fallback)* yazılmıştır.

---

## 🚀 Başlarken (Kurulum ve Çalıştırma)

### 1. Dosyaların Açılması

Sistem klasörlerini Termux ortamına (Örneğin; `~/panel/` dizini) kopyalayın.

### 2. Python ve Bağımlılıkların Kurulumu

Termux'da temel paketlerin olduğundan emin olun:
```bash
pkg update && pkg upgrade
pkg install python python-pip
```

*(Not: Proje, telefonunuzda halihazırda yüklü olan paketler (FastAPI, Uvicorn, SQLAlchemy vb.) ve yerleşik Python kütüphaneleri ile çalışacak şekilde optimize edilmiştir. Harici bir `requirements.txt` kurmanıza gerek yoktur.)*

### 3. Paneli Başlatma

Uvicorn ASGI sunucusunu kullanarak FastAPI uygulamasını başlatın:
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 1569
```

Artık tarayıcınızdan şu adrese giderek panele erişebilirsiniz:
**http://Cihaz_IP_Adresi:1569** 

---

## 🔐 Varsayılan Kimlik Bilgileri

Sistem ilk kez çalıştığında veritabanı `data/panel.db` dosyasına otomatik olarak kurulur.

- **Kullanıcı Adı:** `admin`
- **Şifre:** `admin`

*(Panele giriş yaptıktan sonra güvenlik amacıyla bu şifrenin değiştirilmesi tavsiye edilir)*

---

## ⚠️ Kritik Uyarılar / Termux Kısıtlamaları

1. **Root Olmama Durumu:**
   Android, root (süper kullanıcı) yetkileri olmadan 1024 ve altındaki portların açılmasına izin vermez. Nginx vb. servislerin kurulumlarında her zaman 1569 veya 8080 gibi `>1024` portlar kullanılmalıdır.
   
2. **Arka Plan Uygulamaları Yönetimi:**
   `panel/backend/routers/services.py` dosyası içinde Servislerin durdurma (`pkill`) işlemleri Termux kısıtlamalarına göre optimize edilmelidir. Yanlış `pkill` argümanı Termux shellinin de çökmesine neden olabilir.

3. **Otomatik Başlatma (Autostart):**
   Android işletim sistemi Termux'un sürekli arka planda kalmasını öldürebilir (Battery Optimization). Kalıcı bir yapı için Android izinlerinden Termux için **Pil Optimizasyonunu Kapat** demeyi unutmayınız.

---
*Mustafa için özel olarak tasarlanmıştır. Keyifli yönetimler!*
