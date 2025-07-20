// تهيئة Firebase
const firebaseConfig = {
  apiKey: "AIzaSyAmjrlrjus3lXBsOqCY0xwowahjPOl4XFc",
  authDomain: "aicontentstudio-4a0fd.firebaseapp.com",
  projectId: "aicontentstudio-4a0fd",
  storageBucket: "aicontentstudio-4a0fd.firebasestorage.app",
  messagingSenderId: "212059531856",
  appId: "1:212059531856:web:cf259c0a3c73b6bec87f55"
};

firebase.initializeApp(firebaseConfig);
const db = firebase.firestore();

// --- عناصر الواجهة ---
const productsCountEl = document.getElementById('products-count');
const productsTableBodyEl = document.getElementById('products-table-body');

// --- وظيفة عرض المنتجات في الجدول ---
function renderProductsTable(products) {
    productsTableBodyEl.innerHTML = ''; // تفريغ الجدول قبل العرض
    if (products.length === 0) {
        productsTableBodyEl.innerHTML = '<tr><td colspan="3" style="text-align:center;">لا توجد منتجات لعرضها.</td></tr>';
        return;
    }

    // عرض آخر 5 منتجات فقط
    const latestProducts = products.slice(0, 5);

    latestProducts.forEach(product => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><strong>${product.name}</strong></td>
            <td>${product.description.substring(0, 40)}...</td>
            <td>
                <button class="action-btn-table btn-edit" data-id="${product.id}">تعديل</button>
                <button class="action-btn-table btn-delete" data-id="${product.id}">حذف</button>
            </td>
        `;
        productsTableBodyEl.appendChild(row);
    });
}

// --- الاستماع للتغييرات في قاعدة البيانات ---
db.collection("products").orderBy("createdAt", "desc").onSnapshot((snapshot) => {
    const products = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
    
    // تحديث بطاقة عدد المنتجات
    productsCountEl.innerText = products.length;

    // تحديث جدول آخر المنتجات
    renderProductsTable(products);
});

// ملاحظة: وظائف الحذف والتعديل والإضافة تحتاج إلى إعادة ربطها بالواجهة الجديدة
// سنقوم بذلك في الخطوة التالية بعد أن تتأكد من أن التصميم يعجبك.
// حاليًا، هذا الكود مسؤول فقط عن عرض البيانات في الواجهة الجديدة.
