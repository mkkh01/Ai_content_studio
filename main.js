// =================================================
// استوديو المحتوى - النسخة النهائية مع تسجيل دخول مخصص
// =================================================
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
    const db = firebase.firestore();
    const auth = firebase.auth();
    let currentUserId = "admin_user"; // معرف ثابت للمستخدم الوحيد

    // --- تهيئة Cloudinary ---
    const CLOUD_NAME = 'dbd04hozw';
    const UPLOAD_PRESET = 'Ai_content_studio';
    const cloudinaryWidget = cloudinary.createUploadWidget({
        cloudName: CLOUD_NAME,
        uploadPreset: UPLOAD_PRESET,
        multiple: true,
        folder: 'ai_content_studio_products',
        language: 'ar'
    }, (error, result) => {
        if (!error && result && result.event === "success") {
            addUploadedImage(result.info.secure_url);
        }
    });

    // --- عناصر الواجهة ---
    const loginContainer = document.getElementById('login-container');
    const dashboardMain = document.getElementById('dashboard-main');
    const loginBtn = document.getElementById('login-btn');
    const logoutBtn = document.getElementById('logout-btn');
    const usernameInput = document.getElementById('username-input');
    const passwordInput = document.getElementById('password-input');
    const loginError = document.getElementById('login-error');
    
    const saveProductBtn = document.getElementById('save-product-btn');
    const productNameInput = document.getElementById('product-name-input');
    const productNotesInput = document.getElementById('product-notes-input');
    const productsTableBody = document.querySelector('#products-table tbody');
    const productIdInput = document.getElementById('product-id');
    const cancelEditBtn = document.getElementById('cancel-edit-btn');
    const imageUploadBtn = document.getElementById('image-upload-btn');
    const imagesPreviewContainer = document.getElementById('product-images-preview');
    
    let uploadedImageUrls = [];

    // --- رابط وظيفة مانوس (الجسر) ---
    const MANUS_FUNCTION_URL = 'https://cheerful-lily-5c0d8e.netlify.app/.netlify/functions/manus';

    // --- وظائف تسجيل الدخول ---
    const showDashboard = () => {
        loginContainer.style.display = 'none';
        dashboardMain.style.display = 'flex';
        fetchProducts();
    };

    const showLogin = () => {
        loginContainer.style.display = 'flex';
        dashboardMain.style.display = 'none';
        sessionStorage.removeItem('manus_logged_in');
    };

    loginBtn.addEventListener('click', () => {
        const username = usernameInput.value;
        const password = passwordInput.value;
        if (username === 'admin' && password === '12345') {
            sessionStorage.setItem('manus_logged_in', 'true');
            showDashboard();
        } else {
            loginError.style.display = 'block';
        }
    });

    logoutBtn.addEventListener('click', (e) => {
        e.preventDefault();
        showLogin();
    });

    // التحقق من حالة تسجيل الدخول عند تحميل الصفحة
    if (sessionStorage.getItem('manus_logged_in') === 'true') {
        showDashboard();
    } else {
        showLogin();
    }

    // --- وظائف إدارة المنتجات (مرتبطة بـ Firebase) ---
    const resetProductForm = () => {
        productNameInput.value = '';
        productNotesInput.value = '';
        productIdInput.value = '';
        imagesPreviewContainer.innerHTML = '';
        uploadedImageUrls = [];
        saveProductBtn.textContent = 'حفظ المنتج';
        cancelEditBtn.style.display = 'none';
    };

    const addUploadedImage = (url) => {
        uploadedImageUrls.push(url);
        const imgContainer = document.createElement('div');
        imgContainer.className = 'img-preview-container';
        imgContainer.innerHTML = `<img src="${url}" alt="صورة المنتج"><button class="remove-img-btn" data-url="${url}">&times;</button>`;
        imagesPreviewContainer.appendChild(imgContainer);
    };

    const fetchProducts = async () => {
        try {
            const snapshot = await db.collection('users').doc(currentUserId).collection('products').orderBy('createdAt', 'desc').get();
            productsTableBody.innerHTML = '';
            if (snapshot.empty) {
                productsTableBody.innerHTML = '<tr><td colspan="4" style="text-align: center;">لم تقم بإضافة أي منتجات بعد.</td></tr>';
                return;
            }
            snapshot.forEach(doc => {
                const product = doc.data();
                const row = document.createElement('tr');
                row.dataset.productId = doc.id;
                row.innerHTML = `
                    <td>${product.name}</td>
                    <td>${product.imageUrls ? product.imageUrls.length : 0} صورة</td>
                    <td>
                        <button class="btn-secondary edit-btn" data-id="${doc.id}">تعديل</button>
                        <button class="btn-primary delete-btn" data-id="${doc.id}">حذف</button>
                        <button class="btn-manus" data-id="${doc.id}">🚀 اطلب محتوى من مانوس</button>
                    </td>
                    <td class="manus-result" id="manus-result-${doc.id}" style="display:none;"></td>
                `;
                productsTableBody.appendChild(row);
            });
        } catch (error) {
            console.error("Error fetching products: ", error);
            productsTableBody.innerHTML = `<tr><td colspan="4" style="text-align: center;">خطأ في جلب البيانات: ${error.message}</td></tr>`;
        }
    };

    // --- ربط الأحداث ---
    if (imageUploadBtn) imageUploadBtn.addEventListener('click', () => cloudinaryWidget.open());
    if (imagesPreviewContainer) {
        imagesPreviewContainer.addEventListener('click', (e) => {
            if (e.target.classList.contains('remove-img-btn')) {
                const urlToRemove = e.target.dataset.url;
                uploadedImageUrls = uploadedImageUrls.filter(url => url !== urlToRemove);
                e.target.parentElement.remove();
            }
        });
    }
    if (saveProductBtn) {
        saveProductBtn.addEventListener('click', async () => {
            const name = productNameInput.value.trim();
            const notes = productNotesInput.value.trim();
            const productId = productIdInput.value;
            if (!name) return alert('الرجاء إدخال اسم المنتج.');
            
            const productData = { name, notes, imageUrls: uploadedImageUrls, updatedAt: firebase.firestore.FieldValue.serverTimestamp() };
            const productCollection = db.collection('users').doc(currentUserId).collection('products');
            
            try {
                if (productId) {
                    await productCollection.doc(productId).update(productData);
                } else {
                    productData.createdAt = firebase.firestore.FieldValue.serverTimestamp();
                    await productCollection.add(productData);
                }
                alert('✅ تم حفظ المنتج بنجاح!');
                resetProductForm();
                fetchProducts();
            } catch (error) {
                console.error("Error saving product: ", error);
                alert(`حدث خطأ أثناء الحفظ: ${error.message}`);
            }
        });
    }
    if (productsTableBody) {
        productsTableBody.addEventListener('click', async (e) => {
            const target = e.target;
            const id = target.dataset.id;
            if (!id) return;

            const productRef = db.collection('users').doc(currentUserId).collection('products').doc(id);

            if (target.classList.contains('btn-manus')) {
                const manusResultCell = document.getElementById(`manus-result-${id}`);
                manusResultCell.style.display = 'table-cell';
                manusResultCell.innerHTML = '🧠 مانوس يفكر...';
                
                try {
                    const doc = await productRef.get();
                    if (!doc.exists) throw new Error("Product not found");
                    
                    const product = doc.data();
                    const response = await fetch(MANUS_FUNCTION_URL, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            productName: product.name,
                            productNotes: product.notes
                        })
                    });

                    if (!response.ok) throw new Error(`خطأ من مانوس: ${response.statusText}`);

                    const manusData = await response.json();
                    manusResultCell.innerHTML = `
                        <p><strong>النص المقترح:</strong> ${manusData.postText}</p>
                        <p><strong>الهاشتاجات:</strong> ${manusData.hashtags.join(' ')}</p>
                    `;

                } catch (error) {
                    console.error("Manus Error:", error);
                    manusResultCell.innerHTML = `حدث خطأ: ${error.message}`;
                }
            }

            if (target.classList.contains('delete-btn')) {
                if (confirm('هل أنت متأكد؟')) {
                    try { await productRef.delete(); fetchProducts(); } catch (error) { console.error(error); }
                }
            }
            if (target.classList.contains('edit-btn')) {
                try {
                    const doc = await productRef.get();
                    if (doc.exists) {
                        const product = doc.data();
                        productNameInput.value = product.name;
                        productNotesInput.value = product.notes || '';
                        productIdInput.value = id;
                        imagesPreviewContainer.innerHTML = '';
                        uploadedImageUrls = product.imageUrls || [];
                        uploadedImageUrls.forEach(addUploadedImage);
                        saveProductBtn.textContent = 'حفظ التعديلات';
                        cancelEditBtn.style.display = 'inline-block';
                        window.scrollTo(0, 0);
                    }
                } catch (error) { console.error(error); }
            }
        });
    }
    if (cancelEditBtn) cancelEditBtn.addEventListener('click', resetProductForm);
});
