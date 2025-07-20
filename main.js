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
    const UPLOAD_PRESET = 'ml_default'; // سنحتاج لإنشاء هذا الإعداد في Cloudinary

    const cloudinaryWidget = cloudinary.createUploadWidget({
        cloudName: CLOUD_NAME,
        uploadPreset: UPLOAD_PRESET,
        multiple: true,
        folder: 'ai_content_studio_products',
        language: 'ar'
    }, (error, result) => {
        if (!error && result && result.event === "success") {
            const imageUrl = result.info.secure_url;
            addUploadedImage(imageUrl);
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

    let uploadedImageUrls = [];

    // --- وظائف الواجهة ---
    const showPage = (pageId) => {
        pages.forEach(page => page.classList.remove('active'));
        document.getElementById(pageId).classList.add('active');
        navLinks.forEach(link => {
            link.classList.toggle('active', link.dataset.page === pageId.replace('-page', ''));
        });
    };

    const resetForm = () => {
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

    // --- ربط الأحداث ---
    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            showPage(link.dataset.page + '-page');
        });
    });

    imageUploadBtn.addEventListener('click', () => {
        cloudinaryWidget.open();
    });

    imagesPreviewContainer.addEventListener('click', (e) => {
        if (e.target.classList.contains('remove-img-btn')) {
            const urlToRemove = e.target.dataset.url;
            uploadedImageUrls = uploadedImageUrls.filter(url => url !== urlToRemove);
            e.target.parentElement.remove();
        }
    });

    // --- وظائف Firestore ---
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

    saveProductBtn.addEventListener('click', async () => {
        const name = productNameInput.value.trim();
        const notes = productNotesInput.value.trim();
        const productId = productIdInput.value;

        if (!name) {
            alert('الرجاء إدخال اسم المنتج.');
            return;
        }

        const productData = {
            name: name,
            notes: notes,
            imageUrls: uploadedImageUrls,
            updatedAt: firebase.firestore.FieldValue.serverTimestamp()
        };

        try {
            if (productId) { // وضع التعديل
                await db.collection('products').doc(productId).update(productData);
                alert('✅ تم تحديث المنتج بنجاح!');
            } else { // وضع الإضافة
                productData.createdAt = firebase.firestore.FieldValue.serverTimestamp();
                await db.collection('products').add(productData);
                alert('✅ تم حفظ المنتج بنجاح!');
            }
            resetForm();
            fetchProducts();
        } catch (error) {
            console.error("Error saving product: ", error);
            alert('❌ حدث خطأ أثناء حفظ المنتج.');
        }
    });

    productsTableBody.addEventListener('click', async (e) => {
        const target = e.target;
        const id = target.dataset.id;

        if (target.classList.contains('delete-btn')) {
            if (confirm('هل أنت متأكد من أنك تريد حذف هذا المنتج؟')) {
                try {
                    await db.collection('products').doc(id).delete();
                    alert('🗑️ تم حذف المنتج بنجاح.');
                    fetchProducts();
                } catch (error) {
                    console.error("Error deleting product: ", error);
                }
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
            } catch (error) {
                console.error("Error fetching product for edit: ", error);
            }
        }
    });
    
    cancelEditBtn.addEventListener('click', resetForm);

    // --- بدء تشغيل التطبيق ---
    showPage('dashboard-page');
    fetchProducts();
});
