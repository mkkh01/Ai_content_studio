// 1. استيراد الوظائف الضرورية من مكتبات Firebase
//    نحن نستخدم روابط CDN مباشرة لأننا لا نستخدم أدوات بناء متقدمة الآن
import { initializeApp } from "https://www.gstatic.com/firebasejs/9.15.0/firebase-app.js";
import { getFirestore, collection, addDoc } from "https://www.gstatic.com/firebasejs/9.15.0/firebase-firestore.js";

// 2. إعدادات الربط مع Firebase (معلوماتك الخاصة)
const firebaseConfig = {
  apiKey: "AIzaSyAmjrlrjus3lXBsOqCY0xwowahjPOl4XFc",
  authDomain: "aicontentstudio-4a0fd.firebaseapp.com",
  projectId: "aicontentstudio-4a0fd",
  storageBucket: "aicontentstudio-4a0fd.firebasestorage.app",
  messagingSenderId: "212059531856",
  appId: "1:212059531856:web:cf259c0a3c73b6bec87f55"
};

// 3. تهيئة تطبيق Firebase وقاعدة البيانات
const app = initializeApp(firebaseConfig);
const db = getFirestore(app);

// رسالة للتأكد من أن كل شيء يعمل عند تحميل الصفحة
console.log("Firebase تم تهيئته بنجاح!");
alert("مرحباً بك في استوديو المحتوى الذكي! النظام جاهز.");

// 4. تعريف وظيفة حفظ المنتج
async function saveProduct() {
    // الحصول على البيانات من حقول الإدخال
    const productName = document.getElementById('productName').value;
    const productDesc = document.getElementById('productDesc').value;

    // التحقق من أن الحقول ليست فارغة
    if (!productName || !productDesc) {
        alert("الرجاء ملء اسم المنتج ووصفه قبل الحفظ.");
        return; // إيقاف الوظيفة إذا كانت البيانات ناقصة
    }

    try {
        // محاولة إضافة مستند جديد إلى "مجموعة" اسمها "products"
        const docRef = await addDoc(collection(db, "products"), {
            name: productName,
            description: productDesc,
            createdAt: new Date() // تسجيل وقت إنشاء المنتج
        });
        
        // إبلاغ المستخدم بالنجاح ومسح الحقول
        alert("✅ تم حفظ المنتج بنجاح في قاعدة البيانات!");
        document.getElementById('productName').value = '';
        document.getElementById('productDesc').value = '';

    } catch (e) {
        // في حال حدوث خطأ، إبلاغ المستخدم وعرض الخطأ في الـ console
        console.error("خطأ في إضافة المستند: ", e);
        alert("❌ حدث خطأ أثناء حفظ المنتج. انظر إلى الـ console لمزيد من التفاصيل.");
    }
}

// 5. ربط الزر بوظيفة الحفظ
//    نبحث عن الزر الذي له ID اسمه "saveProductBtn"
const saveButton = document.getElementById('saveProductBtn');
//    نضيف "مستمع حدث" ينتظر نقرة المستخدم لتشغيل وظيفة saveProduct
saveButton.addEventListener('click', saveProduct);
