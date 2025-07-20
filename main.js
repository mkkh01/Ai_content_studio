// ننتظر حتى يتم تحميل محتوى الصفحة بالكامل
document.addEventListener('DOMContentLoaded', (event) => {

    // Import the functions you need from the SDKs you need
    import { initializeApp } from "firebase/app";
    import { getFirestore, collection, addDoc } from "firebase/firestore";

    // Your web app's Firebase configuration
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
    const db = getFirestore(app);

    // رسالة ترحيب للتأكد من أن كل شيء يعمل
    // لقد قمت بتعطيلها مؤقتًا حتى لا تكون مزعجة في كل مرة
    // alert("مرحباً بك في استوديو المحتوى الذكي! النظام جاهز.");

    // --- ربط زر حفظ المنتج بالوظيفة الخاصة به ---
    const saveButton = document.getElementById('save-product-btn');
    
    if (saveButton) {
        saveButton.addEventListener('click', async () => {
            const productName = document.getElementById('product-name').value;
            const productDescription = document.getElementById('product-description').value;

            if (!productName || !productDescription) {
                alert("❌ الرجاء ملء اسم المنتج ووصفه.");
                return;
            }

            try {
                const docRef = await addDoc(collection(db, "products"), {
                    name: productName,
                    description: productDescription,
                    createdAt: new Date()
                });
                
                alert(`✅ تم حفظ المنتج بنجاح في قاعدة البيانات!`);
                
                document.getElementById('product-name').value = '';
                document.getElementById('product-description').value = '';

            } catch (e) {
                console.error("Error adding document: ", e);
                alert("❌ حدث خطأ أثناء حفظ المنتج. انظر إلى الـ console لمزيد من التفاصيل.");
            }
        });
    } else {
        // هذه الرسالة ستظهر فقط إذا كان هناك خطأ في اسم الزر
        alert("خطأ فادح: لم يتم العثور على زر الحفظ!");
    }

}); // <-- هذا هو القوس الذي يغلق الدالة الجديدة
