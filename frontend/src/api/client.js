const API_BASE = 'http://localhost:8000';

async function request(method, path, { body, params, auth = true, multipart = false } = {}) {
    const url = new URL(`${API_BASE}${path}`);
    if (params) {
        Object.entries(params).forEach(([k, v]) => {
            if (v !== undefined && v !== null) url.searchParams.set(k, v);
        });
    }

    const headers = {};
    if (auth) {
        const token = localStorage.getItem('fanforge_jwt');
        if (token) headers['Authorization'] = `Bearer ${token}`;
    }

    const opts = { method, headers };
    if (body) {
        if (multipart) {
            opts.body = body; // FormData — browser sets Content-Type with boundary
        } else {
            headers['Content-Type'] = 'application/json';
            opts.body = JSON.stringify(body);
        }
    }

    const res = await fetch(url.toString(), opts);
    const data = await res.json().catch(() => null);

    if (!res.ok) {
        const msg = data?.error?.message || data?.detail || data?.error || `HTTP ${res.status}`;
        const err = new Error(msg);
        err.status = res.status;
        err.data = data;
        throw err;
    }

    return data;
}

export const api = {
    get: (path, opts) => request('GET', path, opts),
    post: (path, body, opts) => request('POST', path, { body, ...opts }),
    patch: (path, body, opts) => request('PATCH', path, { body, ...opts }),
    delete: (path, opts) => request('DELETE', path, opts),
    upload: (path, formData, opts) => request('POST', path, { body: formData, multipart: true, ...opts }),
};
