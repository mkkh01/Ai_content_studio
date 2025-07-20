// تهيئة Firebase - هذا الكود خاص بك
const firebaseConfig = {
  apiKey: "AIzaSyAmjrlrjus3lXBsOqCY0xwowahjPOl4XFc",
  authDomain: "aicontentstudio-4a0fd.firebaseapp.com",
  projectId: "aicontentstudio-4a0fd",
  storageBucket: "aicontentstudio-4a0fd.firebasestorage.app",
  messagingSenderId: "212059531856",
  appId: "1:212059531856:web:cf259c0a3c73b6bec87f55"
};

// تهيئة التطبيق وقاعدة البيانات
const app = firebase.initializeApp(firebaseConfig);
const db = firebase.firestore();

// --- ربط زر حفظ المنتج بالوظيفة الخاصة به ---
const saveButton = document.getElementById('save-product-btn');

saveButton.addEventListener('click', () => {
    const productName = document.getElementById('product-name').value;
    const productDescription = document.getElementById('product-description').value;

    if (!productName || !productDescription) {
        alert("❌ الرجاء ملء اسم المنتج ووصفه.");
        return;
    }

    // محاولة إضافة المنتج إلى قاعدة البيانات
    db.collection("products").add({
        name: productName,
        description: productDescription,
        createdAt: new Date()
    })
    .then((docRef) => {
        // إذا نجحت العملية
        alert(`✅ تم حفظ المنتج بنجاح!`);
        document.getElementById('product-name').value = '';
        document.getElementById('product-description').value = '';
    })
    .catch((error) => {
        // إذا فشلت العملية
        console.error("Error adding document: ", error);
        alert("❌ حدث خطأ أثناء حفظ المنتج. تحقق من الـ console.");
    });
});

// رسالة ترحيب أخيرة للتأكد أن الملف يعمل
alert("النظام يعمل بالطريقة الكلاسيكية!");
