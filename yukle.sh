REPO_URL="https://github.com/mustafacil38/panelrootsuz.git"

echo "🚀 panelrootsuz GitHub yükleme işlemi başlatılıyor..."

# Git'i temizle ve başlat
rm -rf .git
git init

# Dosyaları ekle
git add .

# İlk commit
git commit -m "panelrootsuz"

# Main branch oluştur
git branch -M main

# Uzak depoyu bağla
git remote add origin $REPO_URL

# Gönder
echo "📤 Kodlar GitHub'a (mustafacil38/panelrootsuzv2) gönderiliyor..."
git push -u origin main --force

echo "✅ İşlem tamamlandı! Artık Firebase App Hosting'e bağlanabilirsin."
