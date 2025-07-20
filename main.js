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
const productsListContainer = document.getElementById('products-list-container');
const saveButton = document.getElementById('save-product-btn');
const productNameInput = document.getElementById('product-name');
const productDescriptionInput = document.getElementById('product-description');
const productIdInput = document.getElementById('product-id');
const formTitle = document.getElementById('form-title');
const cancelEditButton = document.getElementById('cancel-edit-btn');

// --- وظيفة عرض المنتجات ---
function renderProducts(products) {
    productsListContainer.innerHTML = '';
    if (products.length === 0) {
        productsListContainer.innerHTML = '<p>لم تقم بإضافة أي منتجات بعد.</p>';
        return;
    }
    products.forEach(product => {
        const productDiv = document.createElement('div');
        productDiv.className = 'list-item';
        productDiv.innerHTML = `
            <div class="list-item-content">
                <strong>${product.name}</strong>
                <p style="color: #606770; margin: 5px 0 0 0;">${product.description}</p>
            </div>
            <div class="list-item-actions">
                <button class="btn-edit" data-id="${product.id}">تعديل</button>
                <button class="btn-delete" data-id="${product.id}">حذف</button>
            </div>
        `;
        productsListContainer.appendChild(productDiv);
    });
}

// --- وظيفة إعادة تعيين النموذج ---
function resetForm() {
    productNameInput.value = '';
    productDescriptionInput.value = '';
    productIdInput.value = '';
    formTitle.innerText = '🎁 إضافة منتج جديد';
    saveButton.innerText = 'حفظ';
    cancelEditButton.style.display = 'none';
}

// --- الاستماع للتغييرات في قاعدة البيانات ---
db.collection("products").orderBy("createdAt", "desc").onSnapshot((snapshot) => {
    const products = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
    renderProducts(products);
});

// --- وظيفة الحفظ والتعديل ---
saveButton.addEventListener('click', () => {
    const productName = productNameInput.value;
    const productDescription = productDescriptionInput.value;
    const productId = productIdInput.value;

    if (!productName || !productDescription) {
        alert("❌ الرجاء ملء اسم المنتج ووصفه.");
        return;
    }

    if (productId) {
        // --- وضع التعديل ---
        db.collection("products").doc(productId).update({
            name: productName,
            description: productDescription
        }).then(() => {
            alert('✅ تم تحديث المنتج بنجاح!');
            resetForm();
        }).catch(error => console.error("خطأ في تحديث المنتج: ", error));
    } else {
        // --- وضع الحفظ ---
        db.collection("products").add({
            name: productName,
            description: productDescription,
            createdAt: new Date()
        }).then(() => {
            alert('✅ تم حفظ المنتج بنجاح!');
            resetForm();
        }).catch(error => console.error("خطأ في حفظ المنتج: ", error));
    }
});

// --- وظيفة الحذف والتعديل (باستخدام تفويض الأحداث) ---
productsListContainer.addEventListener('click', (e) => {
    const target = e.target;
    const id = target.getAttribute('data-id');

    if (target.classList.contains('btn-delete')) {
        // --- الحذف ---
        if (confirm('هل أنت متأكد من أنك تريد حذف هذا المنتج؟')) {
            db.collection('products').doc(id).delete()
              .then(() => alert('🗑️ تم حذف المنتج بنجاح.'))
              .catch(error => console.error("خطأ في حذف المنتج: ", error));
        }
    } else if (target.classList.contains('btn-edit')) {
        // --- التعديل ---
        db.collection('products').doc(id).get().then(doc => {
            if (doc.exists) {
                const product = doc.data();
                productNameInput.value = product.name;
                productDescriptionInput.value = product.description;
                productIdInput.value = doc.id;
                formTitle.innerText = '✏️ تعديل المنتج';
                saveButton.innerText = 'حفظ التعديلات';
                cancelEditButton.style.display = 'inline-block';
                window.scrollTo(0, 0); // الصعود لأعلى الصفحة
            }
        });
    }
});

// --- وظيفة إلغاء التعديل ---
cancelEditButton.addEventListener('click', resetForm);

