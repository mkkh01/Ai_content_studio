// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getFirestore, collection, addDoc } from "firebase/firestore"; // <-- السطر المهم الذي تم تعديله

// Your web app's Firebase configuration
// (هذا الكود خاص بك ويجب أن يبقى كما هو)
const firebaseConfig = {
  apiKey: "AIzaSyAmjrlrjus3lXBsOqCY0xwowahjPOl4XFc",
  authDomain: "aicontentstudio-4a0fd.firebaseapp.com",
  projectId: "aicontentstudio-4a0fd",
  storageBucket: "aicontentstudio-4a0fd.firebasestorage.app",
  messagingSenderId: "212059531856",
  appId: "1:212059531856:web:cf259c0a3c73b6bec87f55"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const db = getFirestore(app); // <-- تهيئة Firestore وإعطائها اسمًا بسيطًا هو db

// رسالة ترحيب للتأكد من أن كل شيء يعمل
alert("مرحباً بك في استوديو المحتوى الذكي! النظام جاهز.");

// --- ربط زر حفظ المنتج بالوظيفة الخاصة به ---
document.getElementById('save-product-btn').addEventListener('click', async () => {
    const productName = document.getElementById('product-name').value;
    const productDescription = document.getElementById('product-description').value;

    // التحقق من أن الحقول ليست فارغة
    if (!productName || !productDescription) {
        alert("❌ الرجاء ملء اسم المنتج ووصفه.");
        return;
    }

    try {
        // محاولة إضافة المنتج إلى قاعدة البيانات
        const docRef = await addDoc(collection(db, "products"), {
            name: productName,
            description: productDescription,
            createdAt: new Date() // إضافة تاريخ الإنشاء
        });
        
        // إذا نجحت العملية
        alert(`✅ تم حفظ المنتج بنجاح في قاعدة البيانات!`);
        
        // تفريغ الحقول بعد الحفظ
        document.getElementById('product-name').value = '';
        document.getElementById('product-description').value = '';

    } catch (e) {
        // إذا فشلت العملية
        console.error("Error adding document: ", e);
        alert("❌ حدث خطأ أثناء حفظ المنتج. انظر إلى الـ console لمزيد من التفاصيل.");
    }
});
