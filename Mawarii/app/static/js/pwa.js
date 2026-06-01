// static/js/pwa.js
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/service-worker.js')
      .then(registration => {
        console.log('✅ Service Worker registered successfully:', registration);
      })
      .catch(error => {
        console.log('❌ Service Worker registration failed:', error);
      });
  });
}

// كشف ما إذا كان التطبيق مثبتًا (PWA)
let deferredPrompt;
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e;
  console.log('✅ PWA installation prompt available');

  // يمكنك إظهار زر التثبيت هنا إذا أردت
  const installBtn = document.getElementById('installBtn');
  if (installBtn) {
    installBtn.style.display = 'block';
    installBtn.addEventListener('click', () => {
      deferredPrompt.prompt();
      deferredPrompt.userChoice.then((choiceResult) => {
        if (choiceResult.outcome === 'accepted') {
          console.log('User accepted the install prompt');
        }
        deferredPrompt = null;
      });
    });
  }
});