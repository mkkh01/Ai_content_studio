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
const navLinks = document.querySelectorAll('.sidebar-nav a');
const pageContent = document.getElementById('page-content');

// --- عناصر صفحة إدارة المنتجات ---
const saveProductBtn = document.getElementById('save-product-btn');
const productIdInput = document.getElementById('product-id');
const productNameInput = document.getElementById('product-name-input');
const productNotesInput = document.getElementById('product-notes-input');
const cancelEditBtn = document.getElementById('cancel-edit-btn');

// --- نظام التنقل بين الصفحات ---
function showPage(pageId) {
    // إخفاء كل الصفحات
    const pages = pageContent.children;
    for (let page of pages) {
        page.style.display = 'none';
    }
    // إظهار الصفحة المطلوبة
    document.getElementById(`${pageId}-page`).style.display = 'block';

    // تحديث الرابط النشط في الشريط الجانبي
    navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('data-page') === pageId) {
            link.classList.add('active');
        }
    });
}

navLinks.forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        const pageId = link.getAttribute('data-page');
        showPage(pageId);
    });
});

// --- وظيفة عرض المنتجات في الجدول ---
function renderProductsTable(products) {
    productsTableBodyEl.innerHTML = '';
    if (products.length === 0) {
        productsTableBodyEl.innerHTML = '<tr><td colspan="3" style="text-align:center;">لا توجد منتجات.</td></tr>';
        return;
    }
    products.forEach(product => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><strong>${product.name}</strong></td>
            <td>${product.notes || 'لا توجد'}</td>
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
    productsCountEl.innerText = products.length;
    renderProductsTable(products);
});

// --- وظائف الحذف والتعديل ---
productsTableBodyEl.addEventListener('click', (e) => {
    const target = e.target;
    const id = target.getAttribute('data-id');

    if (target.classList.contains('btn-delete')) {
        if (confirm('هل أنت متأكد من الحذف؟')) {
            db.collection('products').doc(id).delete();
        }
    } else if (target.classList.contains('btn-edit')) {
        db.collection('products').doc(id).get().then(doc => {
            if (doc.exists) {
                const product = doc.data();
                productIdInput.value = doc.id;
                productNameInput.value = product.name;
                productNotesInput.value = product.notes || '';
                showPage('products'); // الانتقال إلى صفحة إدارة المنتجات
                cancelEditBtn.style.display = 'inline-block'; // إظهار زر إلغاء التعديل
            }
        });
    }
});

// --- وظيفة حفظ أو تحديث المنتج ---
saveProductBtn.addEventListener('click', () => {
    const id = productIdInput.value;
    const name = productNameInput.value;
    const notes = productNotesInput.value;

    if (!name) {
        alert('اسم المنتج مطلوب.');
        return;
    }

    const data = { name, notes, createdAt: new Date() };

    if (id) { // إذا كان هناك ID، فهذا يعني تحديث
        db.collection('products').doc(id).update({ name, notes })
            .then(() => resetForm());
    } else { // وإلا، فهو إضافة منتج جديد
        db.collection('products').add(data)
            .then(() => resetForm());
    }
});

// --- وظيفة إلغاء التعديل ---
function resetForm() {
    productIdInput.value = '';
    productNameInput.value = '';
    productNotesInput.value = '';
    cancelEditBtn.style.display = 'none';
    showPage('dashboard'); // العودة إلى لوحة الإحصائيات
}
cancelEditBtn.addEventListener('click', resetForm);

// --- إظهار الصفحة الافتراضية عند التحميل ---
showPage('dashboard');
