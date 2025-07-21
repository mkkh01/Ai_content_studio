document.addEventListener('DOMContentLoaded', () => {
    // --- تهيئة Firebase ---
    const firebaseConfig = {
        apiKey: "AIzaSyAmjrlrjus3lXBsOqCY0xwowahjPOl4XFc",
        authDomain: "aicontentstudio-4a0fd.firebaseapp.com",
        projectId: "aicontentstudio-4a0fd",
        storageBucket: "aicontentstudio-4a0fd.firebasestorage.app",
        messagingSenderId: "212059531856",
        appId: "1:212059531856:web:cf259c0a3c73b6bec87f55"
    };
    firebase.initializeApp(firebaseConfig);
    const auth = firebase.auth();

    const loginBtn = document.getElementById('login-btn');
    const statusP = document.getElementById('status');

    // --- وظيفة تسجيل الدخول ---
    const handleLogin = () => {
        statusP.textContent = "جاري إعادة التوجيه إلى فيسبوك...";
        const provider = new firebase.auth.FacebookAuthProvider();
        auth.signInWithRedirect(provider);
    };

    loginBtn.addEventListener('click', handleLogin);

    // --- أهم وظيفة: معالجة نتيجة العودة ---
    auth.getRedirectResult()
        .then((result) => {
            if (result.credential) {
                // نجحت العملية
                const user = result.user;
                statusP.textContent = `✅ نجح تسجيل الدخول! مرحباً بك، ${user.displayName}. معرف المستخدم: ${user.uid}`;
                loginBtn.style.display = 'none'; // إخفاء زر الدخول
            }
        })
        .catch((error) => {
            // فشلت العملية
            statusP.textContent = `❌ فشل تسجيل الدخول. الخطأ: ${error.message}`;
            console.error("Authentication Error:", error);
        });

    // مراقبة حالة المستخدم
    auth.onAuthStateChanged((user) => {
        if (user) {
            statusP.textContent = `أنت مسجل دخولك حاليًا. مرحباً، ${user.displayName}.`;
            loginBtn.style.display = 'none';
        }
    });
});
