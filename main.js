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

    // --- عناصر الواجهة العامة ---
    const navLinks = document.querySelectorAll('.sidebar-nav a');
    const pages = document.querySelectorAll('.page');
    
    // --- عناصر واجهة إدارة المنتجات ---
    const saveProductBtn = document.getElementById('save-product-btn');
    const productNameInput = document.getElementById('product-name-input');
    const productNotesInput = document.getElementById('product-notes-input');
    const productsTableBody = document.querySelector('#products-table tbody');
    const productIdInput = document.getElementById('product-id');
    const cancelEditBtn = document.getElementById('cancel-edit-btn');
    const imageUploadBtn = document.getElementById('image-upload-btn');
    const imagesPreviewContainer = document.getElementById('product-images-preview');
    let uploadedImageUrls = [];

    // --- عناصر واجهة ربط الحسابات ---
    const connectFacebookBtn = document.getElementById('connect-facebook-btn');
    const accountsTableBody = document.querySelector('#accounts-table tbody');

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

    // --- وظائف ربط الحسابات ---
    const fetchAccounts = async () => {
        try {
            const snapshot = await db.collection('accounts').orderBy('createdAt', 'desc').get();
            accountsTableBody.innerHTML = '';
            snapshot.forEach(doc => {
                const account = doc.data();
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${account.platform}</td>
                    <td>${account.name}</td>
                    <td>
                        <button class="btn-primary delete-account-btn" data-id="${doc.id}">حذف</button>
                    </td>
                `;
                accountsTableBody.appendChild(row);
            });
        } catch (error) {
            console.error("Error fetching accounts: ", error);
        }
    };

    const saveAccountToFirestore = async (accountData) => {
        try {
            const existingAccountQuery = await db.collection('accounts')
                .where('platform', '==', accountData.platform)
                .where('id', '==', accountData.id)
                .get();

            if (existingAccountQuery.empty) {
                await db.collection('accounts').add({
                    ...accountData,
                    createdAt: firebase.firestore.FieldValue.serverTimestamp()
                });
                console.log(`${accountData.platform} account saved:`, accountData.name);
            } else {
                console.log(`${accountData.platform} account already exists:`, accountData.name);
            }
        } catch (error) {
            console.error("Error saving account to Firestore:", error);
        }
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
                    alert('✅ تم تحديث المنتج بنجاح!');
                } else {
                    productData.createdAt = firebase.firestore.FieldValue.serverTimestamp();
                    await db.collection('products').add(productData);
                    alert('✅ تم حفظ المنتج بنجاح!');
                }
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
                const id = e.target.dataset.id;
                if (confirm('هل أنت متأكد من حذف هذا الحساب؟')) {
                    try {
                        await db.collection('accounts').doc(id).delete();
                        alert('🗑️ تم حذف الحساب بنجاح.');
                        fetchAccounts();
                    } catch (error) { console.error("Error deleting account:", error); }
                }
            }
        });
    }

    // --- تهيئة Facebook SDK وبدء تشغيل التطبيق ---
    if (connectFacebookBtn) {
        connectFacebookBtn.disabled = true;
    }

    window.fbAsyncInit = function() {
        FB.init({
            appId: '758978576528127',
            cookie: true,
            xfbml: true,
            version: 'v19.0'
        });
        FB.AppEvents.logPageView();

        if (connectFacebookBtn) {
            connectFacebookBtn.disabled = false;
            connectFacebookBtn.addEventListener('click', () => {
                FB.login(response => {
                    if (response.authResponse) {
                        console.log('Welcome! Fetching your information.... ');
                        FB.api('/me/accounts?fields=name,access_token,instagram_business_account{name,username}', async (res) => {
                            if (res && !res.error) {
                                console.log('Pages and accounts:', res.data);
                                for (const page of res.data) {
                                    await saveAccountToFirestore({ platform: 'Facebook', id: page.id, name: page.name });
                                    if (page.instagram_business_account) {
                                        await saveAccountToFirestore({ platform: 'Instagram', id: page.instagram_business_account.id, name: page.instagram_business_account.username });
                                    }
                                }
                                alert('✅ تم ربط حسابات فيسبوك وإنستغرام بنجاح!');
                                fetchAccounts();
                            } else {
                                console.error('Error fetching pages:', res.error);
                            }
                        });
                    } else {
                        console.log('User cancelled login or did not fully authorize.');
                    }
                }, { 
                    // الكود يطلب فقط الأذونات المتاحة الآن
                    scope: 'pages_show_list,pages_manage_posts' 
                });
            });
        }
    };

    // --- بدء تشغيل التطبيق ---
    showPage('dashboard-page');
    fetchProducts();
    fetchAccounts();
});
