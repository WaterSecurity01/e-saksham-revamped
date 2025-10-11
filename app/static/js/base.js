
function resetSelect(sel, placeholder, disabled = true) {
        sel.innerHTML = '';
        const opt = document.createElement('option');
        opt.value = '';
        opt.textContent = placeholder;
        // Keep first option as placeholder to satisfy "selectedIndex is not zero" logic
        sel.appendChild(opt);
        sel.selectedIndex = 0;
        sel.disabled = !!disabled;
    }

// ---------- Loaders ----------
async function loadStates() {
    resetSelect($state, '— Loading States… —', true);
    resetSelect($district, '— Select District —', true);
    resetSelect($block, '— Select Block —', true);

    try {
    const states = await fetchJSON(ENDPOINTS.states);
    if (!states.length) {
        handleError($state, 'No states found');
        return;
    }
    populateSelect($state, states, '— Select State —');
    } catch (err) {
    handleError($state, 'Failed to load states');
    // console.error(err);
    }
}

async function loadDistricts(stateId) {
    // Cancel any in-flight districts request
    if (districtsAbort) districtsAbort.abort();
    districtsAbort = new AbortController();

    resetSelect($district, '— Loading Districts… —', true);
    resetSelect($block, '— Select Block —', true); // blocks depend on district

    try {
    const districts = await fetchJSON(ENDPOINTS.districts(stateId), { signal: districtsAbort.signal });
    if (!districts.length) {
        handleError($district, 'No districts found');
        return;
    }
    populateSelect($district, districts, '— Select District —');
    } catch (err) {
    if (err.name === 'AbortError') return; // selection changed; ignore
    handleError($district, 'Failed to load districts');
    // console.error(err);
    }
}

async function loadBlocks(districtId) {
    // Cancel any in-flight blocks request
    if (blocksAbort) blocksAbort.abort();
    blocksAbort = new AbortController();

    resetSelect($block, '— Loading Blocks… —', true);

    try {
    const blocks = await fetchJSON(ENDPOINTS.blocks(districtId), { signal: blocksAbort.signal });
    if (!blocks.length) {
        handleError($block, 'No blocks found');
        return;
    }
    populateSelect($block, blocks, '— Select Block —');
    } catch (err) {
    if (err.name === 'AbortError') return; // selection changed; ignore
    handleError($block, 'Failed to load blocks');
    // console.error(err);
    }
}

// Fetch public key on page load (async/await)
async function fetchPublicKey() {
    try {
        const response = await fetch('/api/decrypt_keys');
        if (!response.ok) throw new Error('Failed to fetch encryption keys');
        const data = await response.json();

        if (!data.publicKey) throw new Error('Public key missing in response');
        RSA_PUBLIC_KEY = data.publicKey;
        keyLoaded = true;
        console.log("RSA Public key loaded");
    } catch (error) {
        console.error("Error fetching encryption keys:", error);
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
                console.error("Encryption failed:", err);
                throw err;
            }
        }
    });
}

function showLoader() {
    var loader = document.querySelector('.loader');
    loader.classList.remove('loader-hidden');
}
function hideLoader() {
    var loader = document.querySelector('.loader');
    loader.classList.add('loader-hidden');
}