// =================================================
// استوديو المحتوى الذكي - النسخة النهائية مع مانوس
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
    let currentUserId = null;

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
    const navLinks = document.querySelectorAll('.sidebar-nav a');
    const pages = document.querySelectorAll('.page');
    const saveProductBtn = document.getElementById('save-product-btn');
    const productNameInput = document.getElementById('product-name-input');
    const productNotesInput = document.getElementById('product-notes-input');
    const productsTableBody = document.querySelector('#products-table tbody');
    const productIdInput = document.getElementById('product-id');
    const cancelEditBtn = document.getElementById('cancel-edit-btn');
    const imageUploadBtn = document.getElementById('image-upload-btn');
    const imagesPreviewContainer = document.getElementById('product-images-preview');
    const connectFacebookBtn = document.getElementById('connect-facebook-btn');
    const accountsTableBody = document.querySelector('#accounts-table tbody');
    let uploadedImageUrls = [];

    // --- رابط وظيفة مانوس (الجسر) ---
    // استبدل 'cheerful-lily-5c0d8e' باسم مشروعك على Netlify إذا كان مختلفًا
    const MANUS_FUNCTION_URL = 'https://cheerful-lily-5c0d8e.netlify.app/.netlify/functions/manus';

    // --- وظائف الواجهة العامة ---
    const showPage = (pageId) => {
        pages.forEach(page => page.classList.remove('active'));
        const targetPage = document.getElementById(pageId);
        if (targetPage) {
            targetPage.classList.add('active');
        }
        navLinks.forEach(link => {
            link.classList.toggle('active', link.dataset.page === pageId.replace('-page', ''));
        });
    };

    // --- وظائف إدارة المنتجات (مرتبطة بالمستخدم) ---
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
        if (!currentUserId) {
            productsTableBody.innerHTML = '<tr><td colspan="4" style="text-align: center;">الرجاء تسجيل الدخول لعرض المنتجات.</td></tr>';
            return;
        }
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
                row.dataset.productId = doc.id; // إضافة معرف المنتج للصف
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
        }
    };

    // --- وظائف ربط الحسابات (مرتبطة بالمستخدم) ---
    // (الكود الخاص بربط الحسابات يبقى كما هو)
    const renderAccounts = (accounts) => {
        accountsTableBody.innerHTML = '';
        if (!accounts || accounts.length === 0) {
            accountsTableBody.innerHTML = '<tr><td colspan="3" style="text-align: center;">لا توجد حسابات مرتبطة حاليًا.</td></tr>';
            return;
        }
        accounts.forEach(account => {
            const row = document.createElement('tr');
            const iconUrl = account.platform === 'Facebook' ? 'https://upload.wikimedia.org/wikipedia/commons/b/b9/2023_Facebook_icon.svg' : 'https://upload.wikimedia.org/wikipedia/commons/a/a5/Instagram_icon.png';
            row.innerHTML = `<td><img src="${iconUrl}" alt="${account.platform}" width="24" style="vertical-align: middle; margin-left: 8px;"> ${account.platform}</td><td>${account.name}</td><td><button class="btn-primary delete-account-btn" data-id="${account.docId}">حذف</button></td>`;
            accountsTableBody.appendChild(row);
        });
    };

    const fetchAndRenderAccounts = async () => {
        if (!currentUserId) return renderAccounts([]);
        try {
            const snapshot = await db.collection('users').doc(currentUserId).collection('accounts').orderBy('createdAt', 'desc').get();
            const accounts = snapshot.docs.map(doc => ({ ...doc.data(), docId: doc.id }));
            renderAccounts(accounts);
        } catch (error) {
            console.error("Firestore fetch error:", error);
            renderAccounts([]);
        }
    };
    
    const handleFacebookLogin = async () => {
        const provider = new firebase.auth.FacebookAuthProvider();
        provider.addScope('public_profile,email,pages_show_list,pages_manage_posts');
        try {
            await auth.signInWithRedirect(provider);
        } catch (error) {
            console.error("Redirect Error Start:", error);
        }
    };

    const handleRedirectResult = async () => {
        try {
            const result = await auth.getRedirectResult();
            if (result && result.credential && result.user) {
                const user = result.user;
                currentUserId = user.uid;
                const accessToken = result.credential.accessToken;
                const response = await fetch(`https://graph.facebook.com/v18.0/me/accounts?fields=name,access_token&access_token=${accessToken}`);
                const res = await response.json();

                if (res && res.data && res.data.length > 0) {
                    const batch = db.batch();
                    const accountsCollectionRef = db.collection('users').doc(currentUserId).collection('accounts');
                    res.data.forEach(page => {
                        const newAccountRef = accountsCollectionRef.doc(page.id);
                        batch.set(newAccountRef, {
                            platform: 'Facebook',
                            id: page.id,
                            name: page.name,
                            createdAt: firebase.firestore.FieldValue.serverTimestamp()
                        });
                    });
                    await batch.commit();
                    alert('✅ تم ربط الحسابات بنجاح!');
                    await fetchAndRenderAccounts();
                } else if (res.error) {
                    alert(`❌ خطأ من فيسبوك: ${res.error.message}`);
                } else {
                    alert("لم يتم العثور على أي صفحات فيسبوك مرتبطة بهذا الحساب.");
                }
            }
        } catch (error) {
            console.error("!!! CRITICAL REDIRECT ERROR !!!", error);
        }
    };

    // --- مراقبة حالة المصادقة ---
    auth.onAuthStateChanged(user => {
        if (user) {
            currentUserId = user.uid;
            fetchProducts();
            fetchAndRenderAccounts();
        } else {
            currentUserId = null;
            renderAccounts([]);
            fetchProducts();
        }
    });

    // --- ربط الأحداث ---
    navLinks.forEach(link => link.addEventListener('click', (e) => { e.preventDefault(); showPage(link.dataset.page + '-page'); }));
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
            if (!currentUserId) return alert('الرجاء تسجيل الدخول أولاً.');
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
            }
        });
    }
    if (productsTableBody) {
        productsTableBody.addEventListener('click', async (e) => {
            if (!currentUserId) return;
            const target = e.target;
            const id = target.dataset.id;
            const productRef = db.collection('users').doc(currentUserId).collection('products').doc(id);

            // --- منطق زر مانوس الجديد ---
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

                    if (!response.ok) {
                        throw new Error(`خطأ من مانوس: ${response.statusText}`);
                    }

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
                        showPage('products-page');
                        window.scrollTo(0, 0);
                    }
                } catch (error) { console.error(error); }
            }
        });
    }
    if (cancelEditBtn) cancelEditBtn.addEventListener('click', resetProductForm);
    if (connectFacebookBtn) connectFacebookBtn.addEventListener('click', handleFacebookLogin);
    if (accountsTableBody) {
        accountsTableBody.addEventListener('click', async (e) => {
            if (!currentUserId) return;
            if (e.target.classList.contains('delete-account-btn')) {
                const docId = e.target.dataset.id;
                if (confirm('هل أنت متأكد؟')) {
                    try {
                        await db.collection('users').doc(currentUserId).collection('accounts').doc(docId).delete();
                        fetchAndRenderAccounts();
                    } catch (error) { console.error(error); }
                }
            }
        });
    }

    // --- بدء تشغيل التطبيق ---
    showPage('dashboard-page');
    handleRedirectResult();
});
