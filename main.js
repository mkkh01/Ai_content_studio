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

    // --- وظائف إدارة المنتجات ---
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
        imgContainer.innerHTML = `
            <img src="${url}" alt="صورة المنتج">
            <button class="remove-img-btn" data-url="${url}">&times;</button>
        `;
        imagesPreviewContainer.appendChild(imgContainer);
    };

    const fetchProducts = async () => {
        try {
            const snapshot = await db.collection('products').orderBy('createdAt', 'desc').get();
            productsTableBody.innerHTML = '';
            snapshot.forEach(doc => {
                const product = doc.data();
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${product.name}</td>
                    <td>${product.imageUrls ? product.imageUrls.length : 0} صورة</td>
                    <td>
                        <button class="btn-secondary edit-btn" data-id="${doc.id}">تعديل</button>
                        <button class="btn-primary delete-btn" data-id="${doc.id}">حذف</button>
                    </td>
                `;
                productsTableBody.appendChild(row);
            });
        } catch (error) {
            console.error("Error fetching products: ", error);
        }
    };

    // --- وظائف ربط الحسابات (مبسطة ومحسنة) ---
    const renderAccounts = (accounts) => {
        accountsTableBody.innerHTML = '';
        if (!accounts || accounts.length === 0) {
            accountsTableBody.innerHTML = '<tr><td colspan="3" style="text-align: center;">لا توجد حسابات مرتبطة حاليًا.</td></tr>';
            return;
        }
        accounts.forEach(account => {
            const row = document.createElement('tr');
            const iconUrl = account.platform === 'Facebook' 
                ? 'https://upload.wikimedia.org/wikipedia/commons/b/b9/2023_Facebook_icon.svg' 
                : 'https://upload.wikimedia.org/wikipedia/commons/a/a5/Instagram_icon.png';
            row.innerHTML = `
                <td><img src="${iconUrl}" alt="${account.platform}" width="24" style="vertical-align: middle; margin-left: 8px;"> ${account.platform}</td>
                <td>${account.name}</td>
                <td><button class="btn-primary delete-account-btn" data-id="${account.docId}">حذف</button></td>
            `;
            accountsTableBody.appendChild(row);
        });
    };

    const fetchAndRenderAccounts = async () => {
        try {
            const snapshot = await db.collection('accounts').orderBy('createdAt', 'desc').get();
            const accounts = snapshot.docs.map(doc => ({ ...doc.data(), docId: doc.id }));
            renderAccounts(accounts);
        } catch (error) {
            console.error("Firestore fetch error:", error);
            renderAccounts([]); // عرض جدول فارغ في حالة الخطأ
        }
    };

    // --- وظيفة الربط الرئيسية ---
    const handleFacebookLogin = () => {
        const scope = 'email,public_profile,pages_show_list,pages_manage_posts,pages_manage_engagement,pages_read_engagement';
        FB.login(async (response) => {
            if (response.authResponse) {
                FB.api('/me/accounts?fields=name,access_token,instagram_business_account{name,username}', async (res) => {
                    if (res && !res.error) {
                        // مسح الحسابات القديمة قبل إضافة الجديدة لمنع التكرار
                        const oldAccounts = await db.collection('accounts').get();
                        for (const doc of oldAccounts.docs) {
                            await db.collection('accounts').doc(doc.id).delete();
                        }

                        // إضافة الحسابات الجديدة
                        for (const page of res.data) {
                            await db.collection('accounts').add({ platform: 'Facebook', id: page.id, name: page.name, createdAt: firebase.firestore.FieldValue.serverTimestamp() });
                            if (page.instagram_business_account) {
                                await db.collection('accounts').add({ platform: 'Instagram', id: page.instagram_business_account.id, name: page.instagram_business_account.username, createdAt: firebase.firestore.FieldValue.serverTimestamp() });
                            }
                        }
                        alert('✅ تم ربط الحسابات بنجاح!');
                        await fetchAndRenderAccounts();
                    } else {
                        console.error("Facebook API Error:", res.error);
                        alert('حدث خطأ أثناء جلب صفحات فيسبوك.');
                    }
                });
            } else {
                console.log('User cancelled login or did not fully authorize.');
            }
        }, { scope });
    };

    // --- ربط الأحداث ---
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            showPage(link.dataset.page + '-page');
        });
    });

    // أحداث إدارة المنتجات
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
            try {
                if (productId) {
                    await db.collection('products').doc(productId).update(productData);
                } else {
                    productData.createdAt = firebase.firestore.FieldValue.serverTimestamp();
                    await db.collection('products').add(productData);
                }
                alert('✅ تم حفظ المنتج بنجاح!');
                resetProductForm();
                fetchProducts();
            } catch (error) {
                console.error("Error saving product: ", error);
                alert('❌ حدث خطأ أثناء حفظ المنتج.');
            }
        });
    }
    if (productsTableBody) {
        productsTableBody.addEventListener('click', async (e) => {
            const target = e.target;
            const id = target.dataset.id;
            if (target.classList.contains('delete-btn')) {
                if (confirm('هل أنت متأكد من أنك تريد حذف هذا المنتج؟')) {
                    try {
                        await db.collection('products').doc(id).delete();
                        alert('🗑️ تم حذف المنتج بنجاح.');
                        fetchProducts();
                    } catch (error) { console.error("Error deleting product: ", error); }
                }
            }
            if (target.classList.contains('edit-btn')) {
                try {
                    const doc = await db.collection('products').doc(id).get();
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
                } catch (error) { console.error("Error fetching product for edit: ", error); }
            }
        });
    }
    if (cancelEditBtn) cancelEditBtn.addEventListener('click', resetProductForm);

    // أحداث ربط الحسابات
    if (accountsTableBody) {
        accountsTableBody.addEventListener('click', async (e) => {
            if (e.target.classList.contains('delete-account-btn')) {
                const docId = e.target.dataset.id;
                if (confirm('هل أنت متأكد من حذف هذا الحساب؟')) {
                    try {
                        await db.collection('accounts').doc(docId).delete();
                        alert('🗑️ تم حذف الحساب بنجاح.');
                        fetchAndRenderAccounts();
                    } catch (error) { console.error("Error deleting account:", error); }
                }
            }
        });
    }

    // --- تهيئة Facebook SDK ---
    window.fbAsyncInit = function() {
        FB.init({
            appId: '758978576528127',
            cookie: true,
            xfbml: true,
            version: 'v19.0'
        });
        // ربط الحدث بعد التهيئة مباشرة لضمان أن الـ SDK جاهز
        if (connectFacebookBtn) {
            connectFacebookBtn.addEventListener('click', handleFacebookLogin);
        }
    };

    // --- بدء تشغيل التطبيق ---
    showPage('dashboard-page');
    fetchProducts();
    fetchAndRenderAccounts();
});
