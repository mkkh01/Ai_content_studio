document.addEventListener('DOMContentLoaded', () => {
    // --- تهيئة Firebase ---
    // تأكد من أن هذه البيانات صحيحة ومطابقة لمشروعك في Firebase
    const firebaseConfig = {
        apiKey: "AIzaSyAmjrlrjus3lXBsOqCY0xwowahjPOl4XFc",
        authDomain: "aicontentstudio-4a0fd.firebaseapp.com",
        projectId: "aicontentstudio-4a0fd",
        storageBucket: "aicontentstudio-4a0fd.appspot.com",
        messagingSenderId: "212059531856",
        appId: "1:212059531856:web:cf259c0a3c73b6bec87f55"
    };
    
    // استخدام وضع التوافق (compat)
    firebase.initializeApp(firebaseConfig);
    const db = firebase.firestore();
    const auth = firebase.auth();
    console.log("Firebase Initialized (Compat Mode).");

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

    // --- وظائف ربط الحسابات (مع رسائل تشخيص) ---
    const renderAccounts = (accounts) => {
        console.log("Rendering accounts:", accounts);
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
        console.log("Fetching accounts from Firestore...");
        try {
            const snapshot = await db.collection('accounts').orderBy('createdAt', 'desc').get();
            const accounts = snapshot.docs.map(doc => ({ ...doc.data(), docId: doc.id }));
            console.log("Accounts fetched successfully:", accounts);
            renderAccounts(accounts);
        } catch (error) {
            console.error("Firestore fetch error:", error);
            renderAccounts([]);
        }
    };

    const handleFacebookLogin = async () => {
        console.log("Facebook connect button clicked. Starting redirect flow...");
        const provider = new firebase.auth.FacebookAuthProvider();
        // طلب الأذونات اللازمة
        provider.addScope('email');
        provider.addScope('public_profile');
        provider.addScope('pages_show_list');
        provider.addScope('pages_manage_posts');
        provider.addScope('pages_read_engagement');
        provider.addScope('instagram_basic');
        provider.addScope('instagram_content_publish');

        try {
            await auth.signInWithRedirect(provider);
        } catch (error) {
            console.error("Redirect Error Start:", error);
            alert(`❌ حدث خطأ قبل إعادة التوجيه: ${error.message}`);
        }
    };

    const handleRedirectResult = async () => {
        console.log("Checking for redirect result...");
        try {
            const result = await auth.getRedirectResult();
            console.log("Redirect result object:", result);

            if (result && result.credential) {
                console.log("Redirect result contains credential. Proceeding...");
                const accessToken = result.credential.accessToken;
                console.log("Access Token obtained.");

                // جلب صفحات فيسبوك وحسابات انستغرام المرتبطة بها
                const response = await fetch(`https://graph.facebook.com/v19.0/me/accounts?fields=name,access_token,instagram_business_account{name,username}&access_token=${accessToken}`);
                const res = await response.json();
                console.log("Graph API response:", res);

                if (res && !res.error) {
                    console.log("Graph API call successful. Deleting old accounts...");
                    const oldAccounts = await db.collection('accounts').get();
                    const deletePromises = oldAccounts.docs.map(doc => db.collection('accounts').doc(doc.id).delete());
                    await Promise.all(deletePromises);
                    console.log("Old accounts deleted. Adding new accounts...");

                    const addPromises = [];
                    for (const page of res.data) {
                        // إضافة صفحة فيسبوك
                        addPromises.push(db.collection('accounts').add({ 
                            platform: 'Facebook', 
                            id: page.id, 
                            name: page.name, 
                            createdAt: firebase.firestore.FieldValue.serverTimestamp() 
                        }));
                        console.log(`Added Facebook page: ${page.name}`);
                        
                        // إضافة حساب انستغرام إذا كان موجودًا
                        if (page.instagram_business_account) {
                            addPromises.push(db.collection('accounts').add({ 
                                platform: 'Instagram', 
                                id: page.instagram_business_account.id, 
                                name: page.instagram_business_account.username, 
                                createdAt: firebase.firestore.FieldValue.serverTimestamp() 
                            }));
                            console.log(`Added Instagram account: ${page.instagram_business_account.username}`);
                        }
                    }
                    await Promise.all(addPromises);
                    alert('✅ تم ربط الحسابات بنجاح!');
                    await fetchAndRenderAccounts();
                    showPage('accounts-page'); // الانتقال إلى صفحة الحسابات لعرض النتيجة
                } else {
                    console.error("Graph API Error:", res.error);
                    alert(`حدث خطأ أثناء جلب صفحات فيسبوك: ${res.error.message}`);
                }
            } else {
                console.log("No redirect result found. This is normal on initial page load.");
            }
        } catch (error) {
            console.error("!!! CRITICAL REDIRECT ERROR !!!", error);
            alert(`❌ حدث خطأ فادح بعد إعادة التوجيه: ${error.message}`);
        }
    };

    // --- ربط الأحداث ---
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            showPage(link.dataset.page + '-page');
        });
    });

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
            
            const productData = { 
                name, 
                notes, 
                imageUrls: uploadedImageUrls, 
                updatedAt: firebase.firestore.FieldValue.serverTimestamp() 
            };

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

    if (connectFacebookBtn) {
        connectFacebookBtn.addEventListener('click', handleFacebookLogin);
    }

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

    // --- بدء تشغيل التطبيق ---
    const startApp = async () => {
        console.log("App Starting...");
        const urlParams = new URLSearchParams(window.location.search);
        const page = urlParams.get('page');

        // تحقق مما إذا كنا قادمين من إعادة توجيه OAuth
        // هذا الشرط يساعد في تجنب إعادة تنفيذ الكود عند كل تحميل للصفحة
        if (window.location.pathname.includes('__/auth/handler')) {
             await handleRedirectResult();
        } else {
             await fetchAndRenderAccounts();
        }
        
        fetchProducts();

        if (page) {
            showPage(page + '-page');
        } else {
            showPage('dashboard-page');
        }
        console.log("App Started.");
    };

    startApp();
});
