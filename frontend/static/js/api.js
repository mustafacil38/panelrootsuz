const api = {
    async get(endpoint) {
        const token = localStorage.getItem('access_token');
        if (!token) { window.location.href = '/login.html'; return; }
        
        const res = await fetch(`/api${endpoint}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (res.status === 401) {
            window.location.href = '/login.html';
        }
        return res.json();
    },

    async post(endpoint, data = null) {
        const token = localStorage.getItem('access_token');
        if (!token) { window.location.href = '/login.html'; return; }
        
        const options = {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        };
        if (data) options.body = JSON.stringify(data);
        
        const res = await fetch(`/api${endpoint}`, options);
        if (res.status === 401) window.location.href = '/login.html';
        return res.json();
    },
    
    async delete(endpoint) {
        const token = localStorage.getItem('access_token');
        if (!token) { window.location.href = '/login.html'; return; }
        
        const res = await fetch(`/api${endpoint}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.status === 401) window.location.href = '/login.html';
        return res.json();
    }
};

function logout() {
    localStorage.removeItem('access_token');
    window.location.href = '/login.html';
}
