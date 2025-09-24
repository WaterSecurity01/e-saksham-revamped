let RSA_PUBLIC_KEY = null;
let keyLoaded = false;

// Fetch public key on page load (async/await)
async function fetchPublicKey() {
    try {
        const response = await fetch('/api/decrypt_keys');
        if (!response.ok) throw new Error('Failed to fetch encryption keys');
        const data = await response.json();

        if (!data.publicKey) throw new Error('Public key missing in response');
        RSA_PUBLIC_KEY = data.publicKey;
        keyLoaded = true;
        console.log("✅ RSA Public key loaded");
    } catch (error) {
        console.error("❌ Error fetching encryption keys:", error);
        keyLoaded = false;
    }
}

// Encrypt a single password
function encryptPasswordRSA(plaintext) {
    if (!RSA_PUBLIC_KEY) throw new Error("Public key not loaded.");
    const encryptor = new JSEncrypt();
    encryptor.setPublicKey(RSA_PUBLIC_KEY);
    return encryptor.encrypt(plaintext);
}

// Encrypt all password fields before submit
function encryptAllPasswordFieldsRSA(form) {
    const passwordFields = form.querySelectorAll('input[type="password"]');
    passwordFields.forEach(field => {
        if (field.dataset.encrypted === "true") return; // prevent double encryption
        if (field.value.trim() !== "") {
            try {
                field.value = encryptPasswordRSA(field.value);
                field.dataset.encrypted = "true"; // mark as encrypted
            } catch (err) {
                console.error("❌ Encryption failed:", err);
                throw err;
            }
        }
    });
}

// Attach encryption to all forms
function attachEncryptionToForms() {
    document.querySelectorAll("form").forEach(form => {
        form.addEventListener("submit", async function (e) {
            e.preventDefault(); // always prevent default, handle via fetch

            if (!keyLoaded) {
                console.warn("⚠️ Encryption key not loaded. Try again later.");
                return;
            }

            try {
                encryptAllPasswordFieldsRSA(form);

                // ✅ Example fetch-based form submission
                const formData = new FormData(form);
                const response = await fetch(form.action, {
                    method: form.method || "POST",
                    body: formData
                });

                if (!response.ok) throw new Error("Form submission failed");

                console.log("✅ Form submitted successfully");
                // Optional: redirect or show success message
            } catch (err) {
                console.error("❌ Error during form submission:", err);
            }
        });
    });
}

// ✅ Initialize on page load
(async function init() {
    await fetchPublicKey();
    attachEncryptionToForms();
})();
