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
    try {
        firebase.initializeApp(firebaseConfig);
        console.log("Firebase initialized successfully.");
    } catch (e) {
        console.error("Firebase initialization failed:", e);
        alert("فشل تهيئة قاعدة البيانات. يرجى المحاولة مرة أخرى.");
    }
    const db = firebase.firestore();

    // --- تهيئة Cloudinary ---
    const CLOUD_NAME = 'dbd04hozw';
    const UPLOAD_PRESET = 'Ai_content_studio';
    const cloudinaryWidget = cloudinary.createUploadWidget({ cloudName: CLOUD_NAME, uploadPreset: UPLOAD_PRESET, multiple: true, folder: 'ai_content_studio_products', language: 'ar' }, (error, result) => {
        if (!error && result && result.event === "success") addUploadedImage(result.info.secure_url);
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

    // --- وظائف الواجهة ---
    const showPage = (pageId) => {
        pages.forEach(page => page.classList.remove('active'));
        const targetPage = document.getElementById(pageId);
        if (targetPage) targetPage.classList.add('active');
        navLinks.forEach(link => link.classList.toggle('active', link.dataset.page === pageId.replace('-page', '')));
    };

    // --- وظائف إدارة المنتجات (بدون تغيير) ---
    const resetProductForm = () => { productNameInput.value = ''; productNotesInput.value = ''; productIdInput.value = ''; imagesPreviewContainer.innerHTML = ''; uploadedImageUrls = []; saveProductBtn.textContent = 'حفظ المنتج'; cancelEditBtn.style.display = 'none'; };
    const addUploadedImage = (url) => { uploadedImageUrls.push(url); const div = document.createElement('div'); div.className = 'img-preview-container'; div.innerHTML = `<img src="${url}" alt="صورة المنتج"><button class="remove-img-btn" data-url="${url}">&times;</button>`; imagesPreviewContainer.appendChild(div); };
    const fetchProducts = async () => { try { const snapshot = await db.collection('products').orderBy('createdAt', 'desc').get(); productsTableBody.innerHTML = ''; snapshot.forEach(doc => { const product = doc.data(); const row = document.createElement('tr'); row.innerHTML = `<td>${product.name}</td><td>${product.imageUrls ? product.imageUrls.length : 0} صورة</td><td><button class="btn-secondary edit-btn" data-id="${doc.id}">تعديل</button><button class="btn-primary delete-btn" data-id="${doc.id}">حذف</button></td>`; productsTableBody.appendChild(row); }); } catch (error) { console.error("Error fetching products: ", error); } };

    // --- وظائف ربط الحسابات (مُعاد كتابتها بالكامل) ---
    const renderAccounts = (accounts) => {
        console.log("Rendering accounts:", accounts);
        accountsTableBody.innerHTML = '';
        if (accounts.length === 0) {
            console.log("No accounts to render.");
            accountsTableBody.innerHTML = '<tr><td colspan="3" style="text-align: center;">لا توجد حسابات مرتبطة حاليًا.</td></tr>';
            return;
        }
        accounts.forEach(account => {
            const row = document.createElement('tr');
            const iconUrl = account.platform === 'Facebook' ? 'https://upload.wikimedia.org/wikipedia/commons/b/b9/2023_Facebook_icon.svg' : 'https://upload.wikimedia.org/wikipedia/commons/a/a5/Instagram_icon.png';
            row.innerHTML = `
                <td><img src="${iconUrl}" alt="${account.platform}" width="24" style="vertical-align: middle; margin-left: 8px;"> ${account.platform}</td>
                <td>${account.name}</td>
                <td><button class="btn-primary delete-account-btn" data-id="${account.docId}">حذف</button></td>
            `;
            accountsTableBody.appendChild(row);
        });
    };

    const fetchAndRenderAccounts = async () => {
        console.log("Attempting to fetch accounts from Firestore...");
        try {
            const snapshot = await db.collection('accounts').orderBy('createdAt', 'desc').get();
            console.log(`Firestore returned ${snapshot.docs.length} documents.`);
            const accounts = snapshot.docs.map(doc => ({ ...doc.data(), docId: doc.id }));
            renderAccounts(accounts);
        } catch (error) {
            console.error("CRITICAL: Failed to fetch accounts from Firestore:", error);
            alert("فشل في جلب الحسابات من قاعدة البيانات. تحقق من قواعد الأمان.");
            renderAccounts([]);
        }
    };

    const saveAccount = async (accountData) => {
        console.log("Attempting to save account:", accountData);
        try {
            await db.collection('accounts').add({ ...accountData, createdAt: firebase.firestore.FieldValue.serverTimestamp() });
            console.log("Account saved successfully:", accountData.name);
        } catch (error) {
            console.error("CRITICAL: Failed to save account to Firestore:", error);
            alert(`فشل حفظ حساب ${accountData.name}.`);
        }
    };

    // --- ربط الأحداث ---
    navLinks.forEach(link => link.addEventListener('click', (e) => { e.preventDefault(); showPage(link.dataset.page + '-page'); }));
    if (imageUploadBtn) imageUploadBtn.addEventListener('click', () => cloudinaryWidget.open());
    if (saveProductBtn) saveProductBtn.addEventListener('click', async () => { /* ... كود حفظ المنتج ... */ });
    if (productsTableBody) productsTableBody.addEventListener('click', async (e) => { /* ... كود تعديل/حذف المنتج ... */ });
    if (cancelEditBtn) cancelEditBtn.addEventListener('click', resetProductForm);

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
    if (connectFacebookBtn) connectFacebookBtn.disabled = true;
    window.fbAsyncInit = function() {
        FB.init({ appId: '758978576528127', cookie: true, xfbml: true, version: 'v19.0' });
        if (connectFacebookBtn) connectFacebookBtn.disabled = false;
        console.log("Facebook SDK initialized.");

        connectFacebookBtn.addEventListener('click', () => {
            console.log("Facebook connect button clicked.");
            const scope = 'email,public_profile,pages_show_list,pages_manage_posts,pages_manage_engagement,pages_read_engagement';
            FB.login(async (response) => {
                console.log("FB.login response:", response);
                if (response.authResponse) {
                    console.log("Authorization successful. Fetching accounts...");
                    FB.api('/me/accounts?fields=name,access_token,instagram_business_account{name,username}', async (res) => {
                        console.log("Facebook API response:", res);
                        if (res && !res.error) {
                            for (const page of res.data) {
                                await saveAccount({ platform: 'Facebook', id: page.id, name: page.name });
                                if (page.instagram_business_account) {
                                    await saveAccount({ platform: 'Instagram', id: page.instagram_business_account.id, name: page.instagram_business_account.username });
                                }
                            }
                            alert('✅ تمت مزامنة الحسابات بنجاح!');
                            await fetchAndRenderAccounts();
                        } else {
                            console.error('Facebook API Error:', res.error);
                            alert('حدث خطأ أثناء جلب صفحات فيسبوك.');
                        }
                    });
                } else {
                    console.log('User cancelled login or did not fully authorize.');
                }
            }, { scope });
        });
    };

    // --- بدء تشغيل التطبيق ---
    console.log("Application starting...");
    showPage('dashboard-page');
    fetchProducts();
    fetchAndRenderAccounts();
});
