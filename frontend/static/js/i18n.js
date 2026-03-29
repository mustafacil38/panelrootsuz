const translations = {
    en: {
        panel_title: "Server Panel",
        system_summary: "System Summary",
        hostname: "Hostname",
        kernel: "Kernel",
        system_status: "System Status",
        disk: "Disk",
        nav_dashboard: "Dashboard",
        nav_services: "Services",
        nav_store: "App Store",
        nav_files: "File Browser",
        nav_settings: "Settings",
        welcome: "Welcome Admin",
        dashboard_desc: "Monitor your Termux server environment from here.",
        sys_uptime: "System Uptime",
        net_traffic: "Network Traffic",
        service_manager: "Service Manager",
        add_service: "Add Service",
        app_store: "App Store",
        store_desc: "One-click installation for popular Termux packages.",
        file_manager: "File Manager",
        file_manager_desc: "Make sure File Browser is installed and running from the App Store or Services.",
        settings: "Settings",
        service_logs: "Service Logs"
    },
    tr: {
        panel_title: "Sunucu Paneli",
        system_summary: "Sistem Özeti",
        hostname: "Makine Adı",
        kernel: "Çekirdek",
        system_status: "Sistem Durumu",
        disk: "Disk",
        nav_dashboard: "Ana Sayfa",
        nav_services: "Servisler",
        nav_store: "App Store",
        nav_files: "Dosya Yöneticisi",
        nav_settings: "Ayarlar",
        welcome: "Hoşgeldin Yönetici",
        dashboard_desc: "Termux sunucu ortamınızı buradan izleyin.",
        sys_uptime: "Çalışma Süresi",
        net_traffic: "Ağ Trafiği",
        service_manager: "Servis Yöneticisi",
        add_service: "Servis Ekle",
        app_store: "Uygulama Mağazası",
        store_desc: "Popüler Termux paketleri için tek tıkla kurulum.",
        file_manager: "Dosya Yöneticisi",
        file_manager_desc: "App Store'dan File Browser'ın kurulu olduğundan ve servisin çalıştığından emin olun.",
        settings: "Ayarlar",
        service_logs: "Servis Kayıtları (Loglar)"
    }
};

let currentLang = localStorage.getItem('panelLang') || 'en';

function applyTranslations() {
    document.documentElement.lang = currentLang;
    const elements = document.querySelectorAll('[data-i18n]');
    elements.forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (translations[currentLang] && translations[currentLang][key]) {
            el.textContent = translations[currentLang][key];
        }
    });
}

function toggleLang() {
    currentLang = currentLang === 'en' ? 'tr' : 'en';
    localStorage.setItem('panelLang', currentLang);
    applyTranslations();
}

// apply on load
applyTranslations();
