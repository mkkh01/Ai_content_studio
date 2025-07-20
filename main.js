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

// --- عناصر نافذة التعديل ---
const editModalOverlay = document.getElementById('edit-modal-overlay');
const editProductIdInput = document.getElementById('edit-product-id');
const editProductNameInput = document.getElementById('edit-product-name');
const editProductDescriptionInput = document.getElementById('edit-product-description');
const updateButton = document.getElementById('update-product-btn');
const closeModalButton = document.getElementById('close-modal-btn');
const cancelModalButton = document.getElementById('cancel-modal-btn');

// --- وظيفة عرض المنتجات ---
function renderProducts(products) {
    productsListContainer.innerHTML = '';
    if (products.length === 0) {
        productsListContainer.innerHTML = '<p>لم تقم بإضافة أي منتجات بعد. ابدأ بإضافة أول منتج لك!</p>';
        return;
    }
    products.forEach(product => {
        const productDiv = document.createElement('div');
        productDiv.className = 'product-item';
        productDiv.innerHTML = `
            <div>
                <strong>${product.name}</strong>
                <p>${product.description.substring(0, 60)}...</p>
            </div>
            <div>
                <button class="action-btn btn-edit" data-id="${product.id}">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" /></svg>
                </button>
                <button class="action-btn btn-delete" data-id="${product.id}">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.134-2.036-2.134H8.718c-1.126 0-2.036.954-2.036 2.134v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" /></svg>
                </button>
            </div>
        `;
        productsListContainer.appendChild(productDiv);
    });
}

// --- الاستماع للتغييرات في قاعدة البيانات ---
db.collection("products").orderBy("createdAt", "desc").onSnapshot((snapshot) => {
    const products = snapshot.docs.map(doc => ({ id: doc.id, ...doc.data() }));
    renderProducts(products);
});

// --- وظيفة حفظ منتج جديد ---
saveButton.addEventListener('click', () => {
    const productName = productNameInput.value;
    const productDescription = productDescriptionInput.value;
    if (!productName || !productDescription) {
        alert("❌ الرجاء ملء اسم المنتج ووصفه.");
        return;
    }
    db.collection("products").add({
        name: productName,
        description: productDescription,
        createdAt: new Date()
    }).then(() => {
        productNameInput.value = '';
        productDescriptionInput.value = '';
    }).catch(error => console.error("خطأ في حفظ المنتج: ", error));
});

// --- وظائف الحذف والتعديل ---
productsListContainer.addEventListener('click', (e) => {
    const target = e.target.closest('.action-btn');
    if (!target) return;

    const id = target.getAttribute('data-id');
    if (target.classList.contains('btn-delete')) {
        if (confirm('هل أنت متأكد من أنك تريد حذف هذا المنتج؟')) {
            db.collection('products').doc(id).delete();
        }
    } else if (target.classList.contains('btn-edit')) {
        db.collection('products').doc(id).get().then(doc => {
            if (doc.exists) {
                const product = doc.data();
                editProductIdInput.value = doc.id;
                editProductNameInput.value = product.name;
                editProductDescriptionInput.value = product.description;
                editModalOverlay.style.display = 'flex';
            }
        });
    }
});

// --- وظائف نافذة التعديل ---
function closeModal() {
    editModalOverlay.style.display = 'none';
}

updateButton.addEventListener('click', () => {
    const id = editProductIdInput.value;
    db.collection("products").doc(id).update({
        name: editProductNameInput.value,
        description: editProductDescriptionInput.value
    }).then(() => {
        closeModal();
    }).catch(error => console.error("خطأ في تحديث المنتج: ", error));
});

closeModalButton.addEventListener('click', closeModal);
cancelModalButton.addEventListener('click', closeModal);
